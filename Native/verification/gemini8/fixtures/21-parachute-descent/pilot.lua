local plan={["mode"]="coast",["duration"]=599.75}
-- SPDX-License-Identifier: BSD-3-Clause
-- Test pilot: original manual controls only. No state, fuel or docking overrides.
local v=vessel.get_interface('GEMINI')
local agena=vessel.get_interface('GATV')
local earth=v:get_gravityref()
if plan.stabilize_target then agena:set_navmode(1,true) end
local function add(a,b)return{x=a.x+b.x,y=a.y+b.y,z=a.z+b.z}end
local function scale(a,s)return{x=a.x*s,y=a.y*s,z=a.z*s}end
local function sub(a,b)return add(a,scale(b,-1))end
local function dot(a,b)return a.x*b.x+a.y*b.y+a.z*b.z end
local function cross(a,b)return{x=a.y*b.z-a.z*b.y,y=a.z*b.x-a.x*b.z,z=a.x*b.y-a.y*b.x}end
local function norm(a)return math.sqrt(dot(a,a))end
local function unit(a)return scale(a,1/math.max(norm(a),1e-12))end
local function array(a)return{x=a[1],y=a[2],z=a[3]}end
local function clamp(x,a,b)return math.max(a,math.min(b,x))end
local function localvec(R,a)return{x=R.m11*a.x+R.m21*a.y+R.m31*a.z,y=R.m12*a.x+R.m22*a.y+R.m32*a.z,z=R.m13*a.x+R.m23*a.y+R.m33*a.z}end
local function globalvec(R,a)return{x=R.m11*a.x+R.m12*a.y+R.m13*a.z,y=R.m21*a.x+R.m22*a.y+R.m23*a.z,z=R.m31*a.x+R.m32*a.y+R.m33*a.z}end
local start=oapi.get_simtime()
local last=start
local dv=plan.dv and array(plan.dv) or {x=0,y=0,z=0}
local remaining=dv
local totaldv={x=0,y=0,z=0}
local logfile=assert(io.open('pilot.csv','w'))
logfile:write('seconds,range,relative_speed,attitude_error,remaining_dv,wx,wy,wz,fuel,mode\n')
local nextlog=0
local mode=(plan.mode=='coast' or plan.mode=='undock') and 7 or 5
local selector_changed=false
local fired={}
-- Alt-1..7 operates the original control-panel selector.
oapi.simulatebufferedkey(1+mode,0x38)
v:set_rcsmode(1)
proc.skip()
if plan.mode=='undock' then
 oapi.simulatebufferedkey(0x26);proc.skip()
 oapi.simulatebufferedkey(0x24);proc.skip()
