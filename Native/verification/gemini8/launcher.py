#!/usr/bin/env python3
"""Launch the released Gemini VIII manual saves through the normal Qt Launchpad."""
import argparse
import ctypes as c
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import tempfile
import time

from analyze_entry import check
from mission import ship_state

RELEASE = Path(__file__).with_name("release-saves")
SCENARIOS = Path("resources/Scenarios/Gemini VIII - Native Flight")
MID_INFLATION = "20a Main canopy inflating.scn"

xlib = c.CDLL("libX11.so.6")
xtst = c.CDLL("libXtst.so.6")
xlib.XOpenDisplay.argtypes = [c.c_char_p]
xlib.XOpenDisplay.restype = c.c_void_p
xlib.XFlush.argtypes = [c.c_void_p]
xlib.XSetInputFocus.argtypes = [c.c_void_p, c.c_ulong, c.c_int, c.c_ulong]
xlib.XKeysymToKeycode.argtypes = [c.c_void_p, c.c_ulong]
xlib.XKeysymToKeycode.restype = c.c_uint
xtst.XTestFakeMotionEvent.argtypes = [c.c_void_p, c.c_int, c.c_int, c.c_int, c.c_ulong]
xtst.XTestFakeButtonEvent.argtypes = [c.c_void_p, c.c_uint, c.c_int, c.c_ulong]
xtst.XTestFakeKeyEvent.argtypes = [c.c_void_p, c.c_uint, c.c_int, c.c_ulong]
class ClientMessage(c.Structure):
    _fields_ = [("type", c.c_int), ("serial", c.c_ulong), ("send_event", c.c_int),
                ("display", c.c_void_p), ("window", c.c_ulong), ("message_type", c.c_ulong),
                ("format", c.c_int), ("data", c.c_long * 5)]

class XEvent(c.Union):
    _fields_ = [("client", ClientMessage), ("padding", c.c_long * 24)]

xlib.XInternAtom.argtypes = [c.c_void_p, c.c_char_p, c.c_int]
xlib.XInternAtom.restype = c.c_ulong
xlib.XSendEvent.argtypes = [c.c_void_p, c.c_ulong, c.c_int, c.c_long, c.POINTER(XEvent)]
xlib.XResizeWindow.argtypes = [c.c_void_p, c.c_ulong, c.c_uint, c.c_uint]
display = xlib.XOpenDisplay(None)
if not display:
    raise RuntimeError("An X11 display is required")

def find_window(title):
    tree = subprocess.check_output(["xwininfo", "-root", "-tree"], text=True)
    for row in tree.splitlines():
        if title in row and (matched := re.search(r"0x[0-9a-f]+", row)):
            info = subprocess.check_output(["xwininfo", "-id", matched[0]], text=True)
            if "Map State: IsViewable" in info and int(re.search(r"Width:\s+(\d+)", info)[1]) > 300:
                return int(matched[0], 16), row.strip()
    return None

def wait_window(title, process):
    for _ in range(480):
        found = find_window(title)
        if found is not None:
            return found
        assert process.poll() is None
        time.sleep(.25)
    tree = subprocess.check_output(["xwininfo", "-root", "-tree"], text=True)
    raise RuntimeError(f"Missing window {title}\n{tree}")

def keys(window, *syms):
    xlib.XSetInputFocus(display, window, 1, 0)
    codes = [xlib.XKeysymToKeycode(display, sym) for sym in syms]
    for key in codes:
        xtst.XTestFakeKeyEvent(display, key, 1, 0)
    xlib.XFlush(display)
    time.sleep(.18)
    for key in codes[::-1]:
        xtst.XTestFakeKeyEvent(display, key, 0, 0)
    xlib.XFlush(display)

def close(window):
    event = XEvent()
    event.client.type = 33
    event.client.display = display
    event.client.window = window
    event.client.message_type = xlib.XInternAtom(display, b"WM_PROTOCOLS", 0)
    event.client.format = 32
    event.client.data[0] = xlib.XInternAtom(display, b"WM_DELETE_WINDOW", 0)
    assert xlib.XSendEvent(display, window, 0, 0, c.byref(event))
    xlib.XFlush(display)


