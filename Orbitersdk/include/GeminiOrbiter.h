// SPDX-License-Identifier: BSD-3-Clause
#pragma once
#ifdef GEMINI_NATIVE_ORBITER
#include "NativeVesselAPI.h"
#include "DrawAPI.h"
#include "Production/NativeVesselFactory.h"
#include "Production/NativeRenderApi.h"
#include "Production/FlightKeys.h"
#include <algorithm>
#include <cmath>
#include <cstring>
#include <strings.h>
#include <type_traits>
using DWORD = oapi::UInt32;
using UINT = oapi::UInt;
using WORD = oapi::UInt16;
using BYTE = unsigned char;
using RECT = oapi::SdkRectangle;
using HBITMAP = SURFHANDLE;
inline constexpr bool TRUE=true, FALSE=false;
#define DLLCLBK extern "C"
#define _strnicmp strncasecmp
#define stricmp strcasecmp
#define strnicmp strncasecmp
template<class A,class B> constexpr auto min(A a,B b)
{ using C=std::common_type_t<A,B>; return std::min(C(a),C(b)); }
template<class A,class B> constexpr auto max(A a,B b)
{ using C=std::common_type_t<A,B>; return std::max(C(a),C(b)); }
inline void oapiSetAttitudeMode(OBJHANDLE h,int mode) {oapiGetVesselInterface(h)->SetAttitudeMode(mode);}
inline int oapiGetFocusAirspeed(double* value) {return oapiGetAirspeed(oapiGetFocusObject(),value);}
inline int oapiGetFocusPitch(double* value) {return oapiGetPitch(oapiGetFocusObject(),value);}
void oapiCameraSetAperture(double);
SURFHANDLE GeminiBitmap(int id);
// Gemini predates the modern surface colour-key API.
inline void GeminiBlt(SURFHANDLE target,SURFHANDLE source,int x,int y,int sx,int sy,int width,int height,DWORD key=SURF_NO_CK)
{
 if (key!=SURF_NO_CK) oapiSetSurfaceColourKey(source,key);
 ::oapiBlt(target,source,x,y,sx,sy,width,height);
}
#define oapiBlt GeminiBlt

#define MAKEINTRESOURCE(id) (id)
#define LoadBitmap(module,id) GeminiBitmap(id)
inline SURFHANDLE oapiCreateSurface(SURFHANDLE bitmap) { return bitmap; }
#else
#include <Orbitersdk.h>
#endif
