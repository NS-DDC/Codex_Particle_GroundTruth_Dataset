"""Wafer band particle inspection for a V5-style ``WaferDieMap``.

This file is intentionally independent from ``wafer_die_map_v5.py``.  Pass the
``dm`` returned by V5 ``build_die_map()`` directly; no duplicate WaferDieMap
class or import from a different particle module is required.

Coordinate convention
---------------------
All input/output coordinates use ``dm.aligned_image``.  If V5 rotated the
wafer, map the result back to the camera image in the caller that owns the
rotation transform.

Dependencies: numpy, opencv-python (Python 3.9+)
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Literal, Optional, Tuple

import cv2
import numpy as np

DieExclusionMode = Literal["none", "grid_cell", "die_core"]
PartialDiePolicy = Literal["exclude_all", "die_core"]

__all__ = [
    "ParticleInspectionConfig",
    "inspect_particles_in_wafer_band",
    "render_particle_overlay",
    "render_particle_diagnostic_overlay",
]


@dataclass
class ParticleInspectionConfig:
    """Particle inspection tuning values.

    ``band_inner_margin_px=75`` and ``band_outer_margin_px=10`` inspect the
    annulus from 75 px inside the wafer edge up to 10 px before the rim.  They
    define *particle ROI*, not the V5 ``is_edge`` die property.

    ``die_exclusion_mode`` controls how much die signal is removed:

    - ``"grid_cell"``: exclude the whole cell. Safest against circuit signal,
      but may miss a particle on a street.
    - ``"die_core"``: exclude only the cell interior inset by
      ``die_core_inset_px``. Recommended starting mode for street inspection.
    - ``"none"``: do not exclude dies. Use only when an external ROI already
      excludes die interiors.

    A partial die is handled separately.  ``"exclude_all"`` is the safe
    default because a clipped die can expose strong internal white patterns.
    """

    band_inner_margin_px: int = 75
    band_outer_margin_px: int = 10
    band_guard_px: int = 2
    die_exclusion_mode: DieExclusionMode = "die_core"
    die_core_inset_px: int = 2
    partial_die_policy: PartialDiePolicy = "exclude_all"
    min_area_px: int = 8
    max_area_px: int = 300
    max_aspect_ratio: float = 3.0
    min_fill_ratio: float = 0.30
    background_sigma_px: float = 5.0
    min_residual_px: float = 16.0
    residual_mad_z: float = 5.0
    min_local_contrast: float = 12.0
    reject_roi_boundary_touch: bool = True


def _as_gray(image: np.ndarray) -> np.ndarray:
    """Return an 8-bit gray image while accepting V5's gray or BGR image."""
    if image is None:
        raise ValueError("dm.aligned_image is required")
    array = np.asarray(image)
    if array.ndim == 2:
        return array.astype(np.uint8, copy=False)
    if array.ndim == 3 and array.shape[2] == 1:
        return array[:, :, 0].astype(np.uint8, copy=False)
    if array.ndim == 3 and array.shape[2] in (3, 4):
        code = cv2.COLOR_BGR2GRAY if array.shape[2] == 3 else cv2.COLOR_BGRA2GRAY
        return cv2.cvtColor(array, code)
    raise ValueError("dm.aligned_image must be a gray, BGR, or BGRA image")


def _as_bgr(image: np.ndarray) -> np.ndarray:
    """Return BGR for overlays without changing the source image."""
    array = np.asarray(image)
    if array.ndim == 2:
        return cv2.cvtColor(array.astype(np.uint8, copy=False), cv2.COLOR_GRAY2BGR)
    if array.ndim == 3 and array.shape[2] == 1:
        return cv2.cvtColor(array[:, :, 0].astype(np.uint8, copy=False), cv2.COLOR_GRAY2BGR)
    if array.ndim == 3 and array.shape[2] == 3:
        return array.astype(np.uint8, copy=False)
    if array.ndim == 3 and array.shape[2] == 4:
        return cv2.cvtColor(array.astype(np.uint8, copy=False), cv2.COLOR_BGRA2BGR)
    raise ValueError("image must be gray, BGR, or BGRA")


