#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Measure and check the four Gemini entry cases from native telemetry."""
import argparse
import csv
import hashlib
import json
import math
import re
from itertools import zip_longest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FIXTURE = ROOT / "fixtures/18-adapter-separation/saved.scn"
STEP = 1 / 32
DURATION = 4000
G = 9.80665
INITIAL_COLUMNS = """
mjd rx ry rz vx vy vz m11 m12 m13 m21 m22 m23 m31 m32 m33 wx wy wz mass fuel
""".split()
TRACE_COLUMNS = [
    "seconds", "altitude_m", "airspeed_m_s", "dynamic_pressure_Pa",
    "aerodynamic_g", "radial_lift_g", "fuel_kg",
]


def check(condition, description):
    if not condition:
        raise ValueError(description)


def file_hash(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def ships(path):
    return re.search(r"^BEGIN_SHIPS\n.*?^END_SHIPS$", path.read_text(), re.M | re.S)[0]


def radial_lift(row, forces, mass):
    """Project body-axis lift onto the outward radial unit vector, in g."""
    position = [float(row[key]) for key in ("rx", "ry", "rz")]
    lift = [float(forces[key]) for key in ("lift_x", "lift_y", "lift_z")]
    inertial = [
        sum(float(row[f"m{i}{j}"]) * component for j, component in enumerate(lift, 1))
        for i in range(1, 4)
    ]
    return sum(a * b for a, b in zip(position, inertial)) / (math.hypot(*position) * mass * G)


def analyze(case):
    report = json.loads((case / "case.json").read_text())
    report.pop("runtime", None)  # Older run records include an absolute staging path.
    chain = json.loads((case / "chain.json").read_text())
    pilot_path = case / "pilot.lua"
    pilot_body = pilot_path.read_bytes().split(b"\n", 1)[1]
    check(ships(case / "input.scn") == ships(FIXTURE), f"{case}: physical save mismatch")
    check(file_hash(FIXTURE) == chain["input_sha256"] == report["initial_save_sha256"],
          f"{case}: wrong starting save")
    check(file_hash(pilot_path) == chain["pilot_sha256"] and
          hashlib.sha256(pilot_body).hexdigest() == report["pilot_body_sha256"],
          f"{case}: wrong pilot")
    check(chain["step"] == STEP and chain["seconds"] == DURATION and
          (case / "pilot-complete.txt").read_text().strip() == "complete",
          f"{case}: incomplete replay")

    with (case / "chute-events.csv").open() as stream:
        events = list(csv.DictReader(stream))
    # Gemini_Set_Module changes size at deployment, jettison and main release.
    check([float(event["size"]) for event in events] == [2, 9, 2, 12, 2],
          f"{case}: unexpected chute sequence")
    drogue, main = (float(events[index]["seconds"]) for index in (1, 3))
    state_path = case / "evidence/flight-state.csv"
    forces_path = case / "evidence/ground-math.csv"
    peak = pre_drogue = peak_q = 0.0
    lift_sum = 0.0
    lift_samples = 0
    first_contact = first_drag = None
    with state_path.open() as state, forces_path.open() as forces, (case / "trace.csv").open("w") as trace:
        gemini = (row for row in csv.DictReader(state) if row["object"] == "GEMINI")
        writer = csv.writer(trace)
        writer.writerow(TRACE_COLUMNS)
        for tick, (row, force) in enumerate(zip_longest(gemini, csv.DictReader(forces))):
            check(row and force and row["focus"] == "GEMINI" and
                  int(row["tick"]) == int(force["tick"]) == tick and
                  float(row["seconds"]) == float(force["seconds"]) == tick * STEP,
                  f"{case}: mismatched state or force sample at tick {tick}")
            time = tick * STEP
            mass, lift, drag, speed, q, altitude = (
                float(row[k]) for k in ("mass", "lift", "drag", "airspeed", "dynamic_pressure", "altitude_mean")
            )
            load = math.hypot(lift, drag) / (mass * G)
            radial = radial_lift(row, force, mass)
            sample = {"seconds": time, "altitude_m": altitude, "airspeed_m_s": speed}
            if tick == 0:
                report["initial_state"] = {k: float(row[k]) for k in INITIAL_COLUMNS}
            if time == drogue:
                report["drogue_state"] = sample
            if time == main:
                report["main_state"] = sample
            if load > peak:
                peak, report["peak"] = load, sample
            if time < drogue and load > pre_drogue:
                pre_drogue, report["peak_before_drogue"] = load, sample
            peak_q = max(peak_q, q)
            if first_contact is None and row["ground"] == "1":
                first_contact = sample
            if first_drag is None and drag > 0:
                first_drag = {"seconds": time, "drag_N": drag, "dynamic_pressure_Pa": q}
            if speed > 2000 and q > 1000:
                lift_sum += radial
                lift_samples += 1
            if tick % 32 == 0:
                writer.writerow([time, altitude, speed, q, load, radial, row["fuel"]])
        check(time == DURATION and lift_samples and first_contact and first_drag,
              f"{case}: missing flight observations")

    save = case / "saved.scn"
    block = re.search(r"^GEMINI:.*?^END$", save.read_text(), re.S | re.M)[0]
    coordinates = re.search(r"^  POS (.*)", block, re.M)
    check(coordinates, f"{case}: landed coordinates missing from final save")
    report.update(
        peak_aerodynamic_g=peak, peak_before_drogue_g=pre_drogue,
        mean_radial_lift_g=lift_sum / lift_samples, radial_lift_window_s=lift_samples * STEP,
        peak_dynamic_pressure_Pa=peak_q, first_contact=first_contact, first_drag=first_drag,
        final_speed_m_s=speed, final_ground=row["ground"] == "1", final_fuel_kg=float(row["fuel"]),
        coordinates_lon_lat_deg=list(map(float, coordinates[1].split())),
        drogue_seconds=drogue, main_seconds=main, chute_events=events,
        save_sha256=file_hash(save), state_sha256=file_hash(state_path),
        forces_sha256=file_hash(forces_path), trace_sha256=file_hash(case / "trace.csv"),
    )
    (case / "summary.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def verify(reports):
    cases = {(r["drag"], r["bank_up"]): r for r in reports}
    expected = {(drag, up) for drag in ("fixed", "original") for up in (False, True)}
    check(len(reports) == 4 and cases.keys() == expected, "Expected four distinct drag/bank cases")
    reference = reports[0]
    for r in reports:
        label = (r["drag"], r["bank_up"])
        for key in ("initial_save_sha256", "pilot_body_sha256", "initial_state"):
            check(r[key] == reference[key], f"{label}: {key} differs")
        check(r["fixed_step_s"] == STEP and r["duration_s"] == DURATION and not r["resumed_during_run"],
              f"{label}: unexpected replay protocol")
        check(r["final_ground"] and r["final_speed_m_s"] < 1 and r["final_fuel_kg"] > 25,
              f"{label}: did not settle with fuel remaining")
        sign = 1 if r["bank_up"] else -1
        check(sign * r["mean_radial_lift_g"] > 0, f"{label}: bank reversed the expected lift direction")

    check(cases["original", False]["peak_aerodynamic_g"] > 50, "Original load spike missing")
    check(8 < cases["fixed", False]["peak_aerodynamic_g"] < 20, "Drag-only peak outside replay range")
    check(cases["original", True]["peak_aerodynamic_g"] < 10, "Bank-only peak outside replay range")
    check(cases["fixed", True]["peak_aerodynamic_g"] < 8, "Combined peak outside replay range")
    check(cases["original", True]["drogue_seconds"] > 2 * cases["fixed", True]["drogue_seconds"],
          "Correcting axial drag no longer advances drogue deployment with lift banked upward")
    # The low peak in the bank-only trial accompanies a much longer trajectory.
    lon1, lat1 = map(math.radians, cases["original", True]["coordinates_lon_lat_deg"])
    lon2, lat2 = map(math.radians, cases["fixed", True]["coordinates_lon_lat_deg"])
    cosine = math.sin(lat1) * math.sin(lat2) + math.cos(lat1) * math.cos(lat2) * math.cos(lon1 - lon2)
    separation_km = 6371 * math.acos(max(-1.0, min(1.0, cosine)))
    check(separation_km > 5000, "Corrected-bank splashdown positions converged unexpectedly")
    for bank in (False, True):
        fixed, old = (cases[d, bank]["first_drag"] for d in ("fixed", "original"))
        check(fixed["seconds"] == old["seconds"] == STEP and fixed["drag_N"] > 5 * old["drag_N"],
              f"Wrong initial backward drag with bank_up={bank}")
    print("Matched save, force direction, bank sign, chute timing and four splashdowns passed.")


def analyze_all(output):
    reports = []
    for case in sorted(output.iterdir()):
        if (case / "case.json").is_file():
            report = analyze(case)
            reports.append(report)
            print(f"{case.name}: {report['peak_aerodynamic_g']:.3f} g", flush=True)
    verify(reports)
    (output / "results.json").write_text(json.dumps(reports, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    analyze_all(parser.parse_args().output)
