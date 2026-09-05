from pathlib import Path
import sys

import pandas as pd


# =========================================================
# 1. 경로
# =========================================================

BASE_DIR = Path(__file__).resolve().parent.parent

PROCESSED_DIR = (
    BASE_DIR
    / "data"
    / "processed"
)


# 공공임대 병합 전
BEFORE_FILE = (
    PROCESSED_DIR
    / "청년주거환경_정책통합분석_공공시설반영.csv"
)


# 공공임대 병합 후
AFTER_FILE = (
    PROCESSED_DIR
    / "청년주거환경_정책통합분석_공공시설_공공임대반영.csv"
)


EXPECTED_TOTAL_RENTAL = 22855

EXPECTED_CANDIDATES = {
    "서구 치평동",
    "서구 풍암동",
    "남구 진월동"
}


errors = []
warnings = []


# =========================================================
# 2. 도움 함수
# =========================================================

def add_error(message):
    errors.append(message)


def add_warning(message):
    warnings.append(message)


def to_bool(value):

    if isinstance(value, bool):
        return value

    return str(value).strip().lower() in [
        "true",
        "1",
        "yes",
        "y"
    ]


# =========================================================
# 3. 파일 확인
# =========================================================

print()
print("=" * 55)
print("공공임대 반영 정책통합 최종 품질검사")
print("=" * 55)


if not BEFORE_FILE.exists():

    print()
    print("기존 정책통합 파일이 없습니다.")
    print(BEFORE_FILE)

    sys.exit(1)


if not AFTER_FILE.exists():

    print()
    print("공공임대 반영 파일이 없습니다.")
    print(AFTER_FILE)

    sys.exit(1)


# =========================================================
# 4. 파일 읽기
# =========================================================

before = pd.read_csv(
    BEFORE_FILE,
    encoding="utf-8-sig"
)


after = pd.read_csv(
    AFTER_FILE,
    encoding="utf-8-sig"
)


# =========================================================
# 5. 기본 지역 수
# =========================================================

if len(before) != 25:

    add_error(
        f"병합 전 데이터가 25개 동이 아닙니다. "
        f"현재 {len(before)}개"
    )


if len(after) != 25:

    add_error(
        f"병합 후 데이터가 25개 동이 아닙니다. "
        f"현재 {len(after)}개"
    )


# =========================================================
# 6. 지역 중복
# =========================================================

if before["지역"].duplicated().any():

    add_error(
        "병합 전 파일에 중복 지역이 있습니다."
    )


if after["지역"].duplicated().any():

    add_error(
        "병합 후 파일에 중복 지역이 있습니다."
    )


# =========================================================
# 7. 기존 25개 지역이 그대로 유지됐는지
# =========================================================

before_regions = set(
    before["지역"]
)


after_regions = set(
    after["지역"]
)


if before_regions != after_regions:

    add_error(
        "공공임대 병합 과정에서 "
        "지역 목록이 변경되었습니다."
    )


# =========================================================
# 8. 기존 컬럼 값이 바뀌지 않았는지 검사
#
# 공공임대는 보조지표이므로
# 기존 정책결과를 변경하면 안 됨
# =========================================================

before_sorted = (
    before
    .sort_values("지역")
    .reset_index(drop=True)
)


after_sorted = (
    after
    .sort_values("지역")
    .reset_index(drop=True)
)


existing_columns = list(
    before.columns
)


missing_old_columns = [

    column

    for column in existing_columns

    if column not in after.columns
]


if missing_old_columns:

    add_error(
        "기존 컬럼이 사라졌습니다 : "
        + ", ".join(
            missing_old_columns
        )
    )


else:

    try:

        pd.testing.assert_frame_equal(

            before_sorted[
                existing_columns
            ],

            after_sorted[
                existing_columns
            ],

            check_dtype=False,

            check_exact=False,

            rtol=1e-10,

            atol=1e-10

        )

    except AssertionError:

        add_error(
            "공공임대 병합 과정에서 "
            "기존 정책분석 값이 변경되었습니다."
        )


# =========================================================
# 9. 공공임대 필수 컬럼
# =========================================================

required_rental_columns = [

    "공공임대_세대수",

    "공공임대_1000명당",

    "행복주택_세대수",

    "청년주거지원_점검후보",

    "공공임대_수요대비점검후보",

    "공공임대_HL반영여부",

    "공공임대지표_역할",

    "주거지원_보조근거",

    "정책_주거지원_통합신호",

    "공공임대_정책유형변경여부"
]


missing = [

    column

    for column in required_rental_columns

    if column not in after.columns
]


if missing:

    add_error(
        "공공임대 필수 컬럼 누락 : "
        + ", ".join(
            missing
        )
    )


# =========================================================
# 아래 검사는 필수 컬럼이 있을 때만 진행
# =========================================================

