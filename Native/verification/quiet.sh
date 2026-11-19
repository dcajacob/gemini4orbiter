#!/usr/bin/env bash
# SPDX-License-Identifier: BSD-3-Clause
set -euo pipefail
log_dir=$(realpath "$1")
shift
mkdir -p "$log_dir"
audio_dir=$(mktemp -d)
export PULSE_RUNTIME_PATH="$audio_dir" PULSE_SERVER="unix:$audio_dir/pulse.sock" PULSE_SINK=gemini_test
export LIBGL_ALWAYS_SOFTWARE=1 LP_NUM_THREADS=2 QT_QPA_PLATFORM=xcb XDG_SESSION_TYPE=x11
env DBUS_SESSION_BUS_ADDRESS="unix:path=$audio_dir/no-bus" pulseaudio -n --daemonize=no --exit-idle-time=-1 --log-target=stderr -L "module-native-protocol-unix socket=$audio_dir/pulse.sock" -L "module-null-sink sink_name=$PULSE_SINK" > "$log_dir/pulseaudio.log" 2>&1 &
audio_pid=$!
trap 'kill "$audio_pid" 2>/dev/null || true; wait "$audio_pid" 2>/dev/null || true; rm -rf "$audio_dir"' EXIT
for attempt in {1..50}; do
 pactl info > "$log_dir/audio-server.txt" 2>/dev/null && break
 sleep .2
done
pactl set-sink-volume "$PULSE_SINK" 5%
pactl get-sink-volume "$PULSE_SINK" >> "$log_dir/audio-server.txt"
env -u WAYLAND_DISPLAY xvfb-run -a -s '-screen 0 1600x1000x24 +extension GLX' "$@"
