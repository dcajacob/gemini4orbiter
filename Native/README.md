# Native Linux OpenGL integration

This branch ports the original Gemini/Titan II, Agena target vehicle, EVA astronaut,
ejected crew and beacon modules to native Linux x86-64. It uses the real Orbiter
vessel API, OpenGL renderer and native XRSound plugin. Wine is not used.

## Build the qualified Linux integration

Start in the root of the Gemini checkout. Set `work` to an empty directory on your
build disk. The fixed engine uses the published integration base and this
checkout's `Native/orbiter-integration.patch`. The patch includes Gemini vessel
admission, staging, exterior visibility and the legacy axial drag fix.
[Exact Orbiter engine base](https://github.com/dcajacob/orbiter-cross-platform/commit/0702cca393b81b2dcc4722b6de3e905eeae91256).

```sh
gemini=$(pwd -P)
work=/absolute/path/to/build-directory
engine="$work/orbiter"
mkdir -p "$work"
git clone --depth=1 --single-branch --branch codex/gemini-viii-opengl-integration-base \
  https://github.com/dcajacob/orbiter-cross-platform.git "$engine"
git -C "$engine" switch --detach 0702cca393b81b2dcc4722b6de3e905eeae91256
# The cockpit build reads original Dragonfly sources from this historical commit.
git -C "$engine" fetch --depth=1 origin f725194209634f7fd5d1d44d426cfa9b5e303e37
git -C "$engine" apply --index "$gemini/Native/orbiter-integration.patch"
test "$(git -C "$engine" write-tree)" = b456599a4a71b01f62387a6fa50da47514217504
```

The tree ID covers every tracked file in the fixed engine used for the four
entry comparisons. Build Orbiter, its OpenGL renderer and the Gemini modules
with the same configuration. The renderer needs the Linux OpenGL and X11
development packages. The dependency helper downloads and verifies its pinned
source archives.

```sh
cmake -S "$engine/Src/Orbiter/Production" -B "$work/engine-build" -G Ninja \
  -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=OFF \
  -DORBITER_BUILD_NATIVE_VESSELS=ON -DORBITER_BUILD_NATIVE_CELESTIAL_MODULES=ON \
  -DORBITER_BUILD_NATIVE_COCKPIT=ON
cmake --build "$work/engine-build"
python3 "$engine/Tests/Production/NativeScene/dependencies.py" --cache "$work/ogl-deps"
cmake -S "$engine/OVP/OGLClient/Native" -B "$work/renderer-build" -G Ninja \
  -DCMAKE_BUILD_TYPE=Release -DORBITER_ENGINE_BUILD="$work/engine-build" \
  -DORBITER_RENDERER_DEPENDENCIES="$work/ogl-deps"
cmake --build "$work/renderer-build"
cmake -S "$gemini" -B "$work/gemini-build" -G Ninja -DCMAKE_BUILD_TYPE=Release \
  -DORBITER_NATIVE_SOURCE_DIR="$engine" -DORBITER_NATIVE_BUILD_DIR="$work/engine-build"
cmake --build "$work/gemini-build"
```

The Gemini module carries the parachute save/restore logic. Build it from the
Gemini revision you want to fly. Its SDK and C++ ABI must match the engine.
The engine source patch is MIT-licensed under Orbiter's existing license.
The original Visual Studio projects remain available.

Overlay the resulting binaries and Gemini assets onto a complete stock native
runtime with its launcher, celestial data and planetary archives.

```sh
python3 Native/install-runtime.py "$work/engine-build" "$work/gemini-build" /path/to/runtime
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
