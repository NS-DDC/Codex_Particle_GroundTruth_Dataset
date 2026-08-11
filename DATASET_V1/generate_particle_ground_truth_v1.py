"""Create realistic particle test images and instance ground truth from Gray wafer images.

The source wafer is kept as the background.  This avoids replacing real die,
street, rim, and sensor-noise structure with a simplistic black synthetic
image.  The script adds controllable positive particles and known hard
non-particle / ignore cases, then writes a paired PNG + JSON annotation.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List, Tuple

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SOURCE_MODULE = ROOT.parent / "USE_LATEST"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(SOURCE_MODULE))
from use_particle_wafer_band_v1 import ParticleInspectionConfig, inspect_particles_in_wafer_band  # noqa: E402
from use_gray_wafer_die_particle import build_die_map  # noqa: E402


@dataclass
class SyntheticMap:
    """Minimal V5-compatible map written to the JSON and used by evaluation."""

    wafer_cx: float
    wafer_cy: float
    wafer_r: float
    pitch_x: float
    pitch_y: float
    x0: float
    y0: float
    aligned_image: np.ndarray


def _scale_map(dm: Any, image: np.ndarray, scale: float) -> SyntheticMap:
    """Transfer detected V5/grid geometry into the resized image coordinate system."""
    return SyntheticMap(
        wafer_cx=float(dm.wafer_cx) * scale,
        wafer_cy=float(dm.wafer_cy) * scale,
        wafer_r=float(dm.wafer_r) * scale,
        pitch_x=float(dm.pitch_x) * scale,
        pitch_y=float(dm.pitch_y) * scale,
        x0=float(dm.x0) * scale,
        y0=float(dm.y0) * scale,
        aligned_image=image,
    )


def _pick_points(mask: np.ndarray, count: int, radius: int, rng: np.random.Generator, used: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
    """Pick separated centers whose full particle patch remains inside a mask."""
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (radius * 2 + 1, radius * 2 + 1))
    safe = cv2.erode(mask.astype(np.uint8), kernel)
    ys, xs = np.nonzero(safe)
    chosen: List[Tuple[int, int]] = []
    for index in rng.permutation(len(xs)):
        point = (int(xs[index]), int(ys[index]))
        if all(np.hypot(point[0] - x, point[1] - y) >= radius * 3 for x, y in used + chosen):
            chosen.append(point)
            if len(chosen) == count:
                break
    if len(chosen) != count:
        raise RuntimeError(f"Only found {len(chosen)} of {count} safe particle locations")
    return chosen


def _make_particle_patch(template: np.ndarray, radius: int, strength: float, angle_deg: float, rng: np.random.Generator) -> Tuple[np.ndarray, np.ndarray]:
    """Transform the real particle sample into a size/intensity-varied alpha patch."""
    normalized = template.astype(np.float32) / max(1.0, float(template.max()))
    # The sample contains a black background; retain only its physical bright blob.
    alpha = np.clip((normalized - 0.10) / 0.50, 0.0, 1.0)
    side = max(5, radius * 2 + 5)
    alpha = cv2.resize(alpha, (side, side), interpolation=cv2.INTER_CUBIC)
    matrix = cv2.getRotationMatrix2D((side / 2.0, side / 2.0), angle_deg, 1.0)
    alpha = cv2.warpAffine(alpha, matrix, (side, side), flags=cv2.INTER_CUBIC, borderValue=0)
    alpha = cv2.GaussianBlur(alpha, (0, 0), max(0.35, radius / 7.0))
    texture = rng.normal(0.0, 4.0, alpha.shape).astype(np.float32)
    foreground = np.clip(strength + texture, 0, 255)
    return alpha, foreground


def _paste_particle(image: np.ndarray, center: Tuple[int, int], template: np.ndarray, radius: int, strength: float, rng: np.random.Generator) -> Dict[str, Any]:
    """Blend one physical-looking particle and return an exact bounding box annotation."""
    alpha, foreground = _make_particle_patch(template, radius, strength, float(rng.uniform(-35, 35)), rng)
    side = alpha.shape[0]
    x1, y1 = int(center[0] - side // 2), int(center[1] - side // 2)
    x2, y2 = x1 + side, y1 + side
    region = image[y1:y2, x1:x2].astype(np.float32)
    if region.shape != alpha.shape:
        raise ValueError("particle center is not safely inside image")
    image[y1:y2, x1:x2] = np.clip(region * (1.0 - alpha) + np.maximum(region, foreground) * alpha, 0, 255).astype(np.uint8)
    ys, xs = np.nonzero(alpha > 0.15)
    return {
        "center_px": [int(center[0]), int(center[1])],
        "bbox_px": [int(x1 + xs.min()), int(y1 + ys.min()), int(x1 + xs.max() + 1), int(y1 + ys.max() + 1)],
        "radius_px": radius,
        "strength": round(float(strength), 1),
    }


def _draw_rim_glare(image: np.ndarray, dm: SyntheticMap, rng: np.random.Generator) -> None:
    """Add an unlabelled rim-reflection distractor, not a particle."""
    start = int(rng.integers(0, 270))
    overlay = image.copy()
    cv2.ellipse(overlay, (int(dm.wafer_cx), int(dm.wafer_cy)), (int(dm.wafer_r - 5), int(dm.wafer_r - 5)), 0, start, start + 50, 180, 3)
    cv2.addWeighted(overlay, 0.20, image, 0.80, 0, image)


def _build_case(source_path: Path, output_dir: Path, particle_template: np.ndarray, seed: int, target_size: int, positives: int, weak_positives: int) -> Path:
    """Create one upscaled real wafer image with positives and hard negatives."""
    rng = np.random.default_rng(seed)
    source = cv2.imread(str(source_path), cv2.IMREAD_GRAYSCALE)
    if source is None:
        raise FileNotFoundError(source_path)
    source_dm = build_die_map(source, grid_method="cross", notch_align=False)
    scale = target_size / float(source.shape[0])
    aligned = source_dm.aligned_image
    if aligned.ndim == 3:
        aligned = cv2.cvtColor(aligned, cv2.COLOR_BGR2GRAY)
    image = cv2.resize(aligned, (target_size, target_size), interpolation=cv2.INTER_CUBIC)
    # Add subtle sensor/illumination variation after upscaling, preserving real wafer content.
    yy, xx = np.ogrid[:target_size, :target_size]
    illumination = 5.0 * (xx / target_size - 0.5) + 3.0 * np.sin(yy / target_size * np.pi * 1.5)
    image = np.clip(image.astype(np.float32) + illumination + rng.normal(0, 1.5, image.shape), 0, 255).astype(np.uint8)
    dm = _scale_map(source_dm, image, scale)
    config = ParticleInspectionConfig(
        band_inner_margin_px=int(round(75 * scale)),
        band_outer_margin_px=int(round(10 * scale)),
        band_guard_px=int(round(2 * scale)),
        die_exclusion_mode="die_core",
        die_core_inset_px=max(2, int(round(2 * scale))),
        partial_die_policy="exclude_all",
        min_area_px=max(8, int(round(8 * scale * scale))),
        max_area_px=int(round(350 * scale * scale)),
        min_residual_px=10.0,
        min_local_contrast=8.0,
        reject_roi_boundary_touch=True,
    )
    masks = inspect_particles_in_wafer_band(dm, config=config, return_masks=True)["masks"]
    usable = masks["inspection_mask"]
    used: List[Tuple[int, int]] = []
    annotations: List[Dict[str, Any]] = []
    # The real outer-wafer streets are only a few source pixels wide.  Keep
    # small 2~5 px particles in the 3000 px coordinate system as a dedicated
    # challenge rather than requiring an unrealistically wide empty street.
    for index, center in enumerate(_pick_points(usable, positives + weak_positives, 3, rng, used)):
        weak = index >= positives
        radius = int(rng.choice([2, 3, 4, 5]))
        item = _paste_particle(image, center, particle_template, radius, 140.0 if weak else 225.0, rng)
        item.update({"label": "particle", "difficulty": "weak" if weak else "normal", "evaluation": True})
        annotations.append(item)
        used.append(center)

    # Add bright distractors in prohibited die areas: these are intentionally not particles.
    die_area = ((masks["die_exclusion_mask"] > 0) & (masks["ring_mask"] > 0)).astype(np.uint8)
    for center in _pick_points(die_area, 5, 3, rng, used):
        cv2.circle(image, center, int(rng.integers(3, 6)), int(rng.integers(190, 245)), -1)
        annotations.append({"label": "non_particle_die_signal", "center_px": list(center), "evaluation": False})
        used.append(center)

    # Two close particles expose merged-component behaviour; keep both as GT.
    merged_center = _pick_points(usable, 1, 6, rng, used)[0]
    for dx in (-3, 3):
        center = (merged_center[0] + dx, merged_center[1])
        item = _paste_particle(image, center, particle_template, 2, 210.0, rng)
        item.update({"label": "particle", "difficulty": "merged_pair", "group_id": "merged_pair_1", "evaluation": True})
        annotations.append(item)
    _draw_rim_glare(image, dm, rng)

    # A boundary candidate is not used for precision/recall because it is cut by the ROI definition.
    inner_r = dm.wafer_r - config.band_inner_margin_px + config.band_guard_px
    boundary_center = (int(round(dm.wafer_cx + inner_r)), int(round(dm.wafer_cy)))
    item = _paste_particle(image, boundary_center, particle_template, 2, 220.0, rng)
    item.update({"label": "ignore_roi_boundary", "evaluation": False})
    annotations.append(item)

    stem = source_path.stem + "_particle_gt"
    image_path = output_dir / f"{stem}.png"
    json_path = output_dir / f"{stem}.json"
    cv2.imwrite(str(image_path), image)
    payload = {
        "schema_version": "particle_ground_truth_v1",
        "source_image": str(source_path),
        "image_file": image_path.name,
        "coordinate_space": "aligned",
        "image_shape": [target_size, target_size],
        "wafer": {key: getattr(dm, key) for key in ("wafer_cx", "wafer_cy", "wafer_r")},
        "grid": {key: getattr(dm, key) for key in ("pitch_x", "pitch_y", "x0", "y0")},
        "inspection_config": asdict(config),
        "annotations": annotations,
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return json_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--images", nargs="+", required=True, help="Real Gray wafer PNG files")
    parser.add_argument("--particle-template", required=True)
    parser.add_argument("--output-dir", default=str(Path(__file__).parent / "generated"))
    parser.add_argument("--target-size", type=int, default=3000)
    parser.add_argument("--seed", type=int, default=20260811)
    args = parser.parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    template = cv2.imread(args.particle_template, cv2.IMREAD_GRAYSCALE)
    if template is None:
        raise FileNotFoundError(args.particle_template)
    manifests = []
    for index, path_text in enumerate(args.images):
        manifests.append(_build_case(Path(path_text), output_dir, template, args.seed + index, args.target_size, positives=8, weak_positives=4))
    (output_dir / "manifest.json").write_text(json.dumps([path.name for path in manifests], indent=2), encoding="utf-8")
    print(json.dumps({"generated_cases": len(manifests), "output_dir": str(output_dir), "manifests": [str(path) for path in manifests]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
