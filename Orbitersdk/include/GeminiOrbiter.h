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
// Legacy Gemini requests a fresh anonymous group with THGROUP_USER each time.
// Current Orbiter requires a distinct explicit index for each custom group.
inline THGROUP_HANDLE GeminiUserThrusterGroup(VESSEL* vessel,THRUSTER_HANDLE* thrusters,int count)
{
 return vessel->CreateThrusterGroup(thrusters,count,static_cast<THGROUP_TYPE>(THGROUP_USER+vessel->GetUserThrusterGroupCount()));
}
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
inline THGROUP_HANDLE GeminiUserThrusterGroup(VESSEL* vessel,THRUSTER_HANDLE* thrusters,int count)
{ return vessel->CreateThrusterGroup(thrusters,count,THGROUP_USER); }
#endif
