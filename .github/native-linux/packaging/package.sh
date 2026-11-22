#!/usr/bin/env bash
# Stream the archive into upload-sized parts to avoid a second multi-GB copy.
set -euo pipefail
runtime=$(realpath "$1")
evidence=$(realpath "$2")
output=$(realpath -m "$3")
scripts=$(dirname "$(realpath "$0")")
mkdir "$output"
name=Gemini-VIII-Linux-OpenGL-x86_64
archive=$name.tar.zst
stage=$(mktemp -d "$(dirname "$runtime")/release-stage.XXXXXXXX")
trap 'rm -rf "$stage"' EXIT
# Hardlink the exact runtime checked above. Exclude session files and test pilots.
rsync -a --link-dest="$runtime" --exclude=/user --exclude=/verification \
    --exclude=/resources/Script/Gemini8/ --exclude='/resources/Scenarios/Gemini - Native Linux Saves/' \
    "$runtime/" "$stage/$name/"
root="$stage/$name"
mkdir -p "$root/user/Scenarios"
cp "$scripts/LAUNCH.md" "$output/LAUNCH.md"
cp "$scripts/LAUNCH.md" "$root/LAUNCH.md"
for executable in launch-orbiter engine/orbiter-launchpad engine/run-orbiter engine/orbiter-production; do
    test -x "$root/$executable"
done
python3 "$scripts/evidence.py" "$root" "$evidence" "$output"
# tar's compare operation reads back the split stream and checks its contents
# against this exact staging tree, including the PR/tag-tested engine and saves.
cd "$output"
tar --sort=name --numeric-owner -C "$stage" -cf - "$name" |
    zstd -q -3 -T2 -c | split -b 1800M --numeric-suffixes=1 -a 2 - "$archive.part"
parts=("$archive".part[0-9][0-9])
sha256sum "${parts[@]}" > SHA256SUMS.parts
cat "${parts[@]}" | sha256sum | sed "s/  -$/  $archive/" > "$archive.sha256"
cat "${parts[@]}" | zstd -qd -c | tar --compare --numeric-owner -C "$stage" -f -
printf '\nFull archive SHA-256: `%s`\n' "$(cut -d ' ' -f1 "$archive.sha256")" >> release-notes.md
