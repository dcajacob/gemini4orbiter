# Native Linux OpenGL integration

This branch ports the original Gemini/Titan II, Agena target vehicle, EVA astronaut,
ejected crew and beacon modules to native Linux x86-64. It uses the real Orbiter
vessel API, OpenGL renderer and native XRSound plugin. Wine is not used.

The original Visual Studio projects remain available. The native build uses CMake:

```sh
cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Release \
  -DORBITER_NATIVE_SOURCE_DIR=/path/to/matching/orbiter-source \
  -DORBITER_NATIVE_BUILD_DIR=/path/to/matching/orbiter-build
cmake --build build
```

The matching Orbiter build must have native vessels, celestial modules, cockpit,
OpenGL and XRSound enabled. Modules retain Orbiter's SDK fingerprint and C++ ABI
checks. Copying these libraries into an independently built SDK is unsupported;
rebuild the add-on against that SDK instead.

`orbiter-integration.patch` records the complete engine delta used for qualification,
against Orbiter commit `0702cca393b81b2dcc4722b6de3e905eeae91256` from our OpenGL
checkout. It includes original-vessel admission, initial exterior visibility and
staging/input fixes inherited from the Mercury integration. The engine changes
are MIT-licensed, under Orbiter's existing license. Apply the patch to that exact
source revision before building the engine and renderer. `prepare-engine.py` is an
alternative narrow admission update for a newer engine that already has those
shared fixes; do not apply both to the same source.

To overlay matching binaries on a complete stock native runtime:

```sh
python3 Native/install-runtime.py /path/to/orbiter-build /path/to/gemini-build /path/to/runtime
python3 Native/stage-assets.py /path/to/runtime
```

The asset helper installs this repository's original meshes, textures, bitmap
panels, manual and scenarios. It adds historical scenery through the original
`Gemini` scenario context and preserves stock Earth physics. It also installs a
standard Orbiter keymap to avoid laptop letter bindings conflicting with Gemini.

Launch the packaged build with `./launch-orbiter`, then choose **Project Gemini**,
**Earth 1962**, **Gemini - Native Linux Saves**, or **Gemini VIII - Native Flight**. Start paused, then Space resumes;
Ctrl-P pauses. Numpad +/- controls Titan thrust. The original launch autopilot is
on by default. F1 switches cockpit/exterior; F8 cycles cockpit modes. In the 2D
cockpit, Ctrl-arrows select neighbouring panels. Read `Gemini_Titan2_45.pdf` for the
original controls. Common commands are B for beacon release, P for the pilot's
hatch, E for EVA after the hatch opens, and L then J to lock onto/undock Agena.

Linux changes include case-correct includes, native module descriptors, dispatch
of legacy crew/EVA callbacks, initialized legacy stage pointers, bitmap surface
loading, explicit colour keys and a native ADI surface. The ADI retains the original
orbital-reference calculation and uses a procedural monochrome graticule because
upstream omits its `adi.dds` texture. Both upstream and the original SourceForge
4.5 archive omit `sidepane.dds`; the two affected meshes retain their existing
material and geometry with that nonexistent texture reference removed.

The Titan now uses explicit contact stiffness/damping on Linux. The legacy API
computed suspension stiffness from dry mass; the fueled stack leaned about eight
degrees on the pad and its uncompensated launch program missed orbit. The original
contact locations, engines, propellant loads and guidance program are retained.

`verification/quiet.sh LOG_DIR COMMAND...` creates a private PulseAudio null sink,
sets it to 5%, and runs the command under Xvfb. It never adjusts desktop volume.
With the runtime staged, run the flight checks using:

```sh
Native/verification/quiet.sh /tmp/gemini-audio \
  python3 Native/verification/replays.py /path/to/runtime /tmp/gemini-checks
```

See `qualification.json` for measured results and binary identities. Qualification covers original-scenario loading, seven flight regressions and a
continuous Gemini VIII launch/rendezvous/docking/return save chain. See
[the flight report](verification/gemini8/README.md) for measured milestones, fixes,
checkpoint replay instructions and limits. Windows/macOS native ports and Windows
parity remain unverified. This remains the original relatively simple Gemini 4.5 simulation,
not a NASSP-level subsystem model.