def stage_saves(runtime):
    entries = [line.split("  ", 1) for line in (RELEASE / "SHA256SUMS").read_text().splitlines()]
    ledger = json.loads(Path(__file__).with_name("flight-ledger.json").read_text())
    expected = {row["phase"].replace("-", " ", 1) + ".scn" for row in ledger} | {MID_INFLATION}
    check(len(entries) == len(expected) == 23 and {name for _, name in entries} == expected,
          "Expected all 22 mission saves and the separate canopy save")
    folder = runtime / SCENARIOS
    folder.mkdir(parents=True, exist_ok=True)
    for digest, name in entries:
        data = (RELEASE / name).read_bytes()
        check(hashlib.sha256(data).hexdigest() == digest, f"Release fixture differs: {name}")
        # Replace the staged copy, including when a local runtime uses hardlinks.
        dest = folder / name
        dest.unlink(missing_ok=True)
        dest.write_bytes(data)
    return entries


def launch_selected(gui):
    window, _ = wait_window('"Orbiter Launchpad"', gui)
    details = subprocess.check_output(["xwininfo", "-id", hex(window)], text=True)
    x, y, width, height = [int(re.search(key + r"\s+(-?\d+)", details)[1]) for key in
                           ("Absolute upper-left X:", "Absolute upper-left Y:", "Width:", "Height:")]
    xlib.XSetInputFocus(display, window, 1, 0)
    xtst.XTestFakeMotionEvent(display, -1, x + width - 65, y + height - 22, 0)
    xtst.XTestFakeButtonEvent(display, 1, 1, 0)
    xtst.XTestFakeButtonEvent(display, 1, 0, 0)
    xlib.XFlush(display)


def verify_child(gui, runtime, scenario):
    children = Path(f"/proc/{gui.pid}/task/{gui.pid}/children").read_text().split()
    check(len(children) == 1, f"Expected one simulator child: {children}")
    proc = Path("/proc") / children[0]
    args = (proc / "cmdline").read_bytes().decode().rstrip("\0").split("\0")
    check(args[0] == str(runtime / "engine/orbiter-production"), "Unexpected simulator executable")
    for flag, path in [("--scenario", scenario), ("--modules", runtime / "engine/NativeModules"),
                       ("--xrsound-assets", runtime / "resources")]:
        check(args[args.index(flag) + 1] == str(path), f"Incorrect {flag} in launcher arguments")
    maps = (proc / "maps").read_text().splitlines()
    mapped_paths = {fields[5] for line in maps if len(fields := line.split(maxsplit=5)) == 6}
    for name in ("liborbiter_production_boundary.so", "liborbiter_production_vessels.so",
                 "NativeModules/Vessel/Gemini_Titan.so", "NativeModules/Vessel/GATV.so",
                 "NativeModules/Plugin/XRSound.so", "NativeModules/Graphics/OGLClient.so"):
        check(str(runtime / "engine" / name) in mapped_paths, f"Packaged module missing: {name}")
    return proc


def verify_quicksave(scenario, save):
    for _ in range(240):
        if save.is_file() and b"END_SHIPS" in save.read_bytes():
            break
        time.sleep(.25)
    original, saved = scenario.read_text(), save.read_text()
    pattern = re.compile(r"^\s*Date MJD\s+([0-9.]+)", re.M)
    elapsed = (float(pattern.search(saved)[1]) - float(pattern.search(original)[1])) * 86400
    check(elapsed > 0 and "END_SHIPS" in saved, "Quicksave must contain advancing simulation time")
    gemini = ship_state(saved, "GEMINI")
    result = {"simulated_seconds": elapsed}
    if scenario.name == "13 docking.scn":
        agena = ship_state(saved, "GATV")
        check("0:0,GATV" in gemini["DOCKINFO"].split() and "0:0,GEMINI" in agena["DOCKINFO"].split(),
              "Quicksave lost the mutual Gemini–Agena docking connection")
    elif scenario.name == MID_INFLATION:
        before = float(ship_state(original, "GEMINI")["MAIN_CHUTE_STATE"].split()[1])
        after = float(gemini["MAIN_CHUTE_STATE"].split()[1])
        check(0 < before < after <= 1 and gemini["MAIN_DEPLOYED"] == "1.0", "Main canopy did not inflate")
        result.update(main_canopy_fraction_at_load=before, main_canopy_fraction_after_resume=after)
    elif scenario.name == "22 splashdown.scn":
        check(gemini["STATUS"] == "Landed Earth" and gemini["MAIN_JETTISONED"] == "1.0",
              "Quicksave lost the landed capsule or main release")
    return result


