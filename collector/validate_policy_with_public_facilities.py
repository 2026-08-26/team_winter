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

# 공공시설 붙이기 전 정책통합 결과
ORIGINAL_POLICY_FILE = (
    PROCESSED_DIR
    / "청년주거환경_정책통합분석.csv"
)

# 공공시설 분석 원본
PUBLIC_FACILITY_FILE = (
    PROCESSED_DIR
    / "2030_청년인구_대비_공공시설_분석.csv"
)

# 공공시설까지 붙인 최종 결과
MERGED_FILE = (
    PROCESSED_DIR
    / "청년주거환경_정책통합분석_공공시설반영.csv"
)


# =========================================================
# 2. 현재 확정된 값
# =========================================================

EXPECTED_REGION_COUNT = 25

EXPECTED_TOTAL_FACILITIES = 57

EXPECTED_ZERO_REGIONS = 6

EXPECTED_CANDIDATES = 6


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
# 4. Boolean 안전 변환
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
# 5. 문자열 정리
# =========================================================

def clean_text(value):

    if pd.isna(value):
        return ""

    text = str(value).strip()

    if text.lower() in [
        "nan",
        "none"
    ]:
        return ""

    return text


# =========================================================
# 6. 숫자 비교
# =========================================================

def numbers_equal(
    value1,
    value2,
    tolerance=0.001
):

    number1 = pd.to_numeric(
        pd.Series([value1]),
        errors="coerce"
    ).iloc[0]

    number2 = pd.to_numeric(
        pd.Series([value2]),
        errors="coerce"
    ).iloc[0]


    # 둘 다 NaN이면 동일
    if (
        pd.isna(number1)
        and
        pd.isna(number2)
    ):
        return True


    # 하나만 NaN이면 다름
    if (
        pd.isna(number1)
        or
        pd.isna(number2)
    ):
        return False


    return (
        abs(
            float(number1)
            -
            float(number2)
        )
        <= tolerance
    )


# =========================================================
# 7. 파일 읽기
# =========================================================

def load_file(
    path,
    name
):

    if not path.exists():

        print()
        print(
            f"{name} 파일이 없습니다."
        )

        print(
            path
        )

        sys.exit(1)


    return pd.read_csv(
        path,
        encoding="utf-8-sig"
    )


# =========================================================
# 8. 데이터 읽기
# =========================================================

original_df = load_file(
    ORIGINAL_POLICY_FILE,
    "기존 정책통합"
)

facility_df = load_file(
    PUBLIC_FACILITY_FILE,
    "공공시설 분석"
)

merged_df = load_file(
    MERGED_FILE,
    "공공시설 반영 정책통합"
)


print()
print(
    "========================================"
)

print(
    "공공시설 반영 정책통합 최종 품질검사"
)

print(
    "========================================"
)


print()
print(
    f"기존 정책통합 : "
    f"{len(original_df)}개 지역"
)

print(
    f"공공시설 분석 : "
    f"{len(facility_df)}개 지역"
)

print(
    f"공공시설 반영 : "
    f"{len(merged_df)}개 지역"
)


# =========================================================
# 9. 필수 컬럼
# =========================================================

required_merged_columns = [

    "지역",

    # 기존 HL/정책
    "HL_Score",

    "HL정책검토등급",

    "HL정책순위포함여부",

    "최종정책유형",

    "주거가성비점수",

    # 공공시설
    "청년공공시설수",

    "청년공공시설_1000명당",

    "청년공공시설_0개",

    "공공시설_상대부족",

    "공공지원_점검후보",

    "공공지원인프라_상태",

    # 새 보조정책 컬럼
    "공공지원_보조근거",

    "공공지원_정책검토방향",

    "정책_공공지원_통합신호",

    "공공시설_HL반영여부",

    "공공시설지표_역할"
]


missing_columns = [

    column

    for column in required_merged_columns

    if column not in merged_df.columns
]


