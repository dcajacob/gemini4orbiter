#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Audit frozen flight lineage and optional native telemetry for the flown chain."""
import argparse,csv,hashlib,json,re
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path);a=p.parse_args()
root=Path(__file__).resolve().parent;ledger=json.loads((root/'flight-ledger.json').read_text())
previous=None
for item in ledger:
 f=root/'fixtures'/item['phase']
 for name,field in [('input.scn','input_sha256'),('saved.scn','output_sha256')]:
  assert hashlib.sha256((f/name).read_bytes()).hexdigest()==item[field],(f,name)
 if previous:
  assert item['parent_output_sha256']==previous['output_sha256']
  ships=lambda text:re.search(r'BEGIN_SHIPS\n.*END_SHIPS',text,re.S)[0]
  assert ships((f/'input.scn').read_text())==ships((root/'fixtures'/previous['phase']/'saved.scn').read_text())
 if (f/'pilot.lua').exists():assert hashlib.sha256((f/'pilot.lua').read_bytes()).hexdigest()==item['pilot_sha256']
 if a.evidence:
  data=a.evidence/item['phase']/'evidence/flight-state.csv'
  assert hashlib.sha256(data.read_bytes()).hexdigest()==item['evidence_state_sha256']
 previous=item
assert len(ledger)==22
assert ledger[12]['docked_to']=='GATV'
assert ledger[-1]['ground_contact'] and ledger[-1]['final_speed_m_s']<1
assert 19<ledger[-1]['latitude_deg']<21 and 141<ledger[-1]['longitude_deg']<143
assert ledger[-1]['contact_speed_m_s']<8 and ledger[-1]['fuel_index0_kg']>30
assert 4<ledger[19]['peak_drag_g']<8
if a.evidence:
 with (a.evidence/'19-entry-attitude/evidence/flight-state.csv').open() as file:
  row=next(r for r in csv.DictReader(file) if r['object']=='GEMINI' and float(r['seconds'])>0)
  assert float(row['drag'])/float(row['dynamic_pressure'])>2.5,'Backward drag regressed'
print('22 connected phases audited; real Agena docking and Pacific splashdown verified')
