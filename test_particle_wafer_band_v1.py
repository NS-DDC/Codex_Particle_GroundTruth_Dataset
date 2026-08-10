"""Synthetic regression test for use_particle_wafer_band_v1.py.

Run from this directory:
    python test_particle_wafer_band_v1.py
"""

import sys
from pathlib import Path

import cv2
import numpy as np

from use_particle_wafer_band_v1 import (
    ParticleInspectionConfig,
    inspect_particles_in_wafer_band,
    render_particle_diagnostic_overlay,
)

# The test intentionally constructs the actual V5 dataclass, proving that this
# module has no incompatible duplicate WaferDieMap type.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "USE_LATEST"))
from wafer_die_map_v5 import WaferDieMap  # noqa: E402


def make_test_dm() -> WaferDieMap:
    """Create a small wafer with one street particle and one bright die pattern."""
    image = np.zeros((256, 256), np.uint8)
    cv2.circle(image, (128, 128), 100, 80, -1)
    # A normal bright signal inside a die must be protected by die_core masking.
    cv2.circle(image, (206, 131), 4, 255, -1)
    # A particle in the grid street at the wafer band must remain inspectable.
    cv2.circle(image, (188, 128), 3, 255, -1)
    return WaferDieMap(
        wafer_cx=128,
        wafer_cy=128,
        wafer_r=100,
        pitch_x=32.0,
        pitch_y=32.0,
        x0=128.0,
        y0=128.0,
        die_w=32,
        die_h=32,
        pixel_per_unit=1,
        aligned_image=image,
    )


def main() -> None:
    dm = make_test_dm()
    result = inspect_particles_in_wafer_band(
        dm,
        config=ParticleInspectionConfig(
            band_inner_margin_px=40,
            band_outer_margin_px=2,
            band_guard_px=0,
            die_exclusion_mode="die_core",
            die_core_inset_px=3,
            partial_die_policy="exclude_all",
            min_area_px=5,
            min_residual_px=10,
            min_local_contrast=5,
            reject_roi_boundary_touch=False,
        ),
        return_masks=True,
    )
    assert result["summary"]["accepted_particles"] >= 1, result
    assert all(p["coordinate_space"] == "aligned" for p in result["particles"])
    assert result["summary"]["inspection_pixels"] > 0
    # A bright normal die and a center-outside partial die are both protected.
    assert result["masks"]["die_exclusion_mask"][131, 206] == 1
    assert result["masks"]["die_exclusion_mask"][128, 224] == 1
    overlay = render_particle_diagnostic_overlay(dm, result)
    assert overlay.shape == (256, 256, 3)
    print({"accepted": result["summary"]["accepted_particles"], "threshold": result["summary"]["residual_threshold"]})


if __name__ == "__main__":
    main()
