import os
import sys

import pandas as pd


# =========================================================
# 1. 파일 경로
# =========================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

INPUT_FILE = os.path.join(
    BASE_DIR,
    "data",
    "processed",
    "청년주거환경_정책통합분석.csv"
)


# =========================================================
# 2. 검사 결과
# =========================================================

errors = []
warnings = []


def add_error(message):
    errors.append(message)


def add_warning(message):
    warnings.append(message)


# =========================================================
# 3. True / False 안전 변환
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
# 4. 데이터 불러오기
# =========================================================

try:

    df = pd.read_csv(
        INPUT_FILE,
        encoding="utf-8-sig"
    )

except Exception as e:

    print()
    print("[오류]")

    print(
        "정책통합분석 CSV를 "
        "불러오지 못했습니다."
    )

    print(e)

    sys.exit(1)


print()
print(
    "========================================"
)

print(
    "청년 주거환경 정책 데이터 품질검사"
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

print(
    f"열 개수 : {len(df.columns)}"
)


# =========================================================
# 5. 필수 컬럼
# =========================================================

required_columns = [

    "지역",

    # HL
    "HL_Score",
    "HL정책검토등급",
    "HL정책순위포함여부",
    "HL비교가능성",
    "HL산출유형",

    # 주거
    "월환산주거비",
    "월환산주거비_평균값_만원",
    "전체거래건수",
    "HL주거표본판정",
    "HL데이터주의사항",

    # 세부 점수
    "생활인프라점수",
    "2030선호시설점수",
    "교통접근성점수",
    "주거가성비점수",

    # HL 취약 분석
    "HL취약유형",
    "HL주요취약요인",

    # 청년인구
    "2030인구수",
    "2030인구비율",

    # 수요 대비 인프라
    "생활시설_1000명당",
    "버스정류소_1000명당",
    "선호시설_1000명당",

    "2030인구_TOP10",

    "수요대비인프라후보",
    "수요대비우선후보",

    # 통합
    "두분석_동시신호",
    "최종정책유형",

    "정책근거요약",
    "통합정책제안"
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
    print(
        "[검사 실패]"
    )

    for error in errors:

        print(
            "X",
            error
        )

    sys.exit(1)


# =========================================================
# 6. Boolean 컬럼 정리
# =========================================================

bool_columns = [

    "HL정책순위포함여부",

    "2030인구_TOP10",

    "수요대비인프라후보",

    "수요대비우선후보",

    "두분석_동시신호"
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
# 7. 지역 수
# =========================================================

if len(df) != 25:

    add_error(
        f"분석 대상 지역이 25개가 아닙니다. "
        f"현재 {len(df)}개"
    )


# =========================================================
# 8. 지역 중복
# =========================================================

duplicate_regions = (

    df[
        df[
            "지역"
        ].duplicated(
            keep=False
        )
    ][
        "지역"
    ]

    .tolist()

)


if duplicate_regions:

    add_error(

        "중복 지역 발견 : "

        + ", ".join(

            sorted(
                set(
                    duplicate_regions
                )
            )

        )

    )


# =========================================================
# 9. 기본 숫자 결측 검사
#
# 주거가성비점수는 제외
# 두암2동은 NaN이 정상
# =========================================================

numeric_columns = [

    "HL_Score",

    "월환산주거비",

    "월환산주거비_평균값_만원",

    "전체거래건수",

    "생활인프라점수",

    "2030선호시설점수",

    "교통접근성점수",

    "2030인구수",

    "2030인구비율",

    "생활시설_1000명당",

    "버스정류소_1000명당",

    "선호시설_1000명당"
]


for column in numeric_columns:

    missing_count = (

        df[
            column
        ]

        .isna()

        .sum()

    )


    if missing_count > 0:

        add_error(

            f"{column}에 빈 값이 "
            f"{missing_count}개 있습니다."

        )


# =========================================================
# 10. 기본 점수 범위
# =========================================================

score_columns = [

    "HL_Score",

    "생활인프라점수",

    "2030선호시설점수",

    "교통접근성점수"
]


for column in score_columns:

    invalid = df[
        (
            df[
                column
            ]
            < 0
        )
        |
        (
            df[
                column
            ]
            > 100
        )
    ]


    if len(invalid) > 0:

        add_error(

            f"{column}에 "
            "0~100 범위를 벗어난 값이 있습니다."

        )


# =========================================================
# 11. 주거가성비점수 검사
#
# 정책순위 포함 = 값 있어야 함
# 정책순위 제외 = NaN이어야 함
# =========================================================

included = df[
    df[
        "HL정책순위포함여부"
    ]
    == True
]


excluded = df[
    df[
        "HL정책순위포함여부"
    ]
    == False
]


# 포함 지역에서 NaN 금지
included_missing_housing_score = included[
    included[
        "주거가성비점수"
    ].isna()
]


if not included_missing_housing_score.empty:

    add_error(

        "HL 정책순위 포함 지역 중 "
        "주거가성비점수가 없는 지역 : "

        + ", ".join(
            included_missing_housing_score[
                "지역"
            ].tolist()
        )

    )


# 포함 지역 점수 범위
included_invalid_housing_score = included[
    (
        included[
            "주거가성비점수"
        ]
        < 0
    )
    |
    (
        included[
            "주거가성비점수"
        ]
        > 100
    )
]


if not included_invalid_housing_score.empty:

    add_error(
        "주거가성비점수에 "
        "0~100 범위를 벗어난 값이 있습니다."
    )


# 제외 지역은 주거점수 미사용
excluded_has_housing_score = excluded[
    excluded[
        "주거가성비점수"
    ].notna()
]


if not excluded_has_housing_score.empty:

    add_error(

        "HL 정책순위 제외 지역인데 "
        "주거가성비점수가 존재하는 지역 : "

        + ", ".join(
            excluded_has_housing_score[
                "지역"
            ].tolist()
        )

    )


# =========================================================
# 12. 주거 표본 기준 검사
#
# 20건 이상 = 정상
# 5~19건 = 저표본 주의
# 0~4건 = 표본부족
# =========================================================

def expected_sample_status(count):

    if count < 5:
        return "표본부족"

    if count < 20:
        return "저표본 주의"

    return "정상"


df[
    "검증용_주거표본판정"
] = (

    df[
        "전체거래건수"
    ]

    .apply(
        expected_sample_status
    )

)


sample_mismatch = df[
    df[
        "검증용_주거표본판정"
    ]
    !=
    df[
        "HL주거표본판정"
    ]
]


if not sample_mismatch.empty:

    for _, row in (
        sample_mismatch.iterrows()
    ):

        add_error(

            f"{row['지역']} 주거표본판정 불일치 : "
            f"현재 '{row['HL주거표본판정']}' / "
            f"예상 '{row['검증용_주거표본판정']}'"

        )


# =========================================================
# 13. 표본과 정책순위 포함 여부 검사
# =========================================================

expected_rank_inclusion = (

    df[
        "전체거래건수"
    ]
    >= 5

)


rank_inclusion_mismatch = df[
    expected_rank_inclusion
    !=
    df[
        "HL정책순위포함여부"
    ]
]


if not rank_inclusion_mismatch.empty:

    add_error(

        "주거표본 기준과 "
        "HL 정책순위 포함 여부가 다른 지역 : "

        + ", ".join(
            rank_inclusion_mismatch[
                "지역"
            ].tolist()
        )

    )


# =========================================================
# 14. 표본부족지역 정책등급 검사
# =========================================================

insufficient = df[
    df[
        "HL주거표본판정"
    ]
    == "표본부족"
]


for _, row in insufficient.iterrows():

    if (
        row[
            "HL정책검토등급"
        ]
        != "정책순위 제외"
    ):

        add_error(

            f"{row['지역']}은 주거 표본부족인데 "
            "HL정책검토등급이 "
            "'정책순위 제외'가 아닙니다."

        )


    if (
        row[
            "HL정책순위포함여부"
        ]
        != False
    ):

        add_error(

            f"{row['지역']}은 주거 표본부족인데 "
            "HL 정책순위에 포함되어 있습니다."

        )


# =========================================================
# 15. 인구 범위
# =========================================================

if (
    df[
        "2030인구수"
    ]
    <= 0
).any():

    add_error(
        "2030인구수가 0 이하인 지역이 있습니다."
    )


invalid_population_ratio = df[
    (
        df[
            "2030인구비율"
        ]
        < 0
    )
    |
    (
        df[
            "2030인구비율"
        ]
        > 100
    )
]


if not invalid_population_ratio.empty:

    add_error(
        "2030인구비율에 잘못된 값이 있습니다."
    )


# =========================================================
# 16. HL 정책등급 개수
# =========================================================

hl_priority_count = (

    df[
        "HL정책검토등급"
    ]
    == "우선 개선 검토"

).sum()


hl_interest_count = (

    df[
        "HL정책검토등급"
    ]
    == "관심 검토"

).sum()


hl_excluded_count = (

    df[
        "HL정책검토등급"
    ]
    == "정책순위 제외"

).sum()


if hl_priority_count != 5:

    add_error(

        f"HL 우선 개선 지역이 "
        f"5곳이 아닙니다. "
        f"현재 {hl_priority_count}곳"

    )


if hl_interest_count != 5:

    add_error(

        f"HL 관심 검토 지역이 "
        f"5곳이 아닙니다. "
        f"현재 {hl_interest_count}곳"

    )


if hl_excluded_count != 1:

    add_warning(

        f"현재 HL 정책순위 제외지역이 "
        f"{hl_excluded_count}곳입니다. "
        "현재 검증 데이터에서는 1곳이 예상됩니다."

    )


# =========================================================
# 17. 주거 표본 상태 개수
# =========================================================

normal_sample_count = (

    df[
        "HL주거표본판정"
    ]
    == "정상"

).sum()


low_sample_count = (

    df[
        "HL주거표본판정"
    ]
    == "저표본 주의"

).sum()


insufficient_count = (

    df[
        "HL주거표본판정"
    ]
    == "표본부족"

).sum()


if normal_sample_count != 21:

    add_warning(

        f"주거표본 정상 지역이 "
        f"현재 {normal_sample_count}곳입니다. "
        "현재 분석에서는 21곳이었습니다."

    )


if low_sample_count != 3:

    add_warning(

        f"저표본 주의 지역이 "
        f"현재 {low_sample_count}곳입니다. "
        "현재 분석에서는 3곳이었습니다."

    )


if insufficient_count != 1:

    add_warning(

        f"표본부족 지역이 "
        f"현재 {insufficient_count}곳입니다. "
        "현재 분석에서는 1곳이었습니다."

    )


# =========================================================
# 18. 청년 수요 우선후보
# =========================================================

demand_priority_count = (

    df[
        "수요대비우선후보"
    ]
    == True

).sum()


if demand_priority_count != 5:

    add_error(

        f"청년 수요 대응 우선후보가 "
        f"5곳이 아닙니다. "
        f"현재 {demand_priority_count}곳"

    )


# =========================================================
# 19. 2030 인구 TOP10
# =========================================================

top10_count = (

    df[
        "2030인구_TOP10"
    ]
    == True

).sum()


if top10_count != 10:

    add_error(

        f"2030 인구 TOP10 표시가 "
        f"10곳이 아닙니다. "
        f"현재 {top10_count}곳"

    )


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


if expected_top10 != actual_top10:

    add_error(
        "2030 인구 TOP10 표시와 "
        "실제 인구순위가 다릅니다."
    )


# =========================================================
# 20. 두 분석 동시신호 검사
#
# HL 우선/관심 + 수요 인프라 후보
# =========================================================

expected_overlap = (

    df[
        "HL정책검토등급"
    ].isin(
        [
            "우선 개선 검토",
            "관심 검토"
        ]
    )

    &

    (
        df[
            "수요대비인프라후보"
        ]
        == True
    )

)


actual_overlap = (

    df[
        "두분석_동시신호"
    ]
    == True

)


overlap_mismatch = df[
    expected_overlap
    != actual_overlap
]


if not overlap_mismatch.empty:

    add_error(

        "두분석_동시신호 계산이 "
        "맞지 않는 지역 : "

        + ", ".join(
            overlap_mismatch[
                "지역"
            ].tolist()
        )

    )


overlap_count = (
    actual_overlap.sum()
)


if overlap_count != 4:

    add_warning(

        f"현재 두 분석 동시신호가 "
        f"{overlap_count}곳입니다. "
        "현재 분석 결과에서는 4곳입니다."

    )


# =========================================================
# 21. 예상 최종 정책유형
# =========================================================

def expected_policy_type(row):

    hl = row[
        "HL정책검토등급"
    ]

    demand_candidate = (

        row[
            "수요대비인프라후보"
        ]
        == True

    )

    demand_priority = (

        row[
            "수요대비우선후보"
        ]
        == True

    )


    # =============================================
    # HL 순위 제외
    # =============================================

    if hl == "정책순위 제외":

        if demand_priority:

            return (
                "수요분석 우선 · HL순위 제외"
            )


        if demand_candidate:

            return (
                "수요분석 검토 · HL순위 제외"
            )


        return "HL순위 제외"


    # =============================================
    # 복합
    # =============================================

    if (
        hl == "우선 개선 검토"
        and demand_priority
    ):

        return "복합 최우선 검토"


    if (
        hl == "우선 개선 검토"
        and demand_candidate
    ):

        return "복합 정책검토"


    if (
        hl == "관심 검토"
        and demand_priority
    ):

        return "복합 우선 검토"


    if (
        hl == "관심 검토"
        and demand_candidate
    ):

        return "복합 관심 검토"


    # =============================================
    # 단독 신호
    # =============================================

    if hl == "우선 개선 검토":

        return "주거환경 개선 우선"


    if hl == "관심 검토":

        return "주거환경 관심 검토"


    if demand_priority:

        return "청년수요 대응 우선"


    if demand_candidate:

        return (
            "청년수요 대비 인프라 검토"
        )


    return "일반 관찰"


df[
    "검증용_예상정책유형"
] = df.apply(
    expected_policy_type,
    axis=1
)


policy_mismatch = df[
    df[
        "검증용_예상정책유형"
    ]
    !=
    df[
        "최종정책유형"
    ]
]


if not policy_mismatch.empty:

    for _, row in (
        policy_mismatch.iterrows()
    ):

        add_error(

            f"{row['지역']} 정책유형 불일치 : "
            f"현재 '{row['최종정책유형']}' / "
            f"예상 '{row['검증용_예상정책유형']}'"

        )


# =========================================================
# 22. 복합 정책유형 검사
# =========================================================

complex_types = [

    "복합 최우선 검토",

    "복합 우선 검토",

    "복합 정책검토",

    "복합 관심 검토"
]


complex_df = df[
    df[
        "최종정책유형"
    ].isin(
        complex_types
    )
]


for _, row in (
    complex_df.iterrows()
):

    if (
        row[
            "두분석_동시신호"
        ]
        != True
    ):

        add_error(

            f"{row['지역']}은 "
            "복합 정책유형인데 "
            "두분석_동시신호가 False입니다."

        )


# 동시신호인데 복합이 아닌 경우
overlap_not_complex = df[
    (
        df[
            "두분석_동시신호"
        ]
        == True
    )

    &

    (
        ~df[
            "최종정책유형"
        ].isin(
            complex_types
        )
    )
]


if not overlap_not_complex.empty:

    add_error(

        "두 분석 동시신호인데 "
        "복합 정책유형이 아닌 지역 : "

        + ", ".join(
            overlap_not_complex[
                "지역"
            ].tolist()
        )

    )


# =========================================================
# 23. HL 순위 제외지역이 복합유형인지 검사
# =========================================================

excluded_complex = df[
    (
        df[
            "HL정책검토등급"
        ]
        == "정책순위 제외"
    )

    &

    (
        df[
            "최종정책유형"
        ].isin(
            complex_types
        )
    )
]


if not excluded_complex.empty:

    add_error(

        "HL 정책순위 제외지역이 "
        "복합 정책유형으로 분류된 지역 : "

        + ", ".join(
            excluded_complex[
                "지역"
            ].tolist()
        )

    )


# =========================================================
# 24. 저표본 데이터주의사항 검사
# =========================================================

low_sample = df[
    df[
        "HL주거표본판정"
    ]
    == "저표본 주의"
]


for _, row in (
    low_sample.iterrows()
):

    note = str(
        row[
            "HL데이터주의사항"
        ]
    ).strip()


    if (
        note == ""
        or note.lower() == "nan"
    ):

        add_error(

            f"{row['지역']}은 "
            "저표본 주의지역인데 "
            "데이터주의사항이 없습니다."

        )


# =========================================================
# 25. 표본부족 주의사항 검사
# =========================================================

for _, row in (
    insufficient.iterrows()
):

    note = str(
        row[
            "HL데이터주의사항"
        ]
    ).strip()


    if (
        note == ""
        or note.lower() == "nan"
    ):

        add_error(

            f"{row['지역']}은 "
            "주거 표본부족지역인데 "
            "데이터주의사항이 없습니다."

        )


# =========================================================
# 26. 정책 문장 검사
# =========================================================

text_columns = [

    "정책근거요약",

    "통합정책제안"
]


for column in text_columns:

    blank = (

        df[
            column
        ]

        .fillna("")

        .astype(str)

        .str.strip()

        == ""

    )


    if blank.any():

        regions = df[
            blank
        ][
            "지역"
        ].tolist()


        add_error(

            f"{column}이 비어 있는 지역 : "

            + ", ".join(
                regions
            )

        )


# =========================================================
# 27. 주요 검사 결과
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
    f"{len(df)}곳"
)

print(
    f"HL 우선 개선 : "
    f"{hl_priority_count}곳"
)

print(
    f"HL 관심 검토 : "
    f"{hl_interest_count}곳"
)

print(
    f"HL 정책순위 제외 : "
    f"{hl_excluded_count}곳"
)

print(
    f"청년 수요 대응 우선 : "
    f"{demand_priority_count}곳"
)

print(
    f"두 분석 동시 신호 : "
    f"{overlap_count}곳"
)

print(
    f"2030 인구 TOP10 : "
    f"{top10_count}곳"
)

print(
    f"주거표본 정상 : "
    f"{normal_sample_count}곳"
)

print(
    f"주거 저표본 주의 : "
    f"{low_sample_count}곳"
)

print(
    f"주거 표본부족 : "
    f"{insufficient_count}곳"
)


# =========================================================
# 28. 두 분석 동시신호 지역
# =========================================================

print()
print(
    "[두 분석 동시 신호 지역]"
)


overlap_regions = df[
    df[
        "두분석_동시신호"
    ]
    == True
]


for _, row in (
    overlap_regions.iterrows()
):

    print(

        f"- {row['지역']} "
        f"→ {row['최종정책유형']}"

    )


# =========================================================
# 29. 정책순위 제외 지역
# =========================================================

print()
print(
    "[HL 정책순위 비교 제외지역]"
)


if excluded.empty:

    print(
        "없음"
    )


else:

    for _, row in (
        excluded.iterrows()
    ):

        print(

            f"- {row['지역']} "
            f"→ {row['최종정책유형']} "
            f"(주거 {row['전체거래건수']}건)"

        )


# =========================================================
# 30. 저표본 주의 지역
# =========================================================

print()
print(
    "[주거 저표본 주의지역]"
)


if low_sample.empty:

    print(
        "없음"
    )


else:

    for _, row in (
        low_sample.iterrows()
    ):

        print(

            f"- {row['지역']} "
            f"({row['전체거래건수']}건) "
            f"→ {row['최종정책유형']}"

        )


# =========================================================
# 31. 최종 정책유형별 지역 수
# =========================================================

print()
print(
    "[최종 정책유형별 지역 수]"
)


type_count = (

    df[
        "최종정책유형"
    ]

    .value_counts()

)


for policy_type, count in (
    type_count.items()
):

    print(

        f"- {policy_type} : "
        f"{count}곳"

    )


# =========================================================
# 32. 최종 판정
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


    print(
        f"\n총 {len(errors)}개의 "
        "오류를 확인했습니다."
    )


    print()
    print(
        "발표 전 데이터 품질검사 : FAIL"
    )


    sys.exit(1)


else:

    print()
    print(
        "모든 핵심 검사 통과"
    )


    print(
        "정책통합분석 데이터의 "
        "기본 정합성이 확인되었습니다."
    )


    print(
        "주거 저표본 처리와 "
        "HL 정책순위 제외 기준도 정상입니다."
    )


    print(
        "최종 정책유형과 "
        "두 분석 동시신호도 일치합니다."
    )


    if not warnings:

        print(
            "추가 경고사항도 없습니다."
        )


    print()
    print(
        "발표 전 데이터 품질검사 : PASS"
    )