def _validate_dm(dm: Any) -> None:
    """Require fields shared by V5 and custom compatible map objects."""
    required = ("wafer_cx", "wafer_cy", "wafer_r", "pitch_x", "pitch_y", "x0", "y0", "aligned_image")
    missing = [name for name in required if not hasattr(dm, name)]
    if missing:
        raise TypeError("dm must provide V5 fields: " + ", ".join(missing))
    if float(dm.wafer_r) <= 0 or float(dm.pitch_x) <= 0 or float(dm.pitch_y) <= 0:
        raise ValueError("dm.wafer_r, dm.pitch_x, and dm.pitch_y must be positive")


def _rect_intersects_circle(rect: Tuple[int, int, int, int], cx: float, cy: float, radius: float) -> bool:
    """True when an axis-aligned die rectangle intersects or lies in a circle."""
    x1, y1, x2, y2 = rect
    near_x = min(max(cx, x1), x2)
    near_y = min(max(cy, y1), y2)
    return (near_x - cx) ** 2 + (near_y - cy) ** 2 <= radius ** 2


def _iter_theoretical_cells(dm: Any, shape: Tuple[int, int]):
    """Yield float-grid cells around wafer, including center-outside partial dies."""
    height, width = shape
    max_ix = int(np.ceil(float(dm.wafer_r) / float(dm.pitch_x))) + 3
    max_iy = int(np.ceil(float(dm.wafer_r) / float(dm.pitch_y))) + 3
    for iy in range(-max_iy, max_iy + 1):
        for ix in range(-max_ix, max_ix + 1):
            x1 = int(round(float(dm.x0) + ix * float(dm.pitch_x)))
            x2 = int(round(float(dm.x0) + (ix + 1) * float(dm.pitch_x)))
            y1 = int(round(float(dm.y0) - (iy + 1) * float(dm.pitch_y)))
            y2 = int(round(float(dm.y0) - iy * float(dm.pitch_y)))
            if x2 <= 0 or y2 <= 0 or x1 >= width or y1 >= height or x2 <= x1 or y2 <= y1:
                continue
            yield ix, iy, (x1, y1, x2, y2)


def _make_die_exclusion_mask(dm: Any, shape: Tuple[int, int], config: ParticleInspectionConfig) -> np.ndarray:
    """Mask die signal using rect-circle intersection, not a die-center shortcut.

    The circle test is deliberately applied before drawing: this captures cells
    whose centers lie outside the wafer but whose rectangles cross its edge.
    """
    height, width = shape
    mask = np.zeros((height, width), dtype=np.uint8)
    if config.die_exclusion_mode == "none":
        return mask

    for _, _, rect in _iter_theoretical_cells(dm, shape):
        if not _rect_intersects_circle(rect, dm.wafer_cx, dm.wafer_cy, dm.wafer_r):
            continue
        x1, y1, x2, y2 = rect
        partial = _rect_crosses_circle(rect, dm.wafer_cx, dm.wafer_cy, dm.wafer_r)
        exclude_all = config.die_exclusion_mode == "grid_cell" or (
            partial and config.partial_die_policy == "exclude_all"
        )
        if not exclude_all:
            inset = int(config.die_core_inset_px)
            x1, y1, x2, y2 = x1 + inset, y1 + inset, x2 - inset, y2 - inset
        if x2 <= x1 or y2 <= y1:
            continue
        cv2.rectangle(mask, (max(0, x1), max(0, y1)), (min(width - 1, x2), min(height - 1, y2)), 1, -1)
    return mask


def _rect_crosses_circle(rect: Tuple[int, int, int, int], cx: float, cy: float, radius: float) -> bool:
    """True only when part of the rectangle is inside and another part is outside."""
    x1, y1, x2, y2 = rect
    corners = ((x1, y1), (x1, y2), (x2, y1), (x2, y2))
    distances_sq = [(x - cx) ** 2 + (y - cy) ** 2 for x, y in corners]
    radius_sq = radius ** 2
    return min(distances_sq) <= radius_sq < max(distances_sq)


def _roi_boundary(mask: np.ndarray) -> np.ndarray:
    """One-pixel ROI border; components touching it are clipped candidates."""
    kernel = np.ones((3, 3), np.uint8)
    return cv2.morphologyEx(mask.astype(np.uint8), cv2.MORPH_GRADIENT, kernel).astype(bool)


