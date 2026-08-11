# =============================================================================
# 빠른 사용 안내 — 기능별 호출과 파라미터
# =============================================================================
# 이 파일은 use_gray_wafer_die_particle_claude.py의 별도 정리본입니다.
# 검출 알고리즘, 기본값, 함수 구현은 원본과 동일하며 사용자가 찾는 호출법과
# 조정 파라미터만 파일 맨 앞에 기능별로 모았습니다.
#
# -----------------------------------------------------------------------------
# [1] Die map 생성: build_die_map()
# -----------------------------------------------------------------------------
# 가장 먼저 wafer 이미지(BGR ndarray 또는 경로)에서 die 위치·크기·edge 정보를 만듭니다.
#
#     die_map = build_die_map(
#         bgr,
#         grid_method="auto",       # "auto" | "cross" | "corner" | "hybrid" | "std" | "color"
#         min_pitch=None,           # die 폭/높이 탐색 최소값(px), 자동이면 None
#         max_pitch=None,           # die 폭/높이 탐색 최대값(px), 자동이면 None
#         include_edge=True,        # 웨이퍼 가장자리의 잘린 die 포함
#         edge_mode="circle",       # "circle" | "ring" | "both"
#         refine_origin=True,       # street 교차점 기준의 grid origin 정밀 보정
#         exclude_street=False,     # True면 die 사이 street를 제외한 순수 die 영역 사용
#         angle_align_method="die_render",  # "die_render" | "notch" | "vertical_line" | "none"
#     )
#
# 자주 조절하는 항목
# - grid_method: 격자 검출 방식. 보통 "auto" 그대로 사용합니다.
# - min_pitch / max_pitch: 자동 격자 검출이 틀릴 때 예상 die 크기 범위를 px로 제한합니다.
# - edge_mode: 부분 die 기준(circle), 격자 최외곽 줄(ring), 둘 모두(both) 중 선택합니다.
# - edge_clip_all / edge_overlap_min_px: 가장자리 die를 얼마나 포함할지 조절합니다.
# - refine_origin / phase_match: 격자 원점 보정. 기본값을 권장합니다.
# - exclude_street: die 내부만 분석하고 die 사이 경계(street)는 빼고 싶을 때 True입니다.
# - with_crops / border_mode / offset_x·offset_y / margin_x·margin_y: die crop이 필요할 때 사용합니다.
#
# -----------------------------------------------------------------------------
# [2] 흰 rim 안쪽 노이즈 검사: inspect_white_noise_inside_rim()
# -----------------------------------------------------------------------------
# 위에서 만든 die_map을 재사용하는 권장 호출입니다. 모든 검사 파라미터를 이 호출에
# 직접 적을 수 있어, 어떤 값으로 검사했는지 한눈에 확인할 수 있습니다.
#
#     result = inspect_white_noise_inside_rim(
#         bgr,
#         die_map,
#         rim_clearance_px=6,       # 흰 rim 바로 안쪽에서 건너뛸 여유(px)
#         search_depth_px=60,       # rim 안쪽으로 검사할 깊이(px)
#         min_area_px=8,            # particle 후보의 최소 면적(px²)
#         max_area_px=2000,         # particle 후보의 최대 면적(px²)
#         max_aspect_ratio=8.0,     # 너무 길쭉한 후보 제거 기준
#         min_fill_ratio=0.20,      # bbox 내부를 실제로 채운 비율의 하한
#         z_threshold=3.5,          # 밝기 이상치 감도: 낮추면 민감, 올리면 엄격
#         use_repeat_vote=True,     # 주변 die 반복 패턴과 비교해 오검출 억제
#         with_overlay=True,        # 결과 overlay 이미지 생성
#         keep_rejected=False,      # 탈락 후보 정보까지 필요하면 True
#     )
#
# 파라미터 묶음
# - rim 위치/범위: wafer_cx, wafer_cy, wafer_r, rim_band, rim_bright_percentile,
#   rim_level, rim_clearance_px, search_depth_px, include_rim, inner_radius_px,
#   outer_radius_px
# - 후보 크기/형상: min_area_px, max_area_px, max_aspect_ratio, min_fill_ratio
# - 밝기 감도: use_pattern_model, z_threshold, mad_floor, gray_threshold,
#   radial_detrend
# - die 패턴 오인 방지: pattern_model, pattern_ref_ratio, auto_pitch,
#   refine_pitch, pitch_x, pitch_y, min_pitch, max_pitch, use_repeat_vote,
#   repeat_steps, repeat_soft_ratio, repeat_min_votes, repeat_reject_ratio
# - 출력: with_overlay, keep_rejected
#
# -----------------------------------------------------------------------------
# [3] 한 번에 실행: detect_white_noise()
# -----------------------------------------------------------------------------
# die map을 따로 쓸 일이 없으면 아래처럼 검사 옵션을 직접 전달합니다.
#
#     result = detect_white_noise(
#         bgr,
#         min_area_px=8,
#         search_depth_px=60,
#         z_threshold=3.5,
#         use_repeat_vote=True,
#         with_overlay=True,
#     )
#
# 기존 die_map을 갖고 있으면 새 map을 만들지 않고 재사용할 수 있습니다.
#
#     result = detect_white_noise(
#         bgr,
#         die_map=die_map,
#         min_area_px=8,
#         search_depth_px=60,
#     )
#
# build_die_map 파라미터까지 직접 보고 조절하려면 [1] -> [2]의 2단계 호출을
# 사용합니다. detect_white_noise()의 die_map_kwargs / **noise_kwargs 인터페이스는
# 원본 호환성을 위해 그대로 보존했습니다.
#
# -----------------------------------------------------------------------------
# 기능별 함수 찾기
# -----------------------------------------------------------------------------
# A. Wafer/격자 검출: detect_wafer, detect_grid, detect_cross_grid,
#    detect_corner_grid, detect_thin_cross_grid
# B. Die map/좌표/crop: build_die_map, locate_die, crop_die, clip_die,
#    render_die_grid_mask
# C. 회전·notch 보정: detect_notch, detect_notch_angle, align_wafer_by_notch,
#    align_wafer_by_vertical_line, align_wafer_by_die_render
# D. 흰 rim·particle 검사: detect_wafer_rim_band, build_die_pattern_model,
#    inspect_white_noise_inside_rim, detect_white_noise
# E. 진단·검증: validate_quadrant_edges, measure_die_grid_angle,
#    measure_wafer_angle_robust
#
# 원본 동작 유지 원칙
# - 아래 함수 구현과 기본값은 변경하지 않았습니다.
# - 이 안내와 원본의 상세 docstring을 함께 보면, 필요한 호출에만 파라미터를
#   직접 적어 사용하는 방식으로 관리할 수 있습니다.
#
# =============================================================================
# 편집 섹터 지도 — Ctrl+F로 "[SECTOR:" 또는 아래 ID를 검색
# =============================================================================
# 코드를 수정할 때는 기능에 맞는 섹터만 열어 변경합니다. 섹터 사이의 호출 계약과
# 기본값은 그대로 두면, 지금까지 쌓인 검출/보정 로직을 안전하게 조합할 수 있습니다.
#
# [SECTOR: 10_CORE_AND_WAFER]       공통 이미지 변환, wafer 원판 검출
# [SECTOR: 20_DIE_GRID_DETECTION]   pitch·grid origin·corner/cross 검출
# [SECTOR: 30_DIE_MAP_GEOMETRY]     die crop, WaferDieMap, edge 판정
# [SECTOR: 40_ALIGNMENT_AND_CLEAN]  notch/직선/die-render 회전 보정, 외부 정리
# [SECTOR: 50_GRID_ORIGIN_REFINEMENT] phase matching, street 폭, origin 미세 보정
# [SECTOR: 60_DIE_MAP_BUILD_API]    build_die_map() — die map 생성 파이프라인
# [SECTOR: 61_DIE_MAP_LOOKUP_API]   locate_die() — 좌표/BBox에서 die 조회
# [SECTOR: 70_WHITE_RIM_PARTICLE]   rim 측정부터 particle 판정까지의 독립 파이프라인
# [SECTOR: 71_RIM_DETECTION]        흰 외곽선(rim) 반경 측정
# [SECTOR: 72_PATTERN_MODEL]        golden die 모델, pitch 추정/보정
# [SECTOR: 73_PARTICLE_INSPECTION]  inspect_white_noise_inside_rim() 후보 판정
# [SECTOR: 74_PARTICLE_RENDERING]   overlay/진단 이미지 표시
# [SECTOR: 75_ONE_STEP_API]         detect_white_noise() — map 생성+검사 래퍼
# [SECTOR: 90_USAGE_REFERENCE]      복사해 쓰는 호출 예시와 반환값 레퍼런스
#
# 수정 시작점
# - die map 결과가 틀리면: 20 -> 50 -> 60 순서로 확인합니다.
# - die 좌표·crop·edge만 틀리면: 30 또는 61을 확인합니다.
# - 회전/노치 문제면: 40을 확인합니다.
# - particle 오검출/미검출이면: 71 -> 72 -> 73 순서로 확인합니다.
# - 호출 방식/반환값만 확인할 때: 60, 61, 75, 90을 봅니다.
#

