# Particle Ground-Truth Dataset V1

## 원칙

이미지를 단색 바탕에서 새로 그리지 않는다. 실제 `Gray_Wafer` 원본을 V5 좌표계로 정렬·확대해 배경으로 유지하고, 실제 `Paticle/22.png` 형상을 크기·회전·밝기만 바꿔 합성한다. 따라서 Die 회로, street, wafer rim, 조명 불균일, 센서 노이즈가 남는다.

각 생성 case에는 3000x3000 Gray PNG와 같은 이름의 JSON GT가 생긴다. Git에는 기준 샘플 2장과 JSON GT를 포함하고, 용량이 큰 diagnostic/error overlay는 `generated/evaluation/`에 로컬 보관한다.

## GT 레이블

| `label` | `evaluation` | 의미 |
|---|---:|---|
| `particle` | `true` | precision/recall 대상. normal, weak, merged_pair 난이도 포함 |
| `non_particle_die_signal` | `false` | 밝지만 Die 내부라 particle이 아닌 교란 신호 |
| `ignore_roi_boundary` | `false` | 검사 band 경계에서 잘려 판정하면 안 되는 물체 |

JSON에는 wafer circle, float pitch/corner, band config, 좌표계(`aligned`), 중심, bbox, 반지름, 난이도, 강도가 모두 기록된다.

## 생성 및 평가

```powershell
python PARTICLE_INSPECTION_V1\DATASET_V1\generate_particle_ground_truth_v1.py `
  --images E:\mirero\Wafer_Map_Die_V5\Gray_Wafer\111.png E:\mirero\Wafer_Map_Die_V5\Gray_Wafer\2222.png `
  --particle-template E:\mirero\Wafer_Map_Die_V5\Gray_Wafer\Paticle\22.png `
  --output-dir PARTICLE_INSPECTION_V1\DATASET_V1\generated --target-size 3000

python PARTICLE_INSPECTION_V1\DATASET_V1\evaluate_particle_ground_truth_v1.py `
  --dataset-dir PARTICLE_INSPECTION_V1\DATASET_V1\generated
```

평가 결과는 `evaluation_summary.json`, 상세 D/R/P diagnostic overlay, 그리고 TP=녹색·FP=빨강·FN=파랑 error overlay로 저장된다.

## 포함된 어려운 조건

- normal/weak particle, 실제 particle template의 회전·크기·밝기 변화
- 서로 가까운 particle 두 개(merged blob 위험)
- 밝은 Die 내부 신호(non-particle)
- partial EDGE Die는 `rect-circle intersection`으로 보호
- rim glare와 band 경계 잘린 ignore candidate
- 실제 wafer의 grid/street/노이즈 위에서의 검증

현재 이미지는 **회귀 및 알고리즘 튜닝용 합성 GT**다. threshold를 확정하기 전에는 실제 양성/음성 원본을 사람이 라벨링한 holdout 세트에서도 동일한 precision/recall을 확인해야 한다.
