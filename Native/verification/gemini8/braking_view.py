# SPDX-License-Identifier: BSD-3-Clause
"""Check the paused braking-point view in the simulator's own X11 window."""
from contextlib import closing
import time

import numpy as np
from PIL import Image
from Xlib import X, display

MIN_FRACTIONS = {"earth_left": 0.60, "earth_right": 0.60, "bright_clouds": 0.10,
                 "capsule_center": 0.60, "space_below_limb": 0.60}

def view_fractions(image):
    # Use normalized regions so the check tolerates differences in resolution,
    # texture detail and antialiasing between Intel hardware and llvmpipe.
    pixels = np.asarray(image.resize((100, 100), Image.Resampling.BOX), dtype=np.int16)
    red, green, blue = pixels.transpose(2, 0, 1)
    earth = (blue > 85) & (blue > red + 22) & (blue > green + 8)
    clouds = earth & (red > 130)
    capsule = (pixels.max(axis=2) - pixels.min(axis=2) < 22) & (red > 42) & (red < 220)
    space = pixels.max(axis=2) < 35
    return {
        "earth_left": float(earth[6:58, 4:29].mean()),
        "earth_right": float(earth[6:58, 71:96].mean()),
        "bright_clouds": float((clouds[6:58, 4:29].mean() + clouds[6:58, 71:96].mean()) / 2),
        "capsule_center": float(capsule[30:63, 47:53].mean()),
        "space_below_limb": float(space[96:, :].mean()),
    }


def check_braking_view(window_id, screenshot):
    with closing(display.Display()) as connection:
        window = connection.create_resource_object("window", window_id)
        geometry = window.get_geometry()
        size = (geometry.width, geometry.height)
        info = connection.display.info
        if info.image_byte_order != X.LSBFirst or not any(
            fmt.depth == geometry.depth == 24 and fmt.bits_per_pixel == 32 for fmt in info.pixmap_formats
        ):
            raise ValueError("Expected a 24-bit X11 window with 32-bit little-endian pixel storage")
        # The window and atmosphere appear before the cloud textures finish loading.
        deadline = time.monotonic() + 30
        while True:
            frame = window.get_image(0, 0, *size, X.ZPixmap, 0xffffffff)
            image = Image.frombytes("RGB", size, frame.data, "raw", "BGRX")
            fractions = view_fractions(image)
            if all(fractions[key] >= minimum for key, minimum in MIN_FRACTIONS.items()):
                image.save(screenshot)
                return fractions
            if time.monotonic() >= deadline:
                image.save(screenshot)
                raise ValueError(f"Braking-point opening view failed: {fractions}")
            time.sleep(0.25)