if not missing:


    # =====================================================
    # 10. 공공임대 누락값
    # =====================================================

    if (
        after[
            "공공임대_세대수"
        ]
        .isna()
        .any()
    ):

        add_error(
            "공공임대 세대수가 비어 있는 지역이 있습니다."
        )


    # =====================================================
    # 11. 전체 세대수
    # =====================================================

    total_rental = int(

        pd.to_numeric(
            after[
                "공공임대_세대수"
            ],
            errors="coerce"
        )

        .fillna(0)

        .sum()

    )


    if total_rental != EXPECTED_TOTAL_RENTAL:

        add_error(
            f"공공임대 전체 세대수가 "
            f"{EXPECTED_TOTAL_RENTAL:,}세대가 아닙니다. "
            f"현재 {total_rental:,}세대"
        )


    # =====================================================
    # 12. 청년주거지원 후보
    # =====================================================

    after[
        "청년주거지원_점검후보"
    ] = (

        after[
            "청년주거지원_점검후보"
        ]

        .apply(
            to_bool
        )

    )


    actual_candidates = set(

        after[
            after[
                "청년주거지원_점검후보"
            ]
            == True
        ][
            "지역"
        ]

    )


    if actual_candidates != EXPECTED_CANDIDATES:

        add_error(
            "청년주거지원 점검후보가 "
            "예상 결과와 다릅니다. "
            f"현재: {sorted(actual_candidates)}"
        )


    # =====================================================
    # 13. 공공임대가 HL에 들어갔는지 검사
    # =====================================================

    after[
        "공공임대_HL반영여부"
    ] = (

        after[
            "공공임대_HL반영여부"
        ]

        .apply(
            to_bool
        )

    )


    if (
        after[
            "공공임대_HL반영여부"
        ]
        .any()
    ):

        add_error(
            "공공임대가 HL-Score에 "
            "반영된 지역이 있습니다."
        )


    # =====================================================
    # 14. 기존 정책유형 변경 여부
    # =====================================================

    after[
        "공공임대_정책유형변경여부"
    ] = (

        after[
            "공공임대_정책유형변경여부"
        ]

        .apply(
            to_bool
        )

    )


    if (
        after[
            "공공임대_정책유형변경여부"
        ]
        .any()
    ):

        add_error(
            "공공임대로 인해 기존 정책유형이 "
            "변경된 지역이 있습니다."
        )


    # =====================================================
    # 15. 두암2동 확인
    # =====================================================

    duam = after[
        after[
            "지역"
        ]
        == "북구 두암2동"
    ]


    if len(duam) != 1:

        add_error(
            "북구 두암2동을 정확히 찾을 수 없습니다."
        )


    else:

        duam_type = str(
            duam.iloc[0][
                "최종정책유형"
            ]
        ).strip()


        if duam_type != "HL순위 제외":

            add_error(
                "두암2동의 HL순위 제외 상태가 "
                "변경되었습니다."
            )


    # =====================================================
    # 16. 풍암동 확인
    # =====================================================

    pungam = after[
        after[
            "지역"
        ]
        == "서구 풍암동"
    ]


    if len(pungam) == 1:

        row = pungam.iloc[0]


        if str(
            row[
                "최종정책유형"
            ]
        ).strip() != "복합 최우선 검토":

            add_error(
                "풍암동 기존 정책유형이 "
                "변경되었습니다."
            )


        if not to_bool(
            row[
                "청년주거지원_점검후보"
            ]
        ):

            add_error(
                "풍암동 공공임대 점검후보 신호가 "
                "누락되었습니다."
            )


    # =====================================================
    # 17. 진월동 확인
    # =====================================================

    jinwol = after[
        after[
            "지역"
        ]
        == "남구 진월동"
    ]


    if len(jinwol) == 1:

        row = jinwol.iloc[0]


        if str(
            row[
                "최종정책유형"
            ]
        ).strip() != "복합 관심 검토":

            add_error(
                "진월동 기존 정책유형이 "
                "변경되었습니다."
            )


    # =====================================================
    # 18. 치평동 확인
    # =====================================================

    chipyeong = after[
        after[
            "지역"
        ]
        == "서구 치평동"
    ]


    if len(chipyeong) == 1:

        row = chipyeong.iloc[0]


        if str(
            row[
                "최종정책유형"
            ]
        ).strip() != "일반 관찰":

            add_error(
                "치평동 기존 정책유형이 "
                "변경되었습니다."
            )


        if not to_bool(
            row[
                "청년주거지원_점검후보"
            ]
        ):

            add_error(
                "치평동 주거지원 점검신호가 "
                "누락되었습니다."
            )


# =========================================================
# 19. 결과 출력
# =========================================================

print()
print("----------------------------------------")
print("검사 요약")
print("----------------------------------------")

print(
    f"병합 전 지역 : "
    f"{len(before)}개"
)

print(
    f"병합 후 지역 : "
    f"{len(after)}개"
)


if "공공임대_세대수" in after.columns:

    print(
        f"전체 공공임대 : "
        f"{int(pd.to_numeric(after['공공임대_세대수'], errors='coerce').fillna(0).sum()):,}세대"
    )


if "청년주거지원_점검후보" in after.columns:

    candidates = after[
        after[
            "청년주거지원_점검후보"
        ].apply(
            to_bool
        )
    ]


    print(
        f"청년주거지원 점검후보 : "
        f"{len(candidates)}개"
    )


    for region in candidates[
        "지역"
    ].tolist():

        print(
            "-",
            region
        )


# =========================================================
# 20. 최종 판정
# =========================================================

print()
print("=" * 55)
print("최종 품질검사 결과")
print("=" * 55)


if warnings:

    print()
    print("[주의]")

    for warning in warnings:

        print(
            "!",
            warning
        )


if errors:

    print()
    print("[검사 실패]")

    for error in errors:

        print(
            "X",
            error
        )


    print()
    print(
        f"총 오류 : "
        f"{len(errors)}개"
    )


    print()
    print(
        "공공임대 정책통합 품질검사 : FAIL"
    )

    sys.exit(1)


else:

    print()
    print(
        "모든 핵심 검사 통과"
    )

    print(
        "기존 HL-Score와 정책유형이 "
        "그대로 유지되었습니다."
    )

    print(
        "공공임대 22,855세대가 "
        "25개 동에 정상 연결되었습니다."
    )

    print(
        "청년주거지원 점검후보도 "
        "3개 지역으로 정상 확인되었습니다."
    )

    print(
        "두암2동 HL순위 제외 상태도 "
        "그대로 유지되었습니다."
    )


    if not warnings:

        print(
            "추가 경고사항도 없습니다."
        )


    print()
    print(
        "공공임대 정책통합 품질검사 : PASS"
    )