def _nearest_die_index(dm: Any, point: Tuple[float, float]) -> Tuple[int, int]:
    """Return V5 index convention without importing the V5 module."""
    x, y = point
    ix = int(np.floor((x - float(dm.x0)) / float(dm.pitch_x)))
    iy = int(np.floor((float(dm.y0) - y) / float(dm.pitch_y)))
    return ix, iy


def _component_record(
    label: int,
    labels: np.ndarray,
    stats: np.ndarray,
    centroids: np.ndarray,
    gray: np.ndarray,
    residual: np.ndarray,
    inspection_mask: np.ndarray,
    roi_boundary: np.ndarray,
    dm: Any,
) -> Dict[str, Any]:
    """Measure one component once so accepted and rejected records match."""
    x, y, box_w, box_h, area = (int(value) for value in stats[label])
    cx, cy = (float(value) for value in centroids[label])
    component = labels[y:y + box_h, x:x + box_w] == label
    component_gray = gray[y:y + box_h, x:x + box_w][component]
    component_residual = residual[y:y + box_h, x:x + box_w][component]
    pad = max(8, int(round(max(box_w, box_h) * 1.5)))
    rx1, ry1 = max(0, x - pad), max(0, y - pad)
    rx2, ry2 = min(gray.shape[1], x + box_w + pad), min(gray.shape[0], y + box_h + pad)
    local_component = labels[ry1:ry2, rx1:rx2] == label
    local_valid = inspection_mask[ry1:ry2, rx1:rx2].astype(bool) & ~local_component
    background = gray[ry1:ry2, rx1:rx2][local_valid]
    local_background = float(np.median(background)) if background.size else float("nan")
    local_contrast = float(component_gray.mean() - local_background) if background.size else float("nan")
    boundary_hit = bool((roi_boundary[y:y + box_h, x:x + box_w] & component).any())
    aspect_ratio = max(box_w, box_h) / float(max(1, min(box_w, box_h)))
    fill_ratio = area / float(max(1, box_w * box_h))
    edge_distance = float(dm.wafer_r - np.hypot(cx - dm.wafer_cx, cy - dm.wafer_cy))
    return {
        "center_px": (round(cx, 2), round(cy, 2)),
        "bbox_px": (x, y, x + box_w, y + box_h),
        "area_px": area,
        "aspect_ratio": round(aspect_ratio, 3),
        "fill_ratio": round(fill_ratio, 3),
        "mean_intensity": round(float(component_gray.mean()), 2),
        "mean_residual": round(float(component_residual.mean()), 2),
        "local_contrast": round(local_contrast, 2) if np.isfinite(local_contrast) else None,
        "touches_roi_boundary": boundary_hit,
        "radius_from_wafer_center_px": round(float(dm.wafer_r - edge_distance), 2),
        "distance_from_wafer_edge_px": round(edge_distance, 2),
        "nearest_die_index": _nearest_die_index(dm, (cx, cy)),
    }


