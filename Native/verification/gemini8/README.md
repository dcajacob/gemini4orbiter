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
- Entry peak drag deceleration approximately 6.18 g in the accepted save chain. The pilot banks the original lift vector
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

The engine patch selects the negative-Z axial drag coefficient in the legacy
`SetCW` model when the capsule travels backward along its body axis. The entry
pilot also rolls the capsule to direct its existing lift upward. Both changes
were in use from phase 19 of the accepted chain. The controlled replays below
measure their effects separately.

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

## Same-save entry comparisons

Each case starts from the phase 18 adapter-separation save at 106.566 km. The
runner checks the spacecraft section of the input against the fixture. The
analyzer compares initial epoch, position, velocity, attitude, angular rates,
mass and fuel, then reads every native physics sample through 4,000 s at 1/32 s
per step. The runs use a single engine session each. Original chute logic and the
20 km attitude-control cutoff apply in every case.

| Axial drag | Commanded bank | Pre-drogue peak (g) | Peak including chutes (g) | Drogue airspeed (m/s) | Splashdown |
|---|---|---:|---:|---:|---|
| Original | Original | 41.55 | 95.46 | 3,482 | 18.85° N, 139.73° E |
| Corrected | Original | 11.87 | 11.87 | 273 | 17.66° N, 136.84° E |
| Original | Lift up | 1.55 | 5.19 | 598 | 26.16° N, 149.80° W |
| Corrected | Lift up | 5.07 | 6.17 | 243 | 19.78° N, 142.13° E |

Peak load is the magnitude of the reported aerodynamic acceleration,
`hypot(lift, drag) / (mass × 9.80665)`. The bank command reversed the mean radial
lift during high-speed atmospheric flight (airspeed above 2,000 m/s and dynamic
pressure above 1,000 Pa) with either drag model. With upward lift the original
drag gave a lower peak, but drogue deployment came 1,155 s later and the two
splashdowns were about 6,930 km apart by great-circle distance. In the original
bank and drag case the largest load came **after** drogue deployment. The model
recorded surface contact for all four runs. It provides no crew-survival
qualification.

To reproduce, stage two separate Gemini-capable runtimes from the same source
and assets. Use the integration source described in [the build notes](../../README.md)
and its Gemini patch for the fixed engine. For the control build, restore the
`vd_forw*fabs(vnorm.z)` axial term in `Vessel::UpdateAerodynamicForces_OLD`
before building. Build the renderer and Gemini modules against the corresponding
engine SDK for each runtime. The qualified integration snapshot is available
in the local `out/gemini-native/engine-source` checkout. Each runtime needs its
own writable `resources/Script` directory.

From the Gemini repository root, point `work` at a fresh SSD scratch directory
and run the four cases under the private 5% audio sink.

```sh
work=$(mktemp -d /var/tmp/dan-builds/gemini-entry.XXXXXXXX)
export TMPDIR="$work"
Native/verification/quiet.sh "$work/audio" \
  python3 Native/verification/gemini8/compare_entry.py \
  /path/to/original-runtime /path/to/fixed-runtime "$work/runs"
```

The runner writes the two input hashes, a one-second trace, the full-rate force
and state evidence, deployment events and the final save for each case. Recheck
an existing run with `python3 Native/verification/gemini8/analyze_entry.py "$work/runs"`.
Two independent sets of four runs produced identical full-rate force and state
files and final saves per case. [Recorded results and binary hashes](entry-comparison.json).
