// SPDX-License-Identifier: BSD-3-Clause
#include "GeminiOrbiter.h"
extern "C" VESSEL* ovcInit(OBJHANDLE,int);
extern "C" void ovcExit(VESSEL*);
using Factory=orbiter::native::VesselFactory<ovcInit,ovcExit>;
static const OrbiterNativeModuleDescriptor module = {
 sizeof(OrbiterNativeModuleDescriptor), ORBITER_NATIVE_BOOTSTRAP_VERSION,
 sizeof(void*), ORBITER_NATIVE_VESSEL, GEMINI_MODULE_NAME,
 ORBITER_NATIVE_SDK_BUILD, ORBITER_NATIVE_CPP_ABI,
 Factory::initialize, Factory::shutdown
};
extern "C" __attribute__((visibility("default")))
const OrbiterNativeModuleDescriptor* OrbiterNativeQuery(std::uint32_t version)
{ return version==ORBITER_NATIVE_BOOTSTRAP_VERSION ? &module : nullptr; }
