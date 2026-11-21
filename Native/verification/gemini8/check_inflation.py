#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Compare the mid-inflation restart against the continuous fixed-drag, lift-up flight."""
import argparse
import csv
import json
import math
from pathlib import Path

from analyze_entry import ROOT, STEP, check, ships

CHECKPOINT = ROOT / "fixtures/mid-inflation.scn"
DURATION = 2000
# Scenario position/velocity and attitude are serialized as decimal text.
# Allow 1 N of drag error and 0.05 m/s of contact-speed error on reload.
DRAG_TOLERANCE_N = 1.0
CONTACT_TOLERANCE_M_S = 0.05


def gemini_samples(case):
    with (case / "evidence/flight-state.csv").open() as stream:
        yield from (row for row in csv.DictReader(stream) if row["object"] == "GEMINI")


def compare(reference, resumed):
    metadata = json.loads((reference / "case.json").read_text())
    check(metadata["drag"] == "fixed" and metadata["bank_up"], "Wrong continuous reference case")
    check(ships(resumed / "input.scn") == ships(CHECKPOINT), "Wrong mid-inflation save")

    live = gemini_samples(reference)
    restarted = gemini_samples(resumed)
    initial = next(restarted)
    check(int(initial["tick"]) == 0, "Restarted telemetry does not start at load")
    epoch = float(initial["mjd"])
    start = next((row for row in live if abs(float(row["mjd"]) - epoch) * 86400 < STEP / 4), None)
    check(start is not None, "Save epoch outside uninterrupted flight")
    for keys, tolerance in ((("rx", "ry", "rz"), 0.002), (("vx", "vy", "vz"), 0.0002)):
        error = math.dist([float(start[k]) for k in keys], [float(initial[k]) for k in keys])
        check(error <= tolerance, f"Checkpoint {keys} differs from live flight by {error}")

    # The engine's load observer has not computed the aerodynamic forces at tick zero.
    # Compare every integrated step, including reefing transitions, release and touchdown.
    start_tick = int(start["tick"])
    peaks = {"initial_20s": 0.0, "airborne": 0.0, "all": 0.0}
    contacts = {}
    result = {"reference_start_tick": start_tick}
    tick = 0
    for tick, resumed_row in enumerate(restarted, 1):
        ref = next(live, None)
        check(ref and int(ref["tick"]) == start_tick + tick and int(resumed_row["tick"]) == tick and
              abs(float(ref["mjd"]) - float(resumed_row["mjd"])) * 86400 < STEP / 4,
              f"Unmatched physics step {tick}")
        ref_drag, new_drag = float(ref["drag"]), float(resumed_row["drag"])
        difference = abs(ref_drag - new_drag)
        check(difference <= DRAG_TOLERANCE_N,
              f"Drag differs at tick {tick}: continuous {ref_drag:.5f} N, resumed {new_drag:.5f} N")
        if tick == 1:
            result.update(first_continuous_drag_N=ref_drag, first_resumed_drag_N=new_drag)
        peaks["all"] = max(peaks["all"], difference)
        if tick * STEP <= 20:
            peaks["initial_20s"] = max(peaks["initial_20s"], difference)
        if ref["ground"] == resumed_row["ground"] == "0":
            peaks["airborne"] = max(peaks["airborne"], difference)
        for name, sample in (("continuous", ref), ("resumed", resumed_row)):
            if name not in contacts and sample["ground"] == "1":
                contacts[name] = {"seconds_after_save": tick * STEP, "airspeed_m_s": float(sample["airspeed"])}
        if tick == DURATION / STEP:
            check(ref["ground"] == resumed_row["ground"] == "1" and
                  max(float(ref["airspeed"]), float(resumed_row["airspeed"])) < 1,
                  "Both capsules must settle after splashdown")
    check(tick == int(DURATION / STEP), f"Incomplete replay: {tick} physics steps")
    check(contacts.keys() == {"continuous", "resumed"}, "Missing splashdown")
    a, b = contacts["continuous"], contacts["resumed"]
    check(abs(a["seconds_after_save"] - b["seconds_after_save"]) <= STEP, "Contact time differs")
    check(abs(a["airspeed_m_s"] - b["airspeed_m_s"]) <= CONTACT_TOLERANCE_M_S, "Contact speed differs")
    result.update(compared_steps=tick, peak_absolute_drag_difference_N=peaks, first_contact=contacts)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("continuous_case", type=Path)
    parser.add_argument("resumed_case", type=Path)
    args = parser.parse_args()
    print(json.dumps(compare(args.continuous_case, args.resumed_case), indent=2))
