"""Validate release inputs and write the public test report from this workflow run."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys

runtime, evidence, outputs = map(Path, sys.argv[1:])
verification = runtime / "verification"
verification.mkdir()
saves = runtime / "resources/Scenarios/Gemini VIII - Native Flight"
fixture_root = Path("Native/verification/gemini8")
lines = (fixture_root / "release-saves/SHA256SUMS").read_text().splitlines()
expected = {name: sha for sha, name in (line.split("  ", 1) for line in lines)}
rows = json.loads((evidence / "launcher/results.json").read_text())
if len(rows) != 23 or len(expected) != 23 or {r["scenario"] for r in rows} != set(expected):
    raise ValueError("Expected all 23 released scenarios and their launcher results")
if {path.name for path in saves.glob("*.scn")} != set(expected):
    raise ValueError("Packaged launch scenarios differ from the tested set")
for row in rows:
    name = row["scenario"]
    sha = hashlib.sha256((saves / name).read_bytes()).hexdigest()
    if not (sha == expected[name] == row["scenario_sha256"] and row["result"] == "passed"
            and row["simulated_seconds"] > 0 and row["audio_backend"] == "PulseAudio"):
        raise ValueError(f"Missing or mismatched launcher evidence for {name}")

mission = json.loads((evidence / "mission/mission.json").read_text())
phases = [r["phase"] for r in json.loads((fixture_root / "flight-ledger.json").read_text())]
if len(phases) != 22 or [r["phase"] for r in mission] != phases:
    raise ValueError("Incomplete linked mission")
drag = json.loads((evidence / "comparison.json").read_text())
peak = drag["peak_absolute_drag_difference_N"]["all"]
if drag["compared_steps"] != 64000 or not 0 <= peak <= 1:
    raise ValueError("Incomplete or out-of-tolerance drag comparison")
for suite in ("audio", "mission-audio", "launcher-audio"):
    sound = (evidence / suite / "audio-server.txt").read_text().splitlines()
    if "Default Sink: gemini_test" not in sound or not any(line.startswith("Volume:") and
                                                            line.count("5%") == 2 for line in sound):
        raise ValueError(f"Missing private 5% sink in {suite}")

for source, name in [("gemini-commit.txt", "gemini-commit.txt"), ("orbiter-commit.txt", "orbiter-commit.txt"),
                     ("mission/mission.json", "mission.json"), ("comparison.json", "mid-inflation.json")]:
    shutil.copyfile(evidence / source, verification / name)
gemini = (verification / "gemini-commit.txt").read_text().strip()
orbiter = (verification / "orbiter-commit.txt").read_text().strip()
if gemini != os.environ["GITHUB_SHA"]:
    raise ValueError("Tested Gemini revision differs from the workflow revision")
report = dict(passed=len(rows), gemini_commit=gemini, orbiter_commit=orbiter,
              audio_sink="private PulseAudio null sink at 5%", checks=rows)
(verification / "launcher-checks.json").write_text(json.dumps(report, indent=2) + "\n")
shutil.copyfile(verification / "launcher-checks.json", outputs / "launcher-checks.json")
notes = (runtime / "LAUNCH.md").read_text()
notes += f"\n## Verification\n\nGemini `{gemini}` and Orbiter `{orbiter}` passed the 22-phase flight, "
notes += f"the 64,000-step mid-inflation check (maximum drag difference {peak:.4f} N), "
notes += "and all 23 Qt launcher checks with private audio at 5%. "
url = f"{os.environ['GITHUB_SERVER_URL']}/{os.environ['GITHUB_REPOSITORY']}/actions/runs/{os.environ['GITHUB_RUN_ID']}"
notes += f"[Workflow run]({url})\n\n| Manual save | Launcher check |\n| --- | --- |\n"
notes += "".join(f"| {r['scenario']} | Passed |\n" for r in rows)
(outputs / "release-notes.md").write_text(notes)
