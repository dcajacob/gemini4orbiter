#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Replay frozen Gemini VIII checkpoints through the real native engine.

Each selected phase starts from its recorded input. This is a regression runner,
not a claim that one fixed guidance plan remains valid after arbitrary physics changes.
"""
import argparse,json,re,shutil,subprocess
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('runtime',type=Path);p.add_argument('output',type=Path)
p.add_argument('phases',nargs='*');a=p.parse_args()
r=a.runtime.resolve();fixtures=Path(__file__).with_name('fixtures')
for fixture in sorted(fixtures.iterdir()):
 if a.phases and fixture.name not in a.phases:continue
 record=json.loads((fixture/'record.json').read_text())
 case=a.output.resolve()/fixture.name;case.mkdir(parents=True,exist_ok=True)
 for name in ['input.scn','replay.csv']:shutil.copy2(fixture/name,case/name)
 if (fixture/'pilot.lua').exists():
  script=re.search(r'^\s*Script (\S+)',(fixture/'input.scn').read_text(),re.M)[1]
  target=r/'resources/Script'/f'{script}.lua';target.parent.mkdir(parents=True,exist_ok=True)
  target.unlink(missing_ok=True);shutil.copy2(fixture/'pilot.lua',target)
 ticks=round(record['seconds']/record['step'])
 args=[str(r/'engine/run-orbiter'),'--assets',str(r/'resources'),'--data',str(r/'celestial-data'),'--modules',str(r/'engine/NativeModules'),'--planets',str(r/'planet-archives'),'--config',str(r/'Orbiter.cfg'),'--keymap',str(r/'Keymap.cfg'),'--xrsound-assets',str(r/'resources'),'--scenario','input.scn','--save','saved.scn','--replay','replay.csv','--ticks',str(ticks),'--run','--fixed-step',str(record['step']),'--render-every','4096','--evidence','evidence']
 (case/'saved.scn').unlink(missing_ok=True)
 (case/'pilot-docked.txt').unlink(missing_ok=True)
 with (case/'console.log').open('w') as log:subprocess.run(args,cwd=case,stdout=log,stderr=subprocess.STDOUT,check=True)
 saved=(case/'saved.scn').read_text()
 assert 'END_SHIPS' in saved
 if fixture.name=='13-docking':assert 'DOCKINFO 0:0,GATV' in saved and 'pilot-docked.txt' in {f.name for f in case.iterdir()}
 if fixture.name=='22-splashdown':
  gemini=re.search(r'^GEMINI:.*?^END$',saved,re.M|re.S)[0]
  assert 'STATUS Landed Earth' in gemini and 'MAIN_JETTISONED 1.0' in gemini
 (case/'saved.scn').write_text(re.sub(r'^\s*Script .*\n','',saved,flags=re.M))
 print(fixture.name,'passed',flush=True)
