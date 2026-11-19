// SPDX-License-Identifier: BSD-3-Clause
#pragma once
#include "GeminiOrbiter.h"
#include "Production/NativeGraphics.h"
#include <stdexcept>
// Native surface drawing; no private WGL context or desktop GDI handles.
class ADI {
public:
 int ScrX,ScrY;
 vector3 target{};
 SURFHANDLE ball=nullptr;
 std::vector<std::uint8_t> pixels=std::vector<std::uint8_t>(130*130*4,0);
 ADI(int x,int y):ScrX(x),ScrY(y){}
 ~ADI() {if(ball)oapiDestroySurface(ball);}
 void RegisterMe(int index) {oapiRegisterPanelArea(index,_R(ScrX,ScrY,ScrX+212,ScrY+212),PANEL_REDRAW_ALWAYS,PANEL_MOUSE_IGNORE,PANEL_MAP_CURRENT);}
 void RegisterVC(int index,SURFHANDLE targetSurface) {oapiVCRegisterArea(index,_R(ScrX,ScrY,ScrX+212,ScrY+212),PANEL_REDRAW_ALWAYS,PANEL_MOUSE_IGNORE,PANEL_MAP_CURRENT,targetSurface);}
 void SetOrbital(VESSEL* vessel);
 void PaintMe(VESSEL* vessel,SURFHANDLE surface,SURFHANDLE* borders) {
  SetOrbital(vessel);
  if(!ball)ball=oapiCreateSurface(130,130);
  // Inverse of the original sphere's heading, pitch, roll rotations.
  for (int y=0;y<130;++y) for(int x=0;x<130;++x) {
   double a=(x-64.5)/64.5,b=(64.5-y)/64.5,q=1-a*a-b*b;
   if(q<0)continue;
   double c=std::sqrt(q);
   double u=a*std::cos(target.z)+b*std::sin(target.z);
   double v=-a*std::sin(target.z)+b*std::cos(target.z);
   double w=c*std::cos(target.y)-v*std::sin(target.y);
   v=c*std::sin(target.y)+v*std::cos(target.y);
   double longitude=std::atan2(u,w)+target.x;
   double latitude=std::asin(std::clamp(v,-1.0,1.0));
   const bool line=std::abs(std::remainder(longitude,PI/6))<0.015 || std::abs(std::remainder(latitude,PI/6))<0.015;
   auto color=std::uint8_t(line?0xdd:(latitude>=0?0x30:0x8c));
   auto index=4*(y*130+x);pixels[index]=pixels[index+1]=pixels[index+2]=color;pixels[index+3]=255;
  }
  auto* renderer=orbiter::production::GetNativeRenderContext().graphics;
  if(!renderer || !renderer->UploadSurfacePixels(ball,130,130,pixels))throw std::runtime_error("Gemini ADI surface upload failed");
  oapiBlt(surface,ball,42,40,0,0,130,130);
  oapiBlt(surface,borders[0],0,0,0,0,212,212,0xffffff);
  VECTOR3 rates;vessel->GetAngularVel(rates);
  auto rate=[](double v,int range,int offset){return int(std::clamp(v/(PI/12),-1.0,1.0)*range+offset);};
  oapiBlt(surface,borders[1],66,rate(-rates.x,60,104),0,0,80,3,0xffffff);
  oapiBlt(surface,borders[2],rate(-rates.y,60,105),64,0,0,3,80,0xffffff);
  oapiBlt(surface,borders[3],rate(rates.z,38,103),31,0,0,7,8,0xffffff);
 }
};
void ADI::SetOrbital(VESSEL *vessel)//this is quite heavy. API could use a way to get orientation w.r.t. orbit
{
	OBJHANDLE planet=vessel->GetGravityRef();
	VECTOR3 gpos,pos,vel,vel2;
	vector3 Vpos,Vvel,Vnorm;
	vessel->GetGlobalPos(gpos);
	vessel->GetRelativePos(planet,pos);
	vessel->GetRelativeVel(planet,vel);
	Vpos=_vector3(pos.x,pos.y,pos.z);
	Vnorm=_vector3(vel.x,vel.y,vel.z);
	Vnorm=Vpos*Vnorm;//this is normal on orbital plane;
	Vnorm.selfnormalize();
 
	vel.x+=gpos.x;vel.y+=gpos.y;vel.z+=gpos.z;
	vessel->Global2Local(vel,vel2);
	Vvel=_vector3(vel2.x,vel2.y,vel2.z);//this is V vector in local frame
	Vvel.selfnormalize();
	Vnorm.x+=gpos.x;Vnorm.y+=gpos.y;Vnorm.z+=gpos.z;
	vessel->Global2Local(_V(Vnorm.x,Vnorm.y,Vnorm.z),vel2);
	Vnorm=_vector3(vel2.x,vel2.y,vel2.z);//and this is N vector in local frame
	Vnorm.selfnormalize();
	vector3 local_up=Vnorm;
	vector3 local_front=Vnorm*_vector3(0,0,1);
 
	Vnorm.z=0;Vnorm.selfnormalize();//all we need from here is roll now
 // ***********************
	double roll=PI-atan2(Vnorm.x,Vnorm.y);
 // ************************
	double pitch=-(PI/2-local_up.angle(_vector3(0,0,1)));
 //*************************
 
	double heading=Vvel.angle(local_front);
	vector3 local_head=local_front*Vvel;
	local_head.selfnormalize();//need to bring heading to quadtrant. ugly...
	if (local_head.z*local_up.z>0) heading=-heading;
	target.x=heading+PI;
	target.y=pitch;
	target.z=roll;
};
 
