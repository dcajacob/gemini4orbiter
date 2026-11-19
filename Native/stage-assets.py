#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Install Gemini assets into a complete native Orbiter runtime, safely with hardlinks."""
from pathlib import Path
import shutil,sys
source=Path(__file__).resolve().parents[1]
runtime=Path(sys.argv[1]).resolve()
def copy(src,dest):
 dest.parent.mkdir(parents=True,exist_ok=True)
 dest.unlink(missing_ok=True);shutil.copy2(src,dest)
for folder in ['Meshes','Textures','Scenarios']:
 for f in (source/folder).rglob('*'):
  if f.is_file():copy(f,runtime/'resources'/f.relative_to(source))
for f in (source/'Config').glob('*.cfg'):
 if f.name not in ['Base.cfg','Earth.cfg']:copy(f,runtime/'resources/Config'/f.name)
for f in (source/'Config/Earth/BaseGemini').glob('*.cfg'):copy(f,runtime/'resources/Config/Earth/BaseGemini'/f.name)
for f in (source/'Orbitersdk/Project Gemini/Gemini_Titan').glob('*.bmp'):copy(f,runtime/'resources/Textures/Gemini'/f.name)
earth=runtime/'resources/Config/Earth.cfg';text=earth.read_text()
if 'DIR Earth\\BaseGemini CONTEXT Gemini' not in text:
 text=text.replace('BEGIN_SURFBASE','BEGIN_SURFBASE\nDIR Earth\\BaseGemini CONTEXT Gemini',1)
 earth.unlink();earth.write_text(text)
copy(source/'Gemini_Titan2_45.pdf',runtime/'Gemini_Titan2_45.pdf')
copy(source/'LICENSE',runtime/'licenses/Gemini-BSD-3-Clause.txt')
keymap=runtime/'Keymap.cfg';keymap.unlink(missing_ok=True)
keymap.write_text('; Standard Orbiter defaults preserve Gemini letter commands.\n')
