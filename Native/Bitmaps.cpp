// SPDX-License-Identifier: BSD-3-Clause
#include "GeminiOrbiter.h"
#include "../Orbitersdk/Project Gemini/Gemini_Titan/resource.h"
SURFHANDLE GeminiBitmap(int id)
{
 const char* name=nullptr;
 switch(id) {
 case IDB_WINDOWCDR: name="Gemini/GeminiCdr.bmp"; break;
 case IDB_WINDOWPLT: name="Gemini/GeminiPlt.bmp"; break;
 case IDB_CDRPANEL: name="Gemini/CDRPanel.bmp"; break;
 case IDB_ADIPANEL: name="Gemini/adipanel.bmp"; break;
 case IDB_RATEHORZ: name="Gemini/RateHorz.bmp"; break;
 case IDB_RATEVERT: name="Gemini/RateVert.bmp"; break;
 case IDB_RATEROLL: name="Gemini/RateRoll.bmp"; break;
 case IDB_LOWCENTERPNL: name="Gemini/lower_center.bmp"; break;
 case IDB_KNOBSQ: name="Gemini/gem_sq_knob.bmp"; break;
 default: return nullptr;
 }
 return oapiLoadSurfaceEx(name,0);
}

#include "Production/NativeGraphics.h"
#include "Camera.h"
void oapiCameraSetAperture(double value)
{if(auto* camera=orbiter::production::GetNativeRenderContext().camera)camera->SetAperture(value);}