if missing_columns:

    add_error(
        "공공시설 반영 파일 필수 컬럼 누락 : "
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
# 10. Boolean 정리
# =========================================================

merged_bool_columns = [

    "HL정책순위포함여부",

    "청년공공시설_0개",

    "공공시설_상대부족",

    "공공지원_점검후보",

    "공공시설_HL반영여부"
]


for column in merged_bool_columns:

    merged_df[
        column
    ] = (

        merged_df[
            column
        ]

        .apply(
            to_bool
        )

    )


facility_bool_columns = [

    "청년공공시설_0개",

    "공공시설_상대부족",

    "공공지원_점검후보"
]


for column in facility_bool_columns:

    if column in facility_df.columns:

        facility_df[
            column
        ] = (

            facility_df[
                column
            ]

            .apply(
                to_bool
            )

        )


# =========================================================
# 11. 25개 동 검사
# =========================================================

for name, df in [

    (
        "기존 정책통합",
        original_df
    ),

    (
        "공공시설 분석",
        facility_df
    ),

    (
        "공공시설 반영",
        merged_df
    )

]:

    if len(df) != EXPECTED_REGION_COUNT:

        add_error(

            f"{name} 데이터가 "
            f"{EXPECTED_REGION_COUNT}개 동이 아닙니다. "
            f"현재 {len(df)}개"

        )


# =========================================================
# 12. 지역 중복 검사
# =========================================================

for name, df in [

    (
        "기존 정책통합",
        original_df
    ),

    (
        "공공시설 분석",
        facility_df
    ),

    (
        "공공시설 반영",
        merged_df
    )

]:

    duplicate = df[
        df[
            "지역"
        ].duplicated(
            keep=False
        )
    ]


    if not duplicate.empty:

        add_error(

            f"{name} 데이터에 중복 지역 : "

            + ", ".join(

                sorted(
                    duplicate[
                        "지역"
                    ].unique()
                )

            )

        )


# =========================================================
# 13. 지역 집합이 모두 같은지 검사
# =========================================================

original_regions = set(
    original_df[
        "지역"
    ]
)

facility_regions = set(
    facility_df[
        "지역"
    ]
)

merged_regions = set(
    merged_df[
        "지역"
    ]
)


if original_regions != merged_regions:

    add_error(
        "기존 정책통합과 공공시설 반영 파일의 "
        "지역 목록이 다릅니다."
    )


if facility_regions != merged_regions:

    add_error(
        "공공시설 분석과 공공시설 반영 파일의 "
        "지역 목록이 다릅니다."
    )


# =========================================================
# 14. 전체 공공시설 수
# =========================================================

total_facilities = int(

    pd.to_numeric(
        merged_df[
            "청년공공시설수"
        ],
        errors="coerce"
    )

    .fillna(0)

    .sum()

)


if (
    total_facilities
    != EXPECTED_TOTAL_FACILITIES
):

    add_error(

        f"전체 청년 공공시설이 "
        f"{EXPECTED_TOTAL_FACILITIES}개가 아닙니다. "
        f"현재 {total_facilities}개"

    )


# =========================================================
# 15. 시설 0개 지역
# =========================================================

zero_count = int(

    merged_df[
        "청년공공시설_0개"
    ].sum()

)


if zero_count != EXPECTED_ZERO_REGIONS:

    add_error(

        f"공공시설 0개 지역이 "
        f"{EXPECTED_ZERO_REGIONS}곳이 아닙니다. "
        f"현재 {zero_count}곳"

    )


zero_value_mismatch = merged_df[
    (
        merged_df[
            "청년공공시설수"
        ]
        == 0
    )
    !=
    (
        merged_df[
            "청년공공시설_0개"
        ]
        == True
    )
]


if not zero_value_mismatch.empty:

    add_error(

        "청년공공시설수와 "
        "청년공공시설_0개 표시가 다른 지역 : "

        + ", ".join(
            zero_value_mismatch[
                "지역"
            ].tolist()
        )

    )


# =========================================================
# 16. 공공지원 점검후보 수
# =========================================================

candidate_count = int(

    merged_df[
        "공공지원_점검후보"
    ].sum()

)


if candidate_count != EXPECTED_CANDIDATES:

    add_error(

        f"공공지원 점검후보가 "
        f"{EXPECTED_CANDIDATES}곳이 아닙니다. "
        f"현재 {candidate_count}곳"

    )


# =========================================================
# 17. 공공시설 분석 원본과 병합값 비교
# =========================================================

facility_compare_columns = [

    "청년공공시설수",

    "청년공공시설_1000명당",

    "청년공공시설_0개",

    "공공시설_상대부족",

    "공공지원_점검후보",

    "공공지원인프라_상태"
]


facility_check = pd.merge(

    facility_df[
        [
            "지역"
        ]
        + facility_compare_columns
    ],

    merged_df[
        [
            "지역"
        ]
        + facility_compare_columns
    ],

    on="지역",

    suffixes=(
        "_원본",
        "_병합"
    ),

    how="inner"
)


for _, row in (
    facility_check.iterrows()
):

    region = row[
        "지역"
    ]


    # 숫자
    for column in [

        "청년공공시설수",

        "청년공공시설_1000명당"

    ]:

        if not numbers_equal(

            row[
                f"{column}_원본"
            ],

            row[
                f"{column}_병합"
            ]

        ):

            add_error(

                f"{region} "
                f"{column} 값이 병합 과정에서 변경됨."

            )


    # Boolean
    for column in [

        "청년공공시설_0개",

        "공공시설_상대부족",

        "공공지원_점검후보"

    ]:

        if (

            to_bool(
                row[
                    f"{column}_원본"
                ]
            )

            !=

            to_bool(
                row[
                    f"{column}_병합"
                ]
            )

        ):

            add_error(

                f"{region} "
                f"{column} 값이 병합 과정에서 변경됨."

            )


    # 문자열
    if (

        clean_text(
            row[
                "공공지원인프라_상태_원본"
            ]
        )

        !=

        clean_text(
            row[
                "공공지원인프라_상태_병합"
            ]
        )

    ):

        add_error(

            f"{region} "
            "공공지원인프라_상태가 "
            "병합 과정에서 변경됨."

        )


# =========================================================
# 18. 기존 HL / 정책 결과가 바뀌지 않았는지 검사
# =========================================================

policy_compare_columns = [

    "HL_Score",

    "HL정책검토등급",

    "HL정책순위포함여부",

    "최종정책유형",

    "주거가성비점수"
]


policy_check = pd.merge(

    original_df[
        [
            "지역"
        ]
        + policy_compare_columns
    ],

    merged_df[
        [
            "지역"
        ]
        + policy_compare_columns
    ],

    on="지역",

    suffixes=(
        "_기존",
        "_공공시설반영"
    ),

    how="inner"
)


for _, row in (
    policy_check.iterrows()
):

    region = row[
        "지역"
    ]


    # HL Score
    if not numbers_equal(

        row[
            "HL_Score_기존"
        ],

        row[
            "HL_Score_공공시설반영"
        ]

    ):

        add_error(

            f"{region} HL_Score가 "
            "공공시설 병합 후 변경되었습니다."

        )


    # 주거가성비점수
    # 두암2동 NaN도 정상 비교
    if not numbers_equal(

        row[
            "주거가성비점수_기존"
        ],

        row[
            "주거가성비점수_공공시설반영"
        ]

    ):

        add_error(

            f"{region} 주거가성비점수가 "
            "공공시설 병합 후 변경되었습니다."

        )


    # 정책등급
    if (

        clean_text(
            row[
                "HL정책검토등급_기존"
            ]
        )

        !=

        clean_text(
            row[
                "HL정책검토등급_공공시설반영"
            ]
        )

    ):

        add_error(

            f"{region} HL정책검토등급이 "
            "공공시설 병합 후 변경되었습니다."

        )


    # 최종 정책유형
    if (

        clean_text(
            row[
                "최종정책유형_기존"
            ]
        )

        !=

        clean_text(
            row[
                "최종정책유형_공공시설반영"
            ]
        )

    ):

        add_error(

            f"{region} 최종정책유형이 "
            "공공시설 병합 후 변경되었습니다."

        )


    # 정책순위 포함 여부
    if (

        to_bool(
            row[
                "HL정책순위포함여부_기존"
            ]
        )

        !=

        to_bool(
            row[
                "HL정책순위포함여부_공공시설반영"
            ]
        )

    ):

        add_error(

            f"{region} HL정책순위포함여부가 "
            "공공시설 병합 후 변경되었습니다."

        )


# =========================================================
# 19. 공공시설이 HL-Score에 미반영인지 검사
# =========================================================

incorrect_hl_flag = merged_df[
    merged_df[
        "공공시설_HL반영여부"
    ]
    == True
]


if not incorrect_hl_flag.empty:

    add_error(

        "공공시설_HL반영여부가 True인 지역이 있습니다 : "

        + ", ".join(
            incorrect_hl_flag[
                "지역"
            ].tolist()
        )

    )


# =========================================================
# 20. 보조지표 역할 문구 검사
# =========================================================

blank_role = (

    merged_df[
        "공공시설지표_역할"
    ]

    .fillna("")

    .astype(str)

    .str.strip()

    == ""

)


if blank_role.any():

    add_error(
        "공공시설지표_역할이 빈 지역이 있습니다."
    )


# =========================================================
# 21. 정책 보조 문장 검사
# =========================================================

for column in [

    "공공지원_보조근거",

    "공공지원_정책검토방향",

    "정책_공공지원_통합신호"

]:

    blank = (

        merged_df[
            column
        ]

        .fillna("")

        .astype(str)

        .str.strip()

        == ""

    )


    if blank.any():

        add_error(

            f"{column}이 비어 있는 지역 : "

            + ", ".join(
                merged_df[
                    blank
                ][
                    "지역"
                ].tolist()
            )

        )


# =========================================================
# 22. 두암2동 확인
# =========================================================

duam = merged_df[
    merged_df[
        "지역"
    ]
    == "북구 두암2동"
]


if len(duam) != 1:

    add_error(
        "북구 두암2동이 정확히 1개 존재하지 않습니다."
    )


else:

    row = duam.iloc[0]


    if (
        clean_text(
            row[
                "HL정책검토등급"
            ]
        )
        != "정책순위 제외"
    ):

        add_error(
            "두암2동 HL정책검토등급이 "
            "'정책순위 제외'가 아닙니다."
        )


    if (
        to_bool(
            row[
                "HL정책순위포함여부"
            ]
        )
        != False
    ):

        add_error(
            "두암2동이 HL 정책순위에 "
            "포함되어 있습니다."
        )


    if (
        clean_text(
            row[
                "최종정책유형"
            ]
        )
        != "HL순위 제외"
    ):

        add_error(

            "두암2동 최종정책유형이 "
            "'HL순위 제외'가 아닙니다."

        )


# =========================================================
# 23. 신가동 확인
#
# 기존 주거환경 개선 우선
# + 공공시설 0개
# =========================================================

singa = merged_df[
    merged_df[
        "지역"
    ]
    == "광산구 신가동"
]


if len(singa) == 1:

    row = singa.iloc[0]


    if (
        clean_text(
            row[
                "최종정책유형"
            ]
        )
        != "주거환경 개선 우선"
    ):

        add_error(
            "신가동의 기존 정책유형이 변경되었습니다."
        )


    if int(
        row[
            "청년공공시설수"
        ]
    ) != 0:

        add_error(
            "신가동 청년공공시설수가 0개가 아닙니다."
        )


# =========================================================
# 24. 풍암동 확인
#
# 기존 복합 최우선 유지 여부
# =========================================================

pungam = merged_df[
    merged_df[
        "지역"
    ]
    == "서구 풍암동"
]


if len(pungam) == 1:

    row = pungam.iloc[0]


    if (
        clean_text(
            row[
                "최종정책유형"
            ]
        )
        != "복합 최우선 검토"
    ):

        add_error(
            "풍암동의 기존 '복합 최우선 검토' "
            "유형이 변경되었습니다."
        )


    if (
        to_bool(
            row[
                "공공지원_점검후보"
            ]
        )
        != True
    ):

        add_error(
            "풍암동이 공공지원 점검후보로 "
            "연결되지 않았습니다."
        )


# =========================================================
# 25. 주요 검사 결과
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
    f"최종 분석 지역 : "
    f"{len(merged_df)}개"
)