def exercise(runtime, scenario, case, config):
    settings = config / "Orbiter/Orbiter Launchpad.conf"
    settings.parent.mkdir(parents=True)
    settings.write_text(f"[simulator]\nlastScenario={scenario}\nstartPaused=true\n")
    log = runtime / "user/orbiter-session.log"
    audio = runtime / "user/XRSound.log"
    save = runtime / "user/Scenarios/Quicksave.scn"
    check(not any(path.exists() for path in (log, audio, save)), "Use a clean disposable runtime")
    with (case / "launcher.log").open("w") as output:
        gui = subprocess.Popen([runtime / "launch-orbiter"], env=dict(os.environ, XDG_CONFIG_HOME=str(config)),
                               stdout=output, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            launch_selected(gui)
            window, title = wait_window("| GEMINI | PAUSED", gui)
            proc = verify_child(gui, runtime, scenario)
            xlib.XResizeWindow(display, window, 1180, 720)
            xlib.XFlush(display)
            time.sleep(.75)
            info = subprocess.check_output(["xwininfo", "-id", hex(window)], text=True)
            check("Width: 1180" in info and "Height: 720" in info, "Simulator did not resize")
            keys(window, 0x0020)  # Space resumes the selected save.
            _, running = wait_window("| GEMINI | RUNNING", gui)
            keys(window, 0xffe3, 0x0073)  # Ctrl+S
            result = verify_quicksave(scenario, save)
            close(window)
            for attempt in range(240):
                if not proc.exists():
                    break
                if attempt % 12 == 11 and find_window('| GEMINI |'):
                    close(window)
                time.sleep(.25)
            check(not proc.exists(), "Simulator did not exit after closing the window")
            renderer = re.search(r"^Native OpenGL renderer:\s*(.+)$", log.read_text(), re.M)
            sound = audio.read_text()
            check(renderer and "initialized using sound driver PulseAudio" in sound and "terminating." in sound,
                  "Missing OpenGL or XRSound session evidence")
            return dict(result, paused=title, resumed=running, resized="1180x720", renderer=renderer[1],
                        audio_backend="PulseAudio")
        finally:
            try:
                os.killpg(gui.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                gui.wait(timeout=6)
            except subprocess.TimeoutExpired:
                os.killpg(gui.pid, signal.SIGKILL)
                gui.wait()
            for path in (log, audio, save):
                if path.is_file():
                    shutil.move(path, case / path.name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("runtime", type=Path, help="disposable staged runtime")
    parser.add_argument("output", type=Path, help="new directory for results and per-save diagnostics")
    args = parser.parse_args()
    runtime = args.runtime.resolve()
    entries = stage_saves(runtime)
    args.output.mkdir(parents=True, exist_ok=False)
    results = []
    with tempfile.TemporaryDirectory(prefix="gemini-launcher-") as config:
        for index, (digest, name) in enumerate(entries, 1):
            case = args.output / f"checkpoint-{index:02d}"
            case.mkdir()
            scenario = runtime / SCENARIOS / name
            row = {"scenario": name, "scenario_sha256": digest}
            try:
                check(hashlib.sha256(scenario.read_bytes()).hexdigest() == digest, "Wrong staged save")
                row.update(exercise(runtime, scenario, case, Path(config) / case.name), result="passed")
            except Exception as error:
                row.update(result="failed", error=f"{type(error).__name__}: {error}")
            results.append(row)
            (args.output / "results.json").write_text(json.dumps(results, indent=2) + "\n")
            print(name, row["result"], row.get("error", ""), flush=True)
    check(all(row["result"] == "passed" for row in results), "One or more launcher checks failed")


if __name__ == "__main__":
    main()
