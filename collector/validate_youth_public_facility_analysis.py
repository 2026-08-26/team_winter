from pathlib import Path
import sys

import pandas as pd


# =========================================================
# 1. 경로 설정
# =========================================================

BASE_DIR = Path(__file__).resolve().parent.parent

PROCESSED_DIR = (
    BASE_DIR
    / "data"
    / "processed"
)

INPUT_FILE = (
    PROCESSED_DIR
    / "2030_청년인구_대비_공공시설_분석.csv"
)


# =========================================================
# 2. 현재 분석 기준
# =========================================================

EXPECTED_REGION_COUNT = 25

EXPECTED_TOTAL_FACILITIES = 57

EXPECTED_ZERO_FACILITY_REGIONS = 6


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
# 4. True / False 안전 변환
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
print(
    "========================================"
)

print(
    "청년 공공시설 분석 품질검사"
)

print(
    "========================================"
)

print(
    f"\n검사 파일 : {INPUT_FILE}"
)

print(
    f"행 개수 : {len(df)}"
)


# =========================================================
# 6. 필수 컬럼 검사
# =========================================================

required_columns = [

    "지역",

    "청년공공시설수",

    "2030인구수",

    "청년공공시설_1000명당",

    "청년공공시설_0개",

    "공공시설_상대부족",

    "2030인구_TOP10",

    "공공지원_점검후보",

    "공공지원인프라_상태"
]


missing_columns = [

    column

    for column in required_columns

    if column not in df.columns
]


if missing_columns:

    add_error(
        "필수 컬럼 누락 : "
        + ", ".join(
            missing_columns
        )
    )


if errors:

    print()
    print("[검사 실패]")

    for error in errors:

        print(
            "X",
            error
        )

    sys.exit(1)


# =========================================================
# 7. Boolean 컬럼 정리
# =========================================================

bool_columns = [

    "청년공공시설_0개",

    "공공시설_상대부족",

    "2030인구_TOP10",

    "공공지원_점검후보"
]


for column in bool_columns:

    df[
        column
    ] = (

        df[
            column
        ]

        .apply(
            to_bool
        )

    )


# =========================================================
# 8. 숫자형 변환
# =========================================================

numeric_columns = [

    "청년공공시설수",

    "2030인구수",

    "청년공공시설_1000명당"
]


for column in numeric_columns:

    df[
        column
    ] = pd.to_numeric(
        df[
            column
        ],
        errors="coerce"
    )


# =========================================================
# 9. 25개 동 검사
# =========================================================

if len(df) != EXPECTED_REGION_COUNT:

    add_error(

        f"분석 대상 지역이 "
        f"{EXPECTED_REGION_COUNT}개가 아닙니다. "
        f"현재 {len(df)}개"

    )


# =========================================================
# 10. 지역 중복 검사
# =========================================================

duplicate_regions = df[
    df[
        "지역"
    ].duplicated(
        keep=False
    )
]


if not duplicate_regions.empty:

    add_error(

        "중복 지역 발견 : "

        + ", ".join(

            sorted(

                duplicate_regions[
                    "지역"
                ]

                .unique()

            )

        )

    )


# =========================================================
# 11. 청년인구 결측 검사
# =========================================================

population_missing = df[
    df[
        "2030인구수"
    ].isna()
]


if not population_missing.empty:

    add_error(

        "2030 인구수가 없는 지역 : "

        + ", ".join(
            population_missing[
                "지역"
            ].tolist()
        )

    )


# =========================================================
# 12. 청년인구 0 이하 검사
# =========================================================

invalid_population = df[
    df[
        "2030인구수"
    ]
    <= 0
]


if not invalid_population.empty:

    add_error(

        "2030 인구수가 0 이하인 지역 : "

        + ", ".join(
            invalid_population[
                "지역"
            ].tolist()
        )

    )


# =========================================================
# 13. 전체 시설 합계 검사
# =========================================================

total_facilities = int(

    df[
        "청년공공시설수"
    ]

    .fillna(0)

    .sum()

)


