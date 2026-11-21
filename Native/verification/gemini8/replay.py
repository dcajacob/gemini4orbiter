#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Fly selected recorded phases, or pass each new save to the next phase."""
import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess

from mission import validate_phase

ROOT = Path(__file__).resolve().parent
LAUNCH = ROOT.parents[2] / "Scenarios/Earth 1962/Gemini VIII.scn"


def fly_phase(runtime, case, fixture, source):
    record = json.loads((fixture / "record.json").read_text())
    case.mkdir(parents=True, exist_ok=True)
    scenario = re.sub(r"^[ \t]*Script .*\n", "", source.read_text(), flags=re.M)
    pilot = fixture / "pilot.lua"
    if pilot.exists():
        script = f"Gemini8/{fixture.name}"
        scenario = scenario.replace("BEGIN_ENVIRONMENT\n", f"BEGIN_ENVIRONMENT\n  Script {script}\n", 1)
        target = runtime / "resources/Script" / f"{script}.lua"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.unlink(missing_ok=True)
        shutil.copy2(pilot, target)
    (case / "input.scn").write_text(scenario)
    shutil.copy2(fixture / "replay.csv", case / "replay.csv")
    ticks = round(record["seconds"] / record["step"])
    args = [runtime / "engine/run-orbiter", "--assets", runtime / "resources",
            "--data", runtime / "celestial-data", "--modules", runtime / "engine/NativeModules",
            "--planets", runtime / "planet-archives", "--config", runtime / "Orbiter.cfg",
            "--keymap", runtime / "Keymap.cfg", "--xrsound-assets", runtime / "resources",
            "--scenario", "input.scn", "--save", "saved.scn", "--replay", "replay.csv",
            "--ticks", str(ticks), "--run", "--fixed-step", str(record["step"]),
            "--render-every", "4096", "--evidence", "evidence"]
    save = case / "saved.scn"
    for marker in (save, case / "pilot-docked.txt", case / "pilot-complete.txt"):
        marker.unlink(missing_ok=True)
    with (case / "console.log").open("w") as log:
        subprocess.run(args, cwd=case, stdout=log, stderr=subprocess.STDOUT, check=True)
    if pilot.exists() and not (case / "pilot-complete.txt").is_file():
        raise ValueError(f"{fixture.name}: flight script did not complete")
    saved = save.read_text()
    if "END_SHIPS" not in saved:
        raise ValueError(f"Incomplete save in {case}")
    if fixture.name == "13-docking":
        if "DOCKINFO 0:0,GATV" not in saved or not (case / "pilot-docked.txt").is_file():
            raise ValueError("Gemini did not dock with Agena")
    if fixture.name == "22-splashdown":
        gemini = re.search(r"^GEMINI:.*?^END$", saved, re.M | re.S)[0]
        if "STATUS Landed Earth" not in gemini or "MAIN_JETTISONED 1.0" not in gemini:
            raise ValueError("Gemini did not splash down and release the main parachute")
    save.write_text(re.sub(r"^[ \t]*Script .*\n", "", saved, flags=re.M))
    return save


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("runtime", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("phases", nargs="*")
    parser.add_argument("--linked", action="store_true", help="fly all phases from the original launch")
    parser.add_argument("--compact", action="store_true", help="remove raw telemetry after each verified linked phase")
    args = parser.parse_args()
    if args.compact and not args.linked:
        parser.error("--compact requires --linked")
    records = json.loads((ROOT / "flight-ledger.json").read_text())
    phases = [row["phase"] for row in records]
    report = []
    if set(args.phases) - set(phases) or (args.linked and args.phases):
        parser.error("select recorded phases by name, or use --linked for the entire flight")
    if args.linked:
        args.output.mkdir(parents=True, exist_ok=False)
    source = LAUNCH
    for record in records:
        phase = record["phase"]
        if args.phases and phase not in args.phases:
            continue
        fixture = ROOT / "fixtures" / phase
        case = args.output.resolve() / phase
        source = fly_phase(args.runtime.resolve(), case, fixture, source if args.linked else fixture / "input.scn")
        if args.linked:
            report.append(validate_phase(case, record))
            (args.output / "mission.json").write_text(json.dumps(report, indent=2) + "\n")
            if args.compact:
                shutil.rmtree(case / "evidence")
        print(phase, "passed", flush=True)


if __name__ == "__main__":
    main()
