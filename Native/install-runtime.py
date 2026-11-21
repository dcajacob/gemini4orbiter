#!/usr/bin/env python3
"""Overlay matching native engine, renderer and Gemini products on a stock runtime."""
import argparse
import fcntl
import os
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory


ENGINE_BINARIES = (
    "orbiter-production", "liborbiter_production_boundary.so", "liborbiter_production_vessels.so",
)
REQUIRED_ENGINE = ENGINE_BINARIES + (
    "native-sdk/OrbiterNativeBuild.h", "native-lua/liblua.so",
    "NativeModules/Graphics/OGLClient.so", "NativeModules/Plugin/XRSound.so",
    "NativeModules/Plugin/LuaInterpreter.so", "NativeModules/Celbody/spice.so",
    "NativeModules/Celbody/Earth/Atmosphere/EarthAtmJ71G.so",
)
REQUIRED_GEMINI = tuple(
    f"NativeModules/Vessel/{name}.so" for name in ("Gemini_Titan", "GATV", "gemini_astro", "gemini_eva", "Beacon")
)


def require_files(root, names):
    for name in names:
        path = root / name
        if not path.is_file() or not path.stat().st_size:
            raise ValueError(f"Missing or empty required file: {path}")


def install(engine, addon, runtime):
    require_files(engine, REQUIRED_ENGINE)
    require_files(addon, REQUIRED_GEMINI)
    require_files(runtime, ("engine/run-orbiter", "launch-orbiter", "resources/Config/Earth.cfg"))
    for name in ("celestial-data", "planet-archives"):
        if not (runtime / name).is_dir():
            raise ValueError(f"Missing stock runtime directory: {runtime / name}")

    files = {Path(name): engine / name for name in ENGINE_BINARIES}
    # The stock Atlantis wrappers depend on this library. A Gemini-only build
    # can omit both; keep existing optional stock modules in that case.
    atlantis = "liborbiter_native_atlantis.so"
    wrappers = ("Atlantis.so", "Atlantis_Tank.so", "Atlantis_SRB.so")
    if any((engine / "NativeModules/Vessel" / name).is_file() for name in wrappers):
        require_files(engine, (atlantis,))
    if (engine / atlantis).is_file():
        files[Path(atlantis)] = engine / atlantis
    for name, pattern in (("native-sdk", "*"), ("NativeModules", "*"), ("native-lua", "liblua.so*")):
        for src in (engine / name).rglob(pattern):
            if src.is_file():
                files[src.relative_to(engine)] = src
    for src in (addon / "NativeModules").rglob("*.so"):
        if src.is_file():
            files[src.relative_to(addon)] = src

    target = (runtime / "engine").resolve()
    # Serialize installers while preserving stock files outside this overlay.
    lock = os.open(target, os.O_DIRECTORY)
    try:
        fcntl.flock(lock, fcntl.LOCK_EX)
        for rel in files:
            dest = target / rel
            if not dest.parent.resolve().is_relative_to(target) or dest.is_dir():
                raise ValueError(f"Invalid runtime file destination: {dest}")

        with TemporaryDirectory(prefix=".gemini-install-", dir=target) as tmp:
            staging = Path(tmp)
            backup = staging / "previous"
            backup.mkdir()
            # Stage every copy and preserve existing file entries before any replacement.
            for rel, src in files.items():
                staged = staging / rel
                staged.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, staged)
                dest = target / rel
                if os.path.lexists(dest):
                    saved = backup / rel
                    saved.parent.mkdir(parents=True, exist_ok=True)
                    os.link(dest, saved, follow_symlinks=False)

            installed = []
            try:
                for rel in files:
                    dest = target / rel
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    (staging / rel).replace(dest)
                    installed.append(rel)
            except BaseException:
                for rel in reversed(installed):
                    saved = backup / rel
                    if os.path.lexists(saved):
                        saved.replace(target / rel)
                    else:
                        (target / rel).unlink()
                raise
    finally:
        os.close(lock)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("engine", type=Path)
    parser.add_argument("addon", type=Path)
    parser.add_argument("runtime", type=Path)
    args = parser.parse_args()
    try:
        install(args.engine, args.addon, args.runtime)
    except (OSError, ValueError) as error:
        parser.exit(1, f"{parser.prog}: {error}\n")


if __name__ == "__main__":
    main()