# -*- coding: utf-8 -*-
# =============================================================================
#  use_gray_wafer_die_particle_codex.py
# -----------------------------------------------------------------------------
#  wafer_die_map_v5.py (V5.5) 본체 + use_gray_wafer_die_particle.py 의
#  **코너(격자 원점) 검출 로직만** 이식한 병합본. 나머지는 V5.5 그대로다.
#
#  바뀐 점
#   1. 코너 검출 = detect_thin_cross_grid + _select_cross_origin
#      (grid_method 기본값 "thin_cross", cross_origin_mode 기본 "gv_boundary")
#   2. 후처리는 **재앵커링만** 유지한다.
#        · resolve_grid_phase   -> 기본 OFF (phase_match=False)
#        · refine_grid_origin   -> 기본 OFF (refine_origin=False)
#        · V5.5 origin 재앵커링 -> 유지. origin 을 wafer 중심에 가장 가까운
#          die 코너로 되돌린다. pitch 정수배만 더하므로 위상·기하는 불변.
#   3. 그 외(회전 보정 / wafer 검출 / edge clip / die map / 각도·4분면 검증)는
#      전부 동일하다.
#   4. ★ 파일 뒤쪽에 'WHITE-RIM PARTICLE' 블록을 **따로 분리해서** 추가했다.
#      wafer 외곽 흰색선을 측정하고 그 안쪽의 흰 노이즈를 잡는다.
#      die map 을 만든 다음 단계로 부르는 독립 모듈이고, 위쪽 파이프라인과
#      공유하는 것은 WaferDieMap / _gray_u8 / _as_bgr / detect_wafer 뿐이다.
#        detect_white_noise(image) ->  (die map 까지 한 번에)
#          {"binary", "corners_px", "overlay", "particles", "die_map", ...}
#        inspect_white_noise_inside_rim(image, die_map) ->  (2단계 분리)
#          {"binary", "corners_px", "overlay", "particles", ...}
#
#  주의: refine_origin 이 기본 OFF 라 street_w/street_h 는 측정되지 않는다.
#        exclude_street=True 를 쓰려면 refine_origin=True 로 켜야 한다.
# =============================================================================
"""
================================================================================
 Wafer Die Map V5  (Python 3.9, 단일 파일 — 통째로 복사/붙여넣기 해서 사용)
================================================================================

[V5 핵심 변경]
 · 기본 얼라인 = "die_render" : dm.dies(검출한 모든 die)를 cv2.rectangle 굵기 3으로
   그린 '이상적 격자 템플릿'에, 실제 sawline 엣지를 회전 정합시켜 기울기를 찾는다.
   실제 sawline 모양이 굵기 3 사각 테두리와 일치하므로, 모든 die·양축(가로/세로)을
   한꺼번에 이용해 가장 안정적으로 각도를 잡는다(2-pass: 대략검출→정합→재검출).
 · EDGE 구분 강화 : 각 die 에 두 가지 edge 플래그를 모두 부여(둘 다 선택 가능).
     - is_edge_partial : die 사각형이 wafer 원 밖으로 일부라도 나간 '부분 die'.
     - is_edge_ring    : die 격자에서 8방향 이웃이 다 차 있지 않은 '최외곽 줄'.
   build_die_map(edge_mode="circle"|"ring"|"both") 로 is_edge 가 무엇을 가리킬지 선택.
   locate_die 결과에 is_edge(+ is_edge_partial / is_edge_ring)가 함께 반환된다.
 · ★ EDGE die 전부 clip : die 포함 판정을 'die 중심이 원 안'에서 'die 사각형이 원과
   겹침' 으로 바꿨다. 예전엔 중심이 원 밖이면 사각형 절반이 원 안에 걸쳐 있어도
   맵에서 통째로 빠져(실제 이미지엔 보이는데 누락) EDGE 가 일부 사라졌다.
   build_die_map(edge_clip_all=True/False, edge_overlap_min_px=0.0) 로 제어한다.

[기능] (기존 wafer_die_map.py 대비)
 1. Notch 중심점 반환 : wafer '아래쪽'의 파인 곳(notch)만 탐색하고, 그 파임의
    중심 픽셀점을 기준으로 사용. dm.notch_center_px 로 반환.
 2. Angle 이중 검증   : notch 로 구한 각도를, die 격자(sawline) 방향으로 독립
    측정해 교차검증. dm.angle_verified / dm.die_grid_angle_resid.
 3. 4분면 맵 검증     : center corner 에서 die 를 확장해 만든 맵이 4분면(TL/TR/
    BL/BR) 가장자리까지 균형 있게 채워졌는지 확인. dm.quadrant_report.
 4. Wafer 원판 정리   : 시작 시 wafer 원판(가장 큰 연결성분) 밖을 모두 검정으로
    채워 외부 노이즈 제거 (clean_wafer). dm.aligned_image 가 정리된 이미지.
 5. 항상 aligned 반환 : 회전각이 0.0 이어도 dm.aligned_image 를 항상 반환
    (정리/보정 후 실제 사용 이미지).

[V5.1 각도 고도화 + 회전 깨짐 수정]
 · 각도 고도화 : die_render(투영 주기성)에 'FFT 스펙트럼' 교차검증을 추가했다.
   두 독립 단서가 일치하면 신뢰↑(dm.angle_agree/angle_confidence). 불일치/대각이면
   넓게(±44°) 재탐색해 '투영 peak 가 가장 큰' 각을 채택 → 큰 기울기(±10° 이상)도
   잡고, 격자 검출이 실패해도 '이미지 픽셀' 만으로 측정해 '조용히 0' 으로 실패하지 않는다.
 · 회전 깨짐 수정 : 회전 보간을 INTER_NEAREST → INTER_CUBIC 로 변경. 예전엔 die 격자
   같은 미세 주기 패턴이 NEAREST 회전 시 계단/모아레로 '깨져' 보였다. CUBIC 으로 매끈.

[V5.2 grid origin 서브픽셀 보정 + 순수 die crop]
 · ★ 문제 : wafer 중심을 확대해 보면 die 사이 street(십자 여백)의 '진짜 가운데'가
   아니라 살짝 쉬프트된 점이 origin 으로 잡혔다. 원인은 3가지였다.
     (1) detect_corner_grid 가 street band 의 **밝기 무게중심**(Σi·I / ΣI)을 쓴다.
         무게중심은 좌/우(상/하) die 밝기가 다르면 밝은 쪽으로 끌려간다.
     (2) origin/die 크기를 int 로 잘라 서브픽셀 정보가 버려졌다.
     (3) rect 를 `cx - die_w//2 … +die_w` 로 만들어 홀수 폭에서 좌/상으로 1px 치우쳤다.
 · ★ 해결 : refine_grid_origin() 신설 — 중앙 ROI 프로파일을 pitch 주기로 **접어서
   (phase folding)** 한 주기 평균 단면을 만든 뒤, street 의 좌/우 **half-max 교차점**
   을 선형보간으로 찾아 그 **중점** 을 origin 으로 쓴다. 좌/우 plateau(die 내부 밝기)
   로 half 레벨을 각각 따로 잡으므로 한쪽 die 가 밝아도 교차점이 밀리지 않는다.
   합성 검증 결과 origin 오차 5.000 px → 0.15 px (약 34배 개선).
 · ★ x0/y0/die_w/die_h 전부 float(서브픽셀). rect 는 좌/우·상/하 **대칭** 반올림.
 · ★ 부산물 : 두 교차점 간격 = street 실제 폭 → dm.street_w / dm.street_h 로 노출.
   build_die_map(exclude_street=True) 면 그 폭만큼 안쪽으로 줄인 '순수 die' 영역만
   남겨 이웃 street 가 crop 테두리에 묻지 않는다.
 · 제어 : build_die_map(refine_origin=True, exclude_street=False)
   결과 확인 : dm.origin_refined / dm.origin_shift_px / dm.street_w / dm.street_h

[V5.3 die 사이 간격이 '없는' 실제 wafer 대응]
 · ★ 문제 : V5.2 까지는 'die 사이에 street 여백이 있고, 한 주기 안에서 제일 강한 선이
   그 street' 라는 가정 위에 있었다. 실제 wafer 는 die 가 서로 맞붙어 있어 경계가
   얇은 녹색 seal ring(6~10 px) 뿐인데, die **안쪽**에 폭 46 px 짜리 배선 다발이 있어
   밝기로도 채도로도 경계보다 훨씬 강하다. 그래서 격자가 정확히 **반 주기** 밀린다.

     ┌──────────────────────────── 1 die (150 px) ──┐
     │ 회색 텍스처 │ ███ 배선 다발 46px ███ │ 회색  │
     └▲─────────────────────────────────────────────┘
      └ 진짜 die 경계 = 얇은 녹색 seal ring

 · (1) pitch 오검 : 배선 다발이 여러 색 선으로 쪼개져 각각 별도 band 가 되고, band
   간격의 median 이 sub-line 간격(121 px)이 되어 진짜 주기(150 px)를 놓쳤다.
   -> _merge_close_bands() 로 가까운 sub-line 을 한 구조물로 합치고, _resolve_pitch()
      로 자기상관 주기와 대조해 배수/약수 오검을 걸러낸다.
 · (2) origin 보정이 배선 다발 안쪽 '틈' 에서 멈췄다.
   -> _level_cross 가 _REFINE_GAP_RATIO(주기의 5%) 만큼의 틈은 넘어가게 했다.
 · (3) 레벨비 alpha 를 고정하면 이미지마다 폭이 튀었다.
   -> _REFINE_ALPHAS 스윕 + 2-pass 일관성 검사(_REFINE_ROBUST_MAX_JUMP).
 · ★ (4) 반 주기 밀림 : resolve_grid_phase() 신설. die 경계는 x·y 가 **같은 설계
   규칙**에서 나오므로 폭이 서로 비슷해야 한다는 성질만 쓴다(정답 라벨 불필요).
   축마다 phase 후보를 _PHASE_TOP_K 개 뽑아 각 후보가 올라탄 구조물의 외곽 폭을 재고,
   |w_x - w_y| 가 최소인 (x, y) 짝을 고른다. 단, 불일치가 _PHASE_MIN_GAIN(2.0)배
   이상 줄어들 때만 phase 를 바꾼다(멀쩡한 격자를 건드리지 않기 위해).
   실측: 폭 차이 33.4 -> 3.6, origin x0 5026.89 -> 4949.73 (-73.1 px = 반 주기).
 · 제어 : build_die_map(phase_match=True)   결과 확인 : dm.phase_matched
 · 한계 : x·y die 경계 폭이 실제로 크게 다른 공정에서는 끄는 게 맞다. 두 축이
   **동시에** 반 주기 밀린 경우는 폭 차이가 안 생겨 검출하지 못한다.
 · 검증/시각화 : verify_real_wafer.py (실제 wafer 1장 -> out_real/)

[회전(angle) 보정 방식 — build_die_map(angle_align_method=...) 로 선택]
 · "die_render"   (V5 기본) : die 격자(굵기 3 구조)의 '열/행 투영 주기성' + 'FFT 스펙트럼'
    교차검증으로 기울기 산출. 모든 die·양축 사용, 위상/극성 무관, 큰 기울기까지 견고.
 · "notch"        (옵션) : 아래쪽 notch 위치로 보정. 작은 각도까지 정밀(notch 필요).
 · "vertical_line"(옵션) : 이진화(Otsu)로 두꺼운 die 선을 잡고 '세선화'로 1px 중심선화한 뒤,
    '가장 긴 세로선'의 정확한 수직(90°) 대비 기울기로 보정(HoughLinesP). 이어서 가로축
    잔차까지 '순차(V->H)' 재보정. die 무늬가 뚜렷할 때 robust(notch 불필요).
    - 세선화 이유: 두꺼운 선은 양 가장자리가 다른 각도로 잡혀 각도가 흔들림 → 중심선 1개로 안정.
================================================================================

이 파일 "하나"만 다른 코드에 통째로 복붙하면 됩니다. (별도 import 불필요)
필요 외부 패키지는 numpy, opencv-python 뿐이며, 로컬 모듈 의존성은 없습니다.
공개 함수 2개만 쓰면 됩니다:

  1) build_die_map(image, ...)        -> WaferDieMap
        wafer 이미지 한 장을 넣으면 wafer/격자를 검출하고 EDGE 포함 전체 die map 생성.

  2) locate_die(die_map, point|bbox)  -> dict
        픽셀 좌표 또는 BBox(YOLO 등)를 넣으면 그 위치의
          - die_index (ix, iy)
          - die rect 픽셀 좌표 (x1, y1, x2, y2)
          - 실측 좌표/거리 (BBox 면 중심 기준)
        를 반환.

검출(웨이퍼 영역 + die 격자) 로직은 wafer_die_index_extract_39.py 의 것을
**그대로(verbatim)** 가져왔습니다. (detect_wafer / detect_grid / clip_die + 헬퍼)
미사용 함수(_norm01, _detect_line_hue, _wafer_color_mask, _refine_corner)만 제외.

인덱스 규칙 (원본과 동일)
--------------------------
- wafer 중앙 근처 die 4개가 만나는 격자 코너 = grid origin (x0, y0)
- 그 코너의 우측 상단 die 가 (ix=0, iy=0)
- ix +1 -> 한 칸 오른쪽(이미지 x 증가),  iy +1 -> 한 칸 위쪽(이미지 y 감소)
- die (ix, iy) 중심 픽셀:
      cx = x0 + ix*pitch_x + pitch_x/2
      cy = y0 - iy*pitch_y - pitch_y/2

실측 좌표 (real_coord)
-----------------------
- pixel_per_unit (default 32 px = 1 unit) 로 wafer 중심 기준 상대 좌표 환산
      rx = (px - wafer_cx) / pixel_per_unit
      ry = (wafer_cy - py) / pixel_per_unit       # 화면 위쪽이 +y

의존성: numpy, opencv-python
================================================================================
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import cv2
import numpy as np

__all__ = ["WaferDieMap", "build_die_map", "locate_die", "crop_die",
           "detect_notch_angle", "detect_notch", "align_wafer_by_notch",
           "align_wafer_by_vertical_line", "clean_wafer",
           "measure_die_grid_angle", "measure_vertical_line_angle",
           "measure_horizontal_line_angle", "measure_axis_line_angle",
           "validate_quadrant_edges",
           "render_die_grid_mask", "measure_die_render_angle",
           "align_wafer_by_die_render", "measure_wafer_angle_robust",
           # ★[claude] 흰색 외곽선 안쪽 흰 노이즈(particle) 검출
           "WaferRimBand", "DiePatternModel",
           "detect_wafer_rim_band", "build_die_pattern_model",
           "estimate_pattern_pitch", "refine_pattern_pitch",
           "die_pattern_zscore",
           "inspect_white_noise_inside_rim", "detect_white_noise",
           "render_white_noise_overlay",
           "render_white_noise_diagnostic_overlay",
           "imread_unicode"]


# #############################################################################
# [SECTOR: 10_CORE_AND_WAFER] 공통 이미지 처리와 wafer/기초 격자 검출
# #                                                                           #
# #   CORE DETECTION  (원본 로직 그대로 — 수정 금지 영역)                      #
# #   wafer_die_index_extract_39.py 에서 복사. 동작/결과 동일.                #
# #                                                                           #
# #############################################################################

# =============================================================================
# 0) ★[V5.4] 해상도 / 채널 / 신호세기 정규화 헬퍼
#
#   V5.3 까지의 상수는 전부 '10000x10000 3채널, 신호 강함' 을 전제로 손튜닝돼 있다.
#   3000x3000 1채널 약신호 이미지를 넣으면 다음 순서로 무너진다.
#     · detect_wafer   : bg_threshold=20 절대값 -> 어두운 wafer 는 mask 가 비어 실패
#     · detect_wafer   : morphology kernel 25px 고정 -> 작은 이미지에선 과도한 침식
#     · _street_color_mask : 1채널은 채도(max-min)가 항상 0 -> min_color_delta=35 에
#       전부 걸러져 mask 가 완전히 빈다 -> '코너를 못 찾는' 직접 원인
#     · _autocorr_period(min_lag=50) -> pitch 30~70 대역의 아래쪽을 아예 못 찾는다
#   여기의 헬퍼로 '크기 상수는 해상도 비례', '세기 상수는 영상 통계 비례' 로 바꾼다.
# =============================================================================
_REF_DIM = 10000.0          # 기존 상수들이 튜닝된 기준 해상도(짧은 변)
_MONO_CHROMA_EPS = 1.0      # 평균 채도가 이 값 미만이면 사실상 1채널로 취급


def _dim_scale(image: np.ndarray) -> float:
    """기준 해상도 대비 배율. 픽셀 단위 '크기' 상수에만 곱한다."""
    short = float(min(image.shape[:2]))
    return float(np.clip(short / _REF_DIM, 0.1, 4.0))


def _scaled(value: float, image: np.ndarray, minimum: float = 1.0) -> int:
    """픽셀 크기 상수를 해상도에 맞춰 환산 (최소값 보장)."""
    return int(max(minimum, round(float(value) * _dim_scale(image))))


def _is_mono(image: np.ndarray) -> bool:
    """1채널이거나, 3채널이어도 채도가 사실상 0 이면 True.

    grayscale 파일을 cv2.IMREAD_COLOR 로 읽으면 동일한 값 3장이 되므로 shape 만
    봐서는 구분되지 않는다. 채도 자체를 재야 한다.
    """
    if image.ndim == 2 or image.shape[2] == 1:
        return True
    step = max(1, min(image.shape[0], image.shape[1]) // 256)   # 통계용 subsample
    sub = image[::step, ::step, :3].astype(np.int16)
    return float((sub.max(axis=2) - sub.min(axis=2)).mean()) < _MONO_CHROMA_EPS


def _otsu_level(gray: np.ndarray) -> int:
    """Otsu 임계값 원값(보정 없음). detect_wafer 의 상향 후보로 쓴다."""
    step = max(1, min(gray.shape[:2]) // 512)
    otsu, _ = cv2.threshold(gray[::step, ::step], 0, 255,
                            cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return int(round(otsu))


def _auto_bg_threshold(gray: np.ndarray, fallback: int = 20) -> int:
    """wafer / 검정배경 분리 임계를 영상 통계로 정한다 (약신호 대응).

    배경은 0 근처에 뾰족하게 몰려 있고 wafer 는 그보다 훨씬 밝다. Otsu 로 한 번
    가르되, 결과가 터무니없으면(전부/거의 없음) 기존 고정값으로 되돌린다.
    Otsu 가 'die vs street' 를 가르는 쪽으로 빠지는 경우를 막기 위해 상한을 둔다.
    """
    step = max(1, min(gray.shape[:2]) // 512)
    sub = gray[::step, ::step]
    otsu, _ = cv2.threshold(sub, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    # 배경 잡음 수준: 가장 어두운 1% 의 산포
    dark = float(np.percentile(sub, 1.0))
    noise = float(np.percentile(sub, 5.0) - dark)
    floor = max(2.0, dark + 3.0 * max(noise, 1.0))
    # Otsu 는 wafer 내부를 가르는 쪽으로 빠질 수 있으므로 중앙값의 절반으로 상한
    ceil_ = max(floor + 1.0, float(np.median(sub)) * 0.5)
    thr = float(np.clip(otsu * 0.5, floor, ceil_))
    ratio = float((sub > thr).mean())
    if not (0.02 < ratio < 0.98):
        return int(fallback)
    return int(round(thr))


# =============================================================================
# 1) Wafer 영역(원) 검출
# =============================================================================
def detect_wafer(image_bgr: np.ndarray,
                 bg_threshold: Optional[int] = None) -> Tuple[int, int, int]:
    """검정 배경을 제외한 가장 큰 contour 를 wafer 로 간주. -> (cx, cy, radius).

    ★[V5.4] bg_threshold=None(기본) 이면 영상 통계로 자동 결정하고, 여러 후보를
    모두 평가해 '가장 원판다운' 결과를 고른다. morphology kernel 은 해상도 비례.
    약신호에서는 배경 노이즈 점이 minEnclosingCircle 을 부풀리므로,
      · 임계 전 해상도 비례 blur 로 점 노이즈를 죽이고
      · 반지름은 최소외접원이 아니라 '면적 등가 반지름' 으로 잡는다.
    기존처럼 정수를 직접 주면 그 값만 쓴다(동작 완전 호환).
    """
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    ksize = _scaled(25, image_bgr, minimum=3)
    if ksize % 2 == 0:
        ksize += 1
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (ksize, ksize))

    # 약신호 대응: 임계 직전에만 쓰는 blur. wafer 원 크기에 비하면 무시할 수준이라
    # 경계는 안 밀리고, 배경의 고립 노이즈 점만 임계 아래로 내려간다.
    sigma = max(1.0, 3.0 * _dim_scale(image_bgr))
    gray_s = cv2.GaussianBlur(gray, (0, 0), sigmaX=sigma)

    if bg_threshold is None:
        # ★[V5.4] 후보는 반드시 '양방향' 이어야 한다.
        #   배경이 완전한 검정이 아니라 밝기 20~30 대에 떠 있는 영상(센서 플로어,
        #   JPEG 블록 노이즈, 조명 누설)에서는 낮은 후보가 전부 실패한다 —— 마스크가
        #   이미지 전체가 되어 반지름이 20% 부풀어도 '그중 최선' 으로 뽑혀버린다.
        #   Otsu 원값(보정 없음)을 상향 후보로 넣어두면 아래 circ 채점이 알아서
        #   진짜 원판(circ≈1.0)을 고른다. 낮은 후보들은 그대로 두므로 무회귀.
        auto = _auto_bg_threshold(gray_s)
        otsu = _otsu_level(gray_s)
        candidates = [auto, otsu, (auto + otsu) // 2, 20, 10, 5, 3]
    else:
        candidates = [int(bg_threshold)]

    best: Optional[Tuple[int, int, int]] = None
    best_score = -1.0
    seen: set = set()
    area_img = float(gray.shape[0] * gray.shape[1])
    for thr in candidates:
        if thr in seen:
            continue
        seen.add(thr)
        _, mask = cv2.threshold(gray_s, thr, 255, cv2.THRESH_BINARY)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            continue
        cnt = max(contours, key=cv2.contourArea)
        area = float(cv2.contourArea(cnt))
        (mx, my), m_radius = cv2.minEnclosingCircle(cnt)
        if m_radius <= 1.0 or area <= 0.0:
            continue

        # 반지름: 면적 등가( sqrt(A/pi) ). 노이즈 돌기 하나가 반지름을 끌어올리는
        # minEnclosingCircle 과 달리, 튀는 점 몇 개에 흔들리지 않는다.
        radius = math.sqrt(area / math.pi)
        M = cv2.moments(cnt)
        if M["m00"] > 0:
            cx, cy = M["m10"] / M["m00"], M["m01"] / M["m00"]   # 무게중심
        else:
            cx, cy = mx, my
        got = (int(round(cx)), int(round(cy)), int(round(radius)))

        # 원판다움 점수: 면적등가원 대비 최소외접원이 얼마나 안 부풀었는가
        #   (완전한 원이면 1.0, 돌기/노이즈가 붙을수록 작아진다)
        circ = (radius / m_radius) ** 2
        frac = (math.pi * radius * radius) / area_img
        score = circ if 0.05 <= frac <= 0.95 else circ * 0.1
        if score > best_score:
            best, best_score = got, score

    if best is None:
        raise RuntimeError("Wafer region not found "
                           "(전부 배경이거나 bg_threshold 가 너무 높음).")
    return best


# =============================================================================
# 2) Die 격자 자동 검출 (+ 내부 헬퍼)
# =============================================================================
def _autocorr_period(profile: np.ndarray,
                     min_lag: int = 50,
                     max_lag: Optional[int] = None,
                     harmonic_threshold: float = 0.7) -> int:
    """1D 신호의 fundamental period 를 autocorrelation 으로 추정."""
    p = profile.astype(np.float64)
    p -= p.mean()
    n = len(p)
    if n < min_lag * 4:
        raise RuntimeError("Profile too short for autocorrelation.")

    corr = np.correlate(p, p, mode='full')[n - 1:]
    if max_lag is None:
        max_lag = n // 3

    peaks: List[Tuple[int, float]] = []
    for lag in range(min_lag, min(max_lag, len(corr) - 1)):
        if corr[lag] > corr[lag - 1] and corr[lag] > corr[lag + 1] and corr[lag] > 0:
            peaks.append((lag, float(corr[lag])))
    if not peaks:
        raise RuntimeError("Failed to estimate period from autocorrelation.")

    best_lag, best_val = max(peaks, key=lambda x: x[1])

    candidates = [best_lag]
    threshold = best_val * harmonic_threshold
    for k in (2, 3, 4, 5):
        sub = best_lag // k
        if sub < min_lag:
            break
        tol = max(2, sub // 20)
        for lag, val in peaks:
            if abs(lag - sub) <= tol and val >= threshold \
                    and abs(lag * k - best_lag) <= max(3, best_lag // 30):
                candidates.append(lag)
                break

    return min(candidates)


def _best_phase(profile: np.ndarray, pitch: int) -> int:
    """fallback : profile 을 pitch 로 슬라이딩해 grid-line 평균 최대 phase 반환."""
    best_ph, best_val = 0, -np.inf
    for ph in range(pitch):
        v = float(profile[ph::pitch].mean())
        if v > best_val:
            best_val = v
            best_ph = ph
    return best_ph


def _find_periodic_peaks(profile: np.ndarray,
                          approx_pitch: float,
                          min_score_ratio: float = 0.3
                          ) -> List[int]:
    """profile 에서 approx_pitch 간격으로 분포한 local maxima 위치 반환."""
    n = len(profile)
    if n < 3:
        return []
    max_val = float(profile.max())
    thr = max_val * min_score_ratio
    min_spacing = max(2, int(approx_pitch * 0.6))

    peaks: List[int] = []
    for i in range(1, n - 1):
        if profile[i] > profile[i - 1] and profile[i] > profile[i + 1] and profile[i] > thr:
            if not peaks or i - peaks[-1] >= min_spacing:
                peaks.append(i)
            elif profile[i] > profile[peaks[-1]]:
                peaks[-1] = i
    return peaks


def _refine_origin_with_template(image_bgr: np.ndarray,
                                  die_template_bgr: np.ndarray,
                                  pitch_x: float, pitch_y: float,
                                  approx_x0: int, approx_y0: int,
                                  wafer_cx: int, wafer_cy: int, wafer_r: int
                                  ) -> Tuple[float, float, int, int, float]:
    """(옵션) die_sample 이미지로 matchTemplate -> sub-pixel pitch + phase 재추정."""
    tw, th = int(round(pitch_x)), int(round(pitch_y))
    template = cv2.resize(die_template_bgr, (tw, th), interpolation=cv2.INTER_AREA)

    def _edge(g: np.ndarray) -> np.ndarray:
        gf = g.astype(np.float32)
        sx = cv2.Sobel(gf, cv2.CV_32F, 1, 0, ksize=3)
        sy = cv2.Sobel(gf, cv2.CV_32F, 0, 1, ksize=3)
        return np.sqrt(sx * sx + sy * sy).astype(np.float32)

    e_w = _edge(cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY))
    e_t = _edge(cv2.cvtColor(template,  cv2.COLOR_BGR2GRAY))

    half = int(wafer_r * 0.5)
    rx1 = max(wafer_cx - half, 0)
    ry1 = max(wafer_cy - half, 0)
    rx2 = min(wafer_cx + half, e_w.shape[1])
    ry2 = min(wafer_cy + half, e_w.shape[0])
    if rx2 - rx1 <= tw + 2 or ry2 - ry1 <= th + 2:
        return pitch_x, pitch_y, approx_x0, approx_y0, 0.0
    roi = e_w[ry1:ry2, rx1:rx2]

    res = cv2.matchTemplate(roi, e_t, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, _ = cv2.minMaxLoc(res)

    col_proj = res.max(axis=0)
    row_proj = res.max(axis=1)

    x_peaks = _find_periodic_peaks(col_proj, pitch_x)
    y_peaks = _find_periodic_peaks(row_proj, pitch_y)

    if len(x_peaks) >= 3:
        slope_x, intercept_x = np.polyfit(np.arange(len(x_peaks)), x_peaks, 1)
        pitch_x_ref = float(slope_x)
        phase_x = float(intercept_x)
    else:
        pitch_x_ref = float(pitch_x)
        phase_x = float(x_peaks[0]) if x_peaks else 0.0
    if len(y_peaks) >= 3:
        slope_y, intercept_y = np.polyfit(np.arange(len(y_peaks)), y_peaks, 1)
        pitch_y_ref = float(slope_y)
        phase_y = float(intercept_y)
    else:
        pitch_y_ref = float(pitch_y)
        phase_y = float(y_peaks[0]) if y_peaks else 0.0

    kx = round((wafer_cx - rx1 - phase_x) / pitch_x_ref)
    ky = round((wafer_cy - ry1 - phase_y) / pitch_y_ref)
    x0 = int(round(rx1 + phase_x + kx * pitch_x_ref))
    y0 = int(round(ry1 + phase_y + ky * pitch_y_ref))

    return pitch_x_ref, pitch_y_ref, x0, y0, float(max_val)


def _robust_phase(peaks: List[int], pitch: float,
                  profile: np.ndarray) -> float:
    """여러 periodic peak 위치로부터 노이즈에 강인한 phase(0~pitch) 추정."""
    if not peaks:
        return float(_best_phase(profile, int(round(pitch))))
    mods = np.array([p % pitch for p in peaks], dtype=np.float64)
    ref = float(mods[0])
    adj = ((mods - ref + pitch / 2.0) % pitch) - pitch / 2.0
    return float((ref + np.median(adj)) % pitch)


def _grid_profiles_std(gray_roi: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """[method='std'] column/row STD 의 최소점(=균일 boundary 라인) 신호."""
    col_std = gray_roi.std(axis=0)
    row_std = gray_roi.std(axis=1)
    col_profile = float(col_std.max()) - col_std
    row_profile = float(row_std.max()) - row_std
    return col_profile.astype(np.float64), row_profile.astype(np.float64)


def _grid_profiles_color(image_bgr: np.ndarray, gray: np.ndarray,
                         x1: int, x2: int, y1: int, y2: int,
                         wafer_cx: int, wafer_cy: int, wafer_r: int,
                         line_hue: Optional[int], hue_delta: int,
                         sat_min: int, val_min: int
                         ) -> Tuple[np.ndarray, np.ndarray]:
    """[method='color'/'hybrid'] die 중앙 컬러 stripe 다발(채도) projection."""
    hsv = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV)
    sat = hsv[:, :, 1].astype(np.float32)
    val = hsv[:, :, 2]

    valid = (val >= val_min).astype(np.float32)
    sat_roi = sat[y1:y2, x1:x2]
    valid_roi = valid[y1:y2, x1:x2]

    col_num = (sat_roi * valid_roi).sum(axis=0)
    col_den = valid_roi.sum(axis=0) + 1e-6
    row_num = (sat_roi * valid_roi).sum(axis=1)
    row_den = valid_roi.sum(axis=1) + 1e-6
    col_profile = (col_num / col_den).astype(np.float64)
    row_profile = (row_num / row_den).astype(np.float64)
    return col_profile, row_profile


# --- corner-grid detection (codex "corner" 방식: street 선 자체로 코너 직접 검출) ---
def _street_color_mask(image_bgr: np.ndarray,
                       x1: int, x2: int, y1: int, y2: int,
                       min_brightness: float,
                       min_channel: int,
                       min_color_delta: int,
                       max_color_delta: int) -> np.ndarray:
    """밝은 wafer street/grid 색만 mask 로 분리한다.

    검은 노이즈와 회색 die 면은 제외하고, 내부 rainbow stripe 처럼 색 변화가
    너무 큰 패턴도 제외한다. Noise 샘플의 코너 교차점 검출에 쓰는 전용 mask.

    ★[V5.4] 1채널(또는 채도가 사실상 0인) 영상에서는 color_delta 가 항상 0 이라
    min_color_delta 조건에 전부 걸려 mask 가 통째로 비었다. 그래서 street band 가
    하나도 안 잡히고 '코너를 못 찾음' 으로 끝났다. mono 일 때는 색 조건을 빼고
    밝기 조건만 쓰되, 절대 밝기(115/130)는 약신호에서 무의미하므로 ROI 분위수로
    바꾼다.
    """
    roi = image_bgr[y1:y2, x1:x2]
    if roi.ndim == 2:
        roi = roi[:, :, None]
    maxc = roi.max(axis=2).astype(np.int16)
    minc = roi.min(axis=2).astype(np.int16)
    brightness = roi.mean(axis=2)
    color_delta = maxc - minc

    if _is_mono(image_bgr):
        # street 는 die 면보다 밝은 소수 픽셀이다. 상위 분위수를 임계로 쓴다.
        lo = float(np.percentile(brightness, 80.0))
        hi = float(np.percentile(brightness, 99.9))
        if hi - lo < 1.0:            # 대비가 거의 없으면 평균+표준편차로 후퇴
            lo = float(brightness.mean() + brightness.std())
        mask = brightness > lo
    else:
        mask = (
            (brightness > min_brightness)
            & (maxc > min_channel)
            & (color_delta >= min_color_delta)
            & (color_delta <= max_color_delta)
        )
    mask = mask.astype(np.uint8) * 255
    mask = cv2.medianBlur(mask, 3)
    return cv2.morphologyEx(
        mask,
        cv2.MORPH_CLOSE,
        cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3)),
        iterations=1,
    )


def _smooth_projection(values: np.ndarray, window: int) -> np.ndarray:
    """1D projection 을 이동 평균으로 완만하게 만든다."""
    if window <= 1:
        return values.astype(np.float32)
    kernel = np.ones(window, dtype=np.float32) / float(window)
    return np.convolve(values.astype(np.float32), kernel, mode="same")


def _find_projection_bands(profile: np.ndarray,
                           offset: int,
                           min_width: int,
                           threshold_ratio: float,
                           sigma: float,
                           min_projection: float
                           ) -> List[Tuple[float, int, int, float]]:
    """projection 에서 연속된 강한 line band 들을 찾는다.

    Returns
    -------
    [(center, start, end, score), ...]
    """
    if profile.size == 0 or float(profile.max()) <= 0.0:
        return []

    threshold = max(
        float(profile.mean() + sigma * profile.std()),
        float(profile.max() * threshold_ratio),
        float(min_projection),
    )
    above = profile >= threshold

    bands: List[Tuple[float, int, int, float]] = []
    i = 0
    n = len(profile)
    while i < n:
        if not above[i]:
            i += 1
            continue

        j = i
        while j < n and above[j]:
            j += 1

        if j - i >= min_width:
            segment = profile[i:j]
            weights = np.maximum(segment, 1e-6)
            center = float((np.arange(i, j) * weights).sum() / weights.sum())
            bands.append((offset + center, offset + i, offset + j, float(segment.max())))
        i = j

    return bands


def _choose_previous_band(bands: List[Tuple[float, int, int, float]],
                          center: float) -> Tuple[float, int, int, float]:
    """wafer 중심보다 작거나 같은 가장 가까운 band 를 선택한다."""
    if not bands:
        raise RuntimeError("No wafer street/grid line was found near wafer center.")

    previous = [band for band in bands if band[0] <= center]
    if previous:
        return max(previous, key=lambda band: band[0])
    return min(bands, key=lambda band: abs(band[0] - center))


def _choose_nearest_band(bands: List[Tuple[float, int, int, float]],
                         center: float) -> Tuple[float, int, int, float]:
    """wafer 중심에 가장 가까운 band 를 선택한다."""
    if not bands:
        raise RuntimeError("No wafer street/grid line was found near wafer center.")
    return min(bands, key=lambda band: abs(band[0] - center))


def _median_band_spacing(bands: List[Tuple[float, int, int, float]],
                         fallback_pitch: float,
                         min_pitch: int,
                         max_pitch: Optional[int]) -> float:
    """검출된 street band 사이 간격의 median 으로 pitch 를 보정한다."""
    if len(bands) < 3:
        return float(fallback_pitch)

    centers = np.array(sorted(band[0] for band in bands), dtype=np.float64)
    diffs = np.diff(centers)
    upper = float(max_pitch) if max_pitch is not None else float(fallback_pitch * 1.8)
    lower = float(min_pitch)
    diffs = diffs[(diffs >= lower) & (diffs <= upper)]
    if diffs.size == 0:
        return float(fallback_pitch)
    return float(np.median(diffs))


# ---------------------------------------------------------------------------
# ★ V5.3 : 실제 wafer 의 street 는 '한 줄' 이 아니라 여러 색 sub-line 다발이다.
#   projection band 검출은 그 sub-line 을 각각 잡으므로, band 간격 median 은
#   'street 안 sub-line 간격' 과 'street 사이 빈 구간' 이 뒤섞여 엉뚱한 pitch 가
#   나온다(실측: 진짜 150 px 인데 121.4 px 로 잡힘 -> 이후 phase folding 이 전부 붕괴).
#   같은 street 에 속한 band 를 먼저 하나로 묶고, autocorrelation rough pitch 와
#   교차검증해서 채택한다.
# ---------------------------------------------------------------------------
_BAND_MERGE_RATIO = 0.45   # 이 * rough_pitch 보다 가까운 band 는 같은 street 로 본다
_PITCH_AGREE_RATIO = 0.10  # rough pitch 와 이 비율 안에서 일치할 때만 band pitch 채택


def _merge_close_bands(bands: List[Tuple[float, int, int, float]],
                       max_gap: float) -> List[Tuple[float, int, int, float]]:
    """한 street 가 여러 sub-line 으로 쪼개져 잡힌 band 들을 하나로 묶는다."""
    if not bands:
        return []
    ordered = sorted(bands, key=lambda band: band[0])
    groups: List[List[Tuple[float, int, int, float]]] = [[ordered[0]]]
    for band in ordered[1:]:
        if band[0] - groups[-1][-1][0] <= max_gap:
            groups[-1].append(band)
        else:
            groups.append([band])

    merged: List[Tuple[float, int, int, float]] = []
    for group in groups:
        weights = np.array([max(b[3], 1e-6) for b in group], dtype=np.float64)
        centers = np.array([b[0] for b in group], dtype=np.float64)
        merged.append((float((centers * weights).sum() / weights.sum()),
                       int(min(b[1] for b in group)),
                       int(max(b[2] for b in group)),
                       float(max(b[3] for b in group))))
    return merged


def _resolve_pitch(bands: List[Tuple[float, int, int, float]],
                   rough_pitch: float,
                   min_pitch: int,
                   max_pitch: Optional[int]) -> float:
    """band 간격 pitch 후보(원본/병합)를 rough pitch 와 교차검증해 고른다."""
    rough = float(rough_pitch)
    if rough <= 0.0:
        return rough
    merged = _merge_close_bands(bands, rough * _BAND_MERGE_RATIO)
    candidates = [_median_band_spacing(bands, rough, min_pitch, max_pitch),
                  _median_band_spacing(merged, rough, min_pitch, max_pitch)]
    best = min(candidates, key=lambda p: abs(p - rough))
    return best if abs(best - rough) <= rough * _PITCH_AGREE_RATIO else rough



# =============================================================================
# [SECTOR: 20_DIE_GRID_DETECTION] Gray/corner/cross 기반 die grid 검출
# ★[codex] Gray wafer 전용 코너(십자) 검출 — use_gray_wafer_die_particle.py 이식
# -----------------------------------------------------------------------------
# 아래 블록은 use_gray_wafer_die_particle.py 에서 **코너(격자 원점) 찾는 로직만**
# 그대로 가져온 것이다. V5.5 본체의 나머지 파이프라인(회전 보정 / wafer 검출 /
# edge clip / die map 구성 / 검증)은 손대지 않았다.
#
#  · detect_thin_cross_grid : CLAHE -> ridge(absdiff) -> Otsu∪82%tile -> 방향성
#    MORPH_OPEN -> 평균 projection -> thin band 필터 -> sub-pitch band 제거 ->
#    Sobel autocorr rough pitch -> band spacing median.
#  · _select_cross_origin   : "gv_boundary"(기본) / "center_scored" 두 모드.
#    - gv_boundary : 반복되는 밝은 세로 band 는 die '중앙' 노이즈다. 가장 가까운
#      lane 을 고른 뒤 wafer 중심 쪽으로 half-pitch 이동해 경계에 앉힌다.
#    - center_scored : x0 는 wafer_cx 그대로, y0 는 중심 이하(위쪽) 행 우선.
#      실제 Gray wafer 의 코너 특징이 중심보다 살짝 위에 있다는 관측 반영.
#
# _median_band_spacing 은 V5 본체에도 동명 함수가 있으나 동작이 다르다(gray 판은
# [min_pitch, max_pitch] 로 clamp 한다). 기존 detect_corner_grid 의 거동을 그대로
# 두기 위해 여기서는 _median_band_spacing_bounded 라는 별도 이름으로 넣는다.
# =============================================================================

def _as_bgr(image: np.ndarray) -> np.ndarray:
    """Normalize direct Gray/BGR/BGRA input for public detection functions."""
    if not isinstance(image, np.ndarray) or image.size == 0:
        raise ValueError("image must be a non-empty numpy array")
    if image.ndim == 2:
        return cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    if image.ndim != 3:
        raise ValueError("image must have shape (H,W), (H,W,1), (H,W,3), or (H,W,4)")
    if image.shape[2] == 1:
        return cv2.cvtColor(image[:, :, 0], cv2.COLOR_GRAY2BGR)
    if image.shape[2] == 3:
        return image
    if image.shape[2] == 4:
        return cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
    raise ValueError("image must have 1, 3, or 4 channels")


def _gray_u8(image: np.ndarray) -> np.ndarray:
    """Return a stable uint8 gray image for threshold and morphology operations."""
    bgr = _as_bgr(image)
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    if gray.dtype == np.uint8:
        return gray
    return cv2.normalize(gray, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)


def _safe_autocorr_period(profile: np.ndarray, min_pitch: int,
                          max_pitch: Optional[int], fallback: float) -> float:
    """Autocorrelation fallback that never escapes the requested pitch range."""
    try:
        return float(_autocorr_period(profile, min_lag=min_pitch, max_lag=max_pitch))
    except RuntimeError:
        lower = float(min_pitch)
        upper = float(max_pitch) if max_pitch is not None else max(lower, fallback)
        return min(max(float(fallback), lower), upper)


def _discard_subpitch_bands(bands: List[Tuple[float, int, int, float]],
                            min_pitch: int) -> List[Tuple[float, int, int, float]]:
    """Reject both edges of a broad noise stripe that are much closer than one pitch."""
    ordered = sorted(bands, key=lambda band: band[0])
    reject: set[int] = set()
    close_limit = max(4.0, float(min_pitch) * 0.50)
    for index in range(len(ordered) - 1):
        if ordered[index + 1][0] - ordered[index][0] < close_limit:
            reject.add(index)
            reject.add(index + 1)
    return [band for index, band in enumerate(ordered) if index not in reject]


def _periodic_band_support(bands: List[Tuple[float, int, int, float]],
                           position: float, pitch: float) -> float:
    """Measure whether a candidate belongs to a repeating grid phase.

    An isolated narrow vertical noise line can pass the width filter.  Unlike a
    real street, it does not have similarly thin bands at ``position +/- n*pitch``.
    The returned 0..1 support is therefore used as a second guard after width.
    """
    if len(bands) < 2 or pitch <= 0:
        return 0.0
    coords = [float(band[0]) for band in bands]
    lower, upper = min(coords), max(coords)
    tolerance = max(2.0, float(pitch) * 0.14)
    matched = 0
    expected = 0
    step = 1
    while position - step * pitch >= lower - tolerance:
        expected += 1
        if min(abs(coord - (position - step * pitch)) for coord in coords) <= tolerance:
            matched += 1
        step += 1
    step = 1
    while position + step * pitch <= upper + tolerance:
        expected += 1
        if min(abs(coord - (position + step * pitch)) for coord in coords) <= tolerance:
            matched += 1
        step += 1
    return float(matched / expected) if expected else 0.0


def _keep_periodic_candidates(bands: List[Tuple[float, int, int, float]],
                              pitch: float) -> List[Tuple[float, int, int, float]]:
    """Keep grid-phase candidates and reject isolated thin noise when possible."""
    if len(bands) < 3:
        return bands
    scored = [(band, _periodic_band_support(bands, band[0], pitch)) for band in bands]
    best = max(score for _, score in scored)
    # Do not make a weak image fail solely because periodic support is poor;
    # only remove candidates when another phase is clearly better.
    if best < 0.35:
        return bands
    return [band for band, score in scored if score >= max(0.35, best * 0.70)]


def _median_band_spacing_bounded(bands: List[Tuple[float, int, int, float]],
                         fallback_pitch: float,
                         min_pitch: int,
                         max_pitch: Optional[int]) -> float:
    """검출된 street band 사이 간격의 median 으로 pitch 를 보정한다.

    ``max_pitch``는 권장값이 아니라 hard upper bound이다. band가 부족할 때도
    fallback을 그대로 반환하지 않고 같은 상한을 적용해야, `max_pitch=70`인데
    결과 pitch가 100 이상이 되는 문제가 생기지 않는다.
    """
    if max_pitch is not None and max_pitch < min_pitch:
        raise ValueError("max_pitch must be greater than or equal to min_pitch")

    def _bounded(value: float) -> float:
        value = max(float(min_pitch), float(value))
        return min(value, float(max_pitch)) if max_pitch is not None else value

    if len(bands) < 3:
        return _bounded(fallback_pitch)

    centers = np.array(sorted(band[0] for band in bands), dtype=np.float64)
    diffs = np.diff(centers)
    upper = float(max_pitch) if max_pitch is not None else float(fallback_pitch * 1.8)
    lower = float(min_pitch)
    diffs = diffs[(diffs >= lower) & (diffs <= upper)]
    if diffs.size == 0:
        return _bounded(fallback_pitch)
    return _bounded(float(np.median(diffs)))


def _estimate_center_above_guide_y(horizontal_profile: np.ndarray,
                                   ridge_profile: np.ndarray,
                                   roi_y0: int, wafer_cy: float,
                                   pitch_y: float) -> float:
    """Estimate a weak horizontal guide when no reliable guide band survives.

    Search only the expected area just above the wafer center.  Directional
    horizontal support is preferred; the raw ridge projection contributes a
    smaller fallback signal when a broken/weak guide cannot survive morphology.
    """
    horizontal = np.asarray(horizontal_profile, dtype=np.float64).reshape(-1)
    ridge = np.asarray(ridge_profile, dtype=np.float64).reshape(-1)
    if horizontal.size == 0 or ridge.size != horizontal.size:
        return float(wafer_cy - max(1, int(round(pitch_y * 0.46))))

    def normalize(values: np.ndarray) -> np.ndarray:
        lo, hi = np.percentile(values, (10, 95))
        if hi <= lo + 1e-9:
            return np.zeros_like(values)
        return np.clip((values - lo) / (hi - lo), 0.0, 1.0)

    score = normalize(horizontal) + 0.35 * normalize(ridge)
    score = np.asarray(_smooth_projection(score, 3), dtype=np.float64)
    expected_offset = max(1, int(round(float(pitch_y) * 0.46)))
    min_offset = max(2, int(round(float(pitch_y) * 0.12)))
    start_y = int(round(wafer_cy - max(float(pitch_y) * 1.20, min_offset + 1)))
    end_y = int(round(wafer_cy - min_offset))
    start = max(0, start_y - int(roi_y0))
    end = min(score.size, end_y - int(roi_y0) + 1)
    if start >= end or float(score[start:end].max()) <= 1e-9:
        return float(wafer_cy - expected_offset)
    return float(int(roi_y0) + start + int(np.argmax(score[start:end])))


def _select_cross_origin(x_bands: List[Tuple[float, int, int, float]],
                         y_bands: List[Tuple[float, int, int, float]],
                         wafer_cx: float, wafer_cy: float,
                         pitch_x: float, pitch_y: float,
                         origin_mode: str = "gv_boundary") -> Tuple[float, float]:
    """Select central thin vertical/horizontal ridges and form their cross origin."""
    mode = str(origin_mode).lower().strip()
    if mode in ("center", "center_score", "center_scored", "score"):
        mode = "center_scored"
    elif mode in ("gv", "boundary", "gv_boundary", "nearest"):
        mode = "gv_boundary"
    else:
        raise ValueError("cross_origin_mode must be 'gv_boundary' or 'center_scored'.")

    if not y_bands or (not x_bands and mode != "center_scored"):
        raise RuntimeError("No thin vertical/horizontal cross candidates were found near wafer center.")

    # Grid origin must be a central cross. Restricting this first prevents a stronger
    # but distant defect/noise intersection from winning only by projection strength.
    near_x = [band for band in x_bands if abs(band[0] - wafer_cx) <= max(2.0, pitch_x * 1.15)]
    near_y = [band for band in y_bands if abs(band[0] - wafer_cy) <= max(2.0, pitch_y * 1.15)]

    periodic_x = _keep_periodic_candidates(x_bands, pitch_x)
    periodic_y = _keep_periodic_candidates(y_bands, pitch_y)
    candidate_x = [band for band in periodic_x if band in near_x] or periodic_x
    candidate_y = [band for band in periodic_y if band in near_y] or periodic_y
    # In this Gray wafer type the strong repeating vertical bands are die-center
    # noise, not the weak GV boundary.  Select the nearest repeated noise lane
    # only as a reference, then move half a pitch toward the wafer center to the
    # boundary between lanes.  This avoids placing x0 on the bright gray stripe.
    def gv_boundary_from_noise(noise_band: Tuple[float, int, int, float]) -> float:
        direction_to_center = -1.0 if noise_band[0] >= wafer_cx else 1.0
        return float(noise_band[0] + direction_to_center * pitch_x * 0.5)

    if mode == "center_scored":
        # This wafer type has a stable physical prior: the feature x coordinate
        # is essentially the wafer center.  Do not move it half a pitch onto an
        # inferred boundary when a bright vertical lane dominates the image.
        # Vertical lanes are retained only for pitch_x measurement.
        score_y = [band for band in periodic_y if abs(band[0] - wafer_cy) <= pitch_y * 2.2]
        score_y = score_y or candidate_y
        # The real Gray-wafer corner feature is consistently a little above the
        # wafer center.  Prefer that physical side even when a noisy lower row
        # lies one or two pixels closer; use lower rows only as a fallback.
        upper_score_y = [band for band in score_y if band[0] <= wafer_cy]
        score_y = upper_score_y or score_y
        # x stays at the measured wafer center; score only the allowed upper
        # horizontal rows by their distance from it.
        selected_y = min(score_y, key=lambda band: abs(band[0] - wafer_cy))
        return float(wafer_cx), float(selected_y[0])

    selected_noise_x = min(candidate_x, key=lambda band: abs(band[0] - wafer_cx))
    selected_x = gv_boundary_from_noise(selected_noise_x)

    # The horizontal directional mask identifies actual cross rows.  Unlike the
    # vertical die-center noise, y0 is the nearest horizontal row at/before the
    # wafer center and needs no half-pitch conversion.
    upper_y = [band for band in candidate_y if band[0] <= wafer_cy]
    selected_y = max(upper_y, key=lambda band: band[0]) if upper_y else min(
        candidate_y, key=lambda band: abs(band[0] - wafer_cy))
    return selected_x, float(selected_y[0])


def detect_thin_cross_grid(image: np.ndarray,
                           wafer_cx: int, wafer_cy: int, wafer_r: int,
                           roi_half: Optional[int] = None,
                           min_pitch: int = 30,
                           max_pitch: Optional[int] = 70,
                           thin_width_max: int = 5,
                           cross_origin_mode: str = "gv_boundary") -> Tuple[float, float, int, int]:
    """Detect a weak Gray grid from narrow vertical/horizontal cross ridges.

    A local high-pass image is opened separately in vertical and horizontal
    directions. Physical 1-2 px lines become up to 5 px after local contrast
    enhancement, so only bands up to ``thin_width_max`` are retained.  In the
    supplied Gray wafer type the repeated vertical bright bands are die-center
    noise: their period measures ``pitch_x``, while the weak GV boundary ``x0``
    is inferred half a pitch toward the wafer center.  ``pitch_y`` and ``y0``
    come from actual narrow horizontal cross rows.
    """
    # The weak-Gray cross mode is specialized for the requested 30-70px range.
    # Other grid methods keep their historical unbounded default when requested.
    if max_pitch is None:
        max_pitch = 70
    if max_pitch < min_pitch:
        raise ValueError("max_pitch must be greater than or equal to min_pitch")
    bgr = _as_bgr(image)
    height, width = bgr.shape[:2]
    if roi_half is None:
        roi_half = min(700, max(180, int(wafer_r * 0.30)))
    x0 = max(0, int(wafer_cx - roi_half))
    x1 = min(width, int(wafer_cx + roi_half))
    y0 = max(0, int(wafer_cy - roi_half))
    y1 = min(height, int(wafer_cy + roi_half))
    gray = _gray_u8(bgr[y0:y1, x0:x1])

    # CLAHE keeps low-amplitude 1-2 px grid ridges visible without a global brightness assumption.
    enhanced = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(32, 32)).apply(gray)
    local_base = cv2.GaussianBlur(enhanced, (0, 0), sigmaX=1.25)
    ridge = cv2.absdiff(enhanced, local_base)
    otsu_level, _ = cv2.threshold(ridge, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    ridge_threshold = max(2, int(round(otsu_level)), int(round(np.percentile(ridge, 82))))
    thin_mask = (ridge >= ridge_threshold).astype(np.uint8) * 255

    # Weak 3000px wafer streets can be interrupted by die texture; require only
    # a short directional run instead of half of the smallest expected pitch.
    line_length = max(7, int(round(min_pitch * 0.30)))
    vertical = cv2.morphologyEx(
        thin_mask, cv2.MORPH_OPEN,
        cv2.getStructuringElement(cv2.MORPH_RECT, (1, line_length)))
    horizontal = cv2.morphologyEx(
        thin_mask, cv2.MORPH_OPEN,
        cv2.getStructuringElement(cv2.MORPH_RECT, (line_length, 1)))
    x_profile = _smooth_projection(vertical.mean(axis=0), 3)
    # Use directional horizontal runs for y positions as well.  The raw ridge
    # projection also contains fine die texture (often 8-10px apart), which can
    # falsely become a horizontal cross even though it is not a grid street.
    y_profile = _smooth_projection(horizontal.mean(axis=1), 3)
    x_bands = _find_projection_bands(x_profile, x0, 1, 0.10, 0.35, 0.1)
    y_bands = _find_projection_bands(y_profile, y0, 1, 0.10, 0.35, 0.1)
    x_bands = [band for band in x_bands if band[2] - band[1] <= thin_width_max]
    # The 3px projection smoothing makes a physical 1-2px horizontal ridge appear up to 6px.
    y_bands = [band for band in y_bands if band[2] - band[1] <= thin_width_max + 2]
    if len(y_bands) < 2:
        # Keep a weak-signal fallback, but only when no directional horizontal
        # streets survived.  Normal cross detection must not use texture rows.
        y_profile = _smooth_projection(ridge.mean(axis=1), 3)
        y_bands = _find_projection_bands(y_profile, y0, 1, 0.10, 0.35, 0.1)
        y_bands = [band for band in y_bands if band[2] - band[1] <= thin_width_max + 2]
    x_bands = _discard_subpitch_bands(x_bands, min_pitch)
    sx = np.abs(cv2.Sobel(cv2.GaussianBlur(gray, (0, 0), 1.2), cv2.CV_32F, 1, 0, ksize=3))
    sy = np.abs(cv2.Sobel(cv2.GaussianBlur(gray, (0, 0), 1.2), cv2.CV_32F, 0, 1, ksize=3))
    rough_x = _safe_autocorr_period(sx.mean(axis=0), min_pitch, max_pitch, (min_pitch + (max_pitch or min_pitch)) / 2.0)
    rough_y = _safe_autocorr_period(sy.mean(axis=1), min_pitch, max_pitch, (min_pitch + (max_pitch or min_pitch)) / 2.0)
    pitch_x = (_median_band_spacing_bounded(x_bands, rough_x, min_pitch, max_pitch)
               if len(x_bands) >= 2 else float(rough_x))
    pitch_y = (_median_band_spacing_bounded(y_bands, rough_y, min_pitch, max_pitch)
               if len(y_bands) >= 2 else float(rough_y))
    mode = str(cross_origin_mode).lower().strip()
    if mode in ("center", "center_score", "center_scored", "score"):
        near_y = [band for band in y_bands if abs(band[0] - wafer_cy) <= pitch_y * 1.15]
        if len(y_bands) < 2 or not near_y:
            guide_y = _estimate_center_above_guide_y(
                horizontal.mean(axis=1), ridge.mean(axis=1), y0, wafer_cy, pitch_y)
            y_bands = [(guide_y, int(round(guide_y)), int(round(guide_y)) + 1, 0.0)]
    elif len(x_bands) < 2 or len(y_bands) < 2:
        raise RuntimeError(
            "Thin cross grid was not found. Check focus/contrast or increase thin_width_max only when real streets are wider.")
    cross_x, cross_y = _select_cross_origin(
        x_bands, y_bands, wafer_cx, wafer_cy, pitch_x, pitch_y,
        origin_mode=cross_origin_mode)
    return float(pitch_x), float(pitch_y), int(round(cross_x)), int(round(cross_y))


def detect_corner_grid(image_bgr: np.ndarray,
                       wafer_cx: int, wafer_cy: int, wafer_r: int,
                       roi_half: Optional[int] = None,
                       min_pitch: Optional[int] = None,
                       max_pitch: Optional[int] = None,
                       min_brightness: float = 115.0,
                       min_channel: int = 130,
                       min_color_delta: int = 35,
                       max_color_delta: int = 130,
                       open_length: int = 60,
                       smooth_window: int = 9,
                       min_width: int = 3,
                       threshold_ratio: float = 0.35,
                       sigma: float = 1.8,
                       min_projection: float = 5.0
                       ) -> Tuple[float, float, int, int]:
    """Noise wafer 의 실제 4-way 코너 교차점을 직접 찾는 Grid 검출.

    기존 `hybrid` 방식은 die 내부 stripe peak 에 실측 offset 을 더해 코너를
    계산한다. 이 함수는 코너를 이루는 밝은 wafer street 선 자체를 mask 로 잡고,
    wafer 중심 근처의 세로/가로 line band 교차점을 `grid_origin` 으로 반환한다.

    Returns
    -------
    (pitch_x, pitch_y, x0, y0)
        x0, y0 는 코너 한 점이며, overlay 의 박스는 이 점을 확인하는 시각화 용도다.
    """
    H, W = image_bgr.shape[:2]
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY).astype(np.float32)

    if min_pitch is None:
        min_pitch = _default_min_pitch(image_bgr)
    if roi_half is None:
        # ★[V5.4] 900 은 10000px 기준 손튜닝값. 해상도 비례로 환산하고, 최소한
        #   pitch 를 여러 주기 담도록 보장한다(autocorr 이 n >= 4*min_lag 를 요구).
        cap = _scaled(900, image_bgr, minimum=150)
        roi_half = int(min(cap, max(min(300, cap), int(wafer_r * 0.25))))
        roi_half = int(max(roi_half, min_pitch * 6))
    x1 = max(wafer_cx - roi_half, 0)
    x2 = min(wafer_cx + roi_half, W)
    y1 = max(wafer_cy - roi_half, 0)
    y2 = min(wafer_cy + roi_half, H)

    blurred_low = cv2.GaussianBlur(gray, (0, 0), sigmaX=3.0)
    sx_low = np.abs(cv2.Sobel(blurred_low, cv2.CV_32F, 1, 0, ksize=3))
    sy_low = np.abs(cv2.Sobel(blurred_low, cv2.CV_32F, 0, 1, ksize=3))
    pitch_x_rough = float(_autocorr_period(sx_low[y1:y2, x1:x2].mean(axis=0),
                                           min_lag=min_pitch, max_lag=max_pitch))
    pitch_y_rough = float(_autocorr_period(sy_low[y1:y2, x1:x2].mean(axis=1),
                                           min_lag=min_pitch, max_lag=max_pitch))

    street_mask = _street_color_mask(
        image_bgr, x1, x2, y1, y2,
        min_brightness=min_brightness,
        min_channel=min_channel,
        min_color_delta=min_color_delta,
        max_color_delta=max_color_delta)

    open_length = max(15, int(open_length))
    vertical_mask = cv2.morphologyEx(
        street_mask,
        cv2.MORPH_OPEN,
        cv2.getStructuringElement(cv2.MORPH_RECT, (1, open_length)),
    )
    horizontal_mask = cv2.morphologyEx(
        street_mask,
        cv2.MORPH_OPEN,
        cv2.getStructuringElement(cv2.MORPH_RECT, (open_length, 1)),
    )

    x_profile = _smooth_projection(vertical_mask.mean(axis=0), smooth_window)
    y_profile = _smooth_projection(horizontal_mask.mean(axis=1), smooth_window)
    x_bands = _find_projection_bands(
        x_profile, x1, min_width, threshold_ratio, sigma, min_projection)
    y_bands = _find_projection_bands(
        y_profile, y1, min_width, threshold_ratio, sigma, min_projection)

    # ★ V5.3 : street 가 여러 색 sub-line 으로 쪼개져 잡히면 pitch/origin 이 모두
    #   sub-line 단위로 어긋난다. 같은 street 끼리 먼저 묶어서 쓴다.
    x_groups = _merge_close_bands(x_bands, pitch_x_rough * _BAND_MERGE_RATIO)
    y_groups = _merge_close_bands(y_bands, pitch_y_rough * _BAND_MERGE_RATIO)

    # x 축은 wafer 원 검출 중심이 1 px 정도 흔들릴 수 있어 가장 가까운 세로선을 선택한다.
    # y 축은 중심 바로 위의 가로 street 가 grid origin 이므로 previous band 를 선택한다.
    x_band = _choose_nearest_band(x_groups, float(wafer_cx))
    y_band = _choose_previous_band(y_groups, float(wafer_cy))
    pitch_x = _resolve_pitch(x_bands, pitch_x_rough, min_pitch, max_pitch)
    pitch_y = _resolve_pitch(y_bands, pitch_y_rough, min_pitch, max_pitch)
    return pitch_x, pitch_y, int(round(x_band[0])), int(round(y_band[0]))


# ---------------------------------------------------------------------------
# ★[V5.4] 십자(cross) 교차점 기반 grid 검출
#
#   요구: die 경계는 폭 1~2 px 의 얇은 십자(十)다. 반면 방해가 되는 세로 노이즈는
#   '넓다'. 그래서 '얇다' 는 것 자체를 검출 조건으로 삼으면 노이즈가 배제된다.
#
#   원리 — 폭 선택적 능선(ridge) 필터
#     선 방향으로는 길게 평균내서 SNR 을 올리고(약신호 대응),
#     선에 수직한 방향으로는 ±d 만큼 떨어진 양쪽 배경과 비교한다.
#
#        얇은 선 (폭 <= d)          넓은 노이즈 (폭 >> d)
#        bg  |‖|  bg               |███████████|
#        ↑    ↑    ↑                ↑    ↑     ↑
#       x-d   x   x+d              x-d   x    x+d
#        낮   높   낮                높   높    높
#        resp = 높 - max(낮,낮) > 0   resp = 높 - max(높,높) ~ 0
#
#   양쪽 배경 중 '더 밝은 쪽' 과 비교(max)하므로, 한쪽이라도 구조물에 걸치면
#   응답이 죽는다. 폭이 2d 이상인 것은 원리적으로 통과하지 못한다.
#
#   그리고 가로/세로 능선이 '동시에' 강한 곳만 십자로 인정한다(min 결합).
#   세로 노이즈는 가로 능선이 없으므로 여기서 한 번 더 걸러진다.
#
#   pitch 는 사용자 요구대로 십자 점의 최근접 이웃 간격에서 뽑는다.
#   좌우 이웃 간격 -> pitch_x, 위아래 이웃 간격 -> pitch_y.
# ---------------------------------------------------------------------------
DEFAULT_CROSS_LINE_W = 2        # 십자 선 두께 상한(px). 이보다 넓으면 노이즈로 본다
DEFAULT_CROSS_MIN_PITCH = 30    # 실측 die pitch 하한
DEFAULT_CROSS_MAX_PITCH = 70    # 실측 die pitch 상한
_CROSS_SIGMA_K = 2.5            # 능선 응답 임계 (robust sigma 배수)
_CROSS_SMOOTH_RATIO = 0.6       # 선 방향 평균 길이 = pitch 하한 * 이 비율
_CROSS_ROW_TOL_RATIO = 0.25     # 같은 행/열로 묶을 수직방향 허용오차 (pitch 대비)
_CROSS_MIN_POINTS = 8           # 이보다 적게 잡히면 십자 검출 실패로 본다
DEFAULT_ORIGIN_MODE = "center"  # ★[V5.5] origin 선택: "center"(중심 가중) | "nearest"
_ORIGIN_CENTER_SIGMA = 6.0      # 중심 가중 가우시안 폭 (pitch 배수)
# ★[claude] 코너(원점) 검출을 gray 쪽 detect_thin_cross_grid 로 돌린다.
DEFAULT_CROSS_ORIGIN_MODE = "gv_boundary"   # "gv_boundary" | "center_scored"
DEFAULT_THIN_WIDTH_MAX = 5                  # thin band 폭 상한(px)
DEFAULT_THIN_ROI_HALF: Optional[int] = None # None 이면 wafer_r*0.30 (180~700 clamp)


def _shift_pair(a: np.ndarray, d: int, axis: int) -> Tuple[np.ndarray, np.ndarray]:
    """a 에서 axis 방향으로 -d / +d 만큼 떨어진 두 배경면을 반환(가장자리 복제)."""
    if axis == 1:      # 좌/우
        pad = cv2.copyMakeBorder(a, 0, 0, d, d, cv2.BORDER_REPLICATE)
        w = a.shape[1]
        return pad[:, 0:w], pad[:, 2 * d:2 * d + w]
    pad = cv2.copyMakeBorder(a, d, d, 0, 0, cv2.BORDER_REPLICATE)
    h = a.shape[0]
    return pad[0:h, :], pad[2 * d:2 * d + h, :]


_ROBUST_SAMPLE_MAX = 1 << 22        # 4M 개까지는 그냥 전부 쓴다


def _robust_scale(a: np.ndarray) -> float:
    """MAD 기반 산포. 약신호에서도 임계를 신호세기에 비례시키기 위한 정규화 인자.

    ★[V5.4] 표본을 **규칙적 격자로 뽑으면 안 된다**. 대상이 주기 pitch 인 격자
    영상이라 stride 가 pitch 의 약수에 걸리면 표본이 전부 같은 위상에 꽂힌다
    (에일리어싱). 실측: pitch 45 인 영상에서 ROI 가 1410 이면 stride=5, 45/5=9 로
    정확히 공진해 MAD 가 2.02 배 부풀고, 정규화된 응답이 5.05 -> 2.50 으로 내려가
    임계 2.5 를 못 넘어 십자점이 **0 개**가 됐다. ROI 가 1680 이면 stride=6,
    45/6=7.5 라 공진하지 않아 멀쩡했다 —— 즉 ROI 크기에 따라 성패가 튀었다.
    전체 배열을 쓰거나(기본), 너무 크면 **난수** 표본을 쓴다. 난수는 어떤 주기와도
    공진하지 않고, seed 고정이라 결과는 결정적이다.
    """
    flat = np.ascontiguousarray(a, dtype=np.float32).reshape(-1)
    if flat.size > _ROBUST_SAMPLE_MAX:
        idx = np.random.default_rng(0).integers(0, flat.size, _ROBUST_SAMPLE_MAX)
        flat = flat[idx]
    med = float(np.median(flat))
    mad = float(np.median(np.abs(flat - med)))
    return max(1.4826 * mad, 1e-3)


def _thin_ridge(gray: np.ndarray, vertical: bool, line_w: int,
                smooth_len: int, dark: bool) -> np.ndarray:
    """폭이 line_w px 이하인 '얇은 선' 만 남기는 정규화 능선 응답.

    vertical=True 면 세로선(=x 방향으로 얇다)을 찾는다.
    dark=True 면 주변보다 어두운 선을 찾는다(극성 반전).
    반환값은 robust sigma 단위라 신호 세기와 무관하게 임계를 걸 수 있다.
    """
    d = int(max(1, line_w)) + 1          # 배경을 재는 거리 = 선 두께 + 1
    if vertical:
        sm = cv2.blur(gray, (1, max(1, smooth_len)))     # y 방향 평균 (선을 따라)
        lo_side, hi_side = _shift_pair(sm, d, axis=1)
    else:
        sm = cv2.blur(gray, (max(1, smooth_len), 1))     # x 방향 평균
        lo_side, hi_side = _shift_pair(sm, d, axis=0)

    if dark:
        resp = np.minimum(lo_side, hi_side) - sm
    else:
        resp = sm - np.maximum(lo_side, hi_side)
    return resp / _robust_scale(resp)


def _cross_points(vresp: np.ndarray, hresp: np.ndarray,
                  min_pitch: int, sigma_k: float) -> Tuple[np.ndarray, np.ndarray]:
    """세로·가로 능선이 동시에 강한 지점을 십자 점으로 추출. -> (pts Nx2, cross map)."""
    cross = np.minimum(vresp, hresp)
    nms = int(max(3, round(min_pitch * 0.5)))
    if nms % 2 == 0:
        nms += 1
    peak = cv2.dilate(cross, cv2.getStructuringElement(cv2.MORPH_RECT, (nms, nms)))
    hit = (cross >= peak - 1e-6) & (cross > float(sigma_k))
    ys, xs = np.nonzero(hit)
    return np.stack([xs, ys], axis=1).astype(np.float64), cross


def _nn_pitch(pts: np.ndarray, along_x: bool,
              lo: float, hi: float, tol: float) -> Optional[float]:
    """십자 점의 최근접 이웃 간격 median. along_x=True 면 좌우 이웃(-> pitch_x).

    '같은 행(열)' 판정은 수직 방향 차이가 tol 이내인 것으로 한다. 각 점마다
    같은 방향 최근접 1개만 채택해 2·3배 간격이 섞이는 것을 막는다.
    """
    if pts.shape[0] < 2:
        return None
    main = pts[:, 0] if along_x else pts[:, 1]      # 간격을 잴 축
    perp = pts[:, 1] if along_x else pts[:, 0]      # 같은 행/열 판정 축

    order = np.argsort(main)
    main, perp = main[order], perp[order]

    gaps: List[float] = []
    n = main.size
    for i in range(n):
        same = np.abs(perp[i + 1:] - perp[i]) <= tol
        if not same.any():
            continue
        dm = main[i + 1:][same] - main[i]
        dm = dm[(dm >= lo) & (dm <= hi)]
        if dm.size:
            gaps.append(float(dm.min()))
    if len(gaps) < 3:
        return None
    return float(np.median(gaps))


def detect_cross_grid(image_bgr: np.ndarray,
                      wafer_cx: int, wafer_cy: int, wafer_r: int,
                      *,
                      min_pitch: int = DEFAULT_CROSS_MIN_PITCH,
                      max_pitch: int = DEFAULT_CROSS_MAX_PITCH,
                      line_w: int = DEFAULT_CROSS_LINE_W,
                      sigma_k: float = _CROSS_SIGMA_K,
                      polarity: str = "auto",
                      origin_mode: str = DEFAULT_ORIGIN_MODE,
                      return_info: bool = False):
    """얇은 십자 교차점으로 die 격자를 찾는다. -> (pitch_x, pitch_y, x0, y0).

    1채널·약신호·세로 노이즈가 있는 wafer 를 위한 검출기. street 색(채도)에
    의존하지 않으므로 grayscale 에서도 그대로 동작한다.

    Parameters
    ----------
    min_pitch/max_pitch : die pitch 탐색 범위(px). 실측 30~70 이 기본.
    line_w   : 십자 선 두께 상한(px). 넓은 세로 노이즈를 배제하는 핵심 파라미터.
    sigma_k  : 능선 응답 임계(robust sigma 배수). 낮추면 약신호에 민감해진다.
    polarity : "auto" | "bright" | "dark". 십자가 주변보다 밝은지 어두운지.
    origin_mode : ★[V5.5] "center"(기본) 는 중심 근접 가중 위상으로 원점을 잡아
        약신호에서 가짜 십자에 끌려가지 않는다. "nearest" 는 V5.4 까지의 동작
        (거리만 보고 제일 가까운 점 채택).
    """
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY).astype(np.float32)
    H, W = gray.shape[:2]

    # ROI : 격자 주기를 충분히 담되(최소 12 주기) wafer 안쪽으로 제한
    half = int(min(max(max_pitch * 12, min_pitch * 12), max(wafer_r * 0.5, max_pitch * 6)))
    x1, x2 = max(int(wafer_cx) - half, 0), min(int(wafer_cx) + half, W)
    y1, y2 = max(int(wafer_cy) - half, 0), min(int(wafer_cy) + half, H)
    roi = gray[y1:y2, x1:x2]
    if roi.size == 0:
        raise RuntimeError("cross grid: ROI is empty.")

    smooth_len = int(max(3, round(min_pitch * _CROSS_SMOOTH_RATIO)))
    tol = float(max(2.0, min_pitch * _CROSS_ROW_TOL_RATIO))

    modes = [False, True] if polarity == "auto" else [polarity.lower() == "dark"]
    best: Optional[Dict[str, Any]] = None
    for dark in modes:
        vresp = _thin_ridge(roi, True, line_w, smooth_len, dark)
        hresp = _thin_ridge(roi, False, line_w, smooth_len, dark)
        pts, cross = _cross_points(vresp, hresp, min_pitch, sigma_k)
        if pts.shape[0] < _CROSS_MIN_POINTS:
            continue
        px = _nn_pitch(pts, True, min_pitch, max_pitch, tol)
        py = _nn_pitch(pts, False, min_pitch, max_pitch, tol)
        if px is None or py is None:
            continue
        # ★[V5.4] 채점 **전에** 서브픽셀 정제한다. 정수 pitch 로 채점하면 참 pitch 가
        #   정수에서 멀수록(0.5px) 맞는 후보가 오히려 낮은 점수를 받아 극성 선택이
        #   뒤집힌다. 정제 후 채점해야 후보끼리 공정하게 비교된다.
        px = _refine_pitch(pts[:, 0], px)
        py = _refine_pitch(pts[:, 1], py)
        # 채점: 십자 점이 실제로 그 주기의 격자 위에 있는 비율
        score = _cross_score(pts, px, py, tol) * math.log1p(pts.shape[0])
        cand = {"dark": dark, "pts": pts, "cross": cross,
                "pitch_x": px, "pitch_y": py, "score": score}
        if best is None or cand["score"] > best["score"]:
            best = cand

    if best is None:
        raise RuntimeError(
            "cross grid: 십자 교차점을 찾지 못했습니다 "
            f"(min_pitch={min_pitch}, max_pitch={max_pitch}, line_w={line_w}, "
            f"sigma_k={sigma_k}). line_w 를 늘리거나 sigma_k 를 낮춰보세요.")

    pts = best["pts"]
    cxr, cyr = float(wafer_cx - x1), float(wafer_cy - y1)
    ox, oy, org = _pick_origin(pts, best["cross"], cxr, cyr,
                               best["pitch_x"], best["pitch_y"], origin_mode)
    x0, y0 = ox + x1, oy + y1

    if return_info:
        return (float(best["pitch_x"]), float(best["pitch_y"]), x0, y0,
                {"polarity": "dark" if best["dark"] else "bright",
                 "n_points": int(pts.shape[0]),
                 "score": float(best["score"]),
                 "roi": (x1, y1, x2, y2),
                 "origin_mode": origin_mode,
                 "origin": org})
    return float(best["pitch_x"]), float(best["pitch_y"]), x0, y0


def _pick_origin(pts: np.ndarray, cross: np.ndarray, cxr: float, cyr: float,
                 pitch_x: float, pitch_y: float,
                 mode: str = DEFAULT_ORIGIN_MODE
                 ) -> Tuple[float, float, Dict[str, Any]]:
    """격자 원점(십자 하나)을 고른다. -> (x, y, 진단정보). ROI 좌표계.

    ★[V5.5] mode="nearest" 는 **거리만** 본다(V5.4 까지의 동작). 약신호·노이즈
    영상에서 중심 근처에 가짜 십자가 하나라도 뜨면 품질과 무관하게 그게 이기고,
    그 점이 격자에서 벗어나 있으면 **위상이 통째로 최대 half-pitch 어긋난다**.
    origin 은 die 격자의 앵커라 이 오차가 wafer 전체 die 로 그대로 번진다.

    mode="center" 는 두 단계로 나눈다.
      1) **위상**은 전체 점의 '중심 근접 가중' 원형평균으로 구한다. 수백 점의
         가중평균이라 가짜 점 몇 개로는 흔들리지 않는다. 중심에 가까운 십자일수록
         큰 가중을 받으므로(가우시안, 폭 = pitch x 6) 중심부 격자에 정확히 맞는다.
      2) 그 위상이 만드는 격자 노드 중 **wafer 중심에 가장 가까운 노드**를 앵커로
         쓴다. die (0,0) 이 중심 die 가 되는 성질은 그대로 유지된다.
    노드 자리에 실제 십자 응답이 있으면 서브픽셀로 다듬되, 이동량은 tol 로 묶어
    응답이 약할 때 끌려가지 않게 한다.
    """
    d2 = (pts[:, 0] - cxr) ** 2 + (pts[:, 1] - cyr) ** 2
    win = int(max(2, round(pitch_x * 0.15)))

    if mode == "nearest":
        k = int(np.argmin(d2))
        sx, sy = float(pts[k, 0]), float(pts[k, 1])
        ox, oy = _cross_subpixel(cross, sx, sy, win)
        return ox, oy, {"mode": "nearest", "seed": (sx, sy),
                        "seed_dist": float(math.sqrt(d2[k]))}
    if mode != "center":
        raise ValueError(f"origin_mode must be 'center' or 'nearest', got {mode!r}")

    sigma = max(pitch_x, pitch_y) * _ORIGIN_CENTER_SIGMA
    w = np.exp(-d2 / (2.0 * sigma * sigma))
    if float(w.sum()) <= 1e-9:          # 전부 너무 멀면 가중을 포기하고 균등
        w = np.ones_like(w)

    # 중심 가중 원형평균 -> 격자 위상 -> 중심에 제일 가까운 노드
    node = []
    for coord, pitch in ((pts[:, 0], pitch_x), (pts[:, 1], pitch_y)):
        ang = (2.0 * np.pi / pitch) * coord
        ph = math.atan2(float((w * np.sin(ang)).sum()),
                        float((w * np.cos(ang)).sum())) / (2.0 * np.pi) * pitch
        node.append(ph)
    nx = node[0] + round((cxr - node[0]) / pitch_x) * pitch_x
    ny = node[1] + round((cyr - node[1]) / pitch_y) * pitch_y

    # 노드 자리를 서브픽셀로 다듬되, 응답이 약해 끌려가는 것을 tol 로 막는다
    ox, oy = _cross_subpixel(cross, nx, ny, win)
    lim = float(win)
    ox = float(np.clip(ox, nx - lim, nx + lim))
    oy = float(np.clip(oy, ny - lim, ny + lim))

    k = int(np.argmin(d2))
    return ox, oy, {"mode": "center", "node": (nx, ny),
                    "shift": (ox - nx, oy - ny),
                    "nearest_pt": (float(pts[k, 0]), float(pts[k, 1])),
                    "nearest_dist": float(math.sqrt(d2[k])),
                    "eff_n": float(w.sum())}


_PITCH_REFINE_SPAN = 0.08        # 씨앗 pitch 대비 탐색 반경(±8%)


def _refine_pitch(coord: np.ndarray, seed: float,
                  span_ratio: float = _PITCH_REFINE_SPAN) -> float:
    """정수 씨앗 pitch 를 '위상 집중도 최대' 지점으로 서브픽셀 정제한다.

    ★[V5.4] _nn_pitch 는 정수 픽셀 좌표의 차를 median 한 값이라 **항상 정수**다.
    참 pitch 가 49.497 이어도 표현할 방법이 없어 49 나 51 이 나온다. 그러면 ROI 를
    가로지르는 동안 위상이 통째로 밀려(30 주기 x 0.5px = 15px) 격자가 안 맞고,
    _cross_score 의 집중도가 **맞는 후보에서 오히려 무너진다**.
    실측(scale 0.33): 정수 51(참값 49.497) 이라 dark 후보 점수가 0.338 로 깔려
    bright(43, 완전 오답) 에게 극성 선택을 빼앗겼다. 같은 후보를 49.502 로 정제하면
    점수가 3.000 이 되어 정상적으로 선택된다.

    씨앗 ±8% 만 훑으므로 2배/절반 하모닉으로 샐 수 없다(하모닉은 ±100%/-50%).
    """
    c = np.ascontiguousarray(coord, dtype=np.float64).reshape(-1)
    if c.size < 4 or seed <= 1.0:
        return float(seed)
    best = float(seed)
    span = float(seed) * float(span_ratio)
    step = span / 40.0
    for _ in range(2):
        grid = np.arange(best - span, best + span + 1e-12, step)
        grid = grid[grid > 1.0]
        if grid.size == 0:
            break
        # (N,1)/(1,M) 브로드캐스트로 모든 후보 pitch 의 집중도를 한 번에 계산
        ang = (2.0 * np.pi) * (c[:, None] / grid[None, :])
        conc = np.abs(np.cos(ang).mean(axis=0) + 1j * np.sin(ang).mean(axis=0))
        best = float(grid[int(np.argmax(conc))])
        span, step = step * 2.0, step / 20.0
    return best


def _cross_score(pts: np.ndarray, pitch_x: float, pitch_y: float,
                 tol: float) -> float:
    """십자 점들이 (pitch_x, pitch_y) 격자에 맞는 비율. 극성/후보 선택용 점수."""
    if pitch_x <= 0 or pitch_y <= 0:
        return 0.0
    rx = np.mod(pts[:, 0], pitch_x) / pitch_x
    ry = np.mod(pts[:, 1], pitch_y) / pitch_y
    # 위상 원형평균에서의 집중도(0~1). 격자에 잘 맞을수록 1 에 가깝다.
    cx = abs(complex(float(np.cos(2 * np.pi * rx).mean()),
                     float(np.sin(2 * np.pi * rx).mean())))
    cy = abs(complex(float(np.cos(2 * np.pi * ry).mean()),
                     float(np.sin(2 * np.pi * ry).mean())))
    return float(cx * cy)


def _cross_subpixel(cross: np.ndarray, x: float, y: float, win: int) -> Tuple[float, float]:
    """십자 응답의 무게중심으로 교차점을 서브픽셀 보정."""
    h, w = cross.shape[:2]
    xi, yi = int(round(x)), int(round(y))
    x1, x2 = max(xi - win, 0), min(xi + win + 1, w)
    y1, y2 = max(yi - win, 0), min(yi + win + 1, h)
    patch = cross[y1:y2, x1:x2].astype(np.float64)
    patch = np.maximum(patch - patch.min(), 0.0)
    total = patch.sum()
    if total <= 1e-9:
        return float(x), float(y)
    gx = float((patch.sum(axis=0) * np.arange(x1, x2)).sum() / total)
    gy = float((patch.sum(axis=1) * np.arange(y1, y2)).sum() / total)
    return gx, gy


def _default_min_pitch(image_bgr: np.ndarray) -> int:
    """★[V5.4] min_pitch 기본값을 영상 성격으로 정한다.

    10000px 3채널 wafer 는 기존대로 50(=튜닝된 값)을 유지해 무회귀를 보장하고,
    1채널이거나 작은 영상은 실측 pitch 하한 30 까지 열어준다.
    """
    if _is_mono(image_bgr) or min(image_bgr.shape[:2]) < _REF_DIM * 0.6:
        return DEFAULT_CROSS_MIN_PITCH
    return 50


def detect_grid(image_bgr: np.ndarray,
                wafer_cx: int, wafer_cy: int, wafer_r: int,
                method: str = "auto",
                roi_ratio: float = 0.6,
                min_pitch: Optional[int] = None,
                max_pitch: Optional[int] = None,
                die_template_bgr: Optional[np.ndarray] = None,
                line_hue: Optional[int] = None,
                hue_delta: int = 20,
                sat_min: int = 50,
                val_min: int = 50,
                cross_line_w: int = DEFAULT_CROSS_LINE_W,
                cross_sigma_k: float = _CROSS_SIGMA_K,
                origin_mode: str = DEFAULT_ORIGIN_MODE,
                cross_origin_mode: str = DEFAULT_CROSS_ORIGIN_MODE,
                thin_width_max: int = DEFAULT_THIN_WIDTH_MAX,
                thin_roi_half: Optional[int] = DEFAULT_THIN_ROI_HALF
                ) -> Tuple[float, float, int, int]:
    """Die 격자 (pitch + origin) 자동 검출. -> (pitch_x, pitch_y, x0, y0).

    method: "auto"(기본) | "cross" | "corner" | "std" | "color" | "hybrid"

    ★[V5.4] "auto" 는 영상 성격에 따라 순서를 정하고 서로 fallback 한다.
      · 1채널/약신호  -> cross(십자) 먼저, 실패하면 corner
      · 기존 컬러영상 -> corner 먼저, 실패하면 cross
    즉 기존 10000x10000 3채널 경로는 종전과 동일하게 corner 로 풀리고,
    corner 가 죽던 상황에서만 cross 가 받아준다(무회귀 + 복구).
    """
    if min_pitch is None:
        min_pitch = _default_min_pitch(image_bgr)
    if max_pitch is None and (_is_mono(image_bgr)
                              or min(image_bgr.shape[:2]) < _REF_DIM * 0.6):
        max_pitch = DEFAULT_CROSS_MAX_PITCH

    def _try_cross() -> Tuple[float, float, int, int]:
        return detect_cross_grid(
            image_bgr, wafer_cx, wafer_cy, wafer_r,
            min_pitch=min_pitch,
            max_pitch=max_pitch or DEFAULT_CROSS_MAX_PITCH,
            line_w=cross_line_w, sigma_k=cross_sigma_k,
            origin_mode=origin_mode)

    def _try_corner() -> Tuple[float, float, int, int]:
        return detect_corner_grid(
            image_bgr, wafer_cx, wafer_cy, wafer_r,
            min_pitch=min_pitch, max_pitch=max_pitch)

    # ★[claude] gray 쪽에서 이식한 코너(원점) 검출.
    def _try_thin_cross() -> Tuple[float, float, int, int]:
        return detect_thin_cross_grid(
            image_bgr, wafer_cx, wafer_cy, wafer_r,
            roi_half=thin_roi_half,
            min_pitch=min_pitch,
            max_pitch=max_pitch or DEFAULT_CROSS_MAX_PITCH,
            thin_width_max=thin_width_max,
            cross_origin_mode=cross_origin_mode)

    if method in ("thin_cross", "gray_cross", "gray"):
        return _try_thin_cross()

    # ★[V5.4] 십자(十) 교차점 전용 검출. 폭 1~2px 제약으로 넓은 세로 노이즈를 배제한다.
    if method in ("cross", "cross_grid"):
        return _try_cross()

    if method in ("auto", "corner", "corner_grid", "street"):
        # ★[claude] auto 도 gray 코너 로직을 먼저 태운다.
        order = ([_try_thin_cross, _try_cross, _try_corner]
                 if (method == "auto" and _is_mono(image_bgr))
                 else [_try_corner, _try_thin_cross, _try_cross])
        if method != "auto":
            order = [_try_corner]          # 명시적으로 corner 를 고른 경우는 fallback 없음
        first_err: Optional[Exception] = None
        for fn in order:
            try:
                return fn()
            except Exception as exc:       # noqa: BLE001 - 다음 방식으로 넘어가기 위함
                if first_err is None:
                    first_err = exc
        raise RuntimeError(
            f"grid detection failed (method={method}, min_pitch={min_pitch}, "
            f"max_pitch={max_pitch}): {first_err}") from first_err

    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY).astype(np.float32)

    half = int(wafer_r * roi_ratio)
    x1 = max(wafer_cx - half, 0)
    x2 = min(wafer_cx + half, image_bgr.shape[1])
    y1 = max(wafer_cy - half, 0)
    y2 = min(wafer_cy + half, image_bgr.shape[0])

    blurred_low = cv2.GaussianBlur(gray, (0, 0), sigmaX=3.0)
    sx_low = np.abs(cv2.Sobel(blurred_low, cv2.CV_32F, 1, 0, ksize=3))
    sy_low = np.abs(cv2.Sobel(blurred_low, cv2.CV_32F, 0, 1, ksize=3))
    pitch_x_rough = _autocorr_period(sx_low[y1:y2, x1:x2].mean(axis=0),
                                     min_lag=min_pitch, max_lag=max_pitch)
    pitch_y_rough = _autocorr_period(sy_low[y1:y2, x1:x2].mean(axis=1),
                                     min_lag=min_pitch, max_lag=max_pitch)

    col_std, row_std = _grid_profiles_std(gray[y1:y2, x1:x2])
    col_sat, row_sat = _grid_profiles_color(
        image_bgr, gray, x1, x2, y1, y2,
        wafer_cx, wafer_cy, wafer_r,
        line_hue, hue_delta, sat_min, val_min)

    if method == "std":
        col_profile, row_profile = col_std, row_std
        off_x, off_y = 0.0, 0.0
    elif method == "color":
        col_profile, row_profile = col_sat, row_sat
        off_x, off_y = 0.5, 0.5
    elif method == "hybrid":
        col_profile, row_profile = col_sat, row_sat
        off_x, off_y = 0.63, 0.493
    else:
        raise ValueError(
            f"Unknown method: {method!r} (use 'corner' | 'std' | 'color' | 'hybrid')")

    x_peaks = _find_periodic_peaks(col_profile, pitch_x_rough)
    y_peaks = _find_periodic_peaks(row_profile, pitch_y_rough)
    pitch_x = float(pitch_x_rough)
    pitch_y = float(pitch_y_rough)
    phase_x = _robust_phase(x_peaks, pitch_x, col_profile)
    phase_y = _robust_phase(y_peaks, pitch_y, row_profile)

    phase_x += off_x * pitch_x
    phase_y += off_y * pitch_y

    bias_x = pitch_x * 0.05
    bias_y = pitch_y * 0.05
    kx = int(math.floor((wafer_cx - x1 - phase_x - bias_x) / pitch_x + 0.5))
    ky = int(math.floor((wafer_cy - y1 - phase_y - bias_y) / pitch_y + 0.5))
    x0 = int(round(x1 + phase_x + kx * pitch_x))
    y0 = int(round(y1 + phase_y + ky * pitch_y))

    if die_template_bgr is not None:
        pitch_x, pitch_y, x0, y0, _ = _refine_origin_with_template(
            image_bgr, die_template_bgr, pitch_x, pitch_y,
            x0, y0, wafer_cx, wafer_cy, wafer_r)

    return float(pitch_x), float(pitch_y), x0, y0


# =============================================================================
# [SECTOR: 30_DIE_MAP_GEOMETRY] die crop, map 자료구조, edge/좌표 기하
# 3) Die clip (한 die crop)
# =============================================================================
def clip_die(image: np.ndarray, center_x: float, center_y: float,
             die_w: float, die_h: float,
             border_mode: str = "pad") -> Optional[np.ndarray]:
    """(center_x, center_y) 기준 die_w x die_h die crop 반환 (pad / crop).

    ★ die_w/die_h/center 는 float(서브픽셀) 로 들어올 수 있다(pitch 가 float 이므로).
      좌/우 를 같은 float 중심에서 각각 반올림해 **대칭** 으로 자른다
      (예전 `center - die_w//2` 는 홀수 폭에서 왼쪽으로 1px 치우쳤다).
    """
    H, W = image.shape[:2]
    die_w = int(round(float(die_w)))
    die_h = int(round(float(die_h)))
    x1 = int(round(float(center_x) - die_w / 2.0))
    y1 = int(round(float(center_y) - die_h / 2.0))
    x2 = x1 + die_w
    y2 = y1 + die_h

    if x2 <= 0 or y2 <= 0 or x1 >= W or y1 >= H:
        return None

    ix1, iy1 = max(x1, 0), max(y1, 0)
    ix2, iy2 = min(x2, W), min(y2, H)
    crop = image[iy1:iy2, ix1:ix2]
    if crop.size == 0:
        return None

    if border_mode == "crop":
        return crop.copy()

    if border_mode == "pad":
        if image.ndim == 3:
            canvas = np.zeros((die_h, die_w, image.shape[2]), dtype=image.dtype)
        else:
            canvas = np.zeros((die_h, die_w), dtype=image.dtype)
        ox, oy = ix1 - x1, iy1 - y1
        canvas[oy:oy + (iy2 - iy1), ox:ox + (ix2 - ix1)] = crop
        return canvas

    raise ValueError(f"Unknown border_mode: {border_mode!r}")


# #############################################################################
# #                                                                           #
# #   PUBLIC API  (요청한 2개 함수 + 재사용 데이터 구조)                       #
# #                                                                           #
# #############################################################################

# --- 사용자 조정 기본값 -----------------------------------------------------
DEFAULT_GRID_METHOD = "thin_cross"     # ★[V5.4] "auto"(권장, mono면 cross 우선/아니면 corner 우선
                                 #   + 서로 fallback) | "cross" | "corner" | "hybrid" | "std" | "color"
DEFAULT_PIXEL_PER_UNIT = 32      # 실측 좌표 환산 (px / unit)
DEFAULT_EDGE_MARGIN = 1.0        # die 포함 기준: 중심거리 <= r * 이값.
                                 #   1.0=원 안의 die 전부(EDGE 포함), 0.98=가장자리 제외

# --- EDGE die 판정 방식 (둘 다 계산되어 entry 에 저장; is_edge 가 무엇을 가리킬지 선택) ---
#   "circle" : is_edge = is_edge_partial (die 사각형이 wafer 원 밖으로 일부라도 나감)
#   "ring"   : is_edge = is_edge_ring    (die 격자에서 8방향 이웃이 다 차 있지 않은 최외곽)
#   "both"   : is_edge = is_edge_partial OR is_edge_ring
DEFAULT_EDGE_MODE = "circle"

# --- ★ EDGE die 전부 clip (중심 기준 -> 사각형 겹침 기준) ---------------------
#   기존에는 'die 중심이 wafer 원 안'일 때만 die 를 만들었다. 그래서 중심은 원 밖이지만
#   사각형 일부가 원 안에 걸친 최외곽 EDGE die 가 통째로 빠졌다(실제 이미지엔 보임).
#   True 면 'die 사각형이 wafer 원과 겹치기만 하면' 전부 die 로 만들어 clip 한다.
DEFAULT_EDGE_CLIP_ALL = True
#   포함에 필요한 최소 겹침 깊이(px). rect 가 원 안쪽으로 이만큼은 들어와야 포함.
#     0.0 = 1px 라도 겹치면 전부 포함(기본)
#     양수 = 경계를 살짝만 스치는 '거의 빈' die 를 제외 (예: 20 -> 20px 이상 걸친 것만)
DEFAULT_EDGE_OVERLAP_MIN_PX = 0.0

# --- ★ grid origin 서브픽셀 보정 (street 십자 교차점의 '진짜' 중심) ----------------
#   detect_corner_grid 는 street band 의 '밝기 무게중심' 을 origin 으로 잡는다.
#   무게중심은 좌/우(상/하) die 밝기가 다르면 밝은 쪽으로 끌려가 origin 이 쉬프트된다
#   (= 사용자가 그린 '검은 점'). 여기서는 주기 폴딩(phase folding) 으로 한 주기 평균
#   단면을 만든 뒤 street 양쪽 **half-max 교차점의 중점** 을 중심으로 삼아 편향을 없앤다.
# ★[claude] '재앵커링만 유지' — refine_grid_origin 은 origin 을 또 옮겨서
#   gray 코너 로직이 고른 원점을 흔든다. 기본 OFF (필요하면 True 로 켤 것).
DEFAULT_REFINE_ORIGIN = False
#   폴딩에 쓰는 중앙 ROI 크기(= 몇 주기를 평균할지). 클수록 노이즈에 강하지만
#   pitch 추정 오차가 누적되므로 10~16 주기 정도가 적당하다.
DEFAULT_REFINE_ROI_PERIODS = 12
#   보정 허용 한계 = pitch * 이 값. 이보다 크게 움직이려 하면 '옆 street 를 잘못 잡은 것'
#   으로 보고 보정을 포기한다(=die 인덱스가 통째로 밀리는 사고 방지).
DEFAULT_REFINE_MAX_SHIFT_RATIO = 0.35
#   ★ V5.3 : street 한쪽이 검은 노이즈로 덮인 실제 이미지 대응.
#   True 면 직교 투영에 평균 대신 **상위 percentile** 을 쓴다(백분위수는 자동 결정).
#   노이즈는 street 를 어둡게만 만들므로 덜 오염된 픽셀을 골라 단면을 복원한다.
DEFAULT_REFINE_ROBUST = True

# --- ★ 순수 die crop (street 여백 제외) ---------------------------------------
#   die rect 는 기본적으로 pitch 크기(= die + street 절반씩)라서 이웃 die 의 street 가
#   테두리에 묻어난다. True 면 측정된 street 폭만큼 안쪽으로 줄여 '순수 die' 만 남긴다.
DEFAULT_EXCLUDE_STREET = False

# crop 영역 보정/확장 (die 사이 street 포함, 미세 정렬 오차 보정용)
DEFAULT_OFFSET_X = 0   # crop 중심 X 위치 보정 (px). +면 오른쪽, -면 왼쪽으로 이동
DEFAULT_OFFSET_Y = 0   # crop 중심 Y 위치 보정 (px). +면 아래쪽, -면 위쪽으로 이동
DEFAULT_MARGIN_X = 0   # 좌/우로 각각 더 포함할 영역 (px). die 폭이 +2*margin_x 만큼 커짐
DEFAULT_MARGIN_Y = 0   # 상/하로 각각 더 포함할 영역 (px). die 높이가 +2*margin_y 만큼 커짐

# --- Notch 회전(angle) 보정 ---------------------------------------------------
DEFAULT_NOTCH_ALIGN = True       # build_die_map 시작 시 notch 로 회전 보정 (notch 없으면 자동 skip)
DEFAULT_NOTCH_REF_DEG = 90.0     # notch 의 정상 위치 (이미지 좌표 각도. 90 = 아래쪽/6시 방향)
DEFAULT_NOTCH_MIN_ANGLE = 0.05   # 이보다 작은 오차(deg)는 보정 생략 (불필요한 워핑 방지)
DEFAULT_NOTCH_MIN_DEPTH = 4.0    # notch 인정 절대 최소 파임 깊이 (px). 엣지 노이즈 하한
DEFAULT_NOTCH_NOISE_K = 3.0      # ★ 홈 크기 강인성: 실효임계 = max(MIN_DEPTH, 림노이즈*K)
                                 #   거친 엣지 웨이퍼에서 자동으로 임계가 올라가 오검출 방지
DEFAULT_NOTCH_OPEN_KSIZE = 3     # ★ 림 컬러 노이즈 강인성: 경계를 '가장 큰 연결성분'으로
                                 #   잡고, 이 크기 open 으로 얇은 노이즈 다리를 끊음(0=open끔)

# --- Angle alignment method --------------------------------------------------
DEFAULT_ANGLE_ALIGN_METHOD = "die_render"  # "die_render"(V5 기본) | "notch" | "vertical_line" | "none"

# --- die_render 얼라인 (검출 die 를 굵기 3 사각형으로 렌더한 격자에 sawline 정합) ---
DEFAULT_DIE_RENDER_THICKNESS = 3   # ★ dm.dies 를 cv2.rectangle 이 굵기로 렌더(=sawline 모양)
DEFAULT_DIE_RENDER_SEARCH_DEG = 6.0  # ★ 회전 탐색 범위 ±(deg). 넓혀서 큰 기울기도 잡음(예전 3.5)
DEFAULT_DIE_RENDER_COARSE_STEP = 0.15 # 1차 탐색 간격(deg) — 범위 넓힘에 맞춰 약간 키움(속도)
DEFAULT_DIE_RENDER_FINE_STEP = 0.02   # 2차 정밀 탐색 간격(deg)
DEFAULT_DIE_RENDER_ROI_RATIO = 0.55   # 정합에 쓰는 중앙 ROI 반경 비율(wafer_r 대비)
DEFAULT_DIE_RENDER_MAX_DIM = 1400     # 정합 ROI 다운스케일 한계(px) — 클수록 각도 정밀↑(속도↓)
DEFAULT_DIE_RENDER_MAX_ITER = 3       # 2-pass 반복(잔차 수렴까지)
# ★ 고도화: FFT 교차검증 + 합의(agreement). 두 독립 단서가 일치하면 신뢰↑, 어긋나면 재탐색.
DEFAULT_ANGLE_FFT_MAX_DIM = 1024   # FFT ROI 다운스케일 한계(px)
DEFAULT_ANGLE_AGREE_TOL_DEG = 0.40 # projection vs FFT 가 이 안에서 일치하면 '합의'로 본다
DEFAULT_ANGLE_FULL_SCAN_DEG = 44.0 # 합의 실패 시 ±이 범위까지 넓게 재탐색(거의 모든 기울기)
DEFAULT_VERTICAL_LINE_MAX_DEG = 6.0        # accept near-vertical lines within +/-deg
DEFAULT_VERTICAL_LINE_ROI_RATIO = 0.70     # inner wafer ROI used for longest-line scan
DEFAULT_VERTICAL_LINE_MIN_LEN_RATIO = 0.25 # min Hough line length as wafer_r ratio
DEFAULT_VERTICAL_LINE_MAX_ROI_SIZE = 1200  # downsample ROI limit for Hough speed
DEFAULT_AXIS_SEGMENT_MIN_LEN_RATIO = 0.035 # allow broken pieces; cluster decides total
DEFAULT_AXIS_CLUSTER_POS_TOL_RATIO = 0.010 # same-axis grouping tolerance
DEFAULT_AXIS_AGREE_TOL_DEG = 0.75          # vertical/horizontal agreement guard
# vertical_line 보정의 선(線) 소스 방식:
#   True  = 이진화(Otsu)로 두꺼운 die 선을 통째로 잡은 뒤 1px 중심선으로 '세선화'해 비교
#           (사용자 요청: "두껍게 잡은 선을 얇게 해서 비교"). 각도 비교가 두께에 흔들리지 않음.
#   False = 기존 Canny 엣지(이미 가늘다) 사용.
DEFAULT_AXIS_BINARIZE_LINES = True

# --- V2 전용 파라미터 ---------------------------------------------------------
DEFAULT_NOTCH_SECTOR_DEG = 70.0  # [기능1] notch 를 wafer '아래쪽'(ref±이 각도)에서만 탐색
DEFAULT_NOTCH_NOISE_MARGIN = 3.0 # [기능1] notch 인정 임계 = max(MIN_DEPTH, 림노이즈floor + 이값)
                                 #   (가산형 — 림 노이즈 floor 가 커도 진짜 notch 를 안 놓침)
DEFAULT_NOTCH_SMOOTH_DEG = 0.25  # [기능1] notch 검출 전 둘레 깊이를 이 각도폭으로 스무딩.
                                 #   notch(넓고 매끄러움)는 보존, 가장자리 거칠기(좁은 bite)는
                                 #   눌러서 -> 오염이 notch 깊이만큼 심해도 notch 만 골라냄.
DEFAULT_CLEAN_WAFER = True       # [기능4] 시작 시 wafer 원판 밖을 검정으로 (외부 노이즈 제거)
DEFAULT_VERIFY_TOL_DEG = 0.5     # [기능2] notch 각도 vs die 격자 각도 허용 오차(deg)
DEFAULT_GRID_ANGLE_RANGE = 4.0   # [기능2] die 격자 각도 탐색 범위 ±(deg)
DEFAULT_QUAD_BALANCE_TOL = 0.08  # [기능3] 4분면 coverage 허용 편차 (이내면 balanced)


@dataclass
class WaferDieMap:
    """build_die_map() 결과. locate_die() 등에서 재사용하는 격자/웨이퍼 정보 묶음.

    필드
    ----
    wafer_cx, wafer_cy, wafer_r : 웨이퍼 중심/반지름 (px)
    pitch_x, pitch_y            : die 가로/세로 pitch (px, sub-pixel float)
    x0, y0                      : grid origin(중심 코너) (px, ★sub-pixel float)
    die_w, die_h                : die 크기 (= pitch, ★sub-pixel float)
    street_w, street_h          : ★측정된 street(die 사이 여백) 폭/높이 (px). 0 = 측정 실패
    exclude_street              : ★True 면 rect/crop 이 street 를 뺀 '순수 die' 영역
    origin_refined              : ★origin 서브픽셀 보정이 실제로 적용됐는지
    origin_shift_px             : ★보정으로 움직인 양 (dx, dy) px. 예전 무게중심 대비 편차
    pixel_per_unit              : 실측 좌표 환산 단위 (px/unit)
    dies                        : die entry 리스트 (아래 형식)
    dies_by_index               : {(ix,iy): entry} 빠른 조회용
    image_shape                 : (H, W) 원본 이미지 크기

    die entry(dict)
    ---------------
    {
      "index":       (ix, iy),
      "center_px":   (cx, cy),           # 반올림된 정수 중심
      "center_px_f": (cxf, cyf),         # ★ 서브픽셀(float) 중심 — 정밀 계산용
      "rect_px":     (x1, y1, x2, y2),   # die 영역 (exclude_street 면 street 제외)
      "crop_rect_px":(x1, y1, x2, y2),   # offset/margin 적용된 crop 영역
      "real_coord":  (rx, ry),           # die 중심 기준 실측 좌표
      "is_edge_partial": bool,           # 정의① die 사각형이 wafer 원 밖으로 일부라도 나감
      "is_edge_ring":    bool,           # 정의② 격자에서 8방향 이웃이 다 차 있지 않은 최외곽
      "is_edge":     bool,               # edge_mode 가 가리키는 값(circle→partial / ring→ring / both→OR)
      "image":       np.ndarray,         # with_crops=True 일 때만 (crop_rect_px 영역)
    }
    """
    wafer_cx: int
    wafer_cy: int
    wafer_r: int
    pitch_x: float
    pitch_y: float
    x0: float
    y0: float
    die_w: float
    die_h: float
    pixel_per_unit: int
    dies: List[Dict[str, Any]] = field(default_factory=list)
    dies_by_index: Dict[Tuple[int, int], Dict[str, Any]] = field(default_factory=dict)
    image_shape: Tuple[int, int] = (0, 0)
    rotation_deg: float = 0.0     # notch 보정으로 적용된 회전 각도 (0 = 보정 없음)
    aligned_image: Optional[np.ndarray] = field(default=None, repr=False)
                                  # ★ [기능5] 항상 채워짐 = clean+align 후 실제 사용 이미지.
                                  #   모든 좌표(rect/center)는 이 이미지 기준이므로
                                  #   crop/시각화/YOLO 도 이 이미지를 사용해야 좌표가 맞는다.
    # --- V2 추가 필드 ---
    notch_center_px: Optional[Tuple[int, int]] = None   # [기능1] notch 파임의 중심 픽셀점
    die_grid_angle_resid: float = 0.0   # [기능2] 보정 후 die 격자 잔여 기울기(deg)
    angle_verified: bool = False        # [기능2] notch 각도와 die 격자 각도 일치 여부
    quadrant_report: Dict[str, Any] = field(default_factory=dict)  # [기능3] 4분면 검증 결과
    edge_mode: str = DEFAULT_EDGE_MODE  # [V5] is_edge 가 가리키는 기준(circle|ring|both)
    angle_confidence: float = 1.0  # [V5 고도화] 각도 신뢰도 0~1 (projection·FFT 합의 기반)
    angle_agree: bool = True        # [V5 고도화] projection 과 FFT 가 합의했는지
    # --- V5.2 (grid origin 서브픽셀 보정) 추가 필드 ---
    street_w: float = 0.0          # ★ 측정된 세로 street(die 사이 여백) 폭 (px). 0=측정실패
    street_h: float = 0.0          # ★ 측정된 가로 street 높이 (px)
    exclude_street: bool = False   # ★ rect/crop 이 street 를 뺀 '순수 die' 영역인지
    origin_refined: bool = False   # ★ origin 서브픽셀 보정이 실제로 적용됐는지
    origin_shift_px: Tuple[float, float] = (0.0, 0.0)  # ★ 보정으로 움직인 (dx, dy) px
    # --- V5.3 (die 사이 간격이 없는 wafer 대응) 추가 필드 ---
    phase_matched: bool = False    # ★ die 경계 phase 를 half-pitch 옮겨 되찾았는지

    def get_die(self, ix: int, iy: int) -> Optional[Dict[str, Any]]:
        """(ix, iy) die entry 반환 (없으면 None)."""
        return self.dies_by_index.get((ix, iy))

    def effective_die_size(self) -> Tuple[float, float]:
        """rect/crop 에 실제로 쓰이는 die 크기 (px, float).

        exclude_street=True 면 측정된 street 폭만큼 안쪽으로 줄인 '순수 die' 크기,
        아니면 pitch 크기 그대로. street 를 못 쟀으면(0) 자동으로 pitch 크기가 된다.
        """
        if not self.exclude_street:
            return (float(self.die_w), float(self.die_h))
        return (max(1.0, float(self.die_w) - float(self.street_w)),
                max(1.0, float(self.die_h) - float(self.street_h)))

    @property
    def num_dies(self) -> int:
        return len(self.dies)


def _rect_crosses_circle(x1: int, y1: int, x2: int, y2: int,
                         cx: int, cy: int, r: int) -> bool:
    """die rect 의 한 모서리라도 웨이퍼 원 밖이면 True (=정의①: 부분 die)."""
    r2 = r * r
    for (px, py) in ((x1, y1), (x2, y1), (x1, y2), (x2, y2)):
        if (px - cx) ** 2 + (py - cy) ** 2 > r2:
            return True
    return False


def _rect_circle_overlap_px(x1: float, y1: float, x2: float, y2: float,
                            cx: float, cy: float, r: float) -> float:
    """die rect 가 wafer 원 '안쪽으로 파고든 깊이'(px). <= 0 이면 겹치지 않음.

    원 중심에서 rect 까지의 최단거리 d 를 구해 (r - d) 를 반환한다.
      - rect 가 원을 완전히 벗어남      -> 음수
      - 경계에 살짝 걸침(1px 수준)      -> 0 보다 아주 조금 큼
      - rect 가 원 안에 완전히 들어감   -> r (최단거리 0)

    '중심이 원 안인가' 대신 이 값을 쓰면, 중심은 원 밖이지만 사각형 일부가 원 안에
    걸친 최외곽 EDGE die 도 놓치지 않는다(실제 이미지엔 보이는데 맵에서 빠지던 문제).
    """
    nx = min(max(float(cx), float(x1)), float(x2))
    ny = min(max(float(cy), float(y1)), float(y2))
    return float(r) - math.hypot(float(cx) - nx, float(cy) - ny)


def _normalize_edge_mode(edge_mode: str) -> str:
    """edge_mode 문자열 정규화 -> "circle" | "ring" | "both"."""
    m = str(edge_mode).lower().strip()
    if m in ("circle", "partial", "disc", "crop", "1"):
        return "circle"
    if m in ("ring", "neighbor", "outer", "outermost", "grid", "2"):
        return "ring"
    if m in ("both", "or", "all", "union"):
        return "both"
    raise ValueError("edge_mode must be 'circle', 'ring', or 'both'.")


def _resolve_edge_flag(is_partial: bool, is_ring: bool, edge_mode: str) -> bool:
    """edge_mode 에 따라 is_edge 가 가리킬 값 결정 (mode 는 정규화된 값)."""
    if edge_mode == "circle":
        return bool(is_partial)
    if edge_mode == "ring":
        return bool(is_ring)
    return bool(is_partial or is_ring)   # "both"


def _load_bgr(image: Union[str, Path, np.ndarray]) -> np.ndarray:
    """경로(str/Path) 또는 BGR ndarray 를 받아 BGR 이미지로 반환.

    ★[V5.4] 2-D(1채널) ndarray 를 그대로 넘기면 이후 cv2.cvtColor(BGR2GRAY) 에서
    바로 죽는다. 내부는 전부 3채널 전제라 여기서 한 번만 승격시킨다(값 손실 없음).
    파일 경로는 IMREAD_COLOR 라 1채널 파일도 동일 값 3장으로 읽히므로 문제없다.
    """
    if isinstance(image, np.ndarray):
        if image.ndim == 2:
            return cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        if image.ndim == 3 and image.shape[2] == 1:
            return cv2.cvtColor(image[:, :, 0], cv2.COLOR_GRAY2BGR)
        return image
    img = cv2.imread(str(image), cv2.IMREAD_COLOR)
    if img is None:
        raise FileNotFoundError(str(image))
    return img


def _rotate_wafer_keep_size(image_bgr: np.ndarray,
                            wafer_cx: int, wafer_cy: int,
                            angle_deg: float,
                            interp: int = cv2.INTER_CUBIC) -> np.ndarray:
    """Rotate around wafer center without changing output image size.

    ★ 보간법 = INTER_CUBIC (기본). 예전 INTER_NEAREST 는 die 격자처럼 '주기적인
    미세 패턴' 을 회전할 때 계단/모아레(aliasing) 가 심해 결과가 '깨져' 보였다.
    CUBIC(컬러는 LINEAR 대비 더 매끈)으로 바꿔 회전 후에도 격자가 또렷하다.
    각도 측정은 다운스케일·이진화 기반이라 약한 보간 블러에 영향받지 않는다.
    회전각 0 이면 보간 자체를 건너뛰어 원본을 그대로 보존(불필요한 워핑 방지).
    """
    if abs(float(angle_deg)) < 1e-9:
        return image_bgr.copy()
    H, W = image_bgr.shape[:2]
    M = cv2.getRotationMatrix2D((float(wafer_cx), float(wafer_cy)), angle_deg, 1.0)
    rotated = cv2.warpAffine(image_bgr, M, (W, H),
                             flags=interp, borderValue=(0, 0, 0))
    assert rotated.shape[:2] == (H, W)
    return rotated


def _crop_rect(cx: float, cy: float, die_w: float, die_h: float,
               offset_x: int, offset_y: int,
               margin_x: int, margin_y: int) -> Tuple[int, int, int, int]:
    """die 중심에 offset(위치 보정) + margin(영역 확장)을 적용한 crop 사각 좌표.

    crop 중심 = (cx + offset_x, cy + offset_y)
    crop 크기 = (die_w + 2*margin_x, die_h + 2*margin_y)
    반환: (x1, y1, x2, y2)  ← die 사이 street 를 포함하려면 margin 을 키운다.
    """
    ccx = cx + offset_x
    ccy = cy + offset_y
    half_w = die_w / 2.0 + margin_x
    half_h = die_h / 2.0 + margin_y
    return (int(round(ccx - half_w)), int(round(ccy - half_h)),
            int(round(ccx + half_w)), int(round(ccy + half_h)))


def crop_die(image: np.ndarray, center_x: float, center_y: float,
             die_w: float, die_h: float, *,
             offset_x: int = DEFAULT_OFFSET_X, offset_y: int = DEFAULT_OFFSET_Y,
             margin_x: int = DEFAULT_MARGIN_X, margin_y: int = DEFAULT_MARGIN_Y,
             border_mode: str = "pad") -> Optional[np.ndarray]:
    """die 중심 기준으로 offset/margin 을 적용해 crop 한 이미지를 반환.

    - offset_x/y : crop 위치를 (px) 만큼 이동해 미세 정렬 오차를 보정.
    - margin_x/y : 각 변으로 (px) 만큼 영역을 더 포함 (die 사이 street/이웃 일부 포함).
    실제 crop = 중심 (center_x+offset_x, center_y+offset_y),
                크기 (die_w+2*margin_x, die_h+2*margin_y).
    원본 clip_die 를 그대로 재사용한다 (border_mode: "pad" 고정크기 | "crop" 가변).
    """
    return clip_die(image,
                    int(round(center_x + offset_x)),
                    int(round(center_y + offset_y)),
                    int(round(die_w + 2 * margin_x)),
                    int(round(die_h + 2 * margin_y)),
                    border_mode=border_mode)


# =============================================================================
# [SECTOR: 40_ALIGNMENT_AND_CLEAN] notch·직선·die-render 회전 보정과 wafer 정리
# (0) Notch 기반 회전(angle) 보정 — build_die_map 의 모든 연산 전에 적용
# =============================================================================
def _wafer_silhouette(gray: np.ndarray, black_thr: int, open_ksize: int) -> np.ndarray:
    """wafer 실루엣 마스크(가장 큰 연결성분) — 림 주변 컬러 노이즈에 강인.

    notch 검출의 경계 측정이 '림 밖 컬러 노이즈(wafer 색과 다른 선/얼룩)'를 경계로
    오인하지 않도록, 단순 임계 마스크에서 (옵션) 얇은 노이즈 다리를 open 으로 끊고
    '가장 큰 연결성분' 만 남긴다. notch 같은 오목부(concavity)는 보존된다.
    """
    _, mask = cv2.threshold(gray, black_thr, 255, cv2.THRESH_BINARY)
    if open_ksize >= 3:
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (open_ksize, open_ksize))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, k)
    ncomp, labels, stats, _ = cv2.connectedComponentsWithStats(mask, 8)
    if ncomp <= 1:
        return mask
    big = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))   # 배경(0) 제외 최대 성분
    return (labels == big).astype(np.uint8)


def detect_notch_angle(image_bgr: np.ndarray,
                       wafer_cx: int, wafer_cy: int, wafer_r: int,
                       notch_ref_deg: float = DEFAULT_NOTCH_REF_DEG,
                       n_angles: int = 14400,
                       min_depth: float = DEFAULT_NOTCH_MIN_DEPTH,
                       noise_k: float = DEFAULT_NOTCH_NOISE_K,
                       min_span_deg: float = 0.06,
                       black_thr: int = 20,
                       open_ksize: int = DEFAULT_NOTCH_OPEN_KSIZE) -> Optional[float]:
    """Notch(웨이퍼 림의 작은 홈) 위치로 회전 오차(deg)를 측정 — 홈 크기에 강인.

    원리: 웨이퍼 둘레를 각도별로 방사형 스캔해 경계 반지름을 구하면,
    notch 위치에서만 경계가 안쪽으로 파인다(indentation). 그 파임 구간의
    깊이-가중 원형 centroid 각도와 기준 각도(notch_ref_deg)의 차이 = 회전 오차.

    홈 크기 강인성 (★ 적응형 임계)
    -----------------------------
    1) 후보 = (깊이 > min_depth) & (연속 각도폭 >= min_span_deg) 인 가장 깊은 구간.
    2) 림 노이즈(stair-step edge) floor 를 후보 '밖' 둘레에서 추정하고,
       실효 임계 = max(min_depth, 노이즈floor * noise_k) 로 자동 조정.
       => 엣지가 거친 웨이퍼에서도 오검출 없이, 작은 홈(≈8px↑)~큰 홈까지 동일 처리.

    Parameters
    ----------
    notch_ref_deg : notch 의 정상 위치 (이미지 좌표 각도. 90 = 아래쪽/6시 방향)
    n_angles      : 둘레 각도 샘플 수 (14400 = 0.025도 간격)
    min_depth     : notch 인정 절대 최소 파임 깊이 (px). 엣지 노이즈 하한.
    noise_k       : 적응형 임계 배율. 실효임계 = max(min_depth, 림노이즈*noise_k).
    min_span_deg  : notch 최소 각도 폭 (deg) — 단일-샘플 점노이즈 제외용.
    black_thr     : 배경(검정) 판정 임계.

    Returns
    -------
    float : 회전 오차 (deg). cv2.getRotationMatrix2D 의 angle 로 그대로 사용.
    None  : notch 를 찾지 못함 (notch 없는 이미지 -> 보정 불필요)
    """
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    H, W = gray.shape

    # ★ 림 주변 '컬러 노이즈'(wafer 색과 다른 선/얼룩)에 강인하도록, 단순 임계 대신
    #   '가장 큰 연결성분(wafer 실루엣)'을 경계로 사용 (림 밖 노이즈를 경계로 오인 X).
    sil = _wafer_silhouette(gray, black_thr, open_ksize)

    # 둘레 방사형 스캔 (vectorized): 각도별 경계(실루엣 최외곽) 반지름.
    #   rs 범위를 넓게(0.93~1.015r) 잡아 깊은 홈도 끝까지 측정.
    angs = np.linspace(0.0, 2.0 * np.pi, n_angles, endpoint=False)
    rs = np.linspace(wafer_r * 0.93, wafer_r * 1.015, 200)
    xs = (wafer_cx + rs[None, :] * np.cos(angs)[:, None]).astype(np.int32)
    ys = (wafer_cy + rs[None, :] * np.sin(angs)[:, None]).astype(np.int32)
    np.clip(xs, 0, W - 1, out=xs)
    np.clip(ys, 0, H - 1, out=ys)
    on_wafer = sil[ys, xs] > 0
    idx = np.where(on_wafer.any(axis=1),
                   on_wafer.shape[1] - 1 - np.argmax(on_wafer[:, ::-1], axis=1), 0)
    radii = rs[idx]
    depth = np.median(radii) - radii          # 양수 = 안쪽으로 파임

    # 1) 후보 구간: 절대 하한(min_depth) 이상 + 연속(span) 인 구간들
    above = np.where(depth > min_depth)[0]
    if len(above) == 0:
        return None
    clusters: List[List[int]] = [[above[0]]]
    for v in above[1:]:
        if v - clusters[-1][-1] <= 2:
            clusters[-1].append(v)
        else:
            clusters.append([v])
    # 0도/360도 경계에 걸친 cluster 병합
    if len(clusters) > 1 and clusters[0][0] == 0 and clusters[-1][-1] == n_angles - 1:
        clusters[0] = clusters[-1] + [c + n_angles for c in clusters[0]]
        clusters.pop()
    clusters = [c for c in clusters
                if (c[-1] - c[0]) * 360.0 / n_angles >= min_span_deg]
    if not clusters:
        return None

    # 2) 가장 깊은(깊이합 최대) 구간 = notch 후보
    cand = max(clusters,
               key=lambda c: float(depth[[i % n_angles for i in c]].sum()))

    # 3) ★ 적응형 임계: 후보 '밖' 둘레의 노이즈 floor 로 실효 임계 결정
    keep = np.ones(n_angles, dtype=bool)
    keep[[i % n_angles for i in cand]] = False
    outside = depth[keep]
    noise_floor = float(np.percentile(outside, 99.5)) if outside.size else 0.0
    eff_thr = max(min_depth, noise_floor * noise_k)
    d = depth[[i % n_angles for i in cand]]
    if float(d.max()) < eff_thr:               # 노이즈 대비 충분히 깊지 않음 -> notch 아님
        return None

    # 4) 깊이-가중 원형 centroid -> notch 각도 -> 기준 대비 오차 (-180~+180 wrap)
    a = np.array([2.0 * np.pi * (i % n_angles) / n_angles for i in cand])
    notch_deg = math.degrees(math.atan2(float((np.sin(a) * d).sum()),
                                        float((np.cos(a) * d).sum()))) % 360.0
    return ((notch_deg - notch_ref_deg + 180.0) % 360.0) - 180.0


def align_wafer_by_notch(image_bgr: np.ndarray,
                         notch_ref_deg: float = DEFAULT_NOTCH_REF_DEG,
                         min_angle_deg: float = DEFAULT_NOTCH_MIN_ANGLE,
                         max_iter: int = 2) -> Tuple[np.ndarray, float]:
    """Notch 로 회전 오차를 측정/보정한 이미지 반환 -> (보정 이미지, 적용 각도 deg).

    - notch 가 없거나 오차가 min_angle_deg 미만이면 원본 그대로 반환 (각도 0.0).
    - 회전은 웨이퍼 중심 기준, INTER_NEAREST 사용
      (보간 블러가 생기면 die 내부 보조선이 격자 검출에 끼어들 수 있어 픽셀 보존).
    - max_iter=2 : 1차 보정 후 잔차가 남으면 누적 각도로 "원본에서" 다시 1회 회전
      (항상 원본 -> 1회 워핑이므로 이중 보간 없음).
    - ★ 출력 이미지 크기는 입력과 '동일하게 유지'된다 (10000x10000 -> 10000x10000).
      캔버스를 키우지 않으므로 회전 후에도 해상도/좌표계가 변하지 않는다.
    """
    def _angle(im, cx_, cy_, r_):   # V2: 아래쪽 sector notch 의 각도만 추출
        res = detect_notch(im, cx_, cy_, r_, notch_ref_deg=notch_ref_deg)
        return None if res is None else res[0]

    wafer_cx, wafer_cy, wafer_r = detect_wafer(image_bgr)
    err = _angle(image_bgr, wafer_cx, wafer_cy, wafer_r)
    if err is None or abs(err) < min_angle_deg:
        return image_bgr, 0.0

    H, W = image_bgr.shape[:2]

    def _rotate(total_deg: float) -> np.ndarray:
        # dsize=(W, H) 로 출력 캔버스를 입력과 '동일 크기'로 고정한다.
        #   (PIL 의 rotate(expand=True) 처럼 캔버스가 커지지 않음.
        #    wafer 는 중앙에 있어 작은 각도 회전으로 잘리지 않는다.)
        M = cv2.getRotationMatrix2D((float(wafer_cx), float(wafer_cy)), total_deg, 1.0)
        rotated = cv2.warpAffine(image_bgr, M, (W, H),
                                 flags=cv2.INTER_NEAREST, borderValue=(0, 0, 0))
        assert rotated.shape[:2] == (H, W)   # 크기 불변 보장
        return rotated

    total = float(err)
    aligned = _rotate(total)
    for _ in range(max(0, max_iter - 1)):        # 잔차 정밀 보정
        cx2, cy2, r2 = detect_wafer(aligned)
        res = _angle(aligned, cx2, cy2, r2)
        if res is None or abs(res) < min_angle_deg:
            break
        total += float(res)
        aligned = _rotate(total)
    return aligned, total


def _axis_deviation_deg(x1: int, y1: int, x2: int, y2: int,
                        axis: str) -> Optional[float]:
    """Return cv2 rotation angle needed to make a segment vertical/horizontal."""
    dx = float(x2 - x1)
    dy = float(y2 - y1)
    if dx == 0.0 and dy == 0.0:
        return None
    angle = math.degrees(math.atan2(dy, dx)) % 180.0
    if axis == "vertical":
        return angle - 90.0
    if axis == "horizontal":
        return angle if angle <= 90.0 else angle - 180.0
    raise ValueError("axis must be 'vertical' or 'horizontal'.")


def _vertical_deviation_deg(x1: int, y1: int, x2: int, y2: int) -> Optional[float]:
    """Return cv2 rotation angle needed to make an undirected segment vertical."""
    return _axis_deviation_deg(x1, y1, x2, y2, "vertical")


def _horizontal_deviation_deg(x1: int, y1: int, x2: int, y2: int) -> Optional[float]:
    """Return cv2 rotation angle needed to make an undirected segment horizontal."""
    return _axis_deviation_deg(x1, y1, x2, y2, "horizontal")


def _thin_binary(mask: np.ndarray) -> np.ndarray:
    """Thin a binary mask to one-pixel strokes for more stable Hough angles."""
    binary = ((mask > 0).astype(np.uint8) * 255)
    ximgproc = getattr(cv2, "ximgproc", None)
    if ximgproc is not None and hasattr(ximgproc, "thinning"):
        return ximgproc.thinning(binary)

    skel = np.zeros(binary.shape, np.uint8)
    element = cv2.getStructuringElement(cv2.MORPH_CROSS, (3, 3))
    work = binary.copy()
    for _ in range(512):
        eroded = cv2.erode(work, element)
        opened = cv2.dilate(eroded, element)
        skel = cv2.bitwise_or(skel, cv2.subtract(work, opened))
        work = eroded
        if cv2.countNonZero(work) == 0:
            break
    return skel


def _axis_position_at_center(x1: int, y1: int, x2: int, y2: int,
                             axis: str, center_x: float,
                             center_y: float) -> Optional[float]:
    """Project a segment to wafer center and return its axis position."""
    dx = float(x2 - x1)
    dy = float(y2 - y1)
    mx = (float(x1) + float(x2)) * 0.5
    my = (float(y1) + float(y2)) * 0.5
    if axis == "vertical":
        if abs(dy) < 1e-6:
            return None
        return mx + (dx / dy) * (center_y - my)
    if axis == "horizontal":
        if abs(dx) < 1e-6:
            return None
        return my + (dy / dx) * (center_x - mx)
    raise ValueError("axis must be 'vertical' or 'horizontal'.")


def _cluster_axis_segments(segments: List[Dict[str, Any]],
                           axis: str,
                           pos_tol: float,
                           min_total_len: float,
                           center_x: float,
                           center_y: float,
                           roi_origin_x: int,
                           roi_origin_y: int,
                           scale: float
                           ) -> Optional[Tuple[float, Tuple[int, int, int, int], float]]:
    """Merge broken collinear Hough segments and return the strongest axis."""
    if not segments:
        return None

    clusters: List[List[Dict[str, Any]]] = []
    for seg in sorted(segments, key=lambda s: float(s["pos"])):
        if not clusters:
            clusters.append([seg])
            continue
        prev = clusters[-1]
        prev_len = sum(float(s["length"]) for s in prev)
        prev_pos = sum(float(s["pos"]) * float(s["length"]) for s in prev) / prev_len
        if abs(float(seg["pos"]) - prev_pos) <= pos_tol:
            prev.append(seg)
        else:
            clusters.append([seg])

    best: Optional[Tuple[float, Tuple[int, int, int, int], float]] = None
    for cluster in clusters:
        total_len = sum(float(s["length"]) for s in cluster)
        if total_len < min_total_len:
            continue
        dev = sum(float(s["dev"]) * float(s["length"]) for s in cluster) / total_len
        pos = sum(float(s["pos"]) * float(s["length"]) for s in cluster) / total_len

        pts = []
        for s in cluster:
            x1, y1, x2, y2 = s["line"]
            pts.extend([(float(x1), float(y1)), (float(x2), float(y2))])

        if axis == "vertical":
            ys = [p[1] for p in pts]
            y_a, y_b = min(ys), max(ys)
            a = math.radians(90.0 + dev)
            slope = math.cos(a) / max(math.sin(a), 1e-6)
            x_a = pos + slope * (y_a - center_y)
            x_b = pos + slope * (y_b - center_y)
        else:
            xs = [p[0] for p in pts]
            x_a, x_b = min(xs), max(xs)
            slope = math.tan(math.radians(dev))
            y_a = pos + slope * (x_a - center_x)
            y_b = pos + slope * (x_b - center_x)

        line = (
            int(round(x_a / scale)) + roi_origin_x,
            int(round(y_a / scale)) + roi_origin_y,
            int(round(x_b / scale)) + roi_origin_x,
            int(round(y_b / scale)) + roi_origin_y,
        )
        length = total_len / scale
        if best is None or length > best[2]:
            best = (float(dev), line, float(length))
    return best


def _detect_long_axis_lines(image_bgr: np.ndarray,
                            wafer_cx: int, wafer_cy: int, wafer_r: int,
                            axes: Tuple[str, ...] = ("vertical", "horizontal"),
                            max_deviation_deg: float = DEFAULT_VERTICAL_LINE_MAX_DEG,
                            roi_ratio: float = DEFAULT_VERTICAL_LINE_ROI_RATIO,
                            min_length_ratio: float = DEFAULT_VERTICAL_LINE_MIN_LEN_RATIO,
                            segment_min_length_ratio: float = DEFAULT_AXIS_SEGMENT_MIN_LEN_RATIO,
                            cluster_pos_tol_ratio: float = DEFAULT_AXIS_CLUSTER_POS_TOL_RATIO,
                            canny_low: int = 50,
                            canny_high: int = 150,
                            hough_threshold: int = 80,
                            max_line_gap_ratio: float = 0.035,
                            max_roi_size: int = DEFAULT_VERTICAL_LINE_MAX_ROI_SIZE,
                            thin_edges: bool = True,
                            binarize_lines: bool = DEFAULT_AXIS_BINARIZE_LINES
                            ) -> Dict[str, Tuple[float, Tuple[int, int, int, int], float]]:
    """Detect strongest vertical/horizontal axes, merging broken line pieces.

    선(線) 소스는 두 가지:
      - binarize_lines=True : ROI를 Otsu 이진화해 '두꺼운' die 선을 통째로 잡은 뒤
        thin_edges면 1px 중심선으로 세선화한다. 두께가 각도 측정을 흔들지 않게 됨
        (사용자 요청: "두껍게 잡은 선을 얇게 해서 비교"). 빈 결과면 Canny로 폴백.
      - binarize_lines=False: 기존 Canny 엣지(이미 가늘다)를 그대로 사용.
    """
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    H, W = gray.shape
    roi_r = max(8, int(round(wafer_r * roi_ratio)))
    x0 = max(0, wafer_cx - roi_r)
    x1 = min(W, wafer_cx + roi_r + 1)
    y0 = max(0, wafer_cy - roi_r)
    y1 = min(H, wafer_cy + roi_r + 1)
    if x1 <= x0 + 8 or y1 <= y0 + 8:
        return {}

    roi = gray[y0:y1, x0:x1]
    local_cx = wafer_cx - x0
    local_cy = wafer_cy - y0
    yy, xx = np.ogrid[:roi.shape[0], :roi.shape[1]]
    mask = ((xx - local_cx) ** 2 + (yy - local_cy) ** 2 <= roi_r ** 2).astype(np.uint8) * 255

    scale = 1.0
    max_dim = max(roi.shape[:2])
    if max_dim > max_roi_size:
        scale = float(max_roi_size) / float(max_dim)
        roi = cv2.resize(roi, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
        mask = cv2.resize(mask, (roi.shape[1], roi.shape[0]), interpolation=cv2.INTER_NEAREST)

    center_x = float(local_cx) * scale
    center_y = float(local_cy) * scale
    blur = cv2.GaussianBlur(roi, (3, 3), 0)

    edges = None
    if binarize_lines:
        # (1) 이진화: 두꺼운 die 선/무늬를 통째로 잡는다 (Otsu 자동 임계).
        _, binr = cv2.threshold(blur, 0, 255,
                                cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        binr = cv2.bitwise_and(binr, binr, mask=mask)
        # (2) 세선화: 두꺼운 선을 1px 중심선으로 → 각도 비교가 선 두께에 흔들리지 않음.
        line_mask = _thin_binary(binr) if thin_edges else binr
        if int(cv2.countNonZero(line_mask)) >= 1:
            edges = line_mask
    if edges is None:
        # 폴백(또는 binarize_lines=False): 기존 Canny 엣지(이미 가늘다).
        edges = cv2.Canny(blur, canny_low, canny_high)
        edges = cv2.bitwise_and(edges, edges, mask=mask)
        if thin_edges:
            edges = _thin_binary(edges)

    segment_min_len = max(12, int(round(wafer_r * segment_min_length_ratio * scale)))
    max_gap = max(6, int(round(wafer_r * max_line_gap_ratio * scale)))
    threshold = max(25, int(round(hough_threshold * min(1.0, scale))))
    lines = cv2.HoughLinesP(edges, 1, np.pi / 1800.0,
                            threshold=threshold,
                            minLineLength=segment_min_len,
                            maxLineGap=max_gap)
    if lines is None:
        return {}

    candidates: Dict[str, List[Dict[str, Any]]] = {axis: [] for axis in axes}
    for raw in lines.reshape(-1, 4):
        lx1, ly1, lx2, ly2 = (int(v) for v in raw)
        length = math.hypot(float(lx2 - lx1), float(ly2 - ly1))
        if length < segment_min_len:
            continue
        for axis in axes:
            dev = _axis_deviation_deg(lx1, ly1, lx2, ly2, axis)
            if dev is None or abs(dev) > max_deviation_deg:
                continue
            pos = _axis_position_at_center(lx1, ly1, lx2, ly2, axis, center_x, center_y)
            if pos is None:
                continue
            candidates[axis].append({
                "dev": float(dev),
                "pos": float(pos),
                "length": float(length),
                "line": (lx1, ly1, lx2, ly2),
            })

    min_total_len = max(float(segment_min_len) * 1.5,
                        float(wafer_r) * min_length_ratio * scale)
    pos_tol = max(4.0, float(wafer_r) * cluster_pos_tol_ratio * scale)
    out: Dict[str, Tuple[float, Tuple[int, int, int, int], float]] = {}
    for axis, segs in candidates.items():
        best = _cluster_axis_segments(segs, axis, pos_tol, min_total_len,
                                      center_x, center_y, x0, y0, scale)
        if best is not None:
            out[axis] = best
    return out


def _detect_longest_vertical_line(image_bgr: np.ndarray,
                                  wafer_cx: int, wafer_cy: int, wafer_r: int,
                                  max_deviation_deg: float = DEFAULT_VERTICAL_LINE_MAX_DEG,
                                  roi_ratio: float = DEFAULT_VERTICAL_LINE_ROI_RATIO,
                                  min_length_ratio: float = DEFAULT_VERTICAL_LINE_MIN_LEN_RATIO,
                                  **kwargs: Any
                                  ) -> Optional[Tuple[float, Tuple[int, int, int, int], float]]:
    """Find the strongest near-vertical axis, merging broken pieces."""
    axes = _detect_long_axis_lines(
        image_bgr, wafer_cx, wafer_cy, wafer_r,
        axes=("vertical",),
        max_deviation_deg=max_deviation_deg,
        roi_ratio=roi_ratio,
        min_length_ratio=min_length_ratio,
        **kwargs)
    return axes.get("vertical")


def _detect_longest_horizontal_line(image_bgr: np.ndarray,
                                    wafer_cx: int, wafer_cy: int, wafer_r: int,
                                    max_deviation_deg: float = DEFAULT_VERTICAL_LINE_MAX_DEG,
                                    roi_ratio: float = DEFAULT_VERTICAL_LINE_ROI_RATIO,
                                    min_length_ratio: float = DEFAULT_VERTICAL_LINE_MIN_LEN_RATIO,
                                    **kwargs: Any
                                    ) -> Optional[Tuple[float, Tuple[int, int, int, int], float]]:
    """Find the strongest near-horizontal axis, merging broken pieces."""
    axes = _detect_long_axis_lines(
        image_bgr, wafer_cx, wafer_cy, wafer_r,
        axes=("horizontal",),
        max_deviation_deg=max_deviation_deg,
        roi_ratio=roi_ratio,
        min_length_ratio=min_length_ratio,
        **kwargs)
    return axes.get("horizontal")


def measure_vertical_line_angle(image_bgr: np.ndarray,
                                wafer_cx: int, wafer_cy: int, wafer_r: int,
                                max_deviation_deg: float = DEFAULT_VERTICAL_LINE_MAX_DEG,
                                roi_ratio: float = DEFAULT_VERTICAL_LINE_ROI_RATIO,
                                min_length_ratio: float = DEFAULT_VERTICAL_LINE_MIN_LEN_RATIO
                                ) -> Optional[float]:
    """Measure rotation from the strongest vertical wafer axis."""
    res = _detect_longest_vertical_line(
        image_bgr, wafer_cx, wafer_cy, wafer_r,
        max_deviation_deg=max_deviation_deg,
        roi_ratio=roi_ratio,
        min_length_ratio=min_length_ratio)
    return None if res is None else res[0]


def measure_horizontal_line_angle(image_bgr: np.ndarray,
                                  wafer_cx: int, wafer_cy: int, wafer_r: int,
                                  max_deviation_deg: float = DEFAULT_VERTICAL_LINE_MAX_DEG,
                                  roi_ratio: float = DEFAULT_VERTICAL_LINE_ROI_RATIO,
                                  min_length_ratio: float = DEFAULT_VERTICAL_LINE_MIN_LEN_RATIO
                                  ) -> Optional[float]:
    """Measure rotation from the strongest horizontal wafer axis."""
    res = _detect_longest_horizontal_line(
        image_bgr, wafer_cx, wafer_cy, wafer_r,
        max_deviation_deg=max_deviation_deg,
        roi_ratio=roi_ratio,
        min_length_ratio=min_length_ratio)
    return None if res is None else res[0]


def measure_axis_line_angle(image_bgr: np.ndarray,
                            wafer_cx: int, wafer_cy: int, wafer_r: int,
                            max_deviation_deg: float = DEFAULT_VERTICAL_LINE_MAX_DEG,
                            roi_ratio: float = DEFAULT_VERTICAL_LINE_ROI_RATIO,
                            min_length_ratio: float = DEFAULT_VERTICAL_LINE_MIN_LEN_RATIO,
                            agree_tol_deg: float = DEFAULT_AXIS_AGREE_TOL_DEG
                            ) -> Optional[float]:
    """Measure rotation from merged vertical and horizontal wafer axes."""
    axes = _detect_long_axis_lines(
        image_bgr, wafer_cx, wafer_cy, wafer_r,
        axes=("vertical", "horizontal"),
        max_deviation_deg=max_deviation_deg,
        roi_ratio=roi_ratio,
        min_length_ratio=min_length_ratio)
    if not axes:
        return None

    vertical = axes.get("vertical")
    horizontal = axes.get("horizontal")
    if vertical is not None and horizontal is not None:
        v_angle, _, v_len = vertical
        h_angle, _, h_len = horizontal
        if abs(v_angle - h_angle) <= agree_tol_deg:
            return float((v_angle * v_len + h_angle * h_len) / (v_len + h_len))
        return float(v_angle if v_len >= h_len else h_angle)
    only = vertical if vertical is not None else horizontal
    return None if only is None else float(only[0])


def align_wafer_by_vertical_line(image_bgr: np.ndarray,
                                 min_angle_deg: float = DEFAULT_NOTCH_MIN_ANGLE,
                                 max_deviation_deg: float = DEFAULT_VERTICAL_LINE_MAX_DEG,
                                 roi_ratio: float = DEFAULT_VERTICAL_LINE_ROI_RATIO,
                                 min_length_ratio: float = DEFAULT_VERTICAL_LINE_MIN_LEN_RATIO,
                                 max_iter: int = 2) -> Tuple[np.ndarray, float]:
    """Align wafer sequentially: vertical axis first, then horizontal residual."""
    wafer_cx, wafer_cy, _ = detect_wafer(image_bgr)
    total = 0.0
    aligned = image_bgr

    for _ in range(max(1, max_iter)):
        changed = False
        cx, cy, r = detect_wafer(aligned)
        v_err = measure_vertical_line_angle(
            aligned, cx, cy, r,
            max_deviation_deg=max_deviation_deg,
            roi_ratio=roi_ratio,
            min_length_ratio=min_length_ratio)
        if v_err is not None and abs(v_err) >= min_angle_deg:
            total += float(v_err)
            aligned = _rotate_wafer_keep_size(image_bgr, wafer_cx, wafer_cy, total)
            changed = True

        cx, cy, r = detect_wafer(aligned)
        h_err = measure_horizontal_line_angle(
            aligned, cx, cy, r,
            max_deviation_deg=max_deviation_deg,
            roi_ratio=roi_ratio,
            min_length_ratio=min_length_ratio)
        if h_err is not None and abs(h_err) >= min_angle_deg:
            total += float(h_err)
            aligned = _rotate_wafer_keep_size(image_bgr, wafer_cx, wafer_cy, total)
            changed = True

        if not changed:
            break
    return aligned, total


# =============================================================================
# (V5) die_render 얼라인 : dm.dies 를 굵기 3 사각형으로 렌더한 격자에 sawline 정합
# =============================================================================
def render_die_grid_mask(image_shape: Tuple[int, ...],
                         dies: List[Any],
                         thickness: int = DEFAULT_DIE_RENDER_THICKNESS,
                         key: str = "rect_px") -> np.ndarray:
    """모든 die 를 cv2.rectangle(굵기 thickness)로 그린 격자 마스크(uint8) 반환.

    dies 항목은 dict(rect_px 키) 또는 (x1,y1,x2,y2) 튜플 둘 다 허용.
    굵기 3 사각 테두리들의 합집합 = wafer 의 sawline 격자 모양 = 정합/시각화 기준 템플릿.
    """
    H, W = int(image_shape[0]), int(image_shape[1])
    mask = np.zeros((H, W), np.uint8)
    t = max(1, int(thickness))
    for d in dies:
        if isinstance(d, dict):
            x1, y1, x2, y2 = d[key]
        else:
            x1, y1, x2, y2 = d
        cv2.rectangle(mask, (int(x1), int(y1)), (int(x2), int(y2)), 255, t)
    return mask


def _prelim_die_rects(image_bgr: np.ndarray,
                      wafer_cx: int, wafer_cy: int, wafer_r: int,
                      grid_method: str = DEFAULT_GRID_METHOD,
                      edge_margin: float = 1.0
                      ) -> Tuple[List[Tuple[int, int, int, int]],
                                 Tuple[float, float, int, int, int, int]]:
    """현재 이미지에서 die 격자를 검출해 wafer 원 안의 die 사각형 목록을 만든다.

    build_die_map 의 die 순회와 동일한 중심/rect 공식(축정렬). die_render 정합의
    '이상적 격자 템플릿' 재료(렌더할 사각형들)로 쓰인다.

    주의: 이 단계는 '아직 보정 전'(기울어진) 이미지에서 호출될 수 있다. "corner"
    격자검출은 정렬된 이미지를 전제로 해 기울면 실패하므로, 실패 시 기울기에
    강인한 autocorrelation 기반("std"->"hybrid")으로 자동 폴백한다. 템플릿은
    주기적 격자라 원점(phase)이 약간 어긋나도 '각도' 정합 결과는 동일하다.
    """
    pitch_x = pitch_y = None
    x0 = y0 = 0
    for m in (grid_method, "std", "hybrid"):
        try:
            pitch_x, pitch_y, x0, y0 = detect_grid(
                image_bgr, wafer_cx, wafer_cy, wafer_r, method=m)
            break
        except Exception:
            pitch_x = None
            continue
    if pitch_x is None or pitch_y is None or pitch_x <= 1 or pitch_y <= 1:
        return [], (0.0, 0.0, 0, 0, 0, 0)
    die_w = int(round(pitch_x))
    die_h = int(round(pitch_y))
    max_ix = int(np.ceil(wafer_r / pitch_x)) + 2
    max_iy = int(np.ceil(wafer_r / pitch_y)) + 2
    r_lim_sq = (wafer_r * edge_margin) ** 2
    rects: List[Tuple[int, int, int, int]] = []
    for iy in range(-max_iy, max_iy + 1):
        for ix in range(-max_ix, max_ix + 1):
            cx_d = int(round(x0 + ix * pitch_x + pitch_x / 2))
            cy_d = int(round(y0 - iy * pitch_y - pitch_y / 2))
            dx = cx_d - wafer_cx
            dy = cy_d - wafer_cy
            if dx * dx + dy * dy > r_lim_sq:
                continue
            x_a = cx_d - die_w // 2
            y_a = cy_d - die_h // 2
            rects.append((x_a, y_a, x_a + die_w, y_a + die_h))
    return rects, (float(pitch_x), float(pitch_y), x0, y0, die_w, die_h)


def _grid_projection_score(image_bgr: np.ndarray,
                           wafer_cx: int, wafer_cy: int, wafer_r: int,
                           roi_ratio: float = DEFAULT_DIE_RENDER_ROI_RATIO,
                           max_dim: int = DEFAULT_DIE_RENDER_MAX_DIM):
    """중앙 ROI 를 Otsu 이진화해 '열/행 투영 분산' 점수함수를 만든다.

    반환: score(a) -> float  (없으면 None). score 는 격자를 a 만큼 회전 후
    열 투영·행 투영의 분산 합. 격자가 축에 맞으면 최대. die 격자 검출(grid 함수)에
    의존하지 않고 '이미지 픽셀' 만으로 동작하므로, 격자 검출이 실패해도 각도를 잰다.
    """
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    H, W = gray.shape
    half = max(16, int(round(wafer_r * roi_ratio)))
    x0r, x1r = max(0, wafer_cx - half), min(W, wafer_cx + half)
    y0r, y1r = max(0, wafer_cy - half), min(H, wafer_cy + half)
    if x1r <= x0r + 8 or y1r <= y0r + 8:
        return None

    roi_w, roi_h = x1r - x0r, y1r - y0r
    scale = min(1.0, float(max_dim) / float(max(roi_w, roi_h)))
    sw = max(8, int(round(roi_w * scale)))
    sh = max(8, int(round(roi_h * scale)))
    roi = gray[y0r:y1r, x0r:x1r]
    roi_s = cv2.resize(roi, (sw, sh), interpolation=cv2.INTER_AREA) if scale < 1.0 else roi

    lcx = (wafer_cx - x0r) * scale
    lcy = (wafer_cy - y0r) * scale
    yy, xx = np.ogrid[:sh, :sw]
    cmask = ((xx - lcx) ** 2 + (yy - lcy) ** 2 <= (half * scale) ** 2)

    blur = cv2.GaussianBlur(roi_s, (3, 3), 0)
    _, binr = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    grid = binr.astype(np.float32)
    grid[~cmask] = 0.0
    if float(grid.sum()) < 1.0:
        return None

    rot_center = (sw / 2.0, sh / 2.0)
    inner = (((xx - lcx) ** 2 + (yy - lcy) ** 2 <= (half * scale * 0.92) ** 2)
             .astype(np.float32))

    def score(a: float) -> float:
        M = cv2.getRotationMatrix2D(rot_center, float(a), 1.0)
        rot = cv2.warpAffine(grid, M, (sw, sh), flags=cv2.INTER_LINEAR)
        rot *= inner
        return float(rot.sum(axis=0).var() + rot.sum(axis=1).var())

    return score


def _search_peak(score, center: float, search_deg: float,
                 coarse_step: float, fine_step: float) -> Tuple[float, float]:
    """score(a) 를 center±search_deg 에서 coarse->fine->포물선보간으로 최대화.

    반환: (best_angle, best_score).
    """
    coarse = np.arange(center - search_deg, center + search_deg + 1e-9, coarse_step)
    cs = [score(a) for a in coarse]
    ci = int(np.argmax(cs))
    best = float(coarse[ci])

    fine = np.arange(best - coarse_step, best + coarse_step + 1e-9, fine_step)
    fs = [score(a) for a in fine]
    fi = int(np.argmax(fs))
    ang = float(fine[fi])
    peak = float(fs[fi])
    if 0 < fi < len(fine) - 1:
        ym, y0v, yp = fs[fi - 1], fs[fi], fs[fi + 1]
        denom = (ym - 2.0 * y0v + yp)
        if abs(denom) > 1e-9:
            ang += 0.5 * (ym - yp) / denom * fine_step
    return ang, peak


def measure_die_render_angle(image_bgr: np.ndarray,
                             wafer_cx: int, wafer_cy: int, wafer_r: int,
                             *,
                             die_rects: Optional[List[Tuple[int, int, int, int]]] = None,
                             dies: Optional[List[Dict[str, Any]]] = None,
                             grid_method: str = DEFAULT_GRID_METHOD,
                             thickness: int = DEFAULT_DIE_RENDER_THICKNESS,
                             search_deg: float = DEFAULT_DIE_RENDER_SEARCH_DEG,
                             coarse_step: float = DEFAULT_DIE_RENDER_COARSE_STEP,
                             fine_step: float = DEFAULT_DIE_RENDER_FINE_STEP,
                             center: float = 0.0,
                             roi_ratio: float = DEFAULT_DIE_RENDER_ROI_RATIO,
                             max_dim: int = DEFAULT_DIE_RENDER_MAX_DIM
                             ) -> Optional[float]:
    """die 격자(= 모든 die 를 굵기 3 사각형으로 그린 구조)를 후보 각도로 회전하며
    '열/행 투영 주기성(분산)' 이 최대가 되는 각도 = wafer 기울기(deg) 를 잰다.

    ★ V5 고도화: 격자 검출(_prelim_die_rects)에 의존하지 않고 '이미지 픽셀' 만으로
    측정한다(검출 실패해도 각도를 잼). center±search_deg 범위를 탐색.
    die_rects/dies 인자는 하위호환용이며 측정 자체엔 쓰지 않는다.

    반환: 정렬에 적용할 회전각(deg). 신호가 없으면 None.
    """
    score = _grid_projection_score(image_bgr, wafer_cx, wafer_cy, wafer_r,
                                   roi_ratio, max_dim)
    if score is None:
        return None
    ang, _ = _search_peak(score, center, search_deg, coarse_step, fine_step)
    return float(ang)


def _measure_tilt_fft(image_bgr: np.ndarray,
                      wafer_cx: int, wafer_cy: int, wafer_r: int,
                      roi_ratio: float = DEFAULT_DIE_RENDER_ROI_RATIO,
                      max_dim: int = DEFAULT_ANGLE_FFT_MAX_DIM) -> Optional[float]:
    """2D FFT 스펙트럼으로 격자 기울기(=정렬 적용각, [-45,45)) 를 독립 측정.

    die 격자는 2D 주기 패턴이라 진폭 스펙트럼에 격자 축 방향으로 강한 peak 가 생긴다.
    세로/가로 두 축 peak 는 90° 차 → '4배각(4φ)' 합벡터로 모아 위상/4 = 기울기.
    이미지 전체를 반영하므로 projection 과 '독립적인' 교차검증 단서가 된다.
    반환은 projection 과 같은 '적용 회전각' 부호 규약(이미지 y축이 아래라 +1).
    """
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    H, W = gray.shape
    half = max(16, int(round(wafer_r * roi_ratio)))
    x0r, x1r = max(0, wafer_cx - half), min(W, wafer_cx + half)
    y0r, y1r = max(0, wafer_cy - half), min(H, wafer_cy + half)
    roi = gray[y0r:y1r, x0r:x1r]
    if roi.shape[0] < 16 or roi.shape[1] < 16:
        return None
    scale = min(1.0, float(max_dim) / float(max(roi.shape[:2])))
    if scale < 1.0:
        roi = cv2.resize(roi, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    n = min(roi.shape[:2])
    oy = (roi.shape[0] - n) // 2
    ox = (roi.shape[1] - n) // 2
    sq = roi[oy:oy + n, ox:ox + n].astype(np.float32)

    win = np.outer(np.hanning(n), np.hanning(n)).astype(np.float32)
    F = np.fft.fftshift(np.fft.fft2((sq - float(sq.mean())) * win))
    mag2 = (F.real ** 2 + F.imag ** 2)

    c = n // 2
    yy, xx = np.mgrid[:n, :n]
    dx = (xx - c).astype(np.float64)
    dy = (yy - c).astype(np.float64)
    rho = np.sqrt(dx * dx + dy * dy)

    rmin = max(4.0, n * 0.012)
    rmax = n * 0.45
    band = (rho >= rmin) & (rho <= rmax)
    if int(band.sum()) < 16:
        return None
    radial = np.bincount(rho.astype(np.int32)[band].ravel(),
                         weights=mag2[band].ravel(),
                         minlength=int(rmax) + 2)
    if radial.size == 0 or radial.max() <= 0:
        return None
    r_star = float(np.argmax(radial))
    if r_star < rmin:
        r_star = float(rmin + 1)

    ann = (np.abs(rho - r_star) <= max(2.0, r_star * 0.45)) & (rho >= rmin)
    if int(ann.sum()) < 16:
        ann = band
    phi = np.arctan2(dy[ann], dx[ann])
    w = mag2[ann].astype(np.float64)
    vec = np.sum(w * np.exp(1j * 4.0 * phi))
    if float(np.sum(w)) <= 0:
        return None
    tilt = float(np.degrees(np.angle(vec)) / 4.0)
    return float(((tilt + 45.0) % 90.0) - 45.0)   # wrap to [-45,45)


def measure_wafer_angle_robust(image_bgr: np.ndarray,
                               wafer_cx: int, wafer_cy: int, wafer_r: int,
                               *,
                               roi_ratio: float = DEFAULT_DIE_RENDER_ROI_RATIO,
                               max_dim: int = DEFAULT_DIE_RENDER_MAX_DIM,
                               search_deg: float = DEFAULT_DIE_RENDER_SEARCH_DEG,
                               coarse_step: float = DEFAULT_DIE_RENDER_COARSE_STEP,
                               fine_step: float = DEFAULT_DIE_RENDER_FINE_STEP,
                               agree_tol: float = DEFAULT_ANGLE_AGREE_TOL_DEG,
                               full_scan_deg: float = DEFAULT_ANGLE_FULL_SCAN_DEG
                               ) -> Dict[str, Any]:
    """★ 고도화된 각도 측정 : projection(정밀) + FFT(독립) 교차검증으로 견고하게.

    절차
    ----
    1) projection 으로 ±search_deg 정밀 탐색(기본 단서).
    2) FFT 로 기울기를 '독립' 추정([-45,45), 큰 기울기도 잡음).
    3) 두 값이 agree_tol 안에서 일치 → 합의(신뢰↑), projection 채택(정밀).
    4) 불일치/한쪽 실패 → FFT 중심으로 projection 재탐색 + 0° 중심 광역(full_scan)
       재탐색까지 후보로 모아, '투영 peak 점수가 가장 큰' 각을 채택(진짜 격자 정렬).
       => 탐색범위를 벗어난 큰 기울기/이상치에도 조용히 0 으로 실패하지 않는다.

    반환 dict: {angle, confidence, agree, projection, fft, candidates}
    """
    score = _grid_projection_score(image_bgr, wafer_cx, wafer_cy, wafer_r,
                                   roi_ratio, max_dim)
    fft_a = _measure_tilt_fft(image_bgr, wafer_cx, wafer_cy, wafer_r,
                              roi_ratio=roi_ratio)
    if score is None:
        # projection 신호 없음 → FFT 라도 사용
        if fft_a is None:
            return {"angle": 0.0, "confidence": 0.0, "agree": False,
                    "projection": None, "fft": None, "candidates": []}
        return {"angle": float(fft_a), "confidence": 0.45, "agree": False,
                "projection": None, "fft": float(fft_a), "candidates": [fft_a]}

    proj_a, proj_s = _search_peak(score, 0.0, search_deg, coarse_step, fine_step)

    if fft_a is not None and abs(proj_a - fft_a) <= agree_tol:
        # 두 독립 단서 합의 → 가장 신뢰. projection(정밀) 채택.
        return {"angle": float(proj_a), "confidence": 0.97, "agree": True,
                "projection": float(proj_a), "fft": float(fft_a),
                "candidates": [proj_a, fft_a]}

    # 불일치/대각: 여러 후보를 모아 '투영 peak 점수' 가 가장 큰 각을 채택
    cand: List[Tuple[float, float]] = [(proj_a, proj_s)]
    if fft_a is not None:
        rng = max(coarse_step * 3, 1.0)
        cand.append(_search_peak(score, fft_a, rng, coarse_step, fine_step))
    # 0° 중심 광역 스캔(거의 모든 기울기 포함) — 탐색범위 밖 큰 기울기 구제
    cand.append(_search_peak(score, 0.0, full_scan_deg,
                             max(coarse_step * 2, 0.3), fine_step))
    best_a, best_s = max(cand, key=lambda t: t[1])
    agree = bool(fft_a is not None and abs(best_a - fft_a) <= agree_tol)
    conf = 0.9 if agree else 0.6
    return {"angle": float(best_a), "confidence": conf, "agree": agree,
            "projection": float(proj_a),
            "fft": (None if fft_a is None else float(fft_a)),
            "candidates": [c[0] for c in cand]}


def align_wafer_by_die_render(image_bgr: np.ndarray,
                              *,
                              grid_method: str = DEFAULT_GRID_METHOD,
                              thickness: int = DEFAULT_DIE_RENDER_THICKNESS,
                              search_deg: float = DEFAULT_DIE_RENDER_SEARCH_DEG,
                              coarse_step: float = DEFAULT_DIE_RENDER_COARSE_STEP,
                              fine_step: float = DEFAULT_DIE_RENDER_FINE_STEP,
                              roi_ratio: float = DEFAULT_DIE_RENDER_ROI_RATIO,
                              max_dim: int = DEFAULT_DIE_RENDER_MAX_DIM,
                              min_angle_deg: float = DEFAULT_NOTCH_MIN_ANGLE,
                              max_iter: int = DEFAULT_DIE_RENDER_MAX_ITER,
                              return_info: bool = False):
    """die 격자(굵기 3) 투영 주기성 + FFT 교차검증으로 wafer 를 정렬 (반복 수렴).

    매 반복: 현재 이미지에서 robust 측정(projection+FFT) → 누적각으로 '원본'을
    CUBIC 회전(깨짐 없음) → 잔차가 작아지면 종료. 첫 반복 측정값을 신뢰도로 기록.

    return_info=False(기본): (aligned, total)
    return_info=True       : (aligned, total, info)  info={confidence, agree, ...}
    """
    base_cx, base_cy, _ = detect_wafer(image_bgr)
    total = 0.0
    aligned = image_bgr
    info: Dict[str, Any] = {"confidence": 0.0, "agree": False,
                            "projection": None, "fft": None}
    for it in range(max(1, max_iter)):
        cx, cy, r = detect_wafer(aligned)
        res = measure_wafer_angle_robust(
            aligned, cx, cy, r, roi_ratio=roi_ratio, max_dim=max_dim,
            search_deg=search_deg, coarse_step=coarse_step, fine_step=fine_step)
        if it == 0:
            info = res
        delta = float(res.get("angle") or 0.0)
        if abs(delta) < min_angle_deg:
            break
        total += delta
        aligned = _rotate_wafer_keep_size(image_bgr, base_cx, base_cy, total)
    if return_info:
        return aligned, total, info
    return aligned, total


# =============================================================================
# (V2-1) clean_wafer : wafer 원판 밖을 검정으로 (외부 노이즈 제거)  [기능4]
# =============================================================================
def clean_wafer(image_bgr: np.ndarray,
                black_thr: int = 20,
                open_ksize: int = DEFAULT_NOTCH_OPEN_KSIZE) -> np.ndarray:
    """wafer 원판 밖의 모든 픽셀을 검정으로 채워 반환 (외부 노이즈 제거).

    "wafer = 가운데 큰 원, 나머지는 검정" 을 구현. 유지 영역 =
       (가장 큰 연결성분 = wafer 실루엣)  AND  (검출 원판 disc: 중심거리<=r)
    - 실루엣 조건 : 떨어진(detached) 외부 노이즈 제거.
    - disc 조건  : 림에 '연결'되어 원 밖으로 삐져나온 노이즈까지 잘라냄.
    notch(원판의 오목부)는 wafer 소재가 아니므로 자연히 검정 유지(=보존).
    """
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    sil = _wafer_silhouette(gray, black_thr, open_ksize)     # 1=wafer, 0=그외
    cx, cy, r = detect_wafer(image_bgr)
    H, W = gray.shape
    yy, xx = np.ogrid[:H, :W]
    disc = (xx - cx) ** 2 + (yy - cy) ** 2 <= r * r
    keep = (sil > 0) & disc
    out = image_bgr.copy()
    out[~keep] = 0
    return out


# =============================================================================
# (V2-2) detect_notch : wafer '아래쪽' notch + 중심 픽셀점 반환  [기능1]
# =============================================================================
def detect_notch(image_bgr: np.ndarray,
                 wafer_cx: int, wafer_cy: int, wafer_r: int,
                 notch_ref_deg: float = DEFAULT_NOTCH_REF_DEG,
                 sector_deg: float = DEFAULT_NOTCH_SECTOR_DEG,
                 n_angles: int = 14400,
                 min_depth: float = DEFAULT_NOTCH_MIN_DEPTH,
                 noise_margin: float = DEFAULT_NOTCH_NOISE_MARGIN,
                 min_span_deg: float = 0.06,
                 black_thr: int = 20,
                 open_ksize: int = DEFAULT_NOTCH_OPEN_KSIZE,
                 smooth_deg: float = DEFAULT_NOTCH_SMOOTH_DEG
                 ) -> Optional[Tuple[float, Tuple[int, int]]]:
    """wafer 아래쪽(ref±sector_deg) 의 파인 곳(notch) 검출.

    가장자리 오염이 notch 깊이만큼 심한 경우에도, 둘레 깊이를 각도폭 smooth_deg
    로 스무딩(넓은 notch 보존 / 좁은 bite 억제)한 뒤 후보를 찾으므로 robust.

    Returns
    -------
    (angle_err_deg, notch_center_px) 또는 None
      angle_err_deg : 기준 위치(notch_ref_deg, 90=6시) 대비 회전 오차(deg).
      notch_center_px : 파임 구간의 '깊이-가중 중심' 픽셀점 (cx, cy).
                        -> 이 점을 notch 기준점으로 사용.
    """
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    H, W = gray.shape
    sil = _wafer_silhouette(gray, black_thr, open_ksize)

    angs = np.linspace(0.0, 2.0 * np.pi, n_angles, endpoint=False)
    rs = np.linspace(wafer_r * 0.93, wafer_r * 1.015, 200)
    xs = (wafer_cx + rs[None, :] * np.cos(angs)[:, None]).astype(np.int32)
    ys = (wafer_cy + rs[None, :] * np.sin(angs)[:, None]).astype(np.int32)
    np.clip(xs, 0, W - 1, out=xs)
    np.clip(ys, 0, H - 1, out=ys)
    on = sil[ys, xs] > 0
    idx = np.where(on.any(axis=1),
                   on.shape[1] - 1 - np.argmax(on[:, ::-1], axis=1), 0)
    radii = rs[idx]
    depth = np.median(radii) - radii

    # ★ 둘레 깊이 각도 스무딩 (circular moving average):
    #   넓고 매끄러운 notch 는 보존되고, 좁은 가장자리 bite(거칠기)는 평균되어 눌린다.
    #   -> 가장자리 오염이 notch 깊이만큼 심해도 notch 가 가장 깊은 '지속' dip 으로 남음.
    win = max(3, int(round(smooth_deg / 360.0 * n_angles)))
    if win >= 3:
        ker = np.ones(win, dtype=np.float64) / win
        padded = np.concatenate([depth[-win:], depth, depth[:win]])
        depth = np.convolve(padded, ker, mode="same")[win:win + n_angles]

    # 아래쪽 sector(ref±sector_deg) 안에서만 notch 후보를 찾는다.
    degs = np.degrees(angs)
    in_sector = np.abs(((degs - notch_ref_deg + 180.0) % 360.0) - 180.0) <= sector_deg
    above = np.where((depth > min_depth) & in_sector)[0]
    if len(above) == 0:
        return None
    clusters: List[List[int]] = [[above[0]]]
    for v in above[1:]:
        if v - clusters[-1][-1] <= 2:
            clusters[-1].append(v)
        else:
            clusters.append([v])
    clusters = [c for c in clusters
                if (c[-1] - c[0]) * 360.0 / n_angles >= min_span_deg]
    if not clusters:
        return None
    cand = max(clusters, key=lambda c: float(depth[c].sum()))

    # 적응형 임계(가산형) : 노이즈 floor 는 sector '밖' 둘레에서 추정.
    #   곱셈형(floor*k)은 floor 가 커지면 임계가 과도하게 올라가 진짜 notch 를
    #   놓치므로, floor + margin 으로 안정화한다.
    noise_floor = float(np.percentile(depth[~in_sector], 99.5)) if (~in_sector).any() else 0.0
    eff_thr = max(min_depth, noise_floor + noise_margin)
    d = depth[cand]
    if float(d.max()) < eff_thr:
        return None

    a = angs[cand]
    notch_deg = math.degrees(math.atan2(float((np.sin(a) * d).sum()),
                                        float((np.cos(a) * d).sum()))) % 360.0
    err = ((notch_deg - notch_ref_deg + 180.0) % 360.0) - 180.0
    # 중심 픽셀점 : 파임 경계점(cx+radii*cos, ...)을 깊이로 가중 평균
    bx = wafer_cx + radii[cand] * np.cos(a)
    by = wafer_cy + radii[cand] * np.sin(a)
    cxp = int(round(float((bx * d).sum() / d.sum())))
    cyp = int(round(float((by * d).sum() / d.sum())))
    return err, (cxp, cyp)


# =============================================================================
# (V2-3) measure_die_grid_angle : die 격자 기울기 독립 측정  [기능2]
# =============================================================================
def measure_die_grid_angle(image_bgr: np.ndarray,
                           wafer_cx: int, wafer_cy: int, wafer_r: int,
                           search_deg: float = DEFAULT_GRID_ANGLE_RANGE,
                           coarse_step: float = 0.2,
                           fine_step: float = 0.02,
                           roi_ratio: float = 0.45) -> float:
    """die 격자(세로 sawline)를 '진짜 수직'으로 만드는 회전각 = 격자 기울기(deg).

    notch 와 무관하게 die 무늬만으로 각도를 독립 측정 -> notch 각도 교차검증용.
    중앙 ROI 를 후보 각도로 역회전 후, 세로 edge(|Sobel_x|) 열-프로파일의 분산이
    최대가 되는 각도를 찾는다(격자가 수직이면 열 프로파일이 가장 뾰족 = 분산 최대).
    coarse -> fine 2단계 탐색.
    """
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY).astype(np.float32)
    half = int(wafer_r * roi_ratio)
    y0, y1 = max(0, wafer_cy - half), min(gray.shape[0], wafer_cy + half)
    x0, x1 = max(0, wafer_cx - half), min(gray.shape[1], wafer_cx + half)
    roi = gray[y0:y1, x0:x1]
    ch, cw = roi.shape[0] / 2.0, roi.shape[1] / 2.0

    def sharpness(a: float) -> float:
        M = cv2.getRotationMatrix2D((cw, ch), a, 1.0)
        rot = cv2.warpAffine(roi, M, (roi.shape[1], roi.shape[0]), flags=cv2.INTER_NEAREST)
        sx = np.abs(cv2.Sobel(rot, cv2.CV_32F, 1, 0, ksize=3))
        return float(sx.mean(axis=0).var())     # 세로 edge 열-프로파일 분산

    coarse = np.arange(-search_deg, search_deg + 1e-9, coarse_step)
    best = max(coarse, key=sharpness)
    fine = np.arange(best - coarse_step, best + coarse_step + 1e-9, fine_step)
    return float(max(fine, key=sharpness))


# =============================================================================
# (V2-4) validate_quadrant_edges : 4분면 가장자리 맵 검증  [기능3]
# =============================================================================
def validate_quadrant_edges(dies: List[Dict[str, Any]],
                            wafer_cx: int, wafer_cy: int, wafer_r: int,
                            balance_tol: float = DEFAULT_QUAD_BALANCE_TOL) -> Dict[str, Any]:
    """center corner 에서 확장한 die 맵이 4분면(TL/TR/BL/BR) 가장자리까지
    균형 있게 채워졌는지 검증.

    각 분면별로 die 중심의 최대 도달거리/wafer_r = coverage 를 계산하고,
    4분면 coverage 편차가 balance_tol 이내면 balanced=True (정상적으로 채워짐).
    한 분면만 짧으면 그쪽 맵 생성이 잘못된 것.
    """
    quad: Dict[str, List[float]] = {"TR": [], "TL": [], "BL": [], "BR": []}
    edge: Dict[str, int] = {"TR": 0, "TL": 0, "BL": 0, "BR": 0}
    for d in dies:
        dx = d["center_px"][0] - wafer_cx
        dy = d["center_px"][1] - wafer_cy
        key = ("T" if dy < 0 else "B") + ("R" if dx > 0 else "L")
        quad[key].append(math.hypot(dx, dy))
        if d.get("is_edge"):
            edge[key] += 1

    per: Dict[str, Dict[str, Any]] = {}
    covs = []
    for k, arr in quad.items():
        if arr:
            cov = max(arr) / float(wafer_r)
            per[k] = {"n_dies": len(arr), "max_dist": round(max(arr), 1),
                      "coverage": round(cov, 4), "edge_dies": edge[k]}
            covs.append(cov)
        else:
            per[k] = {"n_dies": 0, "max_dist": 0.0, "coverage": 0.0, "edge_dies": 0}
            covs.append(0.0)
    spread = (max(covs) - min(covs)) if covs else 1.0
    balanced = bool(spread <= balance_tol and min(covs) > 0.8)
    return {"per_quadrant": per,
            "coverage_spread": round(spread, 4),
            "balanced": balanced,
            "min_coverage": round(min(covs), 4) if covs else 0.0}


# =============================================================================
# [SECTOR: 50_GRID_ORIGIN_REFINEMENT] phase matching과 street 기반 origin 정밀 보정
# (0.9) ★ grid origin 서브픽셀 보정 — phase folding + half-max 교차점 중점
#
# 왜 필요한가
# -----------
# detect_corner_grid 는 street(die 사이 흰 여백) band 의 **밝기 무게중심** 을 origin
# 으로 잡는다:
#       center = Σ(i * profile[i]) / Σ profile[i]
# 그런데 무게중심은 좌/우(상/하) die 의 밝기가 다르거나 threshold 가 한쪽만 더
# 잘라내면 **밝은 쪽으로 끌려간다**. 그래서 실제 이미지에서 origin 이 street 십자
# 교차점의 진짜 중심에서 살짝 벗어난다(사용자가 그린 '검은 점').
#
# 어떻게 고치나
# -------------
#  1) phase folding : 중앙 ROI 의 열/행 프로파일을 pitch 주기로 접어 한 주기 평균
#     단면을 만든다. 수십 개 주기를 평균하므로 개별 die 얼룩/노이즈가 사라진다.
#  2) half-max 교차점 : street 단면의 좌/우 half-max 교차점을 선형보간(서브픽셀)으로
#     찾아 그 **중점** 을 중심으로 쓴다. 교차점은 street 의 가파른 경사면 위에 있고,
#     좌/우 plateau(=die 내부 밝기) 로 half 레벨을 **각각 따로** 잡으므로
#     한쪽 die 가 밝아도 교차점 위치가 밀리지 않는다 → 무게중심의 편향 제거.
#  3) 부산물 : 두 교차점 간격 = **street 실제 폭**. 이것을 street_w/street_h 로
#     노출하면 "여백만큼 die 를 잘라내기"(exclude_street) 도 바로 된다.
#
# V5.3 — 실제 이미지의 '검은 노이즈 범벅 street' 대응
# ---------------------------------------------------
# 실측 결과 위 half-max 방식만으로는 아래 두 가지가 깨졌다.
#
#  (a) [버그] 좌표계 half-pixel 오차 — 약 -1.0 px 상수 편향
#      · profile[i] 는 픽셀 i 의 평균이므로 연속좌표 중심은 i+0.5 이고,
#      · fold 의 bin b 는 phase 구간 [b, b+1) 이므로 대표 위치는 b+0.5 다.
#      두 군데 모두 0.5 를 빠뜨려 깨끗한 이미지에서도 정확히 1 px 밀렸다.
#
#  (b) street 안쪽이 '균일한 밝은 색' 이 아니라 **한쪽(위/왼쪽)이 검은 노이즈로
#      덮여 die 밝기까지 내려가는** 실제 조건. half-max 레벨이 그 검은 띠보다
#      위에 있어서 교차점 탐색이 street 절반에서 멈춘다
#      → 중심이 밝은 쪽으로 밀리고 street 폭도 절반으로 측정된다.
#
# 대응 (모두 실측으로 선택)
#  1) half-pixel 보정 : 위 (a) 를 그대로 고친다.
#  2) **상위 percentile 투영** : 직교 방향으로 평균 대신 상위 백분위수를 쓴다.
#     오염(노이즈)은 street 를 '어둡게' 만들 뿐이므로, 같은 street 선 위에서
#     덜 오염된 픽셀을 골라내면 street 단면이 원래 밝기로 복원된다.
#     안전한 백분위수는 street 점유율에 달려 있으므로 **1차 패스(평균)로
#     폭을 먼저 재고 그 값으로 백분위수를 자동 결정** 한다.
#  3) **적응형 레벨 스윕** : 레벨비 alpha 를 0.50 → 0.12 로 낮춰가며 재고,
#     폭이 갑자기 튀기(=옆 구조물을 삼킴) 직전 값을 채택한다.
#     검은 띠가 있으면 낮은 alpha 라야 street 전체를 덮고,
#     밝은 rim 이 있으면 낮은 alpha 에서 폭이 급증하므로 자동으로 걸러진다.
#  4) 교차점은 창 안에서 **가장 바깥쪽** 것을 쓴다(street 내부 dip 에 안 멈춤).
#  5) 실패/비상식적 결과는 전부 폐기하고 원래 origin 을 그대로 둔다
#     → 보정이 기존보다 나빠지는 일은 없다.
# =============================================================================
# 적응형 레벨 스윕에 쓰는 레벨비(peak 대비). 큰 값 → 작은 값 순서여야 한다.
_REFINE_ALPHAS: Tuple[float, ...] = (0.50, 0.44, 0.38, 0.33, 0.28,
                                     0.24, 0.20, 0.17, 0.14, 0.12)
# 인접 alpha 사이에서 폭이 이 배율 이상 뛰면 '옆 구조물을 삼켰다' 로 보고 중단
_REFINE_WIDTH_JUMP = 1.45
# street 폭이 pitch 의 이 비율을 넘으면 신뢰하지 않는다
_REFINE_WIDTH_MAX_RATIO = 0.5
# ★[V5.3] street 다발 내부의 어두운 틈은 이 비율(주기 대비)까지 같은 구조물로 본다.
# 그보다 긴 저지대는 die 내부이므로 거기서 멈춰 이웃 구조물 흡수를 막는다.
_REFINE_GAP_RATIO = 0.05
# ★[V5.3] robust 2-pass 가 1-pass 보다 이 배율 넘게 넓어지면 다른 구조물을 잡은 것
_REFINE_ROBUST_MAX_JUMP = 2.5


def _fold_profile(profile: np.ndarray, origin: float,
                  pitch: float, nbins: int) -> Optional[np.ndarray]:
    """profile 을 pitch 주기로 접어(fold) 한 주기 평균 단면을 만든다.

    profile[i] 는 픽셀 i 의 평균이므로 **연속좌표 중심은 i + 0.5** 다.
    반환 배열의 bin 0 은 phase 구간 [0, 1) bin (= 현재 origin 부터 한 bin) 이다.
    """
    n = int(profile.size)
    if pitch <= 1.0 or nbins < 8 or n < nbins * 2:
        return None
    pos = np.arange(n, dtype=np.float64) + 0.5          # ★ half-pixel 보정
    phase = np.mod(pos - float(origin), float(pitch)) / float(pitch)   # 0 ~ 1
    bins = np.minimum((phase * nbins).astype(np.int64), nbins - 1)
    total = np.bincount(bins, weights=profile.astype(np.float64), minlength=nbins)
    count = np.bincount(bins, minlength=nbins).astype(np.float64)
    if float(count.min()) <= 0.0:          # 빈 bin 이 있으면 평균이 왜곡된다
        return None
    return total / count


def _level_cross(g: np.ndarray, p: int, level: float, step: int) -> Optional[float]:
    """peak index p 에서 step(-1/+1) 방향 level 통과점을 선형보간.

    street 내부의 검은 노이즈 dip 에서 멈추면 안 되므로 첫 교차점이 아니라
    **가장 바깥쪽** 교차점을 돌려준다. 다만 반주기를 통째로 훑으면 이웃
    구조물(die 내부 배선 등)까지 삼키므로, level 아래가 gap_tol bin 넘게
    이어지면 die 내부로 보고 거기서 멈춘다.
    반환값은 순환하지 않는 연속 좌표라서 음수/n 이상이 될 수 있다(중점·폭 전용).
    """
    n = int(g.size)
    gap_tol = max(2, int(round(n * _REFINE_GAP_RATIO)))
    found: Optional[float] = None
    below = 0
    for k in range(1, n // 2 + 1):
        i_out = (p + step * k) % n
        i_in = (p + step * (k - 1)) % n
        v_out, v_in = float(g[i_out]), float(g[i_in])
        if v_out <= level <= v_in:
            denom = v_in - v_out
            t = 0.0 if abs(denom) < 1e-12 else (v_in - level) / denom
            found = float(p + step * (k - 1 + t))
        if v_out < level:
            below += 1
            if below > gap_tol:
                break
        else:
            below = 0
    return found


def _street_center_at(folded: np.ndarray, alpha: float
                      ) -> Optional[Tuple[float, float]]:
    """레벨비 alpha 하나로 street 의 (중심 offset, 폭) 을 bin 단위로 구한다."""
    n = int(folded.size)
    if n < 8:
        return None

    c = n // 2
    g = np.roll(folded.astype(np.float64), c)      # bin 0 을 배열 한가운데로

    # street 이 밝은 선인지 어두운 골인지 자동 판정 후, 항상 'peak' 로 통일한다.
    w = max(2, int(round(n * 0.25)))
    lo, hi = max(0, c - w), min(n, c + w + 1)
    win = g[lo:hi]
    med = float(np.median(g))
    if (float(win.max()) - med) < (med - float(win.min())):
        g = -g

    p = lo + int(np.argmax(g[lo:hi]))
    peak = float(g[p])

    # ★ 좌/우 plateau(die 내부) 를 따로 측정 → 좌우 밝기 차이로 인한 편향 제거
    q = max(1, int(round(n * 0.12)))
    far = max(q + 2, int(round(n * 0.45)))
    left = np.take(g, np.arange(p - far, p - q), mode="wrap")
    right = np.take(g, np.arange(p + q + 1, p + far), mode="wrap")
    if left.size == 0 or right.size == 0:
        return None
    base_l = float(np.percentile(left, 20))
    base_r = float(np.percentile(right, 20))
    if peak - max(base_l, base_r) <= 1e-9:         # street 대비가 없다 → 포기
        return None

    xl = _level_cross(g, p, base_l + alpha * (peak - base_l), -1)
    xr = _level_cross(g, p, base_r + alpha * (peak - base_r), +1)
    if xl is None or xr is None:
        return None

    width = xr - xl
    if width <= 0.0:
        return None
    return (0.5 * (xl + xr) - c, width)


def _street_center_from_folded(folded: np.ndarray
                               ) -> Optional[Tuple[float, float]]:
    """적응형 레벨 스윕으로 street 의 (중심 offset, 폭) 을 서브픽셀로 구한다.

    alpha 를 높은 값부터 낮춰가며 잰다. 검은 노이즈에 덮인 street 는 alpha 를
    낮춰야 전체가 잡히고, 밝은 rim 은 alpha 를 낮추면 폭이 **급증** 하므로
    직전 값에서 멈추면 둘 다 자동으로 처리된다.

    Returns
    -------
    (center_offset_bin, width_bin) — bin 단위. 실패하면 None.
        center_offset_bin 은 '현재 origin 대비' 얼마나 움직여야 하는지(부호 포함).
    """
    n = int(folded.size)
    best: Optional[Tuple[float, float]] = None
    for alpha in _REFINE_ALPHAS:
        got = _street_center_at(folded, alpha)
        if got is None:
            break
        if got[1] > n * _REFINE_WIDTH_MAX_RATIO:       # 주기의 절반 초과 → 폐기
            break
        if best is not None and got[1] > best[1] * _REFINE_WIDTH_JUMP:
            break                                       # 옆 구조물을 삼켰다
        best = got
    return best


# -----------------------------------------------------------------------------
# grid phase 결정 (die 사이 간격이 없는 wafer 대응)
# -----------------------------------------------------------------------------
# street(톱길)이 뚜렷한 wafer 는 '주기 안에서 가장 강한 구조물 = die 경계' 가
# 성립한다. 그런데 die 가 간격 없이 맞붙어 있는 wafer 에서는 die 경계가 얇은
# seal-ring 한 줄뿐이고, die 내부의 배선 다발이 훨씬 밝고 넓다. 이때 위 가정은
# 깨지고 origin 이 정확히 half-pitch 만큼 밀린다.
#
# 판별 근거: die 경계 구조물(seal ring / saw lane)은 x·y 가 같은 설계 규칙에서
# 나오므로 **폭이 서로 비슷하다**. 반면 die 내부 배선은 축마다 폭이 제각각이다.
# 따라서 축마다 phase 후보를 몇 개 뽑아 폭을 재고, |w_x - w_y| 가 최소인 조합을
# 고른다. street 이 뚜렷한 wafer 에서는 1순위 후보가 이미 최적이라 무동작이다.
# ★[claude] '재앵커링만 유지' — resolve_grid_phase 도 기본 OFF.
DEFAULT_PHASE_MATCH = False
_PHASE_TOP_K = 3          # 축마다 검사할 phase 후보 수
_PHASE_MIN_GAIN = 2.0     # 폭 불일치가 이 배수 이상 줄어야 phase 를 바꾼다
_PHASE_SEP_RATIO = 0.15   # 후보끼리 최소 이만큼(주기 대비) 떨어져야 한다
_PHASE_WIN_RATIO = 0.08   # 후보 봉우리를 찾을 국소 창 (주기 대비)
_PHASE_ALPHA = 0.25       # 구조물 외곽을 재는 레벨비


def _phase_peaks(folded: np.ndarray, top_k: int) -> List[int]:
    """folded profile 에서 서로 떨어진 '구조물' 후보 bin 을 강한 순으로 고른다."""
    n = int(folded.size)
    g = folded.astype(np.float64)
    dev = np.abs(g - float(np.median(g)))          # 밝은 선/어두운 골 모두 후보
    sep = max(2, int(round(n * _PHASE_SEP_RATIO)))
    picked: List[int] = []
    for b in np.argsort(dev)[::-1]:
        b = int(b)
        if all(min(abs(b - p), n - abs(b - p)) >= sep for p in picked):
            picked.append(b)
            if len(picked) >= top_k:
                break
    return picked


def _phase_measure(folded: np.ndarray, b: int
                   ) -> Optional[Tuple[float, float]]:
    """후보 bin b 에 있는 구조물의 (중심 offset bin, 전체 폭 bin).

    _street_center_from_folded 는 탐색창이 주기의 ±25% 라 어느 후보를 넣어도
    가장 강한 구조물로 끌려간다. phase 비교에는 후보 '자기 자신' 의 폭이
    필요하므로 봉우리는 좁은 창에서 찾고, 폭은 외곽까지 넓게 잰다.
    """
    n = int(folded.size)
    c = n // 2
    g = np.roll(folded.astype(np.float64), c - b)   # 후보를 배열 한가운데로
    med = float(np.median(g))
    w = max(2, int(round(n * _PHASE_WIN_RATIO)))
    lo, hi = c - w, c + w + 1
    win = g[lo:hi]
    if (float(win.max()) - med) < (med - float(win.min())):
        g = -g                                      # 어두운 골 -> 봉우리로 통일
    p = lo + int(np.argmax(g[lo:hi]))
    peak = float(g[p])
    base = float(np.percentile(g, 20))              # die 내부 = 다수파
    if peak - base <= 1e-9:
        return None

    level = base + _PHASE_ALPHA * (peak - base)
    xl = _level_cross(g, p, level, -1)
    xr = _level_cross(g, p, level, +1)
    if xl is None or xr is None or xr <= xl:
        return None
    return (0.5 * (xl + xr) - c, xr - xl)


def _phase_options(folded: np.ndarray, pitch: float
                   ) -> List[Tuple[float, float]]:
    """후보별 (origin 대비 중심 이동량 px, 측정된 폭 px) 목록. 강한 순."""
    n = int(folded.size)
    scale = float(pitch) / n
    out: List[Tuple[float, float]] = []
    for b in _phase_peaks(folded, _PHASE_TOP_K):
        got = _phase_measure(folded, b)
        if got is None:
            continue
        centre = (b + got[0] + 0.5) * scale
        if centre > float(pitch) * 0.5:            # 가장 가까운 등가 위치로
            centre -= float(pitch)
        out.append((centre, got[1] * scale))
    return out


def resolve_grid_phase(image_bgr: np.ndarray,
                       wafer_cx: int, wafer_cy: int, wafer_r: int,
                       pitch_x: float, pitch_y: float,
                       x0: float, y0: float,
                       *,
                       roi_periods: int = DEFAULT_REFINE_ROI_PERIODS
                       ) -> Dict[str, Any]:
    """die 경계 phase 를 x·y 폭 일치도로 고른다.

    Returns
    -------
    dict
        {"x0","y0"           : 선택된 origin,
         "dx","dy"           : 원 origin 대비 이동량 (px),
         "street_w","street_h": 그 phase 에서 잰 경계 폭 (px),
         "phase_matched"     : phase 를 바꿨으면 True}
    """
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY).astype(np.float32)
    H, W = gray.shape[:2]

    def _opts(pitch: float, origin: float, is_x: bool) -> List[Tuple[float, float]]:
        if pitch <= 1.0:
            return []
        half = int(max(pitch * 1.5,
                       min(float(wafer_r) * 0.55, pitch * roi_periods * 0.5)))
        x1, x2 = max(int(wafer_cx) - half, 0), min(int(wafer_cx) + half, W)
        y1, y2 = max(int(wafer_cy) - half, 0), min(int(wafer_cy) + half, H)
        roi = gray[y1:y2, x1:x2]
        if roi.size == 0:
            return []
        profile = roi.mean(axis=0 if is_x else 1)
        nbins = int(round(pitch))
        folded = _fold_profile(profile, float(origin) - (x1 if is_x else y1),
                               float(pitch), nbins)
        if folded is None:
            return []
        return _phase_options(folded, float(pitch))

    res: Dict[str, Any] = {"x0": float(x0), "y0": float(y0),
                           "dx": 0.0, "dy": 0.0,
                           "street_w": 0.0, "street_h": 0.0,
                           "phase_matched": False}
    ox, oy = _opts(float(pitch_x), float(x0), True), _opts(float(pitch_y), float(y0), False)
    if not ox or not oy:
        return res

    res["street_w"], res["street_h"] = ox[0][1], oy[0][1]
    base_gap = abs(ox[0][1] - oy[0][1])
    gap, bx, by = min(((abs(a[1] - b[1]), a, b) for a in ox for b in oy),
                      key=lambda t: t[0])
    if gap * _PHASE_MIN_GAIN < base_gap:
        res.update({"x0": float(x0) + bx[0], "y0": float(y0) + by[0],
                    "dx": bx[0], "dy": by[0],
                    "street_w": bx[1], "street_h": by[1],
                    "phase_matched": True})
    return res


def refine_grid_origin(image_bgr: np.ndarray,
                       wafer_cx: int, wafer_cy: int, wafer_r: int,
                       pitch_x: float, pitch_y: float,
                       x0: float, y0: float,
                       *,
                       roi_periods: int = DEFAULT_REFINE_ROI_PERIODS,
                       max_shift_ratio: float = DEFAULT_REFINE_MAX_SHIFT_RATIO,
                       robust_projection: bool = DEFAULT_REFINE_ROBUST
                       ) -> Dict[str, Any]:
    """grid origin 을 street 십자 교차점의 '진짜' 중심으로 서브픽셀 보정한다.

    Parameters
    ----------
    x0, y0 : detect_grid 가 준 대략적인 origin. street 위(±pitch*max_shift_ratio 이내)
             에 있다고 가정한다. 그보다 멀면 보정을 포기하고 원값을 그대로 돌려준다
             (= die 인덱스가 통째로 밀리는 사고를 막는다).
    robust_projection :
        True 면 2-pass 로 동작한다. 1차는 평균 투영으로 street 폭을 대충 재고,
        그 폭으로 **상위 percentile 투영** 값을 자동 결정해 2차를 돌린다.
        street 한쪽이 검은 노이즈로 덮여 있어도 덜 오염된 픽셀만 골라내므로
        단면이 원래 밝기로 복원된다. 2차가 실패하면 1차 결과를 쓴다.
        False 면 평균 투영 1-pass (V5.2 동작).

    Returns
    -------
    dict
        {"x0", "y0"          : 보정된 origin (float),
         "street_w","street_h": 측정된 street 폭/높이 (px, 0 = 실패),
         "shift_x","shift_y" : 보정으로 움직인 양 (px),
         "percentile_x","percentile_y" : 실제 사용한 투영 백분위수 (0 = 평균),
         "refined"           : 한 축이라도 보정됐으면 True}
    """
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY).astype(np.float32)
    H, W = gray.shape[:2]

    def _once(pitch: float, origin: float, is_x: bool, pct: Optional[float]
              ) -> Optional[Tuple[float, float]]:
        """투영 방식 하나로 (shift_px, width_px) 를 구한다."""
        half = int(max(pitch * 1.5,
                       min(float(wafer_r) * 0.55, pitch * roi_periods * 0.5)))
        x1, x2 = max(int(wafer_cx) - half, 0), min(int(wafer_cx) + half, W)
        y1, y2 = max(int(wafer_cy) - half, 0), min(int(wafer_cy) + half, H)
        roi = gray[y1:y2, x1:x2]
        if roi.size == 0:
            return None
        # 축에 직교하는 방향으로 투영 → 그 축의 street 단면만 남는다
        axis = 0 if is_x else 1
        profile = (roi.mean(axis=axis) if pct is None
                   else np.percentile(roi, float(pct), axis=axis))
        base = x1 if is_x else y1

        nbins = int(round(pitch))
        folded = _fold_profile(profile, float(origin) - base, float(pitch), nbins)
        if folded is None:
            return None
        found = _street_center_from_folded(folded)
        if found is None:
            return None

        scale = float(pitch) / nbins            # bin -> px
        # ★ bin b 의 대표 위치는 b + 0.5 → half-bin 보정
        shift = (found[0] + 0.5) * scale
        width = found[1] * scale
        if abs(shift) > float(pitch) * max_shift_ratio:
            return None                          # 옆 street 를 잡은 듯 → 보정 포기
        if width < 1.0 or width > float(pitch) * _REFINE_WIDTH_MAX_RATIO:
            return None
        return (shift, width)

    def _axis(pitch: float, origin: float, is_x: bool
              ) -> Optional[Tuple[float, float, float]]:
        if pitch <= 1.0:
            return None
        first = _once(pitch, origin, is_x, None)      # 1-pass: 평균 투영
        if first is None or not robust_projection:
            return None if first is None else (first[0], first[1], 0.0)

        # street 점유율이 클수록 안전한 백분위수는 낮아진다.
        # 1차 폭이 과소평가될 수 있으므로 1.6 배 여유 + 5 %p 마진을 둔다.
        fill = min(0.45, max(0.02, first[1] / float(pitch)))
        pct = float(np.clip(100.0 - 100.0 * fill * 1.6 - 5.0, 55.0, 85.0))
        second = _once(pitch, origin, is_x, pct)      # 2-pass: 상위 percentile
        if second is None:
            return (first[0], first[1], 0.0)
        # ★[V5.3] 2-pass 는 '같은 street 를 더 또렷하게' 보려는 것이다. 검은 노이즈에
        # 덮인 street 라면 폭이 최대 2 배 남짓 복원되고 중심도 그 안에서 움직인다.
        # 그 범위를 벗어났다면 percentile 이 die 내부 밝은 노이즈를 끌어올려 엉뚱한
        # 구조물을 잡은 것이므로 1-pass 결과를 유지한다.
        if (abs(second[0] - first[0]) > max(1.0, first[1])
                or second[1] > first[1] * _REFINE_ROBUST_MAX_JUMP):
            return (first[0], first[1], 0.0)
        return (second[0], second[1], pct)

    out: Dict[str, Any] = {"x0": float(x0), "y0": float(y0),
                           "street_w": 0.0, "street_h": 0.0,
                           "shift_x": 0.0, "shift_y": 0.0,
                           "percentile_x": 0.0, "percentile_y": 0.0,
                           "refined": False}
    rx = _axis(float(pitch_x), float(x0), True)
    ry = _axis(float(pitch_y), float(y0), False)
    if rx is not None:
        out["shift_x"], out["street_w"], out["percentile_x"] = rx
        out["x0"] = float(x0) + rx[0]
    if ry is not None:
        out["shift_y"], out["street_h"], out["percentile_y"] = ry
        out["y0"] = float(y0) + ry[0]
    out["refined"] = bool(rx is not None or ry is not None)
    return out


# =============================================================================
# [SECTOR: 60_DIE_MAP_BUILD_API] build_die_map() — wafer 이미지에서 전체 die map 생성
# (1) wafer 이미지 -> Die Map (EDGE 포함)
# =============================================================================
def build_die_map(image: Union[str, Path, np.ndarray],
                  *,
                  grid_method: str = DEFAULT_GRID_METHOD,
                  min_pitch: Optional[int] = None,
                  max_pitch: Optional[int] = None,
                  cross_line_w: int = DEFAULT_CROSS_LINE_W,
                  cross_sigma_k: float = _CROSS_SIGMA_K,
                  origin_mode: str = DEFAULT_ORIGIN_MODE,
                  cross_origin_mode: str = DEFAULT_CROSS_ORIGIN_MODE,
                  thin_width_max: int = DEFAULT_THIN_WIDTH_MAX,
                  thin_roi_half: Optional[int] = DEFAULT_THIN_ROI_HALF,
                  pixel_per_unit: int = DEFAULT_PIXEL_PER_UNIT,
                  include_edge: bool = True,
                  edge_margin: float = DEFAULT_EDGE_MARGIN,
                  edge_clip_all: bool = DEFAULT_EDGE_CLIP_ALL,
                  edge_overlap_min_px: float = DEFAULT_EDGE_OVERLAP_MIN_PX,
                  refine_origin: bool = DEFAULT_REFINE_ORIGIN,
                  phase_match: bool = DEFAULT_PHASE_MATCH,
                  exclude_street: bool = DEFAULT_EXCLUDE_STREET,
                  die_template_path: Optional[str] = None,
                  with_crops: bool = False,
                  border_mode: str = "pad",
                  offset_x: int = DEFAULT_OFFSET_X,
                  offset_y: int = DEFAULT_OFFSET_Y,
                  margin_x: int = DEFAULT_MARGIN_X,
                  margin_y: int = DEFAULT_MARGIN_Y,
                  notch_align: bool = DEFAULT_NOTCH_ALIGN,
                  notch_ref_deg: float = DEFAULT_NOTCH_REF_DEG,
                  angle_align_method: str = DEFAULT_ANGLE_ALIGN_METHOD,
                  edge_mode: str = DEFAULT_EDGE_MODE,
                  clean: bool = DEFAULT_CLEAN_WAFER,
                  notch_sector_deg: float = DEFAULT_NOTCH_SECTOR_DEG,
                  verify_angle: bool = True,
                  verify_tol_deg: float = DEFAULT_VERIFY_TOL_DEG) -> WaferDieMap:
    """wafer 이미지 한 장 -> 전체 die map (EDGE die 포함). [V5]

    처리 순서: clean(외부노이즈 제거) -> 회전 보정(기본 die_render) -> notch 중심점 ->
               die 격자 -> die map(+edge 플래그) -> angle 검증 -> 4분면 검증.

    Parameters
    ----------
    image            : wafer 이미지 경로(str/Path) 또는 BGR ndarray
    grid_method      : 격자 검출 방식 ★[V5.4] "auto"(기본) | "cross" | "corner" |
                       "hybrid" | "std" | "color".
                       "auto"  = 1채널/약신호면 cross(십자) 먼저, 컬러면 corner 먼저.
                                 하나가 실패하면 다른 쪽이 받아준다.
                       "cross" = 폭 1~2px 의 얇은 십자(十) 교차점만 잡는 검출기.
                                 넓은 세로 노이즈를 구조적으로 배제하고, pitch 는
                                 십자 점의 좌우 이웃 간격->x, 위아래 간격->y 로 뽑는다.
    min_pitch/max_pitch : ★[V5.4] die pitch 탐색 범위(px). None(기본)이면 자동
                       (1채널/작은 영상 → 30~70, 기존 10000px 컬러 → 종전 50~).
    cross_line_w     : ★[V5.4] 십자 선 두께 상한(px, 기본 2). 이보다 넓은 것은
                       노이즈로 보고 버린다. 세로 노이즈 배제의 핵심 파라미터.
    cross_sigma_k    : ★[V5.4] 십자 응답 임계(robust sigma 배수, 기본 2.5).
                       신호가 더 약하면 낮추고, 오검출이 많으면 올린다.
    pixel_per_unit   : 실측 좌표 환산 (px/unit)
    include_edge     : True 면 웨이퍼 원 안 die 전부 포함(가장자리 잘린 die 포함).
    edge_margin      : die 포함 판정에 쓰는 유효 반지름 = r * edge_margin.
    edge_clip_all    : ★ True(기본) 면 'die 사각형이 wafer 원과 겹치기만 하면' 전부
                       die 로 만들어 clip 한다(중심이 원 밖이어도 포함).
                       False 면 기존 방식(=die '중심'이 원 안일 때만 포함).
                       중심 기준일 때 빠지던 최외곽 EDGE die 누락을 없앤다.
    edge_overlap_min_px : ★ 포함에 필요한 최소 겹침 깊이(px, edge_clip_all=True 일 때).
                       0.0(기본)=1px 라도 겹치면 포함. 값을 키우면 경계를 살짝만
                       스치는 '거의 빈' die 를 제외한다(예: 20 → 20px 이상 걸친 것만).
    refine_origin    : ★ True(기본) 면 grid origin 을 street 십자 교차점의 '진짜'
                       중심으로 서브픽셀 보정한다(phase folding + half-max 교차점 중점).
                       기존 '밝기 무게중심' origin 은 좌/우 die 밝기가 다르면 밝은 쪽으로
                       끌려가 살짝 쉬프트된다. 이 보정이 그 편향을 없앤다.
                       부산물로 street(die 사이 여백) 폭도 함께 측정된다.
    phase_match      : ★[V5.3] True(기본) 면 die 경계 phase 를 x·y 폭 일치도로 고른다.
                       die 가 간격 없이 맞붙은 wafer 는 die 내부 배선이 die 경계보다
                       더 밝고 넓어서 origin 이 정확히 half-pitch 밀린다. die 경계는
                       x·y 가 같은 설계 규칙이라 폭이 비슷하다는 성질로 이를 되돌린다.
                       street 이 뚜렷한 wafer 에서는 무동작(1순위 후보가 이미 정답).
    exclude_street   : ★ True 면 rect_px/crop 을 측정된 street 폭만큼 안쪽으로 줄여
                       '순수 die' 영역만 남긴다(이웃 street 가 테두리에 안 묻음).
                       street 를 못 쟀으면(=0) 자동으로 아무 것도 안 한다.
                       refine_origin=False 면 street 측정이 없으므로 무시된다.
    die_template_path: (옵션) die_sample 이미지로 격자 보정.
    with_crops       : True 면 각 die entry 에 "image"(crop) 포함.
    border_mode      : with_crops 시 clip 방식 "pad" | "crop".
    offset_x/offset_y, margin_x/margin_y : crop 위치보정 / 영역확장 (px).
    notch_align      : True(기본) 면 angle_align_method 로 회전(angle) 보정.
    notch_ref_deg    : notch 의 정상 위치 (90 = 아래쪽/6시 방향).
    angle_align_method: "die_render"(V5 기본) | "notch" | "vertical_line" | "none".
    edge_mode        : ★ EDGE 판정 기준. "circle"(기본,부분 die) | "ring"(격자 최외곽) | "both".
                       각 die 에는 is_edge_partial / is_edge_ring 가 모두 저장되고,
                       is_edge 는 edge_mode 가 가리키는 값이 된다.
    clean            : ★[기능4] True 면 시작 시 wafer 원판 밖을 검정으로(외부노이즈 제거).
    notch_sector_deg : ★[기능1] notch 를 아래쪽 ref±이 각도에서만 탐색.
    verify_angle     : ★[기능2] True 면 die 격자 각도로 notch 각도를 교차검증.
    verify_tol_deg   : ★[기능2] 두 각도 차이가 이 값 이내면 angle_verified=True.

    Returns
    -------
    WaferDieMap (V2 필드: notch_center_px, angle_verified, die_grid_angle_resid,
                 quadrant_report. aligned_image 는 항상 채워짐[기능5]. edge_mode 저장.)
    """
    img = _load_bgr(image)

    # 0a) ★[기능4] wafer 원판 밖을 검정으로 정리 (외부 노이즈 제거) — 가장 먼저
    if clean:
        img = clean_wafer(img)

    # 0b) ★ 회전(angle) 보정
    rotation_deg = 0.0
    angle_confidence = 1.0
    angle_agree = True
    align_method = angle_align_method.lower().replace("-", "_").strip()
    if notch_align:
        if align_method in ("die_render", "die", "render", "grid_render"):
            img, rotation_deg, _ainfo = align_wafer_by_die_render(
                img, grid_method=grid_method, return_info=True)
            angle_confidence = float(_ainfo.get("confidence", 1.0))
            angle_agree = bool(_ainfo.get("agree", False))
        elif align_method == "notch":
            img, rotation_deg = align_wafer_by_notch(
                img, notch_ref_deg=notch_ref_deg)
        elif align_method in ("vertical_line", "longest_vertical_line", "line"):
            img, rotation_deg = align_wafer_by_vertical_line(img)
        elif align_method in ("none", "off", "false"):
            pass
        else:
            raise ValueError(
                "angle_align_method must be 'die_render', 'notch', "
                "'vertical_line', or 'none'.")

    H, W = img.shape[:2]

    # 1) 웨이퍼 영역
    wafer_cx, wafer_cy, wafer_r = detect_wafer(img)

    # 1b) ★[기능1] 보정된 이미지에서 아래쪽 notch + 중심점 측정 (잔여 오차 포함)
    notch_center_px = None
    notch_resid = 0.0
    nres = detect_notch(img, wafer_cx, wafer_cy, wafer_r,
                        notch_ref_deg=notch_ref_deg, sector_deg=notch_sector_deg)
    if nres is not None:
        notch_resid, notch_center_px = nres

    # 1c) ★[기능2] die 격자 각도로 notch 각도 교차검증
    die_grid_angle_resid = 0.0
    angle_verified = False
    if verify_angle:
        die_grid_angle_resid = measure_die_grid_angle(img, wafer_cx, wafer_cy, wafer_r)
        if align_method == "notch":
            # 두 독립 측정(notch 잔여 / 격자 잔여)이 모두 작고 서로 가까우면 검증 성공
            angle_verified = bool(abs(die_grid_angle_resid - notch_resid) <= verify_tol_deg
                                  and abs(die_grid_angle_resid) <= verify_tol_deg)
        else:
            angle_verified = bool(abs(die_grid_angle_resid) <= verify_tol_deg)

    # 2) die 격자 (원본 로직 그대로) -- 옵션 template 보정
    die_template_bgr = None
    if die_template_path is not None:
        die_template_bgr = cv2.imread(str(die_template_path), cv2.IMREAD_COLOR)
        if die_template_bgr is None:
            raise FileNotFoundError(str(die_template_path))
    pitch_x, pitch_y, x0, y0 = detect_grid(
        img, wafer_cx, wafer_cy, wafer_r,
        method=grid_method, die_template_bgr=die_template_bgr,
        min_pitch=min_pitch, max_pitch=max_pitch,
        cross_line_w=cross_line_w, cross_sigma_k=cross_sigma_k,
        origin_mode=origin_mode,
        cross_origin_mode=cross_origin_mode,
        thin_width_max=thin_width_max,
        thin_roi_half=thin_roi_half)

    # 2b) ★ grid origin 서브픽셀 보정 (street 십자 교차점의 '진짜' 중심)
    #     detect_grid 의 origin 은 street band 의 '밝기 무게중심' 이라 좌/우 die 밝기가
    #     다르면 밝은 쪽으로 끌려간다. half-max 교차점 중점으로 다시 잡아 편향을 없앤다.
    x0 = float(x0)
    y0 = float(y0)
    street_w = 0.0
    street_h = 0.0
    origin_refined = False
    origin_shift = (0.0, 0.0)
    phase_matched = False
    if phase_match:
        # ★[V5.3] die 가 간격 없이 맞붙은 wafer 대응.
        # '주기 안에서 제일 강한 선 = die 경계' 가정이 깨지면 origin 이 half-pitch
        # 밀린다. x·y 경계 폭이 비슷해야 한다는 성질로 올바른 phase 를 되찾는다.
        rp = resolve_grid_phase(img, wafer_cx, wafer_cy, wafer_r,
                                pitch_x, pitch_y, x0, y0)
        if rp["phase_matched"]:
            x0, y0 = rp["x0"], rp["y0"]
            phase_matched = True
    if refine_origin:
        ro = refine_grid_origin(img, wafer_cx, wafer_cy, wafer_r,
                                pitch_x, pitch_y, x0, y0)
        x0, y0 = ro["x0"], ro["y0"]
        street_w, street_h = ro["street_w"], ro["street_h"]
        origin_refined = bool(ro["refined"])
        origin_shift = (ro["shift_x"], ro["shift_y"])

    # ★[V5.5] origin 재앵커링 — '중심에 가장 가까운 die 코너' 를 보장한다.
    #   resolve_grid_phase 는 최대 ±half-pitch, refine_grid_origin 은 그와 별개로
    #   또 origin 을 옮기는데 둘 다 옮긴 뒤 중심에 다시 맞추는 곳이 없다. 두 이동이
    #   같은 방향으로 겹치면 합이 half-pitch 를 넘어 origin 이 **이웃 die 의 코너**로
    #   넘어간다(실측: scale 0.45 에서 중심 대비 x +0.205 -> +0.668 pitch).
    #   origin 은 양방향 격자 앵커라 pitch 정수배를 더해도 위상·기하는 그대로다.
    #   여기서 되돌려도 die 좌표는 하나도 안 바뀌고, die (0,0) 이 중심 die 라는
    #   성질만 복구된다.
    x0 += round((wafer_cx - x0) / pitch_x) * pitch_x
    y0 += round((wafer_cy - y0) / pitch_y) * pitch_y

    # ★ die 크기도 float(pitch) 그대로 — 마지막 rect 계산에서만 반올림해 오차 누적을 막는다
    die_w = float(pitch_x)
    die_h = float(pitch_y)

    # ★ 순수 die crop : street(여백) 폭만큼 안쪽으로 줄인 '유효' die 크기
    if exclude_street:
        eff_w = max(1.0, die_w - street_w)
        eff_h = max(1.0, die_h - street_h)
    else:
        eff_w, eff_h = die_w, die_h

    # 3) 전체 격자 위치 순회 (원본 inspect_wafer 와 동일한 중심/실측 공식)
    max_ix = int(np.ceil(wafer_r / pitch_x)) + 2
    max_iy = int(np.ceil(wafer_r / pitch_y)) + 2
    margin = edge_margin if include_edge else 0.98
    r_lim = wafer_r * margin
    r_lim_sq = r_lim ** 2
    # ★ EDGE 전부 clip : include_edge 일 때만 사각형 겹침 기준을 쓴다.
    clip_all = bool(edge_clip_all and include_edge)
    min_overlap = float(edge_overlap_min_px)

    dies: List[Dict[str, Any]] = []
    dies_by_index: Dict[Tuple[int, int], Dict[str, Any]] = {}

    for iy in range(-max_iy, max_iy + 1):
        for ix in range(-max_ix, max_ix + 1):
            # ★ 서브픽셀 중심 — 반올림은 rect 를 만들 때 한 번만 한다
            cx_f = x0 + ix * pitch_x + pitch_x / 2.0
            cy_f = y0 - iy * pitch_y - pitch_y / 2.0
            cx_d = int(round(cx_f))
            cy_d = int(round(cy_f))

            # ★ 좌/우, 상/하 대칭 rect. 예전 `cx - die_w//2` 는 홀수 폭에서 왼쪽/위로
            #   1px 치우쳐 die 가 한 방향으로 밀려 보였다.
            x_a = int(round(cx_f - eff_w / 2.0))
            y_a = int(round(cy_f - eff_h / 2.0))
            x_b = int(round(cx_f + eff_w / 2.0))
            y_b = int(round(cy_f + eff_h / 2.0))

            if clip_all:
                # ★ die 사각형이 wafer 원과 겹치면 전부 포함 (중심이 원 밖이어도 clip).
                #   중심 기준일 때 빠지던 최외곽 EDGE die 를 살린다.
                #   포함 판정은 exclude_street 와 무관해야 하므로 항상 pitch 크기 rect 로 한다.
                if _rect_circle_overlap_px(cx_f - die_w / 2.0, cy_f - die_h / 2.0,
                                           cx_f + die_w / 2.0, cy_f + die_h / 2.0,
                                           wafer_cx, wafer_cy, r_lim) < min_overlap:
                    continue
            else:
                dx = cx_f - wafer_cx
                dy = cy_f - wafer_cy
                if dx * dx + dy * dy > r_lim_sq:  # 웨이퍼 원 밖 격자 위치 -> die 없음
                    continue

            # offset/margin 적용된 실제 crop 영역 (margin=offset=0 이면 rect_px 와 동일)
            crop_rect = _crop_rect(cx_f, cy_f, eff_w, eff_h,
                                   offset_x, offset_y, margin_x, margin_y)

            rx = (cx_f - wafer_cx) / pixel_per_unit
            ry = (wafer_cy - cy_f) / pixel_per_unit

            entry: Dict[str, Any] = {
                "index":       (ix, iy),
                "center_px":   (cx_d, cy_d),
                "center_px_f": (cx_f, cy_f),      # ★ 서브픽셀 중심
                "rect_px":     (x_a, y_a, x_b, y_b),
                "crop_rect_px": crop_rect,
                "real_coord":  (rx, ry),
                # ★ 두 가지 edge 플래그를 모두 저장 (is_edge 는 아래서 edge_mode 로 결정)
                "is_edge_partial": _rect_crosses_circle(x_a, y_a, x_b, y_b,
                                                        wafer_cx, wafer_cy, wafer_r),
                "is_edge_ring": False,   # 8방향 이웃 확정 후 채움
                "is_edge":      False,   # edge_mode 적용 후 채움
            }

            if with_crops:
                crop = crop_die(img, cx_f, cy_f, eff_w, eff_h,
                                offset_x=offset_x, offset_y=offset_y,
                                margin_x=margin_x, margin_y=margin_y,
                                border_mode=border_mode)
                if crop is None:
                    continue
                entry["image"] = crop

            dies.append(entry)
            dies_by_index[(ix, iy)] = entry

    # 3b) ★ EDGE 플래그 확정 : is_edge_ring(8방향 이웃 결손) 계산 후 edge_mode 로 is_edge 선택
    emode = _normalize_edge_mode(edge_mode)
    present = set(dies_by_index.keys())
    for d in dies:
        ix, iy = d["index"]
        ring = any((ix + dxn, iy + dyn) not in present
                   for dxn in (-1, 0, 1) for dyn in (-1, 0, 1)
                   if not (dxn == 0 and dyn == 0))
        d["is_edge_ring"] = bool(ring)
        d["is_edge"] = _resolve_edge_flag(d["is_edge_partial"], d["is_edge_ring"], emode)

    # 4) ★[기능3] 4분면 가장자리 맵 검증
    quadrant_report = validate_quadrant_edges(dies, wafer_cx, wafer_cy, wafer_r)

    return WaferDieMap(
        wafer_cx=wafer_cx, wafer_cy=wafer_cy, wafer_r=wafer_r,
        pitch_x=pitch_x, pitch_y=pitch_y, x0=x0, y0=y0,
        die_w=die_w, die_h=die_h, pixel_per_unit=pixel_per_unit,
        dies=dies, dies_by_index=dies_by_index, image_shape=(H, W),
        rotation_deg=rotation_deg,
        aligned_image=img,                       # ★[기능5] 항상 반환 (clean+align 결과)
        notch_center_px=notch_center_px,         # ★[기능1]
        die_grid_angle_resid=die_grid_angle_resid,  # ★[기능2]
        angle_verified=angle_verified,           # ★[기능2]
        angle_confidence=angle_confidence,       # ★[V5 고도화] 각도 신뢰도(0~1)
        angle_agree=angle_agree,                 # ★[V5 고도화] projection↔FFT 합의 여부
        edge_mode=emode,                         # ★[V5] is_edge 기준
        quadrant_report=quadrant_report,         # ★[기능3]
        street_w=street_w, street_h=street_h,    # ★[V5.2] 측정된 street 폭
        exclude_street=bool(exclude_street),     # ★[V5.2] 순수 die 영역 여부
        origin_refined=origin_refined,           # ★[V5.2] origin 보정 적용 여부
        origin_shift_px=origin_shift,            # ★[V5.2] 보정으로 움직인 양(px)
        phase_matched=phase_matched,             # ★[V5.3] die 경계 phase 재선택 여부
    )


# =============================================================================
# [SECTOR: 61_DIE_MAP_LOOKUP_API] locate_die() — 픽셀 좌표/BBox에서 die 조회
# (2) 픽셀 좌표 / BBox -> die index + die rect + 실측 좌표
# =============================================================================
def locate_die(die_map: WaferDieMap,
               point: Optional[Tuple[float, float]] = None,
               bbox: Optional[Tuple[float, float, float, float]] = None,
               *,
               offset_x: int = DEFAULT_OFFSET_X, offset_y: int = DEFAULT_OFFSET_Y,
               margin_x: int = DEFAULT_MARGIN_X, margin_y: int = DEFAULT_MARGIN_Y
               ) -> Dict[str, Any]:
    """픽셀 좌표 또는 BBox(YOLO 등)의 위치에 해당하는 die 정보 반환.

    Parameters
    ----------
    die_map : build_die_map() 결과
    point   : (x, y) 픽셀 좌표  (point 또는 bbox 중 하나만)
    bbox    : (x1, y1, x2, y2) 픽셀 BBox. 내부적으로 중심점으로 변환해 사용.
    offset_x/offset_y : crop 중심 위치 보정 (px). crop_rect_px 에 반영.
    margin_x/margin_y : 각 변으로 더 포함할 영역 (px, die 사이 street 포함). crop_rect_px 에 반영.

    Returns
    -------
    dict
        {
          "input_type"   : "point" | "bbox",
          "query_px"     : (qx, qy),           # 사용한 픽셀 좌표 (bbox면 중심)
          "die_index"    : (ix, iy),
          "die_center_px": (cx, cy),           # 반올림된 정수 중심
          "die_center_px_f": (cxf, cyf),       # ★ 서브픽셀(float) 중심
          "die_rect_px"  : (x1, y1, x2, y2),   # 해당 die 의 사각 영역
                                               #   (exclude_street 면 street 제외)
          "crop_rect_px" : (x1, y1, x2, y2),   # offset/margin 적용된 crop 영역
          "real_coord"   : (rx, ry),           # 실측 좌표 (query 기준, 위쪽 +y)
          "real_distance": float,              # 웨이퍼 중심으로부터 실측 거리(스칼라)
          "die_real_coord": (drx, dry),        # 참고: die 중심 기준 실측 좌표
          "wafer_center_px": (wcx, wcy),       # 웨이퍼 중심점 (검출값)
          "corner_px"    : (x0, y0),           # 격자 코너(원점) 점 (검출값)
          "is_edge"      : bool,               # edge_mode 가 가리키는 edge 여부
          "is_edge_partial": bool,             # 정의① die 가 wafer 원 밖으로 일부 나감
          "is_edge_ring" : bool,               # 정의② 격자 최외곽(8방향 이웃 결손)
          "edge_mode"    : str,                # 이 맵의 is_edge 기준(circle|ring|both)
          "in_wafer"     : bool,               # query 점이 웨이퍼 원 안인지
        }

    Notes
    -----
    - die_index 는 격자 공식으로 해석적으로 계산하므로, die_map 에 미포함된
      위치(웨이퍼 밖 등)도 인덱스/실측값을 반환합니다. 포함 여부는 in_wafer 로 판단.
    - crop_rect_px 로 실제 이미지에서 crop 하려면 crop_die() 또는 슬라이싱 사용.
    """
    if (point is None) == (bbox is None):
        raise ValueError("point 또는 bbox 중 정확히 하나를 지정하세요.")

    if bbox is not None:
        x1, y1, x2, y2 = bbox
        qx = (float(x1) + float(x2)) / 2.0       # BBox 중심
        qy = (float(y1) + float(y2)) / 2.0
        input_type = "bbox"
    else:
        qx, qy = float(point[0]), float(point[1])
        input_type = "point"

    px = die_map.pitch_x
    py = die_map.pitch_y
    x0 = die_map.x0
    y0 = die_map.y0

    # --- 좌표 -> die index (build_die_map 의 중심 공식의 역변환, 규칙 동일) ---
    ix = int(math.floor((qx - x0) / px))
    iy = int(math.floor((y0 - qy) / py))         # iy +는 위쪽(y 감소)

    # --- die 중심 / rect (build_die_map 과 동일하게 계산) -------------------
    # ★ build_die_map 과 동일: 서브픽셀 중심 + 좌우/상하 대칭 rect
    cx_f = x0 + ix * px + px / 2.0
    cy_f = y0 - iy * py - py / 2.0
    cx_d = int(round(cx_f))
    cy_d = int(round(cy_f))
    eff_w, eff_h = die_map.effective_die_size()
    x_a = int(round(cx_f - eff_w / 2.0))
    y_a = int(round(cy_f - eff_h / 2.0))
    x_b = int(round(cx_f + eff_w / 2.0))
    y_b = int(round(cy_f + eff_h / 2.0))

    # offset/margin 적용된 실제 crop 영역 (margin=offset=0 이면 die_rect_px 와 동일)
    crop_rect = _crop_rect(cx_f, cy_f, eff_w, eff_h,
                           offset_x, offset_y, margin_x, margin_y)

    # --- 실측 좌표/거리 -----------------------------------------------------
    ppu = die_map.pixel_per_unit
    rx = (qx - die_map.wafer_cx) / ppu           # query(=bbox 중심) 기준 실측 좌표
    ry = (die_map.wafer_cy - qy) / ppu
    real_distance = math.hypot(rx, ry)
    drx = (cx_f - die_map.wafer_cx) / ppu        # die 중심 기준 실측 좌표(참고)
    dry = (die_map.wafer_cy - cy_f) / ppu

    # --- edge 여부(두 정의 모두) / wafer 내부 여부 --------------------------
    emode = _normalize_edge_mode(getattr(die_map, "edge_mode", DEFAULT_EDGE_MODE))
    entry = die_map.get_die(ix, iy)
    if entry is not None:
        # die map 에 있으면 build 때 확정한 플래그 그대로 사용
        is_edge_partial = bool(entry.get("is_edge_partial",
                                         entry.get("is_edge", False)))
        is_edge_ring = bool(entry.get("is_edge_ring", False))
    else:
        # 맵에 없는(웨이퍼 밖 등) 위치 -> 즉석 계산
        is_edge_partial = _rect_crosses_circle(
            x_a, y_a, x_b, y_b,
            die_map.wafer_cx, die_map.wafer_cy, die_map.wafer_r)
        is_edge_ring = any(
            (ix + dxn, iy + dyn) not in die_map.dies_by_index
            for dxn in (-1, 0, 1) for dyn in (-1, 0, 1)
            if not (dxn == 0 and dyn == 0))
    is_edge = _resolve_edge_flag(is_edge_partial, is_edge_ring, emode)
    in_wafer = ((qx - die_map.wafer_cx) ** 2 + (qy - die_map.wafer_cy) ** 2
                <= die_map.wafer_r ** 2)

    return {
        "input_type":    input_type,
        "query_px":      (qx, qy),
        "die_index":     (ix, iy),
        "die_center_px": (cx_d, cy_d),
        "die_center_px_f": (cx_f, cy_f),      # ★ 서브픽셀 중심
        "die_rect_px":   (x_a, y_a, x_b, y_b),
        "crop_rect_px":  crop_rect,
        "real_coord":    (rx, ry),
        "real_distance": real_distance,
        "die_real_coord": (drx, dry),
        "wafer_center_px": (die_map.wafer_cx, die_map.wafer_cy),  # 웨이퍼 중심점
        "corner_px":     (die_map.x0, die_map.y0),                # 격자 코너(원점)
        "is_edge":       is_edge,             # edge_mode 가 가리키는 값
        "is_edge_partial": is_edge_partial,   # 정의① 부분 die(원 밖으로 나감)
        "is_edge_ring":  is_edge_ring,        # 정의② 격자 최외곽(이웃 결손)
        "edge_mode":     emode,               # 이 맵의 is_edge 기준
        "in_wafer":      bool(in_wafer),
    }


# #############################################################################
# [SECTOR: 70_WHITE_RIM_PARTICLE] 흰 rim 안쪽 particle 검출 전체 파이프라인
# #                                                                           #
# #   ★[codex] WHITE-RIM PARTICLE  —  wafer 외곽 흰색선 안쪽 '흰 노이즈' 검출   #
# #                                                                           #
# #   die map 을 만든 '다음 단계' 로 돌리는 독립 모듈.  위쪽 파이프라인(회전     #
# #   보정 / wafer 검출 / 코너 / die map)은 전혀 건드리지 않는다.               #
# #                                                                           #
# #   왜 기존 inspect_particles_in_wafer_ring 을 그대로 못 쓰는가               #
# #   -------------------------------------------------------------------     #
# #   기존 로직은 (a) wafer_r 에서 고정 margin 을 뺀 기하학적 ring 을 ROI 로     #
# #   잡고 (b) 모든 die 셀을 마스크로 **지운 뒤** (c) 절대 밝기(>=220)로         #
# #   이진화한다.  이 폴더의 실제 샘플에서는 셋 다 깨진다.                       #
# #     (a) 흰색 외곽선의 반경이 이미지마다 다르다  -> 고정 margin 은 위험       #
# #     (b) 노이즈가 최외곽 clip die '위에' 얹혀 있다 -> die 를 지우면 표적도    #
# #         같이 지워진다                                                       #
# #     (c) die 내부의 밝은 세로 bar 가 노이즈보다 밝다 -> 절대 임계로는         #
# #         분리 불가 (실측: 깨끗한 영역 frac>=220 = 0.031,                     #
# #                       더러운 영역 frac>=220 = 0.050)                       #
# #                                                                           #
# #   그래서 3단으로 바꿨다                                                     #
# #     1) 흰색 외곽선을 '밝은 화소 비율' 반경 프로파일로 **측정**한다.          #
# #        (평균 프로파일은 띠가 얇아 방위평균에 묻힌다 — 실측 실패)             #
# #     2) die map 의 pitch/origin 으로 **golden die(위상 타일) 모델**을         #
# #        깨끗한 안쪽(r<=ratio*R)에서 만들고, 그 median/MAD 대비 robust         #
# #        z-score 로 이진화한다.  die 패턴은 모델에 흡수돼 사라진다.           #
# #     3) 그래도 남는 것(pitch 오차로 인한 위상 밀림 등)은 **주기성 투표**로    #
# #        떨군다.  ±1,±2 pitch 위치에서도 같이 밝으면 그건 die 패턴이다.       #
# #                                                                           #
# #############################################################################

# ---------------------------------------------------------------- 기본 파라미터
# 흰색 띠 기준
DEFAULT_RIM_BRIGHT_PERCENTILE = 99.0   # 이 분위수 이상을 '흰색' 으로 본다
DEFAULT_RIM_LEVEL = 0.15               # 띠 경계를 정하는 상대 레벨 (base~peak 사이)
DEFAULT_RIM_SEARCH_LO_RATIO = 0.80     # 반경 프로파일 시작 (wafer_r 대비)
DEFAULT_RIM_SEARCH_HI_RATIO = 1.02     # 반경 프로파일 끝

# 검사 범위 ('흰색 띠 안쪽으로 어디까지 볼 것인가')
DEFAULT_RIM_CLEARANCE_PX = 2.0         # 흰색 띠 안쪽 경계에서 더 안으로 띄울 여유
DEFAULT_SEARCH_DEPTH_PX = 60.0         # 거기서부터 안쪽으로 볼 깊이
DEFAULT_INCLUDE_RIM = False            # True 면 흰색 띠 자체도 검사 대상에 넣는다

# 크기/모양 ('어느 크기부터 어느 크기까지')
DEFAULT_NOISE_MIN_AREA_PX = 4          # 이 화소수 미만은 버린다 (가장 공격적인 필터)
DEFAULT_NOISE_MAX_AREA_PX = 400        # 이 화소수 초과는 particle 이 아니라 구조물로 본다
DEFAULT_NOISE_MAX_ASPECT = 3.5         # max(w,h)/min(w,h) 상한 — 길쭉한 건 die 경계선
DEFAULT_NOISE_MIN_FILL = 0.35          # area/(w*h) 하한 — 성긴 건 패턴 잔상

# 검출 감도
DEFAULT_NOISE_Z_THRESHOLD = 4.0        # golden die 모델 대비 robust z
DEFAULT_NOISE_MAD_FLOOR = 5.0          # MAD 하한 (0 나눗셈/과민 방지)
DEFAULT_NOISE_GRAY_THRESHOLD = 220     # use_pattern_model=False 일 때의 절대 임계

# die 패턴 오인 방지
DEFAULT_PATTERN_REF_RATIO = 0.80       # golden die 를 만들 '깨끗한 안쪽' 반경비
DEFAULT_REPEAT_VOTE = True             # 이웃 die 에도 같은 게 있으면 패턴으로 보고 기각
DEFAULT_REPEAT_STEPS = (1, 2)          # ±1, ±2 pitch 위치를 본다
DEFAULT_REPEAT_SOFT_RATIO = 0.55       # 이웃 판정용 완화 임계 (z_threshold 대비)
DEFAULT_REPEAT_MIN_VOTES = 4           # 유효 이웃이 이 수 미만이면 투표 기각 안 함
DEFAULT_REPEAT_REJECT_RATIO = 0.50     # 유효 이웃 중 이 비율 이상 밝으면 die 패턴
DEFAULT_RADIAL_DETREND = True          # 가장자리 밝기 기울기 제거

DEFAULT_NOISE_AUTO_PITCH = True        # die map pitch 를 믿지 않고 직접 재측정
DEFAULT_NOISE_MIN_PITCH = 8            # 자기상관 lag 탐색 하한 (px)
DEFAULT_NOISE_MAX_PITCH = 200          # 자기상관 lag 탐색 상한 (px)

# detect_white_noise() 가 die map 을 직접 만들 때 쓰는 기본값.
#   angle_align_method="none" 이 중요하다 — build_die_map 이 회전 보정을 하면
#   반환된 die map 좌표는 '회전된 이미지' 기준이 되어 입력 이미지와 어긋난다.
DEFAULT_NOISE_DIE_MAP_KWARGS = {
    "grid_method": "thin_cross",
    "angle_align_method": "none",
    "min_pitch": 12,
    "max_pitch": 80,
}

_NOISE_PITCH_SCAN_SPAN = 1.6           # pitch 미세탐색 폭 (±px)
_NOISE_PITCH_SCAN_STEP = 0.05
_NOISE_PITCH_SUBSAMPLE = 2             # 미세탐색 시 화소 간솎음
_NOISE_HARMONIC_TOL = 0.80             # 기본주기 판정 (배음 대비 자기상관 비)
_NOISE_DETREND_WIN = 31


# ---------------------------------------------------------------- 자료구조
@dataclass
class WaferRimBand:
    """wafer 외곽 흰색선(띠)의 반경 구간."""
    found: bool
    inner_r: float          # 띠 안쪽 경계
    outer_r: float          # 띠 바깥 경계
    peak_r: float           # 띠가 가장 진한 반경
    peak_ratio: float       # 그 반경의 밝은 화소 비율
    base_ratio: float       # die 영역의 밝은 화소 비율 (배경 수준)
    bright_level: int       # '흰색' 판정에 쓴 그레이 임계


@dataclass
class DiePatternModel:
    """golden die — die 내부 위상(phase)별 median/MAD 타일."""
    ok: bool
    med: np.ndarray         # (ny, nx) float32
    mad: np.ndarray         # (ny, nx) float32
    x0: float
    y0: float
    pitch_x: float
    pitch_y: float
    nx: int
    ny: int
    quality: float          # 1 - resid_std/raw_std  (1 에 가까울수록 잘 설명)
    ref_radius: float
    pitch_seed: Tuple[float, float] = (0.0, 0.0)   # 넘겨받은 pitch (보통 die map)
    pitch_source: str = "given"                    # "auto" | "given"


# ---------------------------------------------------------------- 보조
def imread_unicode(path: Union[str, Path],
                   flags: int = cv2.IMREAD_COLOR) -> np.ndarray:
    """★ 한글/유니코드 경로 대응 imread.

    cv2.imread 는 Windows 에서 비 ASCII 경로를 열지 못하고 조용히 None 을 준다.
    (이 폴더의 샘플 경로에 '원본' 이 들어 있어 실제로 걸렸다.)
    """
    buf = np.fromfile(str(path), dtype=np.uint8)
    img = cv2.imdecode(buf, flags)
    if img is None:
        raise FileNotFoundError(str(path))
    return img


def _noise_load_bgr(image: Union[str, Path, np.ndarray]) -> np.ndarray:
    if isinstance(image, np.ndarray):
        return _as_bgr(image)
    return imread_unicode(image, cv2.IMREAD_COLOR)


def _radial_map(shape: Tuple[int, int], cx: float, cy: float) -> np.ndarray:
    h, w = shape[:2]
    yy = np.arange(h, dtype=np.float32).reshape(-1, 1) - float(cy)
    xx = np.arange(w, dtype=np.float32).reshape(1, -1) - float(cx)
    return np.sqrt(xx * xx + yy * yy)


# =============================================================================
# [SECTOR: 71_RIM_DETECTION] 흰 외곽선 반경/폭 측정
# 1) 흰색 외곽선(띠) 검출
# =============================================================================
def detect_wafer_rim_band(image: Union[str, Path, np.ndarray],
                          wafer_cx: float, wafer_cy: float, wafer_r: float,
                          *,
                          bright_percentile: float = DEFAULT_RIM_BRIGHT_PERCENTILE,
                          level: float = DEFAULT_RIM_LEVEL,
                          search_lo_ratio: float = DEFAULT_RIM_SEARCH_LO_RATIO,
                          search_hi_ratio: float = DEFAULT_RIM_SEARCH_HI_RATIO,
                          min_ring_samples: int = 30,
                          radius_map: Optional[np.ndarray] = None
                          ) -> WaferRimBand:
    """wafer 바깥 테두리의 '흰색선' 이 차지하는 반경 구간을 측정한다.

    평균 밝기 프로파일은 쓰지 않는다. 띠가 얇아서 방위(azimuth) 평균에 묻히고,
    die 영역 평균(110~124)이 띠 평균(188)과 그리 멀지 않아 경계가 안 선다.
    대신 **밝은 화소의 비율**(gray >= 상위 percentile) 을 반경별로 센다.
    실측에서 이 프로파일은 깨끗한 계단이 된다.

        r  595 597 599 601 603 605 607
        f 0.00 .06 .12 .23 .31 .15 0.00      (22.png)

    반환 구간은 base + level*(peak-base) 를 넘는 peak 주변 **연속 구간**이다.
    """
    gray = _gray_u8(_noise_load_bgr(image))
    h, w = gray.shape[:2]
    rad = _radial_map((h, w), wafer_cx, wafer_cy) if radius_map is None else radius_map

    disc = rad <= float(wafer_r)
    if not np.any(disc):
        return WaferRimBand(False, float(wafer_r), float(wafer_r), float(wafer_r),
                            0.0, 0.0, 255)
    bright_level = int(round(float(np.percentile(gray[disc], bright_percentile))))
    bright_level = int(np.clip(bright_level, 1, 255))

    lo = float(wafer_r) * float(search_lo_ratio)
    hi = float(wafer_r) * float(search_hi_ratio)
    n = max(2, int(math.ceil(hi - lo)) + 1)

    sel = (rad >= lo) & (rad <= hi)
    idx = np.clip((rad[sel] - lo).astype(np.int32), 0, n - 1)
    cnt = np.bincount(idx, minlength=n).astype(np.float64)
    brt = np.bincount(idx,
                      weights=(gray[sel] >= bright_level).astype(np.float64),
                      minlength=n)
    valid = cnt >= float(min_ring_samples)
    prof = np.full(n, np.nan, dtype=np.float64)
    prof[valid] = brt[valid] / cnt[valid]
    xs = lo + np.arange(n, dtype=np.float64)

    # 배경 수준 = die 영역(띠보다 확실히 안쪽)의 중앙값
    inner_sel = valid & (xs < float(wafer_r) * 0.93)
    base = float(np.nanmedian(prof[inner_sel])) if np.any(inner_sel) else 0.0

    scan = np.where(valid & (xs <= float(wafer_r)), np.nan_to_num(prof, nan=-1.0), -1.0)
    if not np.any(scan > 0.0):
        return WaferRimBand(False, float(wafer_r), float(wafer_r), float(wafer_r),
                            0.0, base, bright_level)
    pk = int(np.argmax(scan))
    peak = float(prof[pk])
    if not np.isfinite(peak) or peak <= base:
        return WaferRimBand(False, float(wafer_r), float(wafer_r), float(wafer_r),
                            0.0, base, bright_level)

    thr = base + float(level) * (peak - base)
    i = pk
    while i - 1 >= 0 and np.isfinite(prof[i - 1]) and prof[i - 1] >= thr:
        i -= 1
    j = pk
    while j + 1 < n and np.isfinite(prof[j + 1]) and prof[j + 1] >= thr:
        j += 1
    return WaferRimBand(True, float(xs[i]), float(xs[j]), float(xs[pk]),
                        peak, base, bright_level)


# =============================================================================
# [SECTOR: 72_PATTERN_MODEL] golden die 모델과 pattern pitch 추정/미세 보정
# 2) golden die (위상 타일) 패턴 모델
# =============================================================================
def _fold_axis_residual(values: np.ndarray, coord: np.ndarray,
                        origin: float, pitch: float, nbin: int) -> float:
    """1축 위상 접기 후 잔차 표준편차. pitch 미세탐색용 목적함수."""
    u = np.mod(coord - origin, pitch) / pitch * nbin
    u = np.minimum(u.astype(np.int32), nbin - 1)
    cnt = np.bincount(u, minlength=nbin).astype(np.float64)
    s = np.bincount(u, weights=values, minlength=nbin)
    cnt = np.maximum(cnt, 1.0)
    resid = values - (s / cnt)[u]
    return float(np.std(resid))


def _fundamental_lag(ac: np.ndarray, best: int, min_lag: int,
                     tol: float = _NOISE_HARMONIC_TOL) -> int:
    """자기상관 최대 lag 이 배음일 수 있다. 약수 중 가장 작은 유효 주기를 고른다."""
    cand = best
    for k in (2, 3, 4, 5):
        i = int(round(best / float(k)))
        if i < min_lag:
            break
        lo = max(min_lag, i - 2)
        hi = min(len(ac) - 1, i + 2)
        if hi <= lo:
            continue
        loc = lo + int(np.argmax(ac[lo:hi + 1]))
        if ac[loc] >= tol * ac[best]:
            cand = loc
    return cand


def _axis_pitch_autocorr(profile: np.ndarray, min_lag: int, max_lag: int
                         ) -> Optional[int]:
    n = profile.size
    max_lag = min(int(max_lag), n - 2)
    if n < 32 or max_lag <= min_lag:
        return None
    p = profile.astype(np.float32)
    p = p - cv2.blur(p.reshape(-1, 1), (1, _NOISE_DETREND_WIN)).ravel()
    p = p - float(p.mean())
    ac = np.correlate(p, p, "full")[n - 1:]
    if ac[0] <= 1e-9:
        return None
    ac = ac / float(ac[0])
    best = int(np.argmax(ac[min_lag:max_lag + 1])) + int(min_lag)
    return _fundamental_lag(ac, best, int(min_lag))


def estimate_pattern_pitch(gray: np.ndarray,
                           wafer_cx: float, wafer_cy: float, wafer_r: float,
                           *,
                           ref_radius_ratio: float = DEFAULT_PATTERN_REF_RATIO,
                           min_pitch: int = DEFAULT_NOISE_MIN_PITCH,
                           max_pitch: int = DEFAULT_NOISE_MAX_PITCH
                           ) -> Optional[Tuple[float, float]]:
    """깨끗한 안쪽 정사각 ROI 의 축별 평균 projection 자기상관으로 pitch 를 잰다.

    die map 의 pitch 를 그대로 믿으면 안 된다. 이 폴더 샘플에서 실측하면
    22.png thin_cross -> (20.03, 16.00), 43.png cross -> (37.82, 28.87) 로
    실제 (38.1, 16.3) 과 크게 어긋난다. 위상 모델은 pitch 가 몇 % 만 틀어져도
    wafer 반대편에서 완전히 밀리므로 여기서는 다시 잰다.
    """
    h, w = gray.shape[:2]
    half = int(float(wafer_r) * float(ref_radius_ratio) / math.sqrt(2.0))
    x1 = max(0, int(round(wafer_cx)) - half)
    x2 = min(w, int(round(wafer_cx)) + half)
    y1 = max(0, int(round(wafer_cy)) - half)
    y2 = min(h, int(round(wafer_cy)) + half)
    if x2 - x1 < 32 or y2 - y1 < 32:
        return None
    roi = gray[y1:y2, x1:x2].astype(np.float32)
    lx = _axis_pitch_autocorr(roi.mean(axis=0), min_pitch, max_pitch)
    ly = _axis_pitch_autocorr(roi.mean(axis=1), min_pitch, max_pitch)
    if lx is None or ly is None:
        return None
    return float(lx), float(ly)


def refine_pattern_pitch(gray: np.ndarray,
                         wafer_cx: float, wafer_cy: float,
                         seed_x: float, seed_y: float,
                         *,
                         ref_mask: np.ndarray,
                         span: float = _NOISE_PITCH_SCAN_SPAN,
                         step: float = _NOISE_PITCH_SCAN_STEP,
                         subsample: int = _NOISE_PITCH_SUBSAMPLE
                         ) -> Tuple[float, float]:
    """seed pitch 주변만 1축씩 미세탐색한다.

    2-D 전탐색은 90점에 12.8s 나와 못 쓴다. 축을 분리하면 각 축 ~65점,
    화소도 subsample 로 솎아서 1초 이하로 끝난다. die map 의 pitch 는 실제
    샘플에서 오차가 있었으므로(22.png: 20.03 vs 실측 38.1) 이 보정이 없으면
    위상이 밀려 die bar 가 통째로 검출된다.
    """
    ys, xs = np.nonzero(ref_mask)
    if ys.size < 5000:
        return float(seed_x), float(seed_y)
    if subsample > 1:
        ys = ys[::subsample]
        xs = xs[::subsample]
    vals = gray[ys, xs].astype(np.float64)
    fx = xs.astype(np.float64)
    fy = float(wafer_cy) - ys.astype(np.float64)

    out = []
    for seed, coord, origin in ((seed_x, fx, float(wafer_cx)),
                                (seed_y, fy, 0.0)):
        seed = float(seed)
        nbin = max(2, int(round(seed)))
        lo = max(2.0, seed - span)
        hi = seed + span
        cand = np.arange(lo, hi + 1e-9, float(step))
        best, best_p = None, seed
        for p in cand:
            e = _fold_axis_residual(vals, coord, origin, float(p), nbin)
            if best is None or e < best:
                best, best_p = e, float(p)
        out.append(best_p)
    return out[0], out[1]


def build_die_pattern_model(image: Union[str, Path, np.ndarray],
                            wafer_cx: float, wafer_cy: float, wafer_r: float,
                            pitch_x: float, pitch_y: float,
                            *,
                            x0: Optional[float] = None,
                            y0: Optional[float] = None,
                            ref_radius_ratio: float = DEFAULT_PATTERN_REF_RATIO,
                            auto_pitch: bool = DEFAULT_NOISE_AUTO_PITCH,
                            refine_pitch: bool = True,
                            min_pitch: int = DEFAULT_NOISE_MIN_PITCH,
                            max_pitch: int = DEFAULT_NOISE_MAX_PITCH,
                            radius_map: Optional[np.ndarray] = None
                            ) -> DiePatternModel:
    """깨끗한 wafer 안쪽에서 'die 한 칸의 평균 모습' 을 만든다.

    die 내부 위상 (u,v) = (mod(x-x0,px)/px*nx, mod(y0-y,py)/py*ny) 로 화소를
    모아 median / MAD 를 낸다. 정수 modulo 는 pitch 가 정수가 아닐 때
    (실측 py=16.3) die 마다 위상이 밀려 못 쓴다. 반드시 실수 modulo.

    기준 영역을 **바깥 ring 이 아니라 안쪽 원판**으로 잡는 게 핵심이다.
    ring 자체로 통계를 내면 그 안의 오염이 MAD 를 부풀려서 정작 오염을
    못 잡는다(실측: ring 기준은 얼룩 대부분을 놓쳤다).
    """
    gray = _gray_u8(_noise_load_bgr(image))
    h, w = gray.shape[:2]
    rad = _radial_map((h, w), wafer_cx, wafer_cy) if radius_map is None else radius_map

    ref_radius = float(wafer_r) * float(ref_radius_ratio)
    ref = rad <= ref_radius
    seed = (float(pitch_x), float(pitch_y))
    px, py = seed
    source = "given"

    if auto_pitch:
        est = estimate_pattern_pitch(gray, wafer_cx, wafer_cy, wafer_r,
                                     ref_radius_ratio=ref_radius_ratio,
                                     min_pitch=min_pitch, max_pitch=max_pitch)
        if est is not None:
            px, py = est
            source = "auto"

    if px < 2.0 or py < 2.0 or int(np.count_nonzero(ref)) < 1000:
        z = np.zeros((1, 1), np.float32)
        return DiePatternModel(False, z, z, float(wafer_cx), float(wafer_cy),
                               px, py, 1, 1, 0.0, ref_radius, seed, source)

    ox = float(wafer_cx) if x0 is None else float(x0)
    oy = float(wafer_cy) if y0 is None else float(y0)

    if refine_pitch:
        px, py = refine_pattern_pitch(gray, ox, oy, px, py, ref_mask=ref)

    nx = max(2, int(round(px)))
    ny = max(2, int(round(py)))

    ys, xs = np.nonzero(ref)
    u = np.minimum((np.mod(xs - ox, px) / px * nx).astype(np.int32), nx - 1)
    v = np.minimum((np.mod(oy - ys, py) / py * ny).astype(np.int32), ny - 1)
    flat = v * nx + u
    vals = gray[ys, xs].astype(np.float32)

    order = np.argsort(flat, kind="stable")
    fs = flat[order]
    vs = vals[order]
    bounds = np.searchsorted(fs, np.arange(nx * ny + 1))
    med = np.zeros(nx * ny, np.float32)
    mad = np.zeros(nx * ny, np.float32)
    for k in range(nx * ny):
        seg = vs[bounds[k]:bounds[k + 1]]
        if seg.size == 0:
            continue
        m = float(np.median(seg))
        med[k] = m
        mad[k] = float(np.median(np.abs(seg - m)))
    med = med.reshape(ny, nx)
    mad = mad.reshape(ny, nx)

    raw_std = float(np.std(vals))
    res_std = float(np.std(vals - med.reshape(-1)[flat]))
    quality = 0.0 if raw_std <= 1e-6 else max(0.0, 1.0 - res_std / raw_std)
    return DiePatternModel(True, med, mad, ox, oy, px, py, nx, ny,
                           quality, ref_radius, seed, source)


def _pattern_phase_index(model: DiePatternModel,
                         shape: Tuple[int, int]) -> Tuple[np.ndarray, np.ndarray]:
    h, w = shape[:2]
    xs = np.arange(w, dtype=np.float64).reshape(1, -1)
    ys = np.arange(h, dtype=np.float64).reshape(-1, 1)
    u = np.minimum(
        (np.mod(xs - model.x0, model.pitch_x) / model.pitch_x * model.nx).astype(np.int32),
        model.nx - 1)
    v = np.minimum(
        (np.mod(model.y0 - ys, model.pitch_y) / model.pitch_y * model.ny).astype(np.int32),
        model.ny - 1)
    return np.broadcast_to(v, (h, w)), np.broadcast_to(u, (h, w))


def die_pattern_zscore(gray: np.ndarray, model: DiePatternModel,
                       *, mad_floor: float = DEFAULT_NOISE_MAD_FLOOR
                       ) -> np.ndarray:
    """golden die 대비 robust z-score 맵. 클수록 '패턴으로 설명 안 되는 밝음'."""
    v, u = _pattern_phase_index(model, gray.shape)
    med = model.med[v, u]
    scale = np.maximum(1.4826 * model.mad[v, u], float(mad_floor))
    return (gray.astype(np.float32) - med) / scale


# =============================================================================
# [SECTOR: 73_PARTICLE_INSPECTION] 후보 생성, 모양/반복 패턴 필터, 최종 particle 판정
# 3) 본체 — 흰색 띠 안쪽 흰 노이즈 검사
# =============================================================================
def _bbox_corners(x1: int, y1: int, x2: int, y2: int
                  ) -> List[Tuple[int, int]]:
    """외각 4포인트 — 좌상 / 우상 / 우하 / 좌하 (시계방향)."""
    return [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]


def inspect_white_noise_inside_rim(
        image: Union[str, Path, np.ndarray],
        die_map: Optional[WaferDieMap] = None,
        *,
        # --- wafer / 흰색 띠 ------------------------------------------------
        wafer_cx: Optional[float] = None,
        wafer_cy: Optional[float] = None,
        wafer_r: Optional[float] = None,
        rim_band: Optional[WaferRimBand] = None,
        rim_bright_percentile: float = DEFAULT_RIM_BRIGHT_PERCENTILE,
        rim_level: float = DEFAULT_RIM_LEVEL,
        # --- 검사 범위 (흰색 띠 안쪽으로 어디까지) ---------------------------
        rim_clearance_px: float = DEFAULT_RIM_CLEARANCE_PX,
        search_depth_px: float = DEFAULT_SEARCH_DEPTH_PX,
        include_rim: bool = DEFAULT_INCLUDE_RIM,
        inner_radius_px: Optional[float] = None,
        outer_radius_px: Optional[float] = None,
        # --- 크기 / 모양 (어느 크기부터 어느 크기까지) -----------------------
        min_area_px: int = DEFAULT_NOISE_MIN_AREA_PX,
        max_area_px: int = DEFAULT_NOISE_MAX_AREA_PX,
        max_aspect_ratio: float = DEFAULT_NOISE_MAX_ASPECT,
        min_fill_ratio: float = DEFAULT_NOISE_MIN_FILL,
        # --- 검출 감도 ------------------------------------------------------
        use_pattern_model: bool = True,
        z_threshold: float = DEFAULT_NOISE_Z_THRESHOLD,
        mad_floor: float = DEFAULT_NOISE_MAD_FLOOR,
        gray_threshold: int = DEFAULT_NOISE_GRAY_THRESHOLD,
        radial_detrend: bool = DEFAULT_RADIAL_DETREND,
        # --- die 패턴 오인 방지 ----------------------------------------------
        pattern_model: Optional[DiePatternModel] = None,
        pattern_ref_ratio: float = DEFAULT_PATTERN_REF_RATIO,
        auto_pitch: bool = DEFAULT_NOISE_AUTO_PITCH,
        refine_pitch: bool = True,
        pitch_x: Optional[float] = None,
        pitch_y: Optional[float] = None,
        min_pitch: int = DEFAULT_NOISE_MIN_PITCH,
        max_pitch: int = DEFAULT_NOISE_MAX_PITCH,
        use_repeat_vote: bool = DEFAULT_REPEAT_VOTE,
        repeat_steps: Tuple[int, ...] = DEFAULT_REPEAT_STEPS,
        repeat_soft_ratio: float = DEFAULT_REPEAT_SOFT_RATIO,
        repeat_min_votes: int = DEFAULT_REPEAT_MIN_VOTES,
        repeat_reject_ratio: float = DEFAULT_REPEAT_REJECT_RATIO,
        # --- 출력 -------------------------------------------------------------
        with_overlay: bool = True,
        keep_rejected: bool = False,
        ) -> Dict[str, Any]:
    """흰색 외곽선 **안쪽**의 흰 노이즈(particle)를 찾는다.

    die map 을 만든 다음 단계로 호출하는 것을 전제로 한다. die_map 을 주면
    wafer 중심/반경과 격자 pitch/origin 을 거기서 가져온다. 안 줘도 동작한다
    (wafer 는 Otsu 로 직접 잡고, pitch 는 pitch_x/pitch_y 인자로 준다).

    반환 dict (요청한 3가지가 각각 "binary" / "corners_px" / "overlay")

      "binary"      uint8 (h,w) 0/255   — 노이즈만 남긴 이진 영상
      "corners_px"  List[List[(x,y)*4]] — 노이즈별 외각 4포인트(좌상→우상→우하→좌하)
      "overlay"     uint8 (h,w,3)       — 원본에 노이즈를 표시한 이미지
      "particles"   List[dict]          — 개별 정보(아래)
      "rejected"    List[dict]          — keep_rejected=True 일 때 탈락 사유 포함
      "rim"         WaferRimBand        — 검출된 흰색 띠
      "pattern"     DiePatternModel     — 쓰인 golden die 모델
      "roi_mask"    uint8               — 실제 검사한 고리 영역
      "raw_mask"    uint8               — 필터 전 이진화 결과
      "zscore"      float32             — 사용한 z 맵 (use_pattern_model=True)
      "stats"       dict                — {"total","pass","area","shape","repeat"}
      "radii_px"    dict                — 실제 사용한 반경들
      "parameters"  dict                — 되돌려주는 옵션 값

    particles[i] 키
      "id","center_px","bbox_px","corners_px","area_px","aspect_ratio",
      "fill_ratio","mean_intensity","max_intensity","peak_z","mean_z",
      "radius_from_wafer_center_px","die_index"

    ------------------------------------------------------------------
    옵션 전체 (기본값은 위 DEFAULT_* 상수)
    ------------------------------------------------------------------

    [1] wafer 기하 — 보통 건드릴 일 없다. die_map 을 주면 거기서 가져온다.

      die_map            WaferDieMap. 중심/반경/pitch/origin 의 출처.
      wafer_cx           중심 x 를 직접 지정 (die_map 값보다 우선)
      wafer_cy           중심 y 를 직접 지정
      wafer_r            wafer 반경을 직접 지정
      rim_band           이미 잰 WaferRimBand 를 재사용 (rim 재검출 생략)

    [2] 흰색 띠(rim) 검출 — 띠는 고정값이 아니라 매 장 측정한다.

      rim_bright_percentile  99.0   '흰색' 판정 밝기 = disc gray 의 이 백분위.
                                    낮추면 띠가 두껍게 잡힌다.
      rim_level              0.15   bright-fraction 프로파일에서 띠 폭을 자르는
                                    상대 레벨. base + level*(peak-base) 를 넘는
                                    연속 구간이 띠다. 올리면 띠가 얇아진다.

    [3] 검사 범위 — '흰 띠 안쪽으로 어디까지 볼 것인가'

      rim_clearance_px   2.0    띠 안쪽 경계에서 더 안으로 띄울 여유(px).
                                띠 자체의 번짐이 검출되는 걸 막는다.
      search_depth_px    60.0   거기서부터 안쪽으로 볼 깊이(px). 가장 자주
                                조정하는 값. 키우면 ROI 가 넓어진다.
      include_rim        False  True 면 띠 자체도 검사 대상에 넣는다.
                                (띠 위에 얹힌 오염까지 잡고 싶을 때)
      inner_radius_px    None   위 셋을 무시하고 ROI 안쪽 반경을 직접 지정
      outer_radius_px    None   〃 바깥 반경을 직접 지정

      실제 적용된 값은 result["radii_px"]["roi_inner"/"roi_outer"] 로 확인한다.

    [4] 크기 / 모양 — '어느 크기부터 어느 크기까지'

      min_area_px        4      연결성분 면적 하한(px). 기본값은 매우 공격적이다
                                (22.png 후보 1970개 중 1172개가 여기서 탈락).
                                현장 판정 기준에 맞춰 올려 쓸 것.
      max_area_px        400    면적 상한. 큰 얼룩/스크래치를 제외한다.
      max_aspect_ratio   3.5    max(w,h)/min(w,h) 상한. 길쭉한 die bar 조각 배제.
      min_fill_ratio     0.35   area/(w*h) 하한. 성기게 흩어진 성분 배제.

    [5] 검출 감도

      use_pattern_model  True   golden die 위상 모델을 쓸지. False 면 절대 밝기
                                (gray_threshold) 로 떨어진다 — 이 샘플에선
                                276 -> 8 로 무너지므로 켜 두는 게 맞다.
      z_threshold        4.0    모델 대비 robust z 임계. 내리면 더 많이 잡는다.
      mad_floor          5.0    MAD 하한. 분모가 0 에 가까운 위상(=거의 균일한
                                픽셀)에서 z 가 폭발하는 걸 막는다. 올리면 둔해진다.
      gray_threshold     220    use_pattern_model=False 일 때만 쓰이는 절대 임계.
      radial_detrend     True   반경별 z 중앙값을 빼서 가장자리로 갈수록 전체가
                                밝아지는 성분을 제거한다.

    [6] die 패턴 모델 / pitch

      pattern_model      None   미리 만든 DiePatternModel 재사용. 같은 wafer 를
                                여러 옵션으로 sweep 할 때 필수(시간의 대부분).
      pattern_ref_ratio  0.80   모델을 만들 '깨끗한 내부' 반경 비율(r <= 0.80R).
                                오염 구역으로 모델을 만들면 그 MAD 가 부풀어
                                자기 자신을 숨긴다. 반드시 내부 기준.
      auto_pitch         True   die map 의 pitch 를 믿지 않고 자기상관으로 다시
                                잰다. False 면 die_map.pitch_x/y (또는 아래
                                pitch_x/y)를 그대로 쓴다 — 신뢰할 때만.
      refine_pitch       True   ±1.6px 를 0.05px 간격으로 fold-residual 미세조정.
      pitch_x            None   pitch 를 직접 지정 (auto_pitch 의 seed 로도 쓰임)
      pitch_y            None   〃
      min_pitch          8      자기상관 lag 탐색 하한
      max_pitch          200    〃 상한

      교정이 실제로 일어났는지는 result["parameters"] 의
      pitch_seed / pitch_source / pitch_used / pattern_quality 로 확인한다.

    [7] 반복성 투표 — die 패턴 오인 방지의 마지막 관문

      use_repeat_vote    True   끄면 die 패턴 잔재가 그대로 통과한다
                                (이 샘플: 276 -> 607).
      repeat_steps       (1,2)  중심에서 몇 pitch 떨어진 곳까지 볼지
      repeat_soft_ratio  0.55   이웃 판정용 완화 임계 (z_threshold 배수)
      repeat_min_votes   4      유효 이웃 표본이 이 수 미만이면 투표하지 않는다
      repeat_reject_ratio 0.50  유효 이웃 중 이 비율 이상이 같이 뜨면 die 패턴
                                으로 보고 기각

    [8] 출력

      with_overlay       True   False 면 overlay 를 만들지 않는다(약간 빠름)
      keep_rejected      False  True 면 탈락분을 reason("area"/"shape"/"repeat")
                                과 함께 result["rejected"] 에 남긴다
    """
    bgr = _noise_load_bgr(image)
    gray = _gray_u8(bgr)
    h, w = gray.shape[:2]

    # ---- wafer 기하 -------------------------------------------------------
    if die_map is not None:
        cx = float(die_map.wafer_cx) if wafer_cx is None else float(wafer_cx)
        cy = float(die_map.wafer_cy) if wafer_cy is None else float(wafer_cy)
        rr = float(die_map.wafer_r) if wafer_r is None else float(wafer_r)
    else:
        if None in (wafer_cx, wafer_cy, wafer_r):
            dcx, dcy, drr = detect_wafer(bgr)
            cx = float(dcx) if wafer_cx is None else float(wafer_cx)
            cy = float(dcy) if wafer_cy is None else float(wafer_cy)
            rr = float(drr) if wafer_r is None else float(wafer_r)
        else:
            cx, cy, rr = float(wafer_cx), float(wafer_cy), float(wafer_r)

    rad = _radial_map((h, w), cx, cy)

    # ---- 1) 흰색 띠 -------------------------------------------------------
    rim = rim_band if rim_band is not None else detect_wafer_rim_band(
        bgr, cx, cy, rr,
        bright_percentile=rim_bright_percentile,
        level=rim_level, radius_map=rad)

    # ---- 2) 검사 고리 -----------------------------------------------------
    if outer_radius_px is not None:
        r_out = float(outer_radius_px)
    elif include_rim:
        r_out = float(rim.outer_r if rim.found else rr)
    else:
        r_out = float((rim.inner_r if rim.found else rr) - float(rim_clearance_px))
    if inner_radius_px is not None:
        r_in = float(inner_radius_px)
    else:
        r_in = r_out - float(search_depth_px)
    r_in = max(0.0, min(r_in, r_out))
    roi = (rad >= r_in) & (rad <= r_out)
    roi_u8 = roi.astype(np.uint8) * 255

    # ---- 3) 검출 신호 -----------------------------------------------------
    model: Optional[DiePatternModel] = pattern_model
    z: Optional[np.ndarray] = None
    if use_pattern_model:
        if model is None:
            seed_x = pitch_x if pitch_x is not None else (
                die_map.pitch_x if die_map is not None else None)
            seed_y = pitch_y if pitch_y is not None else (
                die_map.pitch_y if die_map is not None else None)
            if (seed_x is None or seed_y is None) and not auto_pitch:
                raise ValueError(
                    "pitch 를 알 수 없다. die_map 을 주거나 pitch_x/pitch_y 를 지정할 것 "
                    "(또는 auto_pitch=True / use_pattern_model=False).")
            model = build_die_pattern_model(
                bgr, cx, cy, rr,
                float(seed_x) if seed_x is not None else 0.0,
                float(seed_y) if seed_y is not None else 0.0,
                x0=(die_map.x0 if die_map is not None else None),
                y0=(die_map.y0 if die_map is not None else None),
                ref_radius_ratio=pattern_ref_ratio,
                auto_pitch=auto_pitch, refine_pitch=refine_pitch,
                min_pitch=min_pitch, max_pitch=max_pitch, radius_map=rad)
        if not model.ok:
            use_pattern_model = False

    if use_pattern_model and model is not None:
        z = die_pattern_zscore(gray, model, mad_floor=mad_floor)
        if radial_detrend and np.any(roi):
            # 가장자리로 갈수록 전체가 밝아지는(또는 어두워지는) 성분 제거.
            depth = max(1, int(round(r_out - r_in)))
            rb = np.clip((rad - r_in).astype(np.int32), 0, depth)
            trend = np.zeros(depth + 1, np.float32)
            zb = rb[roi]
            zv = z[roi]
            order = np.argsort(zb, kind="stable")
            zb_s, zv_s = zb[order], zv[order]
            bounds = np.searchsorted(zb_s, np.arange(depth + 2))
            for k in range(depth + 1):
                seg = zv_s[bounds[k]:bounds[k + 1]]
                if seg.size:
                    trend[k] = float(np.median(seg))
            z = z - trend[rb]
        detect = (z >= float(z_threshold)) & roi
        soft = z >= float(z_threshold) * float(repeat_soft_ratio)
    else:
        detect = (gray >= int(gray_threshold)) & roi
        soft = gray >= int(gray_threshold)

    raw_mask = detect.astype(np.uint8) * 255

    # ---- 4) 성분 분해 + 필터 ---------------------------------------------
    num, labels, stats, cents = cv2.connectedComponentsWithStats(
        detect.astype(np.uint8), 8)

    px = float(model.pitch_x) if (model is not None and model.ok) else float(pitch_x or 0.0)
    py = float(model.pitch_y) if (model is not None and model.ok) else float(pitch_y or 0.0)
    steps = tuple(int(s) for s in repeat_steps if int(s) > 0)
    can_vote = bool(use_repeat_vote) and px >= 2.0 and py >= 2.0 and len(steps) > 0

    binary = np.zeros((h, w), np.uint8)
    particles: List[Dict[str, Any]] = []
    rejected: List[Dict[str, Any]] = []
    counts = {"area": 0, "shape": 0, "repeat": 0, "pass": 0}

    for lid in range(1, num):
        x1 = int(stats[lid, cv2.CC_STAT_LEFT])
        y1 = int(stats[lid, cv2.CC_STAT_TOP])
        bw = int(stats[lid, cv2.CC_STAT_WIDTH])
        bh = int(stats[lid, cv2.CC_STAT_HEIGHT])
        area = int(stats[lid, cv2.CC_STAT_AREA])
        x2 = x1 + bw - 1
        y2 = y1 + bh - 1
        ccx = float(cents[lid, 0])
        ccy = float(cents[lid, 1])

        reason = None
        if area < int(min_area_px) or area > int(max_area_px):
            reason = "area"
        else:
            aspect = float(max(bw, bh)) / float(max(1, min(bw, bh)))
            fill = float(area) / float(max(1, bw * bh))
            if aspect > float(max_aspect_ratio) or fill < float(min_fill_ratio):
                reason = "shape"
            elif can_vote:
                votes = 0
                total = 0
                for s in steps:
                    for dx, dy in ((s * px, 0.0), (-s * px, 0.0),
                                   (0.0, s * py), (0.0, -s * py)):
                        qx = int(round(ccx + dx))
                        qy = int(round(ccy + dy))
                        if not (1 <= qx < w - 1 and 1 <= qy < h - 1):
                            continue
                        if rad[qy, qx] > rr:
                            continue
                        total += 1
                        if bool(soft[qy - 1:qy + 2, qx - 1:qx + 2].any()):
                            votes += 1
                if total >= int(repeat_min_votes) and \
                        votes >= float(repeat_reject_ratio) * total:
                    reason = "repeat"

        if reason is not None:
            counts[reason] += 1
            if keep_rejected:
                rejected.append({
                    "id": lid, "reason": reason,
                    "center_px": (ccx, ccy),
                    "bbox_px": (x1, y1, x2, y2),
                    "corners_px": _bbox_corners(x1, y1, x2, y2),
                    "area_px": area,
                })
            continue

        comp = labels[y1:y2 + 1, x1:x2 + 1] == lid
        patch = gray[y1:y2 + 1, x1:x2 + 1]
        binary[y1:y2 + 1, x1:x2 + 1][comp] = 255
        aspect = float(max(bw, bh)) / float(max(1, min(bw, bh)))
        fill = float(area) / float(max(1, bw * bh))
        entry: Dict[str, Any] = {
            "id": len(particles),
            "center_px": (ccx, ccy),
            "bbox_px": (x1, y1, x2, y2),
            "corners_px": _bbox_corners(x1, y1, x2, y2),
            "area_px": area,
            "aspect_ratio": aspect,
            "fill_ratio": fill,
            "mean_intensity": float(patch[comp].mean()),
            "max_intensity": int(patch[comp].max()),
            "radius_from_wafer_center_px": float(math.hypot(ccx - cx, ccy - cy)),
        }
        if z is not None:
            zp = z[y1:y2 + 1, x1:x2 + 1][comp]
            entry["peak_z"] = float(zp.max())
            entry["mean_z"] = float(zp.mean())
        else:
            entry["peak_z"] = None
            entry["mean_z"] = None
        if die_map is not None:
            entry["die_index"] = (
                int(math.floor((ccx - die_map.x0) / die_map.pitch_x)),
                int(math.floor((die_map.y0 - ccy) / die_map.pitch_y)))
        else:
            entry["die_index"] = None
        particles.append(entry)
        counts["pass"] += 1

    result: Dict[str, Any] = {
        "binary": binary,
        "corners_px": [p["corners_px"] for p in particles],
        "particles": particles,
        "rejected": rejected,
        "rim": rim,
        "pattern": model,
        "roi_mask": roi_u8,
        "raw_mask": raw_mask,
        "zscore": z,
        "stats": {"total": int(num - 1), **counts},
        "radii_px": {
            "wafer_r": rr,
            "rim_inner": rim.inner_r, "rim_outer": rim.outer_r,
            "rim_peak": rim.peak_r,
            "roi_inner": r_in, "roi_outer": r_out,
        },
        "wafer_center_px": (cx, cy),
        "parameters": {
            "rim_bright_percentile": rim_bright_percentile,
            "rim_level": rim_level,
            "rim_clearance_px": rim_clearance_px,
            "search_depth_px": search_depth_px,
            "include_rim": include_rim,
            "min_area_px": min_area_px, "max_area_px": max_area_px,
            "max_aspect_ratio": max_aspect_ratio,
            "min_fill_ratio": min_fill_ratio,
            "use_pattern_model": use_pattern_model,
            "z_threshold": z_threshold, "mad_floor": mad_floor,
            "gray_threshold": gray_threshold,
            "radial_detrend": radial_detrend,
            "pattern_ref_ratio": pattern_ref_ratio,
            "auto_pitch": auto_pitch,
            "refine_pitch": refine_pitch,
            "pitch_seed": (model.pitch_seed if model is not None else (pitch_x, pitch_y)),
            "pitch_source": (model.pitch_source if model is not None else "given"),
            "pitch_used": (px, py),
            "pattern_quality": (model.quality if (model is not None and model.ok) else None),
            "use_repeat_vote": can_vote,
            "repeat_steps": steps,
            "repeat_soft_ratio": repeat_soft_ratio,
            "repeat_min_votes": repeat_min_votes,
            "repeat_reject_ratio": repeat_reject_ratio,
        },
    }
    result["overlay"] = (render_white_noise_overlay(bgr, result)
                         if with_overlay else None)
    return result


# =============================================================================
# [SECTOR: 74_PARTICLE_RENDERING] 합격/탈락 후보 overlay와 진단 시각화
# 4) 시각화
# =============================================================================
def render_white_noise_overlay(image: Union[str, Path, np.ndarray],
                               result: Dict[str, Any],
                               *,
                               box_color: Tuple[int, int, int] = (0, 0, 255),
                               ring_color: Optional[Tuple[int, int, int]] = (255, 255, 0),
                               rim_color: Optional[Tuple[int, int, int]] = (0, 255, 255),
                               thickness: int = 1,
                               pad_px: int = 1,
                               draw_index: bool = False) -> np.ndarray:
    """원본에 노이즈 위치를 표시한 이미지."""
    out = _noise_load_bgr(image).copy()
    cx, cy = result["wafer_center_px"]
    rr = result["radii_px"]
    if rim_color is not None and result["rim"].found:
        for r in (rr["rim_inner"], rr["rim_outer"]):
            cv2.circle(out, (int(round(cx)), int(round(cy))), int(round(r)),
                       rim_color, 1, cv2.LINE_AA)
    if ring_color is not None:
        for r in (rr["roi_inner"], rr["roi_outer"]):
            cv2.circle(out, (int(round(cx)), int(round(cy))), int(round(r)),
                       ring_color, 1, cv2.LINE_AA)
    for p in result["particles"]:
        x1, y1, x2, y2 = p["bbox_px"]
        cv2.rectangle(out, (x1 - pad_px, y1 - pad_px), (x2 + pad_px, y2 + pad_px),
                      box_color, thickness)
        if draw_index:
            cv2.putText(out, str(p["id"]), (x1, max(0, y1 - 2)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.3, box_color, 1, cv2.LINE_AA)
    return out


_NOISE_REASON_COLOR = {
    "pass":   (0, 0, 255),      # 빨강 — 노이즈로 채택
    "repeat": (0, 165, 255),    # 주황 — 주기성 투표에서 die 패턴으로 판정
    "shape":  (255, 0, 0),      # 파랑 — 가늘고 긴 조각
    "area":   (128, 128, 128),  # 회색 — 크기 범위 밖
}


def render_white_noise_diagnostic_overlay(image: Union[str, Path, np.ndarray],
                                          result: Dict[str, Any],
                                          *,
                                          pad_px: int = 1,
                                          draw_legend: bool = True
                                          ) -> np.ndarray:
    """튜닝용 — 탈락 사유별 색으로 전부 그린다.

    keep_rejected=True 로 검사해야 탈락분이 나온다.
    빨강=채택 / 주황=die 패턴(주기성) / 파랑=모양 / 회색=크기.
    """
    out = render_white_noise_overlay(image, result, box_color=(0, 0, 255),
                                     pad_px=pad_px)
    for r in result.get("rejected", []):
        x1, y1, x2, y2 = r["bbox_px"]
        cv2.rectangle(out, (x1 - pad_px, y1 - pad_px), (x2 + pad_px, y2 + pad_px),
                      _NOISE_REASON_COLOR.get(r["reason"], (200, 200, 200)), 1)
    if draw_legend:
        y = 18
        for key in ("pass", "repeat", "shape", "area"):
            n = (result["stats"].get(key, 0) if key != "pass"
                 else result["stats"].get("pass", 0))
            cv2.putText(out, "%-7s %d" % (key, n), (10, y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45,
                        _NOISE_REASON_COLOR[key], 1, cv2.LINE_AA)
            y += 16
    return out


# ---------------------------------------------------------------- 한 번에 부르기
# [SECTOR: 75_ONE_STEP_API] detect_white_noise() — die map 생성과 particle 검사를 한 번에
def detect_white_noise(image: Union[str, Path, np.ndarray],
                       *,
                       die_map: Optional["WaferDieMap"] = None,
                       die_map_kwargs: Optional[Dict[str, Any]] = None,
                       **noise_kwargs) -> Dict[str, Any]:
    """이미지 한 장 -> die map 생성 + 흰 노이즈 검출을 한 번에.

    `build_die_map()` -> `inspect_white_noise_inside_rim()` 2단계를 묶은
    편의 함수다. 두 단계를 따로 제어하고 싶으면 원래 함수들을 직접 부르면 된다.

    Parameters
    ----------
    image          : wafer 이미지 경로(str/Path, 한글 경로 OK) 또는 BGR ndarray
    die_map        : 이미 만들어 둔 die map. 주면 새로 만들지 않는다.
    die_map_kwargs : `build_die_map()` 에 넘길 옵션.
                     `DEFAULT_NOISE_DIE_MAP_KWARGS` 위에 덮어쓴다.
    **noise_kwargs : `inspect_white_noise_inside_rim()` 의 모든 옵션
                     (`search_depth_px`, `min_area_px`, `z_threshold` 등)

    Returns
    -------
    `inspect_white_noise_inside_rim()` 의 반환 dict 에 두 키가 추가된다.

    - `die_map`          : 사용한 `WaferDieMap`
    - `die_map_kwargs`   : 실제로 적용된 build_die_map 옵션 (die_map 을
                           직접 준 경우 None)

    주요 반환값은 그대로다 — `binary`(이진화), `corners_px`(외곽 4포인트),
    `overlay`(원본에 표기한 이미지).

    Notes
    -----
    기본 die map 옵션은 **회전 보정을 끈다**(`angle_align_method="none"`).
    회전을 켜면 die map 좌표가 회전된 이미지 기준이 되어 여기서 검사하는
    입력 이미지와 어긋나기 때문이다. 회전이 필요한 영상이라면 먼저 정렬한
    이미지를 만들어 그것을 넣을 것.

    Examples
    --------
    >>> res = detect_white_noise("22.png")
    >>> res["binary"].shape, len(res["corners_px"])
    >>> res = detect_white_noise("22.png", min_area_px=12, search_depth_px=80)
    >>> res = detect_white_noise(bgr, die_map_kwargs=dict(max_pitch=120))
    """
    bgr = _noise_load_bgr(image)

    used_kwargs = None
    if die_map is None:
        used_kwargs = dict(DEFAULT_NOISE_DIE_MAP_KWARGS)
        if die_map_kwargs:
            used_kwargs.update(die_map_kwargs)
        die_map = build_die_map(bgr, **used_kwargs)
    elif die_map_kwargs:
        raise ValueError("die_map 을 직접 주면 die_map_kwargs 는 쓸 수 없다")

    result = inspect_white_noise_inside_rim(bgr, die_map, **noise_kwargs)
    result["die_map"] = die_map
    result["die_map_kwargs"] = used_kwargs
    return result


# =============================================================================
# [SECTOR: 90_USAGE_REFERENCE] 호출 예시와 반환값 레퍼런스 — 수정 없이 복사해 사용
# 사용 예시  (복붙해서 쓰는 파일이라 자동 실행 안 되도록 주석 처리해 둠.
#            그대로 본인 코드에서 호출하면 됩니다.)
# =============================================================================
#
#   # 1) wafer 이미지 -> die map (EDGE 포함)
#   dm = build_die_map("wafer.jpg", grid_method="corner",
#                      pixel_per_unit=32, include_edge=True)
#   print(dm.num_dies, dm.pitch_x, dm.pitch_y, (dm.x0, dm.y0))
#
#   # 2-a) 픽셀 좌표로 조회
#   r1 = locate_die(dm, point=(5499, 4700))
#   print(r1["die_index"], r1["die_rect_px"], r1["real_coord"])
#
#   # 2-b) BBox(YOLO box, x1,y1,x2,y2) 로 조회 (중심 기준)
#   r2 = locate_die(dm, bbox=(4880, 5080, 4980, 5180))
#   print(r2["die_index"], r2["die_rect_px"], r2["real_coord"],
#         r2["wafer_center_px"], r2["corner_px"])
#
#   # 3) offset(위치 보정) + margin(die 사이 street 포함) 으로 더 넓게 crop
#   #    - offset_x/y : 미세 정렬 오차 보정 (px)
#   #    - margin_x/y : 각 변으로 더 포함할 영역 (px)  ← die 간격만큼 더 따고 싶을 때
#   r3 = locate_die(dm, bbox=(4880, 5080, 4980, 5180),
#                   offset_x=0, offset_y=0, margin_x=8, margin_y=8)
#   x1, y1, x2, y2 = r3["crop_rect_px"]          # 확장된 crop 영역
#   patch = crop_die(img_bgr, *r3["die_center_px"], dm.die_w, dm.die_h,
#                    margin_x=8, margin_y=8)      # 또는 직접 crop (clip_die 재사용)
#
#   # build_die_map 단계에서 일괄로 margin/offset crop 을 받으려면:
#   dm2 = build_die_map("wafer.jpg", with_crops=True, margin_x=8, margin_y=8)
#   #   -> 각 entry["image"] 가 margin 포함 crop, entry["crop_rect_px"] 가 그 영역
#
#   # 4) ★ 회전(angle) 보정 — 기본 ON (V5 기본 방식 = "die_render"). 연산 전에 자동 수행
#   dm = build_die_map("wafer_rotated.jpg")        # angle_align_method="die_render" 기본
#   print(dm.rotation_deg)                          # 적용된 보정 각도 (0 = 보정 없음)
#   img_use = dm.aligned_image                      # ★ 항상 채워짐 = 좌표 기준 이미지!
#   #   crop / YOLO / 시각화는 모두 img_use(=dm.aligned_image) 에서 해야 좌표가 맞음
#
#   # 4-a) 회전 보정 방식 선택 (die_render 기본 / notch / vertical_line / none)
#   dm = build_die_map("wafer.jpg", angle_align_method="notch")
#   dm = build_die_map("wafer.jpg", angle_align_method="vertical_line")
#
#   # 4-b) 각도만 따로 쓰고 싶을 때 (YOLO 전에 이미지부터 정렬)
#   aligned, deg = align_wafer_by_die_render(img_bgr)   # 또는 align_wafer_by_notch(...)
#   dm = build_die_map(aligned, angle_align_method="none")  # 이미 정렬 -> 보정 OFF
#
#   # 5) ★ EDGE die 구분 — is_edge 기준 선택 (둘 다 entry 에 저장됨)
#   dm = build_die_map("wafer.jpg", edge_mode="circle")  # 부분 die(원 밖) / 기본
#   dm = build_die_map("wafer.jpg", edge_mode="ring")    # 격자 최외곽 줄
#   dm = build_die_map("wafer.jpg", edge_mode="both")    # 둘 중 하나라도면 edge
#   r = locate_die(dm, point=(5499, 4700))
#   print(r["is_edge"], r["is_edge_partial"], r["is_edge_ring"], r["edge_mode"])
#
#   # 5-a) ★ EDGE die 전부 clip (기본 ON) — 중심이 원 밖이어도 사각형이 걸치면 포함
#   dm = build_die_map("wafer.jpg")                          # edge_clip_all=True 기본
#   dm = build_die_map("wafer.jpg", edge_clip_all=False)     # 예전 방식(중심 기준)
#   #   경계를 살짝만 스치는 '거의 빈' die 를 빼고 싶으면 최소 겹침(px)을 올린다
#   dm = build_die_map("wafer.jpg", edge_overlap_min_px=20)  # 20px 이상 걸친 것만
#
#   # 6) ★[V5.2] grid origin 서브픽셀 보정 — street 십자 교차점의 '진짜' 중심
#   #    기본 ON. 밝기 무게중심 origin 이 한쪽 die 가 밝을 때 밀리는 문제를
#   #    phase folding + half-max 교차점 중점으로 잡아준다.
#   dm = build_die_map("wafer.jpg")                       # refine_origin=True 기본
#   print(dm.origin_refined, dm.origin_shift_px)          # 보정 여부 / 움직인 (dx,dy) px
#   print(dm.x0, dm.y0)                                   # ★ float (서브픽셀)
#   print(dm.street_w, dm.street_h)                       # 측정된 street 폭 (0 = 실패)
#   dm = build_die_map("wafer.jpg", refine_origin=False)  # 예전(무게중심) 방식
#
#   # 6-a) ★[V5.2] 순수 die crop — street(여백) 폭만큼 안쪽으로 줄여서 자르기
#   #      기본 rect 는 pitch 크기라 이웃 street 가 테두리에 묻는다. 이걸 없앤다.
#   dm = build_die_map("wafer.jpg", exclude_street=True)
#   print(dm.effective_die_size())        # (die_w-street_w, die_h-street_h)
#   d = dm.get_die(0, 0)
#   print(d["rect_px"], d["center_px_f"]) # rect 는 street 제외 / 중심은 서브픽셀 float
#   #   NOTE: die 인덱스/개수는 exclude_street 와 무관하게 그대로 유지된다
#   #         (원 포함 판정은 항상 pitch 크기 rect 로 하기 때문)
#
#   # 6-b) origin 보정만 따로 쓰고 싶을 때
#   px, py, gx0, gy0 = detect_corner_grid(img_bgr, wcx, wcy, wr)
#   ro = refine_grid_origin(img_bgr, wcx, wcy, wr, px, py, gx0, gy0)
#   print(ro["x0"], ro["y0"], ro["street_w"], ro["street_h"], ro["refined"])

# =============================================================================
# 반환값 정리  (각 함수가 돌려주는 값 레퍼런스)
# =============================================================================
#
# [1] build_die_map(...) -> WaferDieMap  (필드)
#     wafer_cx        # int  : 웨이퍼 중심 X 픽셀 (검출값)
#     wafer_cy        # int  : 웨이퍼 중심 Y 픽셀 (검출값)
#     wafer_r         # int  : 웨이퍼 반지름 픽셀
#     pitch_x         # float: die 가로 간격(px, sub-pixel) ← 한 die 의 폭
#     pitch_y         # float: die 세로 간격(px, sub-pixel) ← 한 die 의 높이
#     x0              # float: ★[V5.2] 격자 코너(원점) X 픽셀 (서브픽셀) ← die(0,0) 기준점
#     y0              # float: ★[V5.2] 격자 코너(원점) Y 픽셀 (서브픽셀)
#     die_w           # float: ★[V5.2] die 폭  = pitch_x (반올림은 rect 만들 때 한 번만)
#     die_h           # float: ★[V5.2] die 높이 = pitch_y
#     pixel_per_unit  # int  : 실측 좌표 환산 단위 (px/unit). 32 → 32px = 1unit
#     image_shape     # (H,W): 원본 이미지 크기
#     num_dies        # int  : die 총 개수 (property)
#     dies            # list : die entry(dict) 리스트 (아래 [1-a] 참고)
#     dies_by_index   # dict : {(ix,iy): entry} 빠른 조회용
#     get_die(ix,iy)  # method: entry 또는 None 반환
#     rotation_deg    # float: ★ 회전 보정으로 적용된 각도 (0 = 보정 없음). 기본 die_render
#     aligned_image   # ndarray: ★ 항상 채워짐 = clean+align 후 실제 사용 이미지(CUBIC 회전).
#                     #   모든 좌표는 이 이미지 기준 -> crop/YOLO 에 반드시 이걸 사용
#     angle_confidence# float: ★[고도화] 각도 신뢰도 0~1 (projection·FFT 합의 기반)
#     angle_agree     # bool : ★[고도화] projection 과 FFT 가 합의했는지 (False면 의심 -> 검토)
#     edge_mode       # str  : ★ is_edge 가 가리키는 기준 ("circle"|"ring"|"both")
#     street_w        # float: ★[V5.2] 측정된 세로 street(die 사이 여백) 폭 px (0 = 측정 실패)
#     street_h        # float: ★[V5.2] 측정된 가로 street 높이 px (0 = 측정 실패)
#     exclude_street  # bool : ★[V5.2] rect/crop 이 street 를 뺀 '순수 die' 영역인지
#     origin_refined  # bool : ★[V5.2] origin 서브픽셀 보정이 실제로 적용됐는지
#     origin_shift_px # (dx,dy): ★[V5.2] 보정으로 움직인 양 px (예전 무게중심 대비 편차)
#     effective_die_size()  # method: rect/crop 에 실제 쓰이는 (w,h) float
#                     #   exclude_street=True 면 (die_w-street_w, die_h-street_h)
#
# [1-a] dies 안의 die entry(dict) 하나의 형식
#     "index"        # (ix,iy)        die 격자 인덱스 (오른쪽 +ix, 위쪽 +iy, 코너 위-오른쪽=(0,0))
#     "center_px"    # (cx,cy)        die 중심 픽셀 좌표 (반올림된 int)
#     "center_px_f"  # (cxf,cyf)      ★[V5.2] die 중심 서브픽셀 좌표 (float) — 정밀 계산용
#     "rect_px"      # (x1,y1,x2,y2)  die 사각 영역(좌상~우하) 픽셀 좌표. 중심 기준 좌우/상하 대칭.
#                    #                exclude_street=True 면 street 를 뺀 '순수 die' 영역
#     "crop_rect_px" # (x1,y1,x2,y2)  offset/margin 적용된 crop 영역 (margin=offset=0이면 rect_px와 동일)
#     "real_coord"   # (rx,ry)        die 중심의 실측 좌표
#                    #                = ((cx-wafer_cx)/ppu, (wafer_cy-cy)/ppu), 위쪽 +y
#     "is_edge_partial" # bool        ★정의① die 사각형이 wafer 원 밖으로 일부라도 나감
#     "is_edge_ring"    # bool        ★정의② 격자에서 8방향 이웃이 다 차 있지 않은 최외곽 줄
#     "is_edge"      # bool           ★ edge_mode 가 가리키는 값(circle→partial/ring→ring/both→OR)
#     "image"        # np.ndarray     crop_rect_px 영역 crop (with_crops=True 일 때만 존재)
#
# [2] locate_die(...) -> dict  (키)
#     "input_type"     # str          "point" | "bbox" (어떤 입력으로 조회했는지)
#     "query_px"       # (qx,qy)      실제 조회에 쓴 픽셀 좌표 (bbox면 그 중심)
#     "die_index"      # (ix,iy)      그 좌표가 속한 die 의 격자 인덱스
#     "die_center_px"  # (cx,cy)      그 die 의 중심 픽셀 좌표 (반올림된 int)
#     "die_center_px_f"# (cxf,cyf)    ★[V5.2] 그 die 의 중심 서브픽셀 좌표 (float)
#     "die_rect_px"    # (x1,y1,x2,y2) 그 die 의 사각 영역(좌상~우하). 중심 기준 대칭.
#                      #               exclude_street=True 면 street 제외된 순수 die 영역
#     "crop_rect_px"   # (x1,y1,x2,y2) offset/margin 적용된 crop 영역 (die 사이 street 포함용)
#     "real_coord"     # (rx,ry)      조회 좌표(=bbox면 중심)의 실측 좌표
#                      #              = ((qx-wafer_cx)/ppu, (wafer_cy-qy)/ppu), 위쪽 +y
#     "real_distance"  # float        웨이퍼 중심으로부터의 실측 거리(스칼라) = hypot(rx,ry)
#     "die_real_coord" # (drx,dry)    참고용 — die '중심' 기준 실측 좌표
#     "wafer_center_px"# (wcx,wcy)    웨이퍼 중심점 (검출값) = (dm.wafer_cx, dm.wafer_cy)
#     "corner_px"      # (x0,y0)      격자 코너(원점) 점 (검출값) = (dm.x0, dm.y0)
#     "is_edge"        # bool         ★ edge_mode 가 가리키는 edge 여부
#     "is_edge_partial"# bool         ★정의① die 가 wafer 원 밖으로 일부 나감(부분 die)
#     "is_edge_ring"   # bool         ★정의② 격자 최외곽(8방향 이웃 결손)
#     "edge_mode"      # str          ★ 이 맵의 is_edge 기준 ("circle"|"ring"|"both")
#     "in_wafer"       # bool         조회 좌표가 웨이퍼 원 '안'인지 (밖이어도 index 는 계산됨)
