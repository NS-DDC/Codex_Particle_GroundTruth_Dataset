# Codex Particle Ground-Truth Dataset

실제 Gray wafer 이미지를 배경으로 유지하면서, 실제 particle template을 합성하고 정답지(GT)와 detector 평가 결과를 만드는 독립 도구입니다.

## 구성

- `use_particle_wafer_band_v1.py`: V5 `build_die_map()`의 `dm`을 직접 받는 particle 검사 모듈
- `test_particle_wafer_band_v1.py`: V5 dataclass 호환, Die 보호, street particle 검출 회귀 테스트
- `PARTICLE_INSPECTION_V1_KO.md`: particle ROI, Die 제외 정책, 반환값 설명
- `DATASET_V1/generate_particle_ground_truth_v1.py`: 실제 Gray wafer + 실제 particle template 기반 3000x3000 GT 생성기
- `DATASET_V1/evaluate_particle_ground_truth_v1.py`: precision/recall/F1, diagnostic, TP/FP/FN overlay 생성기
- `DATASET_V1/GROUND_TRUTH_DATASET_KO.md`: GT schema와 실행 방법
- `DATASET_V1/RUN_RESULT_20260811_KO.md`: 실제 실행 결과와 threshold 탐색 결과

## 빠른 실행

```powershell
python test_particle_wafer_band_v1.py

python DATASET_V1\generate_particle_ground_truth_v1.py `
  --images E:\mirero\Wafer_Map_Die_V5\Gray_Wafer\111.png E:\mirero\Wafer_Map_Die_V5\Gray_Wafer\2222.png `
  --particle-template E:\mirero\Wafer_Map_Die_V5\Gray_Wafer\Paticle\22.png `
  --output-dir DATASET_V1\generated --target-size 3000

python DATASET_V1\evaluate_particle_ground_truth_v1.py `
  --dataset-dir DATASET_V1\generated
```

생성 PNG와 evaluation overlay는 대용량이라 Git에는 넣지 않고 `DATASET_V1/generated/`에 로컬로 저장합니다.
