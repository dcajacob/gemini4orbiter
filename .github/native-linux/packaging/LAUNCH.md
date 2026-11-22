# Gemini VIII for native Linux x86-64 OpenGL

Download every numbered `.tar.zst.partNN` file, `SHA256SUMS.parts`, and
`Gemini-VIII-Linux-OpenGL-x86_64.tar.zst.sha256` from the same release into
a new writable directory. From that directory run:

```sh
archive=Gemini-VIII-Linux-OpenGL-x86_64.tar.zst
sha256sum -c SHA256SUMS.parts &&
cat "$archive".part[0-9][0-9] > "$archive" &&
sha256sum -c "$archive.sha256" &&
tar --zstd -xf "$archive" &&
cd Gemini-VIII-Linux-OpenGL-x86_64 &&
./launch-orbiter
```

In the Qt Launchpad's **Scenarios** tab, open **Gemini VIII - Native Flight**,
select a save, and click **Launch**. The 22 numbered saves cover the flight
from ascent through Agena docking and Pacific recovery. **20a Main canopy
inflating** is a separate manual mid-inflation checkpoint. To start on the pad,
choose **Earth 1962 → Gemini VIII**. **Space** resumes a paused flight.
**Ctrl+S** saves to `user/Scenarios`.

The tested environment is Ubuntu 26.04 x86-64 with Qt 6 Widgets, X11/XWayland,
Mesa OpenGL and PulseAudio-compatible sound. The spacecraft manual is
`Gemini_Titan2_45.pdf`. The `verification/` folder contains the tested
revisions, per-save launcher results, linked flight report and drag comparison.
