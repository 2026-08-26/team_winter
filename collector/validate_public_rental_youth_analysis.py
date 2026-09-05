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

INPUT_FILE = (
    PROCESSED_DIR
    / "2030_청년인구_대비_공공임대_분석.csv"
)


# =========================================================
# 2. 현재 확정값
# =========================================================

EXPECTED_REGION_COUNT = 25
EXPECTED_TOTAL_RENTAL = 22855
EXPECTED_CANDIDATES = 3


# =========================================================
# 3. 검사 결과
# =========================================================

errors = []
warnings = []


def add_error(message):
    errors.append(message)


def add_warning(message):
    warnings.append(message)


# =========================================================
# 4. Boolean 변환
# =========================================================

def to_bool(value):

    if isinstance(value, bool):
        return value

    text = str(value).strip().lower()

    return text in [
        "true",
        "1",
        "yes",
        "y"
    ]


# =========================================================
# 5. 데이터 읽기
# =========================================================

if not INPUT_FILE.exists():

    print()
    print("분석 파일이 없습니다.")
    print(INPUT_FILE)

    sys.exit(1)


df = pd.read_csv(
    INPUT_FILE,
    encoding="utf-8-sig"
)


print()
print("=" * 50)
print("공공임대 청년인구 대비 분석 품질검사")
print("=" * 50)


# =========================================================
# 6. 필수 컬럼
# =========================================================

required_columns = [

    "지역",
    "2030인구수",

    "공공임대_세대수",
    "매입임대_세대수",
    "국민임대_세대수",
    "행복주택_세대수",
    "영구임대_세대수",

    "공공임대_1000명당",
    "매입임대_1000명당",
    "국민임대_1000명당",
    "행복주택_1000명당",
    "영구임대_1000명당",

    "공공임대_상대부족",

    "2030인구_TOP10",

    "공공임대_수요대비점검후보",

    "행복주택_공급없음",

    "행복주택_공급공백_TOP10",

    "청년주거지원_점검후보",

    "공공임대_HL반영여부",

    "공공임대지표_역할"
]


missing = [

    column

    for column in required_columns

    if column not in df.columns
]


if missing:

    add_error(
        "필수 컬럼 누락 : "
        + ", ".join(missing)
    )


if errors:

    print()
    print("[검사 실패]")

    for error in errors:
        print("X", error)

    sys.exit(1)


# =========================================================
# 7. Boolean 정리
# =========================================================

bool_columns = [

    "공공임대_상대부족",

    "2030인구_TOP10",

    "공공임대_수요대비점검후보",

    "행복주택_공급없음",

    "행복주택_공급공백_TOP10",

    "청년주거지원_점검후보",

    "공공임대_HL반영여부"
]


for column in bool_columns:

    df[column] = (
        df[column]
        .apply(to_bool)
    )


# =========================================================
# 8. 숫자형 변환
# =========================================================

numeric_columns = [

    "2030인구수",

    "공공임대_세대수",

    "매입임대_세대수",

    "국민임대_세대수",

    "행복주택_세대수",

    "영구임대_세대수",

    "공공임대_1000명당",

    "매입임대_1000명당",

    "국민임대_1000명당",

    "행복주택_1000명당",

    "영구임대_1000명당"
]


for column in numeric_columns:

    df[column] = pd.to_numeric(
        df[column],
        errors="coerce"
    )


# =========================================================
# 9. 25개 동 검사
# =========================================================

if len(df) != EXPECTED_REGION_COUNT:

    add_error(
        f"분석지역이 25개가 아닙니다. "
        f"현재 {len(df)}개"
    )


# =========================================================
# 10. 지역 중복
# =========================================================

duplicate = df[
    df["지역"].duplicated(
        keep=False
    )
]


if not duplicate.empty:

    add_error(
        "중복 지역 : "
        + ", ".join(
            duplicate["지역"]
            .unique()
        )
    )


# =========================================================
# 11. 전체 세대수
# =========================================================

total_rental = int(
    df[
        "공공임대_세대수"
    ].sum()
)


