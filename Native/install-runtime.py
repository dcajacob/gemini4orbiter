#!/usr/bin/env python3
"""Overlay a complete matching engine, renderer and Gemini build on a stock runtime."""
from pathlib import Path
import shutil,sys
engine,addon,runtime=map(Path,sys.argv[1:])
def copy(source,target):
 target.parent.mkdir(parents=True,exist_ok=True)
 target.unlink(missing_ok=True)
 shutil.copy2(source,target)
for name in ['orbiter-production','liborbiter_production_boundary.so','liborbiter_production_vessels.so','liborbiter_native_atlantis.so']:
 if (engine/name).exists():copy(engine/name,runtime/'engine'/name)
for folder in ['native-sdk','NativeModules','native-lua']:
 for f in (engine/folder).rglob('*'):
  if f.is_file() and (folder!='native-lua' or f.name.startswith('liblua.so')):copy(f,runtime/'engine'/f.relative_to(engine))
for f in (addon/'NativeModules').rglob('*.so'):copy(f,runtime/'engine'/f.relative_to(addon))
