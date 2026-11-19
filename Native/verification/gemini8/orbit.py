# SPDX-License-Identifier: BSD-3-Clause
"""Two-body planning estimates; all flown motion comes from native Orbiter."""
import math,re
from pathlib import Path
import numpy as np
from scipy.optimize import root
MU=3.98600435507e14

def state(path,name):
 text=Path(path).read_text();b=re.search(r'^'+re.escape(name)+r':[^\n]*\n(.*?)^END$',text,re.M|re.S)[1]
 return np.array([float(v) for tag in ['RPOS','RVEL'] for v in re.search(r'^\s*'+tag+r' (.*)$',b,re.M)[1].split()])

def stumpff(z):
 if abs(z)<1e-6:return .5-z/24+z*z/720,1/6-z/120+z*z/5040
 if z>0:
  q=math.sqrt(z);return (1-math.cos(q))/z,(q-math.sin(q))/(q*q*q)
 q=math.sqrt(-z);return (1-math.cosh(q))/z,(math.sinh(q)-q)/(q*q*q)

def propagate(y,dt):
 r0=np.linalg.norm(y[:3]);v0=y[3:];vr=np.dot(y[:3],v0)/r0;alpha=2/r0-np.dot(v0,v0)/MU;sq=math.sqrt(MU)
 chi=sq*dt*alpha if alpha>0 else sq*dt/r0
 for _ in range(100):
  z=alpha*chi*chi;c,s=stumpff(z)
  f=r0*vr/sq*chi*chi*c+(1-alpha*r0)*chi**3*s+r0*chi-sq*dt
  fp=r0*vr/sq*chi*(1-z*s)+(1-alpha*r0)*chi*chi*c+r0
  change=f/fp;chi-=change
  if abs(change)<1e-8:break
 else:raise ValueError('Kepler solver did not converge')
 z=alpha*chi*chi;c,s=stumpff(z);f=1-chi*chi/r0*c;g=dt-chi**3/sq*s;r=f*y[:3]+g*v0;rad=np.linalg.norm(r)
 fd=sq/(rad*r0)*(alpha*chi**3*s-chi);gd=1-chi*chi/rad*c
 return np.r_[r,fd*y[:3]+gd*v0]

def transfer(chaser,target,dt):
 destination=propagate(target,dt)
 def residual(delta):
  try:return (propagate(np.r_[chaser[:3],chaser[3:]+delta],dt)[:3]-destination[:3])/1e5
  except (ValueError,OverflowError):return np.array([1e6,1e6,1e6])
 solution=root(residual,np.zeros(3),tol=1e-9)
 if np.linalg.norm(residual(solution.x))>1e-5:raise ValueError('Transfer targeting failed')
 final=propagate(np.r_[chaser[:3],chaser[3:]+solution.x],dt)
 return solution.x,destination[3:]-final[3:]


def finite_transfer(chaser,target,dt,acceleration=.20):
 from scipy.integrate import solve_ivp
 target_state=propagate(target,dt)
 guess,_=transfer(chaser,target,dt)
 def trajectory(delta):
  length=np.linalg.norm(delta)
  duration=length/acceleration
  if duration>=dt:raise ValueError('Burn exceeds transfer duration')
  direction=delta/max(length,1e-12)
  def rhs(t,y):return np.r_[y[3:],-MU*y[:3]/np.linalg.norm(y[:3])**3+acceleration*direction]
  burned=solve_ivp(rhs,[0,duration],chaser,rtol=1e-10,atol=1e-6).y[:,-1]
  return propagate(burned,dt-duration)
 def residual(delta):return (trajectory(delta)[:3]-target_state[:3])/1e5
 result=root(residual,guess,tol=1e-8)
 if np.linalg.norm(residual(result.x))>1e-5:raise ValueError('Finite transfer failed')
 return result.x,target_state[3:]-trajectory(result.x)[3:]


def rendezvous(chaser,target,dt,acceleration=.20):
 from scipy.integrate import solve_ivp
 destination=propagate(target,dt)
 initial,final=finite_transfer(chaser,target,dt,acceleration)
 def burn(y,dv):
  length=np.linalg.norm(dv);duration=length/acceleration
  if duration<1e-8:return y,duration
  direction=dv/length
  def rhs(t,y):return np.r_[y[3:],-MU*y[:3]/np.linalg.norm(y[:3])**3+acceleration*direction]
  return solve_ivp(rhs,[0,duration],y,rtol=2e-10,atol=1e-6).y[:,-1],duration
 def trajectory(x):
  y,t1=burn(chaser,x[:3]);t2=np.linalg.norm(x[3:])/acceleration
  if t1+t2>dt:raise ValueError('Rendezvous burns overlap')
  y=propagate(y,dt-t1-t2);y,_=burn(y,x[3:]);return y
 def residual(x):
  y=trajectory(x);return np.r_[(y[:3]-destination[:3])/1e5,(y[3:]-destination[3:])/100]
 solution=root(residual,np.r_[initial,final],tol=2e-8)
 if np.linalg.norm(residual(solution.x))>1e-5:raise ValueError('Rendezvous targeting failed')
 return solution.x[:3],solution.x[3:]

def match_velocity(chaser,target,guess,delay=35,acceleration=.20):
 from scipy.integrate import solve_ivp
 start=propagate(chaser,delay)
 def trajectory(delta):
  length=np.linalg.norm(delta);duration=length/acceleration;direction=delta/length
  def rhs(t,y):return np.r_[y[3:],-MU*y[:3]/np.linalg.norm(y[:3])**3+acceleration*direction]
  y=solve_ivp(rhs,[0,duration],start,rtol=2e-10,atol=1e-6).y[:,-1]
  return y,propagate(target,delay+duration)
 def residual(delta):
  g,a=trajectory(delta);return (g[3:]-a[3:])/100
 result=root(residual,guess,tol=1e-9)
 if np.linalg.norm(residual(result.x))>1e-5:raise ValueError('Velocity matching failed')
 g,a=trajectory(result.x)
 return result.x,float(np.linalg.norm(g[:3]-a[:3]))