print(
    f"전체 청년공공시설 : "
    f"{total_facilities}개"
)

print(
    f"공공시설 0개 지역 : "
    f"{zero_count}개"
)

print(
    f"공공지원 점검후보 : "
    f"{candidate_count}개"
)


print()
print(
    "기존 HL-Score / 정책유형 변경 검사 완료"
)

print(
    "공공시설 원본 → 정책통합 병합값 검사 완료"
)


# =========================================================
# 26. 공공지원 점검후보 출력
# =========================================================

print()
print(
    "[공공지원 점검후보]"
)


candidate_df = merged_df[
    merged_df[
        "공공지원_점검후보"
    ]
    == True
]


for _, row in (
    candidate_df.iterrows()
):

    print(

        f"- {row['지역']} "
        f"→ {row['최종정책유형']} "
        f"/ {row['청년공공시설_1000명당']:.3f}개/1,000명"

    )


# =========================================================
# 27. 공공시설 0개 지역 출력
# =========================================================

print()
print(
    "[청년 공공시설 0개 지역]"
)


zero_df = merged_df[
    merged_df[
        "청년공공시설_0개"
    ]
    == True
]


for _, row in (
    zero_df.iterrows()
):

    print(

        f"- {row['지역']} "
        f"→ {row['최종정책유형']}"

    )


# =========================================================
# 28. 최종 품질검사
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
        f"총 {len(errors)}개의 오류를 확인했습니다."
    )


    print()
    print(
        "공공시설 반영 정책통합 품질검사 : FAIL"
    )


    sys.exit(1)


else:

    print()
    print(
        "모든 핵심 검사 통과"
    )


    print(
        "공공시설 병합 과정에서 "
        "기존 HL-Score와 정책유형이 변경되지 않았습니다."
    )


    print(
        "청년 공공시설 57개와 "
        "25개 동 분석 결과도 정상적으로 연결되었습니다."
    )


    print(
        "두암2동의 HL 정책순위 제외 처리도 유지되었습니다."
    )


    if not warnings:

        print(
            "추가 경고사항도 없습니다."
        )


    print()
    print(
        "공공시설 반영 정책통합 품질검사 : PASS"
    )