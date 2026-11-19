#ifndef __COMMON_ADDON_H
#define __COMMON_ADDON_H

#include "GeminiOrbiter.h"

#ifdef GEMINI_NATIVE_ORBITER
extern "C" void ovcSetClassCaps(VESSEL*,FILEHANDLE);
extern "C" int ovcConsumeBufferedKey(VESSEL*,DWORD,bool,char*);
extern "C" int ovcConsumeKey(VESSEL*,const char*);
extern "C" void ovcTimestep(VESSEL*,double);
class COMMON_VESSEL:public VESSEL2 {
public:
 COMMON_VESSEL(OBJHANDLE h):VESSEL2(h,1){}
 virtual void* GetSystemInterface(const char*) {return nullptr;}
 virtual int SendMessage(const char*,void*) {return 0;}
 void clbkSetClassCaps(FILEHANDLE cfg) override {ovcSetClassCaps(this,cfg);}
 int clbkConsumeBufferedKey(DWORD key,bool down,char* state) override {return ovcConsumeBufferedKey(this,key,down,state);}
 int clbkConsumeDirectKey(char* state) override {return ovcConsumeKey(this,state);}
 void clbkPreStep(double time,double,double) override {ovcTimestep(this,time);}
};
#else
class COMMON_VESSEL: public VESSEL {
public:
	COMMON_VESSEL (OBJHANDLE hObj);
	virtual void* GetSystemInterface(const char* pszSystem);
	virtual int SendMessage(const char* pszMessage, void* aMessage);
};

COMMON_VESSEL::COMMON_VESSEL(OBJHANDLE hObj)
: VESSEL(hObj)
{
}

void* COMMON_VESSEL::GetSystemInterface(const char* pszSystem)
{
	return 0;
}

int COMMON_VESSEL::SendMessage(const char* pszMessage, void* aMessage)
{
	return 0;
}


#endif
#endif // !__COMMON_ADDON_H
