#!/usr/bin/env python3
"""Fly the continuous entry and the mid-inflation restart on the same runtime."""
import argparse
import json
import subprocess
import sys
from pathlib import Path

from check_inflation import CHECKPOINT, DURATION, compare
from compare_entry import ROOT, STEP, fly, instrument_pilot


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("runtime", type=Path)
    parser.add_argument("output", type=Path, help="new directory for both flights")
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    runtime = args.runtime.resolve()
    fly(output, runtime, "fixed", True, instrument_pilot())
    resumed = output / "mid-inflation"
    subprocess.run([sys.executable, ROOT / "runner.py", runtime, resumed, CHECKPOINT,
                    "--seconds", str(DURATION), "--step", str(STEP)], check=True)
    result = compare(output / "fixed-bank-up", resumed)
    report = json.dumps(result, indent=2)
    (output / "comparison.json").write_text(report + "\n")
    print(report)


if __name__ == "__main__":
    main()
