#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Run a Gemini VIII continuation, changing only scenario script metadata."""
import argparse,hashlib,json,re,shutil,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('runtime',type=Path);p.add_argument('case',type=Path);p.add_argument('input',type=Path);p.add_argument('--seconds',type=float,required=True);p.add_argument('--step',type=float,default=.125);p.add_argument('--plan',type=Path);p.add_argument('--pilot',type=Path);a=p.parse_args()
r=a.runtime.resolve();case=a.case.resolve();case.mkdir(parents=True,exist_ok=True)
(case/'pilot-complete.txt').unlink(missing_ok=True)
(case/'saved.scn').unlink(missing_ok=True)
src=a.input.resolve();original=src.read_text();text=re.sub(r'^\s*Script .*\n','',original,flags=re.M)
text=re.sub(r'BEGIN_MFD[^\n]*\n.*?END_MFD\n','',text,flags=re.S)
assert re.search(r'BEGIN_SHIPS\n.*END_SHIPS',original,re.S)[0]==re.search(r'BEGIN_SHIPS\n.*END_SHIPS',text,re.S)[0]
plan=json.loads(a.plan.read_text()) if a.plan else {'mode':'coast'}
plan['duration']=a.seconds-2*a.step
scriptname='Gemini8/'+case.name
text=text.replace('BEGIN_ENVIRONMENT\n','BEGIN_ENVIRONMENT\n  Script '+scriptname+'\n',1)
(case/'input.scn').write_text(text)
def lua(value):
 if isinstance(value,dict):return '{'+','.join('['+json.dumps(k)+']='+lua(v) for k,v in value.items())+'}'
 if isinstance(value,list):return '{'+','.join(map(lua,value))+'}'
 if isinstance(value,bool):return 'true' if value else 'false'
 if value is None:return 'nil'
 return json.dumps(value)
pilot=(a.pilot or Path(__file__).with_name('pilot.lua')).read_text();target=r/'resources/Script'/f'{scriptname}.lua';target.parent.mkdir(exist_ok=True,parents=True);target.unlink(missing_ok=True);target.write_text(pilot if a.pilot else 'local plan='+lua(plan)+'\n'+pilot)
(case/'pilot.lua').write_bytes(target.read_bytes())
ticks=round(a.seconds/a.step);assert abs(ticks*a.step-a.seconds)<1e-8
(case/'replay.csv').write_text(f'tick,phase,action,value\n{ticks-1},after,save,0\n')
(case/'chain.json').write_text(json.dumps({'input':str(src),'input_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'pilot_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'only_metadata_changed':True,'plan':plan,'seconds':a.seconds,'step':a.step},indent=2)+'\n')
args=[str(r/'engine/run-orbiter'),'--assets',str(r/'resources'),'--data',str(r/'celestial-data'),'--modules',str(r/'engine/NativeModules'),'--planets',str(r/'planet-archives'),'--config',str(r/'Orbiter.cfg'),'--keymap',str(r/'Keymap.cfg'),'--xrsound-assets',str(r/'resources'),'--scenario','input.scn','--save','saved.scn','--replay','replay.csv','--ticks',str(ticks),'--run','--fixed-step',str(a.step),'--render-every','4096','--evidence','evidence']
with (case/'console.log').open('w') as log:subprocess.run(args,cwd=case,stdout=log,stderr=subprocess.STDOUT,check=True)
assert (case/'saved.scn').exists(),(case/'console.log').read_text()[-2000:]
assert (case/'pilot-complete.txt').exists(),(case/'console.log').read_text()[-2000:]
raw=(case/'saved.scn').read_text()
(case/'engine-save.scn').write_text(raw)
(case/'saved.scn').write_text(re.sub(r'^\s*Script .*\n','',raw,flags=re.M))
print(case.name,'saved',flush=True)