if (
    total_facilities
    != EXPECTED_TOTAL_FACILITIES
):

    add_error(

        f"전체 청년 공공시설 합계가 "
        f"{EXPECTED_TOTAL_FACILITIES}개가 아닙니다. "
        f"현재 {total_facilities}개"

    )


# =========================================================
# 14. 시설 0개 지역 검사
# =========================================================

actual_zero_condition = (

    df[
        "청년공공시설수"
    ]
    == 0

)


stored_zero_condition = (

    df[
        "청년공공시설_0개"
    ]
    == True

)


zero_mismatch = df[
    actual_zero_condition
    != stored_zero_condition
]


if not zero_mismatch.empty:

    add_error(

        "청년공공시설_0개 표시가 "
        "실제 시설 수와 다른 지역 : "

        + ", ".join(
            zero_mismatch[
                "지역"
            ].tolist()
        )

    )


zero_count = int(
    actual_zero_condition.sum()
)


if (
    zero_count
    != EXPECTED_ZERO_FACILITY_REGIONS
):

    add_error(

        f"시설 0개 지역이 "
        f"{EXPECTED_ZERO_FACILITY_REGIONS}곳이 아닙니다. "
        f"현재 {zero_count}곳"

    )


# =========================================================
# 15. 1,000명당 계산 검증
# =========================================================

df[
    "검증용_1000명당"
] = (

    df[
        "청년공공시설수"
    ]

    /

    df[
        "2030인구수"
    ]

    * 1000

).round(
    3
)


rate_difference = (

    df[
        "검증용_1000명당"
    ]

    -

    df[
        "청년공공시설_1000명당"
    ]

).abs()


rate_mismatch = df[
    rate_difference
    > 0.001
]


if not rate_mismatch.empty:

    for _, row in (
        rate_mismatch.iterrows()
    ):

        add_error(

            f"{row['지역']}의 "
            "청년공공시설_1000명당 계산 불일치 : "
            f"저장값 {row['청년공공시설_1000명당']} / "
            f"검증값 {row['검증용_1000명당']}"

        )


# =========================================================
# 16. 중앙값 재계산
# =========================================================

median_rate = (

    df[
        "청년공공시설_1000명당"
    ]

    .median()

)


# =========================================================
# 17. 상대부족 조건 검사
#
# 중앙값 미만 = True
# =========================================================

expected_shortage = (

    df[
        "청년공공시설_1000명당"
    ]

    < median_rate

)


shortage_mismatch = df[
    expected_shortage
    !=
    df[
        "공공시설_상대부족"
    ]
]


if not shortage_mismatch.empty:

    add_error(

        "공공시설 상대부족 판정이 "
        "중앙값 기준과 다른 지역 : "

        + ", ".join(
            shortage_mismatch[
                "지역"
            ].tolist()
        )

    )


# =========================================================
# 18. 2030 인구 TOP10 검사
# =========================================================

expected_top10_regions = set(

    df

    .sort_values(
        "2030인구수",
        ascending=False
    )

    .head(10)[
        "지역"
    ]

)


actual_top10_regions = set(

    df[
        df[
            "2030인구_TOP10"
        ]
        == True
    ][
        "지역"
    ]

)


if len(
    actual_top10_regions
) != 10:

    add_error(

        f"2030인구_TOP10이 "
        f"10곳이 아닙니다. "
        f"현재 {len(actual_top10_regions)}곳"

    )


if (
    expected_top10_regions
    != actual_top10_regions
):

    add_error(
        "2030 인구 TOP10 표시와 "
        "실제 인구순위가 일치하지 않습니다."
    )


# =========================================================
# 19. 공공지원 점검후보 검사
#
# 인구 TOP10
# AND
# 공공시설 상대부족
# =========================================================

expected_candidate = (

    df[
        "2030인구_TOP10"
    ]

    &

    df[
        "공공시설_상대부족"
    ]

)


candidate_mismatch = df[
    expected_candidate
    !=
    df[
        "공공지원_점검후보"
    ]
]


if not candidate_mismatch.empty:

    add_error(

        "공공지원 점검후보 조건이 "
        "맞지 않는 지역 : "

        + ", ".join(
            candidate_mismatch[
                "지역"
            ].tolist()
        )

    )


candidate_count = int(
    expected_candidate.sum()
)


