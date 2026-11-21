"""Read live mission telemetry and check the operational milestones."""
import csv
import math
import re

from analyze_entry import G, check, file_hash


def ship_state(scenario, name):
    block = re.search(rf"^{name}:[^\n]+\n(.*?)^END$", scenario, re.M | re.S)
    if not block:
        raise ValueError(f"Missing ship {name} in save")
    return dict(line.strip().split(maxsplit=1) for line in block[1].splitlines() if line.strip())


def validate_phase(case, record):
    phase = record["phase"]
    ticks = round(record["seconds"] / record["step"])
    peak_drag_g = 0
    contact = None
    last = None
    with (case / "evidence/flight-state.csv").open() as stream:
        for row in csv.DictReader(stream):
            if row["object"] != "GEMINI":
                continue
            last = row
            if phase == "20-reentry":
                peak_drag_g = max(peak_drag_g, float(row["drag"]) / (G * float(row["mass"])))
            if phase == "22-splashdown" and row["ground"] == "1" and contact is None:
                contact = float(row["airspeed"])
    check(last and int(last["tick"]) == ticks, f"{phase}: incomplete telemetry")
    altitude, speed = float(last["altitude_mean"]), float(last["airspeed"])
    check(math.isfinite(altitude) and math.isfinite(speed), f"{phase}: nonfinite final state")
    saved = (case / "saved.scn").read_text()
    epoch = float(re.search(r"^  Date MJD (.+)$", saved, re.M)[1])
    check(abs(epoch - record["actual_saved_mjd"]) * 86400 < record["step"] / 2,
          f"{phase}: save at unexpected epoch {epoch}")
    gemini = ship_state(saved, "GEMINI")
    agena = ship_state(saved, "GATV")
    result = dict(phase=phase, ticks=ticks, mjd=epoch, altitude_m=altitude, airspeed_m_s=speed,
                  input_sha256=file_hash(case / "input.scn"), save_sha256=file_hash(case / "saved.scn"))
    if phase == "01-ascent":
        check(gemini["CONFIGURATION"] == "2" and gemini["STATUS"] == "Orbiting Earth"
              and 200_000 < altitude < 300_000 and 7000 < speed < 8000, "Titan missed orbital insertion")
    if phase in ("10-rendezvous-braking", "11-terminal-approach", "12-final-approach"):
        def separation(key):
            return math.dist(*(map(float, vessel[key].split()) for vessel in (gemini, agena)))
        distance, relative_speed = separation("RPOS"), separation("RVEL")
        limits = {"10-rendezvous-braking": (9000, 6), "11-terminal-approach": (700, 1),
                  "12-final-approach": (80, 0.5)}
        check(distance < limits[phase][0] and relative_speed < limits[phase][1],
              f"{phase}: range {distance:.1f} m, relative speed {relative_speed:.3f} m/s")
        result.update(range_m=distance, relative_speed_m_s=relative_speed)
    docked = "0:0,GATV" in gemini.get("DOCKINFO", "").split()
    reciprocal = "0:0,GEMINI" in agena.get("DOCKINFO", "").split()
    check(docked == reciprocal == (phase == "13-docking"), f"{phase}: unexpected docking state")
    if docked:
        result["docking_seconds"] = float((case / "pilot-docked.txt").read_text())
    if phase == "17-retrofire":
        check(gemini["EQUIP_JETTISONED"] == "1.0" and int(gemini["RETRO_SEQ"]) >= 3,
              "Equipment jettison or retrofire sequence failed")
    if phase == "18-adapter-separation":
        check(gemini["ADAPT_JETTISONED"] == "1.0" and 80_000 < altitude < 130_000,
              f"Missed atmospheric entry after retrofire: {altitude:.0f} m")
    if phase == "20-reentry":
        check(4 < peak_drag_g < 8 and gemini["DROGUE_DEPLOYED"] == "1.0",
              f"Unexpected entry load or drogue deployment, peak drag {peak_drag_g:.2f} g")
        result["peak_drag_g"] = peak_drag_g
    if phase == "21-parachute-descent":
        check(gemini["MAIN_DEPLOYED"] == "1.0" and gemini["MAIN_JETTISONED"] == "0.0",
              "Main canopy did not deploy and remain attached")
    if phase == "22-splashdown":
        lon, lat = map(float, gemini["POS"].split())
        check(19 < lat < 21 and 141 < lon < 143, f"Outside Pacific recovery area: {lat}, {lon}")
        check(contact is not None and 0 < contact < 8 and speed < 1 and last["ground"] == "1",
              f"Unexpected contact speed {contact} or settled speed {speed}")
        result.update(latitude_deg=lat, longitude_deg=lon, contact_speed_m_s=contact)
    return result
