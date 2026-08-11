# 실행 결과: 실제 Gray wafer 기반 GT V1

실행일: 2026-08-11

## 입력과 생성물

- 원본 배경: `Gray_Wafer/111.png`, `Gray_Wafer/2222.png`
- 출력: 각 원본을 V5 aligned 좌표계로 3000x3000 Gray로 확대하고, 실제 `Paticle/22.png` 템플릿을 이용해 particle을 합성
- 각 이미지의 평가 GT: normal 8개 + weak 4개 + merged-pair 2개 = `particle` 14개
- 평가 제외 객체: Die 내부 밝은 신호 5개, rim glare 1개, ROI 경계 ignore candidate 1개

## 기본 설정 결과

| case | GT | TP | FP | FN | Precision | Recall | 검사 가능 비율 |
|---|---:|---:|---:|---:|---:|---:|---:|
| `111_particle_gt` | 14 | 0 | 0 | 14 | 0.000 | 0.000 | 8.40% |
| `2222_particle_gt` | 14 | 0 | 0 | 14 | 0.000 | 0.000 | 8.93% |
| 합계 | 28 | 0 | 0 | 28 | 0.000 | 0.000 | - |

기본 detector의 MAD adaptive threshold는 각각 `108.155`, `115.766`까지 상승했다. 실제 wafer street/rim의 residual 변동이 크고, ring의 91% 이상이 Die exclusion으로 보호돼 약한 particle이 후보 단계에 진입하지 못했다.

## 탐색 설정 결과

아래 값은 최종 튜닝값이 아니다. `min_area=2`, `min_local_contrast=2`, ROI 경계 reject 해제 후 MAD 계수만 바꿔 현재 구조의 한계를 보기 위한 탐색이다.

| `residual_mad_z` | TP | FP | FN | Precision | Recall |
|---:|---:|---:|---:|---:|---:|
| 0.0 | 19 | 1,990 | 9 | 0.009 | 0.679 |
| 1.0 | 24 | 1,979 | 4 | 0.012 | 0.857 |
| 2.0 | 26 | 1,265 | 2 | 0.020 | 0.929 |
| 3.0 | 24 | 649 | 4 | 0.036 | 0.857 |

결론은 명확하다. threshold만 낮추면 recall은 올라가지만 wafer texture/rim/grid로 FP가 급증한다. 다음 코드 개선은 threshold 조정이 아니라 `die_core/street` mask 정밀화, particle template/shape score, candidate 분리, partial Die 노출 영역 정책을 함께 다뤄야 한다.

## 확인 이미지

- `generated/111_particle_gt.png`: 실제 Gray wafer 기반 3000x3000 GT 입력
- `generated/evaluation/111_particle_gt_diagnostic.png`: D/R/P 검사 상태
- `generated/evaluation/111_particle_gt_errors.png`: 녹색 TP, 빨강 FP, 파랑 FN

원본 PNG 샘플 2장과 JSON GT는 Git에 추적한다. 용량이 큰 diagnostic/error overlay는 `generated/evaluation/`의 로컬 산출물이고, 생성기와 GT 스키마, 평가기는 Git에 추적된다.