end
local burn_started=false
local burn_complete=false
local steering=false
local attitude_complete=false
while oapi.get_simtime()-start < plan.duration and not wait_exit do
 local now=oapi.get_simtime()
 local t=now-start
 local dt=now-last;last=now
 for index,command in ipairs(plan.commands or {}) do
  if not fired[index] and t>=command.at then
   oapi.simulatebufferedkey(command.key,unpack(command.modifiers or {}));fired[index]=true
  end
 end
 if plan.mode=='undock' and t>=(plan.backoff_seconds or 20) and not selector_changed then oapi.simulatebufferedkey(6,0x38);selector_changed=true end
 if plan.mode=='terminal' and v:get_dockstatus(v:get_dockhandle(0)) then
  oapi.simulatebufferedkey(8,0x38)
  local docked=assert(io.open('pilot-docked.txt','w'));docked:write(string.format('%.9f\n',t));docked:close();break
 end
 local R=v:get_rotationmatrix()
 local r=v:get_relativepos(earth)
 local velocity=v:get_relativevel(earth)
 local ar=agena:get_relativepos(earth)
 local av=agena:get_relativevel(earth)
 local rel=sub(ar,r);local rv=sub(av,velocity)
 local omega=v:get_angvel()
 if plan.mode=='burn' and dt>0 and not burn_complete then
  local thrust=globalvec(R,v:get_thrustvector())
  totaldv=add(totaldv,scale(thrust,dt/v:get_mass()))
  remaining=sub(dv,totaldv)
  if norm(remaining)<(plan.tolerance or .08) then burn_complete=true;oapi.simulatebufferedkey(8,0x38) end
 end
 local desired=plan.direction and array(plan.direction) or unit(velocity)
 if plan.retrograde then desired=scale(unit(velocity),-1) end
 local up=scale(unit(r),plan.lift_up and -1 or 1)
 if plan.control_until_altitude and norm(r)-6371010 < plan.control_until_altitude and not attitude_complete then
  attitude_complete=true;oapi.simulatebufferedkey(8,0x38)
 end
 local acceleration=nil
 if plan.mode=='burn' and norm(remaining)>.015 then desired=unit(remaining) end
 if plan.mode=='terminal' then
  local AR=agena:get_rotationmatrix()
  local port,dir,rot=agena:get_dockparams(agena:get_dockhandle(0))
  desired=scale(globalvec(AR,dir),-1)
  up=globalvec(AR,rot)
  local ownport=v:get_dockparams(v:get_dockhandle(0))
  local offset=add(port,scale(dir,plan.standoff or 0))
  local goal=sub(add(ar,globalvec(AR,offset)),globalvec(R,ownport))
  local error=sub(goal,r)
  local maxspeed=plan.maxspeed or 1
  local target=scale(error,plan.position_gain or .01)
  if plan.lateral_gain then
   local e=localvec(AR,error)
   target=globalvec(AR,{x=e.x*plan.lateral_gain,y=e.y*plan.lateral_gain,z=e.z*(plan.position_gain or .01)})
  end
  if norm(target)>maxspeed then target=scale(unit(target),maxspeed)end
  local aomega=agena:get_angvel()
  local goalvelocity=add(av,globalvec(AR,cross(offset,aomega)))
  local mu=3.98600435507e14
  local gravitydifference=sub(scale(ar,-mu/norm(ar)^3),scale(r,-mu/norm(r)^3))
  acceleration=add(gravitydifference,scale(sub(add(goalvelocity,target),velocity),plan.velocity_gain or .1))
 end
 local d=localvec(R,unit(desired))
 local u=localvec(R,unit(up))
 local error={x=math.atan2(d.y,d.z),y=-math.atan2(d.x,math.sqrt(d.y*d.y+d.z*d.z)),z=math.atan2(u.x,u.y)}
 local attitude_error=math.acos(clamp(d.z,-1,1))
 local keys={}
 if plan.mode~='coast' and not burn_complete and not attitude_complete and not (plan.mode=='undock' and t<(plan.backoff_seconds or 20)) then
  local function axis(e,w,positive,negative,alpha)
   local rate=clamp(e*.2,-(plan.maxrate or .07),(plan.maxrate or .07))
   local request=rate-w
   local deadband=.6*alpha*math.max(dt,.03125)+.0008
   if request>deadband then keys[#keys+1]=positive elseif request<-deadband then keys[#keys+1]=negative end
  end
  axis(error.x,omega.x,0x50,0x48,plan.angular_acceleration or .10)
  axis(error.y,omega.y,0x4f,0x51,plan.angular_acceleration or .10)
  if plan.mode~='burn' then axis(error.z,omega.z,0x4d,0x4b,plan.angular_acceleration or .10) end
 end
 if plan.mode=='burn' then
  if attitude_error>.015 then steering=true elseif attitude_error<.007 and math.abs(omega.x)<.006 and math.abs(omega.y)<.006 then steering=false end
  if not steering then keys={} end
 end
 if plan.mode=='undock' and t<(plan.backoff_seconds or 20) then
  v:set_rcsmode(2);oapi.simulateimmediatekey(0x49)
 elseif plan.mode=='burn' and not burn_complete and norm(remaining)<2 then
  local trim=localvec(R,remaining);keys={}
  local function trimaxis(value,positive,negative)
   if value>.02 then keys[#keys+1]=positive elseif value<-.02 then keys[#keys+1]=negative end
  end
  trimaxis(trim.x,0x51,0x4f);trimaxis(trim.y,0x50,0x48);trimaxis(trim.z,0x4d,0x49)
  v:set_rcsmode(2)
  if #keys>0 then oapi.simulateimmediatekey(unpack(keys))end
 elseif #keys>0 then
  v:set_rcsmode(1)
  oapi.simulateimmediatekey(unpack(keys))
 elseif plan.mode=='burn' and not burn_complete and t>=(plan.not_before or 0) and norm(remaining)>.03 and attitude_error<.025 then
  v:set_rcsmode(2)
  oapi.simulateimmediatekey(0x4d)
  burn_started=true
 elseif plan.mode=='terminal' and acceleration and attitude_error<.03 then
  v:set_rcsmode(2)
  local a=localvec(R,acceleration)
  local function translation(value,pos,neg)
   local deadband=plan.acceleration_deadband or .003
   if value>deadband then keys[#keys+1]=pos elseif value<-deadband then keys[#keys+1]=neg end
  end
  translation(a.x,0x51,0x4f)
  translation(a.y,0x50,0x48)
  translation(a.z,0x4d,0x49)
  if #keys>0 then oapi.simulateimmediatekey(unpack(keys))end
 end
 if t>=nextlog then
  logfile:write(string.format('%.6f,%.9f,%.9f,%.9f,%.9f,%.9f,%.9f,%.9f,%.9f,%s\n',t,norm(rel),norm(rv),attitude_error,norm(remaining),omega.x,omega.y,omega.z,v:get_propellantmass(v:get_propellanthandle(0)),plan.mode))
  logfile:flush();nextlog=t+1
 end
 proc.skip()
end
logfile:close()
local dvfile=assert(io.open('applied-dv.csv','w'));dvfile:write(string.format('%.12f,%.12f,%.12f\n',totaldv.x,totaldv.y,totaldv.z));dvfile:close()
local result=assert(io.open('pilot-complete.txt','w'));result:write('complete\n');result:close()
