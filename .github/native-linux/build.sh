#!/usr/bin/env bash
# Build the OpenGL branch in place and use its generated SDK for every module.
set -euo pipefail
gemini=$(pwd -P)
orbiter=$(realpath "$1")
work=$(realpath "$2")
base=361c4d1110338cadce9a00ccd2c37dcca333b0db
integration=0702cca393b81b2dcc4722b6de3e905eeae91256
dragonfly=f725194209634f7fd5d1d44d426cfa9b5e303e37
(
    cd "$orbiter"
    git fetch --no-tags --depth=1 origin "$base" "$integration" "$dragonfly"
    # Reconstruct only the qualified runtime/SDK changes. Keep the OpenGL
    # branch's vessel physics and apply the other hunks against its actual tip.
    export GIT_INDEX_FILE="$work/integration.index"
    git read-tree "$integration"
    git apply --cached --whitespace=nowarn "$gemini/Native/orbiter-integration.patch"
    tree=$(git write-tree)
    test "$tree" = b456599a4a71b01f62387a6fa50da47514217504
    unset GIT_INDEX_FILE
    git diff --binary "$base" "$tree" -- Src OVP Orbitersdk Sound \
        ':(exclude)Src/Orbiter/Vessel.cpp' ':(exclude)Src/Orbiter/Vessel.h' > "$work/runtime.patch"
    git apply --whitespace=nowarn "$work/runtime.patch"
    git diff --exit-code -- Src/Orbiter/Vessel.cpp Src/Orbiter/Vessel.h
)
export CMAKE_BUILD_PARALLEL_LEVEL=${CMAKE_BUILD_PARALLEL_LEVEL:-4}
flags=(-G Ninja -DCMAKE_BUILD_TYPE=Release)
python3 "$orbiter/Tests/Production/NativeScene/dependencies.py" --cache "$work/deps"
cmake -S "$orbiter/Src/Orbiter/Production" -B "$work/engine" "${flags[@]}" \
    -DBUILD_TESTING=OFF -DORBITER_BUILD_NATIVE_VESSELS=ON \
    -DORBITER_BUILD_NATIVE_CELESTIAL_MODULES=ON -DORBITER_BUILD_NATIVE_COCKPIT=ON \
    -DORBITER_NATIVE_UI_ARCHIVE="$work/deps/imgui.zip"
cmake --build "$work/engine"
cmake -S "$orbiter/OVP/OGLClient/Native" -B "$work/renderer" "${flags[@]}" \
    -DORBITER_ENGINE_BUILD="$work/engine" -DORBITER_RENDERER_DEPENDENCIES="$work/deps"
cmake --build "$work/renderer" --target orbiter_ogl_native
cmake -S "$gemini" -B "$work/gemini" "${flags[@]}" \
    -DORBITER_NATIVE_SOURCE_DIR="$orbiter" -DORBITER_NATIVE_BUILD_DIR="$work/engine"
cmake --build "$work/gemini"
