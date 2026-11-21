#!/usr/bin/env bash
set -euo pipefail
gemini=$(pwd -P)
cd "$1"
assets=https://github.com/dcajacob/NASSP/releases/download/native-linux-ci-inputs-v1
stock=https://github.com/dcajacob/orbiter-cross-platform/releases/download/production-inputs-v2
fetch() {
    curl --fail --location --retry 3 --output "$2" "$1"
    printf '%s  %s\n' "$3" "$2" | sha256sum -c -
}
# Only import data, settings and the two shell launchers from the stock fixture.
fetch "$assets/nassp-native-ci-inputs-v1.tar.zst" inputs.tar.zst \
    26d5891ea54a01ab8d007bed3ab2e9f5ed46ff8cd315921c57ca0e334faf37bd
tar --zstd -xf inputs.tar.zst ./runtime/{resources,celestial-data,planet-archives,Orbiter.cfg,launch-orbiter,engine/run-orbiter}
rm inputs.tar.zst
sed -i '/^ACTIVE_MODULES$/,/^END_MODULES$/d' runtime/Orbiter.cfg
fetch "$assets/nassp-native-ci-terrain-v1.tar.zst" terrain.tar.zst \
    00e2e3d7198684a58ec4c96a148a485759d1695667e030416399a017dbe977db
tar --zstd -xf terrain.tar.zst -C runtime/planet-archives
rm terrain.tar.zst
fetch "$stock/production-stock-data-v1.zip" stock.zip \
    b70a4065ceda469e4b0f35d3d8935138483873fdb8d8eb2dd6b99829f8ce0cb3
unzip -p stock.zip Kernels/orbiter.bsp > runtime/celestial-data/Kernels/orbiter.bsp
rm stock.zip
python3 "$gemini/Native/install-runtime.py" engine gemini runtime
python3 "$gemini/Native/stage-assets.py" runtime
