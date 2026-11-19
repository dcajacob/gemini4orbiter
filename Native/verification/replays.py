#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Run original Gemini scenarios with declared native input replays and evidence."""
from pathlib import Path
import csv,json,math,subprocess,sys
runtime=Path(sys.argv[1]).resolve()
output=Path(sys.argv[2]).resolve();output.mkdir(parents=True,exist_ok=True)
cases=[
 ('ascent','Earth 1962/Gemini III.scn',9600,.0625,[(0,'main',1)]),
 ('orbit-operations','Project Gemini/Gemini Orbit.scn',960,.0625,[(0,'key',48),(1,'key',-48),(100,'key',77),(132,'key',-77)]),
 ('agena-undock','Project Gemini/Gemini Docked.scn',480,.0625,[(0,'key',38),(1,'key',-38),(16,'key',36),(17,'key',-36)]),
 ('eva','Project Gemini/Gemini Orbit.scn',960,.0625,[(0,'key',25),(1,'key',-25),(160,'key',18),(161,'key',-18)]),
 ('pad-abort','Earth 1962/Gemini III.scn',160,.0625,[(0,'key',18),(1,'key',-18)]),
 ('reentry','Project Gemini/Gemini Reentry.scn',19200,.125,[]),
]
if len(sys.argv)>3:cases=[c for c in cases if c[0] in sys.argv[3:]]
results=[]
for name,scenario,ticks,step,commands in cases:
 case=output/name;case.mkdir(parents=True,exist_ok=True)
 commands.append((ticks-1,'save',0))
 replay=case/'replay.csv'
 with replay.open('w') as f:
  f.write('tick,phase,action,value\n')
  for tick,action,value in commands:f.write(f'{tick},before,{action},{value}\n')
 args=[str(runtime/'engine/run-orbiter'),'--assets',str(runtime/'resources'),'--data',str(runtime/'celestial-data'),'--modules',str(runtime/'engine/NativeModules'),'--planets',str(runtime/'planet-archives'),'--config',str(runtime/'Orbiter.cfg'),'--keymap',str(runtime/'Keymap.cfg'),'--xrsound-assets',str(runtime/'resources'),'--scenario',str(runtime/'resources/Scenarios'/scenario),'--save',str(case/'saved.scn'),'--replay',str(replay),'--ticks',str(ticks),'--run','--fixed-step',str(step),'--render-every','1024','--evidence',str(case/'evidence')]
 with (case/'console.log').open('w') as log:subprocess.run(args,cwd=case,stdout=log,stderr=subprocess.STDOUT,check=True)
 assert (case/'saved.scn').is_file(),(name,'missing final save')
 rows=list(csv.DictReader((case/'evidence/flight-state.csv').open()))
 final=[r for r in rows if int(r['tick'])==ticks]
 by_name={r['object']:r for r in final}
 assert final and all(math.isfinite(float(r[k])) for r in final for k in ['altitude_mean','airspeed','mass','fuel'])
 saved=(case/'saved.scn').read_text()
 if name=='orbit-operations':
  assert 'Gemini-BEACON' in by_name and float(by_name['Gemini']['fuel'])<419.9
 elif name=='agena-undock':
  assert not by_name['GEMINI']['dock'] and not by_name['GATV']['dock']
 elif name=='eva':
  assert by_name['Gemini-PLT']['focus']=='Gemini-PLT'
 elif name=='pad-abort':
  assert 'Molly-Brown-CDR' in by_name and 'Molly-Brown-PLT' in by_name
 elif name=='reentry':
  assert by_name['GEMINI']['ground']=='1' and float(by_name['GEMINI']['airspeed'])<1
  for key in ['DROGUE_DEPLOYED','MAIN_DEPLOYED','MAIN_JETTISONED']:assert key+' 1.0' in saved
 elif name=='ascent':
  r=by_name['Molly-Brown'];assert r['ground']=='0'
  xyz=[float(r[k]) for k in ['rx','ry','rz']];velocity=[float(r[k]) for k in ['vx','vy','vz']]
  mu=3.98600435507e14 # Earth DE440 GM used by the qualified runtime
  radius=math.sqrt(sum(x*x for x in xyz));speed2=sum(x*x for x in velocity)
  a=1/(2/radius-speed2/mu)
  h=[xyz[1]*velocity[2]-xyz[2]*velocity[1],xyz[2]*velocity[0]-xyz[0]*velocity[2],xyz[0]*velocity[1]-xyz[1]*velocity[0]]
  eccentricity=math.sqrt(1-sum(x*x for x in h)/(mu*a))
  assert a*(1-eccentricity)-6371010>180000 and a*(1+eccentricity)-6371010<500000
 result=dict(case=name,scenario=scenario,ticks=ticks,step=step,final=[{k:r[k] for k in ['object','altitude_mean','airspeed','mass','fuel','ground','dock','focus']} for r in final])
 results.append(result);(output/'results.json').write_text(json.dumps(results,indent=2)+'\n');print(json.dumps(result),flush=True)