if total_rental != EXPECTED_TOTAL_RENTAL:

    add_error(
        f"전체 공공임대 세대수가 "
        f"{EXPECTED_TOTAL_RENTAL:,}세대가 아닙니다. "
        f"현재 {total_rental:,}세대"
    )


# =========================================================
# 12. 1,000명당 계산 검증
# =========================================================

rate_pairs = {

    "공공임대_세대수":
        "공공임대_1000명당",

    "매입임대_세대수":
        "매입임대_1000명당",

    "국민임대_세대수":
        "국민임대_1000명당",

    "행복주택_세대수":
        "행복주택_1000명당",

    "영구임대_세대수":
        "영구임대_1000명당"
}


for count_col, rate_col in rate_pairs.items():

    expected = (

        df[count_col]
        /
        df["2030인구수"]
        *
        1000

    ).round(2)


    difference = (
        expected
        -
        df[rate_col]
    ).abs()


    mismatch = df[
        difference > 0.01
    ]


    if not mismatch.empty:

        add_error(
            f"{rate_col} 계산 불일치 지역 : "
            + ", ".join(
                mismatch["지역"]
                .tolist()
            )
        )


# =========================================================
# 13. 중앙값 및 상대부족
# =========================================================

median_rate = (
    df[
        "공공임대_1000명당"
    ]
    .median()
)


expected_shortage = (

    df[
        "공공임대_1000명당"
    ]

    < median_rate

)


shortage_mismatch = df[
    expected_shortage
    !=
    df[
        "공공임대_상대부족"
    ]
]


if not shortage_mismatch.empty:

    add_error(
        "공공임대 상대부족 판정 불일치 : "
        + ", ".join(
            shortage_mismatch[
                "지역"
            ].tolist()
        )
    )


# =========================================================
# 14. 2030 인구 TOP10
# =========================================================

expected_top10 = set(

    df

    .sort_values(
        "2030인구수",
        ascending=False
    )

    .head(10)[
        "지역"
    ]

)


actual_top10 = set(

    df[
        df[
            "2030인구_TOP10"
        ]
        == True
    ][
        "지역"
    ]

)


if len(actual_top10) != 10:

    add_error(
        f"2030인구 TOP10이 "
        f"10곳이 아닙니다. "
        f"현재 {len(actual_top10)}곳"
    )


if expected_top10 != actual_top10:

    add_error(
        "2030 인구 TOP10 표시가 "
        "실제 인구순위와 다릅니다."
    )


# =========================================================
# 15. 행복주택 공급없음
# =========================================================

expected_no_happy = (

    df[
        "행복주택_세대수"
    ]
    == 0

)


happy_mismatch = df[
    expected_no_happy
    !=
    df[
        "행복주택_공급없음"
    ]
]


if not happy_mismatch.empty:

    add_error(
        "행복주택 공급없음 판정 불일치 : "
        + ", ".join(
            happy_mismatch[
                "지역"
            ].tolist()
        )
    )


# =========================================================
# 16. 공공임대 수요대비 점검후보
#
# TOP10 AND 상대부족
# =========================================================

expected_demand_candidate = (

    df[
        "2030인구_TOP10"
    ]

    &

    df[
        "공공임대_상대부족"
    ]

)


candidate_mismatch = df[
    expected_demand_candidate
    !=
    df[
        "공공임대_수요대비점검후보"
    ]
]


if not candidate_mismatch.empty:

    add_error(
        "공공임대 수요대비 점검후보 "
        "조건 불일치 : "
        + ", ".join(
            candidate_mismatch[
                "지역"
            ].tolist()
        )
    )


# =========================================================
# 17. 행복주택 공급공백 TOP10
# =========================================================

expected_happy_gap = (

    df[
        "2030인구_TOP10"
    ]

    &

    df[
        "행복주택_공급없음"
    ]

)


happy_gap_mismatch = df[
    expected_happy_gap
    !=
    df[
        "행복주택_공급공백_TOP10"
    ]
]


if not happy_gap_mismatch.empty:

    add_error(
        "행복주택 공급공백 TOP10 "
        "판정 불일치 : "
        + ", ".join(
            happy_gap_mismatch[
                "지역"
            ].tolist()
        )
    )


