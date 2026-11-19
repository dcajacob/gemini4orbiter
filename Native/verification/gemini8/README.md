# Gemini VIII continuous native flight

The original `Scenarios/Earth 1962/Gemini VIII.scn` was flown from the pad through
Titan II ascent, Agena rendezvous and physical port capture, undocking, retrofire,
entry, automatic drogue/main deployment and Pacific splashdown. The 22 phases
share one physical save lineage. No scenario position, velocity, attitude, fuel or
docking state was substituted between phases. Failed trials remain outside this
accepted chain. View and script metadata are the only scenario edits.

Measured milestones:

- Initial orbit approximately 206 x 315 km; original Agena target retained.
- Final braking burn: 68.108 m/s target, residual below 0.08 m/s.
- Actual docking at 360.5625 seconds into phase 13, using original OAMS controls.
  Both vessels serialize their real mutual DOCKINFO; no dock setter was used.
- Original L/J undocking, J equipment separation, D/D four-motor retrofire and J
  adapter separation. The original tanks were used without refilling.
- Retrofire orbit approximately 44 x 351 km. Deorbit was timed for the Pacific.
- Entry peak drag deceleration 6.18 g. The pilot banks the original lift vector
  upward and stops attitude commands below 20 km before parachute descent.
- Splashdown near 19.7761 N, 142.1289 E, at 6.37 m/s after automatic main release
  below 3 m. Final capsule settled at zero speed with 32.305 kg RCS fuel remaining.

## Launch

Start `./launch-orbiter` from the packaged native runtime. Choose **Gemini VIII -
Native Flight**. All 22 saves are ordinary manual-flight checkpoints with the
automated pilot removed. Space resumes the initial pause. The sunlit **09 braking-
point** checkpoint has an Earth-facing exterior view. Docking and recovery occur
at night, so their unlit exterior views are dark. F1 switches cockpit/exterior.

Alt+1 through Alt+7 selects the original seven-position attitude selector; Alt+5
is DIRECT and Alt+7 is passive HORSCAN. Numpad controls attitude/translation;
standard Orbiter ROT/LIN selection still applies. L then J releases Agena. Once
separated, J jettisons the equipment section, D arms retrofire, D again starts the
sequence, and a later J discards the retro adapter. The original manual is bundled.

## Fixes and qualification

The port now allocates each legacy anonymous user-thruster group at its own
explicit SDK index, forwards focus after stage replacement, reads angular rates
for the rate controller, and uses the intended 35 kg RCS tank instead of the
420 kg OAMS constant. These changes restored actual manual attitude control.

The engine patch also fixes legacy backward drag: `SetCW`'s negative-Z coefficient
was stored but never selected. The previous entry trial delayed deceleration
until chute altitude; the corrected trial gives the 6.18 g peak above. This
engine change is included in `Native/orbiter-integration.patch`, not a separate
unpublished edit to the main Orbiter checkout. Entry phases 19 onward use it.

Main parachutes previously reloaded without their mesh or drag. Deployment phase,
inflation progress and remaining reefing time are now saved/restored for both
canopies. Old deployed saves infer a fully open canopy. The final descent was
replayed after this fix. A separate test saved during reefing at 2.125 s, reloaded
for 6 s to 8.125 s, then reloaded for another 6 s and reached full opening. The
RETRO token parser also no longer swallows RETRO_SEQ and RETRO_TIMER.

Final-build checks: 41 normal-launcher scenarios (13 originals, six regenerated
representative saves, 22 mission saves); resize, resume, quicksave and clean close;
seven flight regressions; a separate replay of actual Agena capture; reefing and
fully open main-chute reloads. Native OpenGL 4.5/llvmpipe on Xvfb, native XRSound,
no Wine. Every test uses a private PulseAudio null sink at 5%, without changing
desktop audio volume. Hardware GPU, Windows and macOS are not qualified here.

This remains the simplified original Gemini 4.5 simulation. The flight is a normal
launch/docking/return exercise, not a reconstruction of Gemini VIII's stuck-thruster
emergency. Original parachute areas, barometric deployment and contact-release
logic remain; slow main-canopy descent is not a new validated recovery model.
Discarded-stage dynamics and long-term debris propagation are not qualified.

## Evidence and replay

`flight-ledger.json` and `fixtures/` preserve original inputs, finalized saves,
exact per-phase pilot versions, input replays and hashes. Those pilot versions
changed during flight development; use the frozen version for a checkpoint
replay. Early checkpoints saved just before their last physics step; actual MJD
in each record is authoritative. Native engine/module fixes were applied at
preserved checkpoints as blockers were found; this is not a claim that an
unchanging binary was used for the entire development flight.

Audit the lineage, optionally including the full local telemetry directory:

```sh
python3 Native/verification/gemini8/verify.py
python3 Native/verification/gemini8/verify.py --evidence /path/to/gemini8
```

Replay selected recorded inputs on a matching staged runtime:

```sh
Native/verification/quiet.sh /tmp/gemini-replay-audio \
  python3 Native/verification/gemini8/replay.py /path/to/runtime \
  /tmp/gemini-replay 13-docking 22-splashdown
```

`replay.py` starts each selected regression from its recorded input. To develop a
new continuation, `runner.py` injects only script/view metadata and asserts the
physical SHIPS block is unchanged. `pilot.lua` uses original keyboard controls,
real thrusters and the Agena's real kill-rotation mode. `orbit.py` supplies
approximate two-body finite-burn targeting (NumPy/SciPy); native Orbiter performs
all actual propagation. Coarse attitude/translation pulses caused fuel-wasting
limit cycles during development; terminal approach and docking use 0.03125 s.
