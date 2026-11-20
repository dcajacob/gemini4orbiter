#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Fly one phase-18 save on two matching native runtimes and two bank commands."""
import argparse
import hashlib
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from analyze_entry import DURATION, FIXTURE, ROOT, STEP, analyze_all, check, file_hash


def instrument_pilot():
    """Log read-only vessel size transitions for the automatic parachute events."""
    source = (ROOT / "pilot.lua").read_text()
    hooks = {
        "local steering=false": (
            'local chute_log=assert(io.open("chute-events.csv","w"))\n'
            'chute_log:write("seconds,size\\n")\nlocal last_size=-1\nlocal steering=false'
        ),
        " local t=now-start": (
            ' local t=now-start\n local size=oapi.get_size(oapi.get_objhandle("GEMINI"))\n'
            ' if size~=last_size then chute_log:write(string.format("%.9f,%.9f\\n",t,size));'
            'chute_log:flush();last_size=size end'
        ),
        "logfile:close()": "logfile:close()\nchute_log:close()",
    }
    for anchor, instrumented in hooks.items():
        check(source.count(anchor) == 1, f"Missing or ambiguous pilot hook: {anchor}")
        source = source.replace(anchor, instrumented)
    return source


def fly(output, runtime, drag, bank, pilot):
    case = output / (drag + ("-bank-up" if bank else "-bank-original"))
    case.mkdir()
    plan = dict(mode="orient", retrograde=True, lift_up=bank, angular_acceleration=0.3,
                maxrate=0.04, control_until_altitude=20000)
    plan_file = case / "plan.json"
    plan_file.write_text(json.dumps(plan, indent=2) + "\n")
    # runner.py accepts a frozen full script. Use the same plan for both files.
    lua_plan = dict(plan, duration=DURATION - 2 * STEP)
    fields = ",".join(f"{key}={json.dumps(value)}" for key, value in lua_plan.items())
    pilot_file = case / "frozen-pilot.lua"
    pilot_file.write_text("local plan={" + fields + "}\n" + pilot)
    record = dict(drag=drag, bank_up=bank, controller=plan, initial_save_sha256=file_hash(FIXTURE),
                  pilot_body_sha256=hashlib.sha256(pilot.encode()).hexdigest(), duration_s=DURATION,
                  fixed_step_s=STEP, resumed_during_run=False)
    (case / "case.json").write_text(json.dumps(record, indent=2) + "\n")
    cmd = [
        sys.executable, str(ROOT / "runner.py"), str(runtime), str(case), str(FIXTURE),
        "--seconds", str(DURATION), "--step", str(STEP), "--plan", str(plan_file), "--pilot", str(pilot_file),
    ]
    with (case / "runner.log").open("w") as log:
        subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("original_runtime", type=Path)
    parser.add_argument("fixed_runtime", type=Path)
    parser.add_argument("output", type=Path, help="new output directory for telemetry and summaries")
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    pilot = instrument_pilot()
    with ThreadPoolExecutor(max_workers=4) as pool:
        jobs = [
            pool.submit(fly, output, runtime.resolve(), drag, bank, pilot)
            for drag, runtime in (("original", args.original_runtime), ("fixed", args.fixed_runtime))
            for bank in (False, True)
        ]
        for job in jobs:
            job.result()
    analyze_all(output)


if __name__ == "__main__":
    main()