def inspect_particles_in_wafer_band(
    dm: Any,
    *,
    config: Optional[ParticleInspectionConfig] = None,
    valid_region_mask: Optional[np.ndarray] = None,
    return_masks: bool = False,
    include_rejected: bool = True,
) -> Dict[str, Any]:
    """Detect bright particles in a configurable wafer-edge band.

    Parameters
    ----------
    dm:
        The object returned by V5 ``build_die_map()``.  This module checks
        fields (duck typing), so it accepts the V5 object directly.
    config:
        :class:`ParticleInspectionConfig`.  Defaults are suitable starting
        values, not fixed production thresholds.
    valid_region_mask:
        Optional ``(H, W)`` 1-channel mask from the caller.  Use it to inspect
        only a selected outer-wafer sector. Nonzero pixels are allowed.
    return_masks:
        ``False`` by default to avoid returning roughly 45 MB of masks for a
        3000x3000 image.  Set ``True`` for diagnostics and overlays.
    include_rejected:
        Include filtered candidates and their exact ``rejection_reason``.

    Returns
    -------
    dict
        ``particles`` are accepted defects; ``rejected`` are review/debug
        candidates. Every coordinate is in ``"aligned"`` space.  A particle
        record has ``center_px``, ``bbox_px``, ``nearest_die_index``,
        ``distance_from_wafer_edge_px``, shape/contrast metrics, confidence,
        and ``touches_roi_boundary``.  Mask arrays only exist when
        ``return_masks=True``.
    """
    _validate_dm(dm)
    config = config or ParticleInspectionConfig()
    if config.band_inner_margin_px <= config.band_outer_margin_px:
        raise ValueError("band_inner_margin_px must be greater than band_outer_margin_px")
    if config.band_guard_px < 0 or config.die_core_inset_px < 0:
        raise ValueError("band_guard_px and die_core_inset_px must be >= 0")
    if config.min_area_px <= 0 or config.max_area_px < config.min_area_px:
        raise ValueError("area limits must satisfy 0 < min_area_px <= max_area_px")
    if config.die_exclusion_mode not in ("none", "grid_cell", "die_core"):
        raise ValueError("die_exclusion_mode must be none, grid_cell, or die_core")
    if config.partial_die_policy not in ("exclude_all", "die_core"):
        raise ValueError("partial_die_policy must be exclude_all or die_core")

    gray = _as_gray(dm.aligned_image)
    height, width = gray.shape
    yy, xx = np.ogrid[:height, :width]
    radius = np.hypot(xx - float(dm.wafer_cx), yy - float(dm.wafer_cy))
    inner_radius = float(dm.wafer_r - config.band_inner_margin_px + config.band_guard_px)
    outer_radius = float(dm.wafer_r - config.band_outer_margin_px - config.band_guard_px)
    if inner_radius <= 0 or outer_radius <= inner_radius:
        raise ValueError("band margins leave no inspection area")
    ring_mask = ((radius >= inner_radius) & (radius <= outer_radius)).astype(np.uint8)
    if valid_region_mask is not None:
        user_mask = np.asarray(valid_region_mask)
        if user_mask.shape != gray.shape:
            raise ValueError("valid_region_mask must have the same (H, W) shape as dm.aligned_image")
        ring_mask &= (user_mask > 0).astype(np.uint8)

    die_mask = _make_die_exclusion_mask(dm, gray.shape, config)
    inspection_mask = ((ring_mask > 0) & (die_mask == 0)).astype(np.uint8)
    if int(inspection_mask.sum()) == 0:
        raise RuntimeError("inspection area is empty; change band or die exclusion settings")

    # Background subtraction makes weak-but-local particles candidates before
    # any global intensity threshold can discard them.
    background = cv2.GaussianBlur(gray.astype(np.float32), (0, 0), config.background_sigma_px)
    residual = gray.astype(np.float32) - background
    valid_residuals = residual[inspection_mask > 0]
    median = float(np.median(valid_residuals))
    mad = float(np.median(np.abs(valid_residuals - median)))
    robust_sigma = max(1.0, 1.4826 * mad)
    residual_threshold = median + max(config.min_residual_px, config.residual_mad_z * robust_sigma)
    candidate_mask = ((residual >= residual_threshold) & (inspection_mask > 0)).astype(np.uint8)
    label_count, labels, stats, centroids = cv2.connectedComponentsWithStats(candidate_mask, connectivity=8)
    boundary = _roi_boundary(ring_mask)

    particles: List[Dict[str, Any]] = []
    rejected: List[Dict[str, Any]] = []
    for label in range(1, label_count):
        record = _component_record(label, labels, stats, centroids, gray, residual, inspection_mask, boundary, dm)
        reasons: List[str] = []
        if not config.min_area_px <= record["area_px"] <= config.max_area_px:
            reasons.append("area")
        if record["aspect_ratio"] > config.max_aspect_ratio or record["fill_ratio"] < config.min_fill_ratio:
            reasons.append("shape")
        if record["local_contrast"] is None or record["local_contrast"] < config.min_local_contrast:
            reasons.append("local_contrast")
        if config.reject_roi_boundary_touch and record["touches_roi_boundary"]:
            reasons.append("roi_boundary")

        # 0..1 score is for sorting/review, not a replacement for acceptance rules.
        contrast_score = min(1.0, max(0.0, record["mean_residual"] / max(residual_threshold, 1.0)))
        shape_score = min(1.0, record["fill_ratio"] / max(config.min_fill_ratio, 0.01))
        record["particle_confidence"] = round(0.70 * contrast_score + 0.30 * shape_score, 3)
        record["coordinate_space"] = "aligned"
        if reasons:
            record["rejection_reason"] = reasons
            if include_rejected:
                rejected.append(record)
            continue
        record["id"] = len(particles) + 1
        record["rejection_reason"] = None
        particles.append(record)

    summary: Dict[str, Any] = {
        "coordinate_space": "aligned",
        "ring_pixels": int(ring_mask.sum()),
        "die_excluded_pixels_in_ring": int(((ring_mask > 0) & (die_mask > 0)).sum()),
        "inspection_pixels": int(inspection_mask.sum()),
        "inspection_ratio_in_ring": round(float(inspection_mask.sum()) / max(1, int(ring_mask.sum())), 4),
        "candidate_components": int(label_count - 1),
        "accepted_particles": len(particles),
        "rejected_candidates": len(rejected),
        "residual_threshold": round(residual_threshold, 3),
        "residual_median": round(median, 3),
        "residual_mad_sigma": round(robust_sigma, 3),
        "review_required": any(item["touches_roi_boundary"] for item in rejected),
    }
    result: Dict[str, Any] = {
        "particles": particles,
        "rejected": rejected if include_rejected else [],
        "summary": summary,
        "config": asdict(config),
        "inspection_radii_px": {"inner": round(inner_radius, 2), "outer": round(outer_radius, 2)},
    }
    if return_masks:
        result["masks"] = {
            "ring_mask": ring_mask,
            "die_exclusion_mask": die_mask,
            "inspection_mask": inspection_mask,
            "candidate_mask": candidate_mask,
        }
    return result


