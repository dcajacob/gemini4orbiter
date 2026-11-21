"""Target the linked mission's OAMS burns from the flown Gemini and Agena states."""
import json

from orbit import match_velocity, propagate, rendezvous, state


def set_burn_target(fixture, save, duration):
    # Seconds to arrival from each phase start. The last 200 s of the braking
    # phase allow the pilot to finish trim before switching to terminal control.
    times = {"02-orient": 12500, "03-transfer-burn": 12500, "04-transfer-completion": 11900,
             "06-midcourse-correction": 2400, "08-intercept-correction": 1200}
    chaser, target = (state(save, name) for name in ("GEMINI", "GATV"))
    plan = json.loads((fixture / "plan.json").read_text())
    if fixture.name == "10-rendezvous-braking":
        delta, separation = match_velocity(chaser, target, target[3:] - chaser[3:])
        plan = dict(mode="burn", dv=delta.tolist(), predicted_separation=separation)
    else:
        if fixture.name == "02-orient":
            chaser, target = propagate(chaser, duration), propagate(target, duration)
        delta, _ = rendezvous(chaser, target, times[fixture.name])
        if plan["mode"] == "orient":
            plan = dict(mode="orient", direction=delta.tolist())
        else:
            plan = dict(mode="burn", dv=delta.tolist(), tolerance=plan.get("tolerance", 0.08))
    return plan


def pilot_source(fixture, case, save, record):
    plan = set_burn_target(fixture, save, record["seconds"])
    plan["duration"] = record["seconds"] - 2 * record["step"]
    (case / "burn-plan.json").write_text(json.dumps(plan, indent=2) + "\n")
    fields = []
    for name, value in plan.items():
        if isinstance(value, list):
            encoded = "{" + ",".join(map(str, value)) + "}"
        else:
            encoded = json.dumps(value)
        fields.append(f"{name}={encoded}")
    return "local plan={" + ",".join(fields) + "}\n" + (fixture.parents[1] / "pilot.lua").read_text()
