"""Run particle inspection on generated PNG/JSON pairs and write metrics + overlays."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List, Tuple

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from use_particle_wafer_band_v1 import ParticleInspectionConfig, inspect_particles_in_wafer_band, render_particle_diagnostic_overlay  # noqa: E402


def _match(predictions: List[Dict[str, Any]], annotations: List[Dict[str, Any]], tolerance: float) -> Tuple[List[Tuple[int, int]], List[int], List[int]]:
    """Greedily one-to-one match prediction centers to evaluation particle GT."""
    pairs: List[Tuple[float, int, int]] = []
    for pi, prediction in enumerate(predictions):
        for gi, annotation in enumerate(annotations):
            distance = float(np.hypot(prediction["center_px"][0] - annotation["center_px"][0], prediction["center_px"][1] - annotation["center_px"][1]))
            if distance <= max(tolerance, float(annotation.get("radius_px", 0)) + tolerance / 2.0):
                pairs.append((distance, pi, gi))
    matches: List[Tuple[int, int]] = []
    used_p, used_g = set(), set()
    for _, pi, gi in sorted(pairs):
        if pi not in used_p and gi not in used_g:
            matches.append((pi, gi))
            used_p.add(pi)
            used_g.add(gi)
    return matches, [index for index in range(len(predictions)) if index not in used_p], [index for index in range(len(annotations)) if index not in used_g]


def _render_error_overlay(image: np.ndarray, matches: List[Tuple[int, int]], predictions: List[Dict[str, Any]], gt: List[Dict[str, Any]], unmatched_pred: List[int], unmatched_gt: List[int]) -> np.ndarray:
    """Green=TP, red=FP, blue=FN. This is the primary human review image."""
    canvas = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    for pi, _ in matches:
        x, y = (int(round(v)) for v in predictions[pi]["center_px"])
        cv2.drawMarker(canvas, (x, y), (0, 220, 0), cv2.MARKER_CROSS, 18, 2)
    for pi in unmatched_pred:
        x, y = (int(round(v)) for v in predictions[pi]["center_px"])
        cv2.drawMarker(canvas, (x, y), (0, 0, 255), cv2.MARKER_TILTED_CROSS, 18, 2)
    for gi in unmatched_gt:
        x, y = (int(round(v)) for v in gt[gi]["center_px"])
        cv2.drawMarker(canvas, (x, y), (255, 0, 0), cv2.MARKER_DIAMOND, 18, 2)
    return canvas


def evaluate_case(json_path: Path, output_dir: Path) -> Dict[str, Any]:
    """Evaluate one annotation file and save diagnostic/error overlays."""
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    image_path = json_path.parent / payload["image_file"]
    image = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
    dm = SimpleNamespace(**payload["wafer"], **payload["grid"], aligned_image=image)
    config = ParticleInspectionConfig(**payload["inspection_config"])
    result = inspect_particles_in_wafer_band(dm, config=config, return_masks=True)
    gt = [item for item in payload["annotations"] if item["label"] == "particle" and item.get("evaluation")]
    matches, fp, fn = _match(result["particles"], gt, tolerance=12.0)
    tp = len(matches)
    precision = tp / max(1, tp + len(fp))
    recall = tp / max(1, tp + len(fn))
    diagnostic = render_particle_diagnostic_overlay(dm, result)
    error = _render_error_overlay(image, matches, result["particles"], gt, fp, fn)
    cv2.imwrite(str(output_dir / f"{json_path.stem}_diagnostic.png"), diagnostic)
    cv2.imwrite(str(output_dir / f"{json_path.stem}_errors.png"), error)
    return {
        "case": json_path.stem,
        "gt_particles": len(gt),
        "tp": tp,
        "fp": len(fp),
        "fn": len(fn),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(2 * precision * recall / max(1e-9, precision + recall), 4),
        "inspection_ratio_in_ring": result["summary"]["inspection_ratio_in_ring"],
        "threshold": result["summary"]["residual_threshold"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-dir", required=True)
    parser.add_argument("--output-dir", default=None)
    args = parser.parse_args()
    dataset_dir = Path(args.dataset_dir)
    output_dir = Path(args.output_dir) if args.output_dir else dataset_dir / "evaluation"
    output_dir.mkdir(parents=True, exist_ok=True)
    reports = [evaluate_case(path, output_dir) for path in sorted(dataset_dir.glob("*_particle_gt.json"))]
    total = {key: sum(report[key] for report in reports) for key in ("gt_particles", "tp", "fp", "fn")}
    precision = total["tp"] / max(1, total["tp"] + total["fp"])
    recall = total["tp"] / max(1, total["tp"] + total["fn"])
    summary = {"cases": reports, "total": total, "precision": round(precision, 4), "recall": round(recall, 4), "f1": round(2 * precision * recall / max(1e-9, precision + recall), 4)}
    (output_dir / "evaluation_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