# 현재 결과는 6곳이었음
if candidate_count != 6:

    add_warning(

        f"현재 공공지원 점검후보가 "
        f"{candidate_count}곳입니다. "
        "직전 분석에서는 6곳이었습니다."

    )


# =========================================================
# 20. 상태 문구 검사
# =========================================================

def expected_status(row):

    if (
        row[
            "청년공공시설수"
        ]
        == 0
    ):

        return "시설 없음"


    if (
        row[
            "공공시설_상대부족"
        ]
        == True
    ):

        return "청년인구 대비 상대부족"


    return "상대적으로 양호"


df[
    "검증용_상태"
] = df.apply(
    expected_status,
    axis=1
)


status_mismatch = df[
    df[
        "검증용_상태"
    ]
    !=
    df[
        "공공지원인프라_상태"
    ]
]


if not status_mismatch.empty:

    add_error(

        "공공지원인프라 상태 문구가 "
        "조건과 다른 지역 : "

        + ", ".join(
            status_mismatch[
                "지역"
            ].tolist()
        )

    )


# =========================================================
# 21. 첨단2동 프로젝트 표기 확인
# =========================================================

cheomdan2 = df[
    df[
        "지역"
    ]
    == "북구 첨단2동"
]


if len(
    cheomdan2
) != 1:

    add_error(

        "프로젝트 표기 "
        "'북구 첨단2동'이 "
        "정확히 1개 존재하지 않습니다."

    )


# =========================================================
# 22. 주요 검사 결과 출력
# =========================================================

print()
print(
    "----------------------------------------"
)

print(
    "주요 검사 결과"
)

print(
    "----------------------------------------"
)


print(
    f"분석 대상 지역 : "
    f"{len(df)}개"
)

print(
    f"전체 청년 공공시설 : "
    f"{total_facilities}개"
)

print(
    f"시설 0개 지역 : "
    f"{zero_count}개"
)

print(
    f"1,000명당 중앙값 : "
    f"{median_rate:.3f}개"
)

print(
    f"상대부족 지역 : "
    f"{int(expected_shortage.sum())}개"
)

print(
    f"2030 인구 TOP10 : "
    f"{len(actual_top10_regions)}개"
)

print(
    f"공공지원 점검후보 : "
    f"{candidate_count}개"
)


# =========================================================
# 23. 시설 0개 지역 출력
# =========================================================

print()
print(
    "[청년 공공시설 0개 지역]"
)


zero_df = df[
    actual_zero_condition
]


for _, row in (
    zero_df.iterrows()
):

    print(
        f"- {row['지역']} "
        f"/ 2030인구 "
        f"{int(row['2030인구수']):,}명"
    )


# =========================================================
# 24. 점검후보 출력
# =========================================================

print()
print(
    "[공공지원 점검후보]"
)


candidate_df = df[
    expected_candidate
]


for _, row in (
    candidate_df.iterrows()
):

    print(

        f"- {row['지역']} : "
        f"{row['청년공공시설_1000명당']:.3f}개/1,000명"

    )


# =========================================================
# 25. 최종 판정
# =========================================================

print()
print(
    "========================================"
)

print(
    "최종 품질검사 결과"
)

print(
    "========================================"
)


if warnings:

    print()
    print(
        "[주의]"
    )


    for warning in warnings:

        print(
            "!",
            warning
        )


if errors:

    print()
    print(
        "[검사 실패]"
    )


    for error in errors:

        print(
            "X",
            error
        )


    print()
    print(
        f"총 {len(errors)}개의 "
        "오류를 확인했습니다."
    )


    print()
    print(
        "청년 공공시설 데이터 품질검사 : FAIL"
    )


    sys.exit(1)


else:

    print()
    print(
        "모든 핵심 검사 통과"
    )


    print(
        "25개 동 공공시설 집계와 "
        "2030 인구 대비 계산이 일치합니다."
    )


    print(
        "상대부족 및 공공지원 점검후보 "
        "판정도 정상입니다."
    )


    if not warnings:

        print(
            "추가 경고사항도 없습니다."
        )


    print()
    print(
        "청년 공공시설 데이터 품질검사 : PASS"
    )