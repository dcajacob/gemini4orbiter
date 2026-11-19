#!/usr/bin/env python3
"""Admit original Gemini vessels in a matching native Orbiter source checkout."""
from pathlib import Path
import sys
source=Path(sys.argv[1])/'Src/Orbiter/Production/NativeApplication.cpp'
s=source.read_text()
anchor='            if(apolloWorld && SupportedApolloVessel(*body,type))continue;'
if '// Gemini4Orbiter native admission' in s: raise SystemExit('Gemini admission already installed')
if s.count(anchor)!=1: raise SystemExit('Unknown native host: review admission before porting')
admission='''
            // Gemini4Orbiter native admission. NativeModule retains all SDK/ABI guards.
            auto geminiType=ResourceResolver::Normalize(type);
            if(geminiType.rfind("vessels/",0)==0)geminiType.erase(0,8);
            const std::pair<const char*,const char*> geminiModules[]={
                {"gemini_titan","gemini_titan"},{"gemini_titan7","gemini_titan"},
                {"cv_gatv","gatv"},{"cv_gatv-5003","gatv"},
                {"gemini_cdr","gemini_astro"},{"gemini_plt","gemini_astro"},
                {"gemini_eva","gemini_eva"},{"beacon","beacon"}
            };
            if(body->NativeModuleName() && std::any_of(std::begin(geminiModules),std::end(geminiModules),
                [&](const auto& entry){return geminiType==entry.first && ResourceResolver::Normalize(body->NativeModuleName())==entry.second;}))continue;
            // These original classes are defined entirely by Orbiter configuration.
            static const char* geminiConfigured[]={"titan_stage_first","titan_stage_second","titan_mid_section",
                "microm","gemini_nose","gemini_chute","gemini_drogue","gemini_equip","gemini_adapt",
                "gemini_door_left","gemini_door_right","ejectseat","agena","agena_dock"};
            if(!body->NativeModuleName() && vessel->Version()==0 && std::any_of(std::begin(geminiConfigured),std::end(geminiConfigured),
                [&](const char* name){return geminiType==name;}))continue;
'''
source.write_text(s.replace(anchor,anchor+admission))