def render_particle_overlay(dm: Any, result: Dict[str, Any]) -> np.ndarray:
    """Return a BGR overview: cyan band boundary, red accepted particles."""
    _validate_dm(dm)
    canvas = _as_bgr(dm.aligned_image).copy()
    radii = result["inspection_radii_px"]
    center = (int(round(dm.wafer_cx)), int(round(dm.wafer_cy)))
    cv2.circle(canvas, center, int(round(radii["inner"])), (255, 220, 0), 1)
    cv2.circle(canvas, center, int(round(radii["outer"])), (255, 220, 0), 1)
    for particle in result["particles"]:
        x1, y1, x2, y2 = particle["bbox_px"]
        point = tuple(int(round(value)) for value in particle["center_px"])
        cv2.rectangle(canvas, (x1, y1), (x2, y2), (0, 0, 255), 1)
        cv2.drawMarker(canvas, point, (0, 0, 255), cv2.MARKER_CROSS, 10, 1)
        cv2.putText(canvas, str(particle["id"]), (x1, max(12, y1 - 3)), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1, cv2.LINE_AA)
    return canvas


def render_particle_diagnostic_overlay(dm: Any, result: Dict[str, Any]) -> np.ndarray:
    """Return a detailed BGR overlay. Call inspection with ``return_masks=True``."""
    if "masks" not in result:
        raise ValueError("diagnostic overlay requires return_masks=True")
    canvas = render_particle_overlay(dm, result)
    masks = result["masks"]
    # Orange = protected die signal. Green = remaining particle inspection ROI.
    canvas[masks["die_exclusion_mask"] > 0] = cv2.addWeighted(
        canvas[masks["die_exclusion_mask"] > 0], 0.60,
        np.full_like(canvas[masks["die_exclusion_mask"] > 0], (0, 140, 255)), 0.40, 0,
    )
    canvas[masks["inspection_mask"] > 0] = cv2.addWeighted(
        canvas[masks["inspection_mask"] > 0], 0.75,
        np.full_like(canvas[masks["inspection_mask"] > 0], (0, 110, 0)), 0.25, 0,
    )
    for item in result.get("rejected", []):
        x1, y1, x2, y2 = item["bbox_px"]
        color = (0, 215, 255) if item["touches_roi_boundary"] else (180, 180, 180)
        cv2.rectangle(canvas, (x1, y1), (x2, y2), color, 1)
    return canvas