# =========================================================
# 18. 청년주거지원 복합 후보
#
# TOP10
# AND 전체 공공임대 상대부족
# AND 행복주택 0세대
# =========================================================

expected_final_candidate = (

    df[
        "2030인구_TOP10"
    ]

    &

    df[
        "공공임대_상대부족"
    ]

    &

    df[
        "행복주택_공급없음"
    ]

)


final_mismatch = df[
    expected_final_candidate
    !=
    df[
        "청년주거지원_점검후보"
    ]
]


if not final_mismatch.empty:

    add_error(
        "청년주거지원 복합 점검후보 "
        "판정 불일치 : "
        + ", ".join(
            final_mismatch[
                "지역"
            ].tolist()
        )
    )


candidate_count = int(
    expected_final_candidate.sum()
)


if candidate_count != EXPECTED_CANDIDATES:

    add_warning(
        f"현재 청년주거지원 복합 후보가 "
        f"{candidate_count}곳입니다. "
        "직전 분석에서는 3곳이었습니다."
    )


# =========================================================
# 19. 현재 3개 후보 확인
# =========================================================

expected_candidate_regions = {

    "서구 치평동",

    "서구 풍암동",

    "남구 진월동"
}


actual_candidate_regions = set(

    df[
        df[
            "청년주거지원_점검후보"
        ]
        == True
    ][
        "지역"
    ]

)


if (
    actual_candidate_regions
    != expected_candidate_regions
):

    add_warning(
        "청년주거지원 후보지역이 "
        "직전 분석 결과와 달라졌습니다."
    )


# =========================================================
# 20. 공공임대가 HL에 들어가지 않았는지
# =========================================================

hl_applied = df[
    df[
        "공공임대_HL반영여부"
    ]
    == True
]


if not hl_applied.empty:

    add_error(
        "공공임대_HL반영여부가 "
        "True인 지역이 있습니다."
    )


# =========================================================
# 21. 역할 문구
# =========================================================

blank_role = (

    df[
        "공공임대지표_역할"
    ]

    .fillna("")

    .astype(str)

    .str.strip()

    == ""

)


if blank_role.any():

    add_error(
        "공공임대지표_역할이 "
        "비어 있는 지역이 있습니다."
    )


# =========================================================
# 22. 주요 결과 출력
# =========================================================

print()
print("----------------------------------------")
print("주요 검사 결과")
print("----------------------------------------")

print(
    f"분석지역 : "
    f"{len(df)}개"
)

print(
    f"전체 공공임대 : "
    f"{total_rental:,}세대"
)

print(
    f"1,000명당 중앙값 : "
    f"{median_rate:.2f}세대"
)

print(
    f"공공임대 상대부족 : "
    f"{int(expected_shortage.sum())}개"
)

print(
    f"2030 인구 TOP10 : "
    f"{len(actual_top10)}개"
)

print(
    f"청년주거지원 복합 후보 : "
    f"{candidate_count}개"
)


print()
print(
    "[청년주거지원 복합 점검후보]"
)


for region in sorted(
    actual_candidate_regions
):

    print(
        "-",
        region
    )


# =========================================================
# 23. 최종 판정
# =========================================================

print()
print("=" * 50)
print("최종 품질검사 결과")
print("=" * 50)


if warnings:

    print()
    print("[주의]")

    for warning in warnings:
        print("!", warning)


if errors:

    print()
    print("[검사 실패]")

    for error in errors:
        print("X", error)


    print()
    print(
        f"총 {len(errors)}개 오류"
    )


    print()
    print(
        "공공임대 청년분석 품질검사 : FAIL"
    )


    sys.exit(1)


else:

    print()
    print(
        "모든 핵심 검사 통과"
    )

    print(
        "공공임대 세대수와 "
        "2030 인구 대비 계산이 일치합니다."
    )

    print(
        "청년주거지원 점검후보 "
        "조건도 정상입니다."
    )

    print(
        "공공임대 지표가 "
        "HL-Score에 혼입되지 않은 것도 "
        "확인했습니다."
    )


    if not warnings:

        print(
            "추가 경고사항도 없습니다."
        )


    print()
    print(
        "공공임대 청년분석 품질검사 : PASS"
    )