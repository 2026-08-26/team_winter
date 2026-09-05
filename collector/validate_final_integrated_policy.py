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


# 현재 최종 통합 결과
FINAL_FILE = (
    PROCESSED_DIR
    / "청년주거환경_정책통합분석_공공시설_공공임대_버스정류소반영.csv"
)


# 버스정류소 병합 전 결과
# → 기존 결과가 변조되지 않았는지 비교
BASELINE_FILE = (
    PROCESSED_DIR
    / "청년주거환경_정책통합분석_공공시설_공공임대반영.csv"
)


# =========================================================
# 2. 프로젝트 확정값
# =========================================================

EXPECTED_REGIONS = {

    "동구 충장동",
    "동구 계림1동",
    "동구 지산2동",
    "동구 학동",
    "동구 지원1동",

    "서구 치평동",
    "서구 풍암동",
    "서구 화정2동",
    "서구 농성1동",
    "서구 금호1동",

    "남구 봉선2동",
    "남구 진월동",
    "남구 방림1동",
    "남구 효덕동",
    "남구 송암동",

    "북구 용봉동",
    "북구 두암2동",
    "북구 운암1동",
    "북구 첨단2동",
    "북구 문흥1동",

    "광산구 첨단1동",
    "광산구 수완동",
    "광산구 신가동",
    "광산구 우산동",
    "광산구 송정1동"
}


EXPECTED_POLICY_COUNTS = {

    "일반 관찰":
        10,

    "주거환경 개선 우선":
        4,

    "청년수요 대응 우선":
        4,

    "복합 관심 검토":
        3,

    "주거환경 관심 검토":
        2,

    "복합 최우선 검토":
        1,

    "HL순위 제외":
        1
}


EXPECTED_RENTAL_CANDIDATES = {

    "서구 풍암동",
    "남구 진월동",
    "서구 치평동"
}


EXPECTED_BUS_CANDIDATES = {

    "서구 금호1동",
    "북구 첨단2동",
    "광산구 수완동",
    "남구 진월동",
    "북구 용봉동",
    "광산구 우산동"
}


EXPECTED_FACILITY_CANDIDATES = {

    "광산구 수완동",
    "북구 용봉동",
    "광산구 첨단1동",
    "서구 풍암동",
    "남구 송암동",
    "서구 금호1동"
}


EXPECTED_FACILITY_ZERO = {

    "동구 계림1동",
    "서구 화정2동",
    "북구 두암2동",
    "북구 운암1동",
    "북구 문흥1동",
    "광산구 신가동"
}


EXPECTED_LOW_HOUSING_SAMPLES = {

    "남구 방림1동":
        7,

    "광산구 신가동":
        13,

    "서구 화정2동":
        15
}


EXPECTED_INSUFFICIENT_HOUSING = {

    "북구 두암2동":
        1
}


EXPECTED_TOTAL_PUBLIC_RENTAL = 22855
EXPECTED_TOTAL_BUS_STOPS = 570
EXPECTED_TOTAL_YOUTH_FACILITIES = 57
EXPECTED_ROUTE_MATCH_RATE = 0.54


# =========================================================
# 3. 검사 결과 저장
# =========================================================

errors = []
warnings = []


def add_error(message):

    errors.append(
        message
    )


def add_warning(message):

    warnings.append(
        message
    )


# =========================================================
# 4. Boolean 변환
# =========================================================

def to_bool(value):

    if isinstance(
        value,
        bool
    ):

        return value


    text = str(
        value
    ).strip().lower()


    return text in [

        "true",
        "1",
        "yes",
        "y"

    ]


# =========================================================
# 5. Boolean 컬럼의 True 지역 가져오기
# =========================================================

def get_true_regions(
    df,
    column
):

    temp = df[
        column
    ].apply(
        to_bool
    )


    return set(

        df.loc[
            temp,
            "지역"
        ]

    )


# =========================================================
# 6. 후보 컬럼명 중 존재하는 컬럼 찾기
# =========================================================

def find_existing_column(
    df,
    candidates
):

    for column in candidates:

        if column in df.columns:

            return column


    return None


# =========================================================
# 7. 청년공공시설 수 컬럼 자동 탐색
# =========================================================

def find_facility_count_column(
    df
):

    preferred = [

        "청년공공시설수",
        "청년공공시설_수",
        "청년공공시설_개수",
        "청년공공시설_시설수",
        "청년공공시설_총개수",
        "청년공공시설_총시설수",
        "공공시설수"

    ]


    result = find_existing_column(
        df,
        preferred
    )


    if result:

        return result


    # 이름에 시설이 들어가는 숫자 컬럼 중
    # 합계가 57인 것을 찾음
    for column in df.columns:

        if "시설" not in str(
            column
        ):

            continue


        numeric = pd.to_numeric(
            df[
                column
            ],
            errors="coerce"
        )


        if numeric.notna().sum() == 0:

            continue


        total = numeric.fillna(
            0
        ).sum()


        if abs(
            total
            -
            EXPECTED_TOTAL_YOUTH_FACILITIES
        ) < 0.001:

            return column


    return None


# =========================================================
# 8. 청년공공시설 후보 컬럼 자동 탐색
# =========================================================

def find_facility_candidate_column(
    df
):

    preferred = [

        "청년공공시설_점검후보",
        "청년공공시설_수요대비점검후보",
        "청년공공시설_공급점검후보",
        "청년공공시설_정책지원후보",
        "청년공공시설_후보",
        "공공시설_점검후보"

    ]


    result = find_existing_column(
        df,
        preferred
    )


    if result:

        return result


    # 이름에 시설 + 후보/점검이 있고
    # True 지역이 기존 확정 6곳과 같으면 사용
    for column in df.columns:

        name = str(
            column
        )


        if "시설" not in name:

            continue


        if (
            "후보" not in name
            and
            "점검" not in name
        ):

            continue


        try:

            regions = get_true_regions(
                df,
                column
            )


            if (
                regions
                ==
                EXPECTED_FACILITY_CANDIDATES
            ):

                return column


        except Exception:

            pass


    return None


# =========================================================
# 9. 주거 표본수 컬럼 자동 탐색
# =========================================================

def find_housing_sample_column(
    df
):

    preferred = [

        "주거비_표본수",
        "주거표본수",
        "주거_표본수",
        "주거거래건수",
        "주거비_거래건수",
        "주거비표본수",
        "표본수"

    ]


    result = find_existing_column(
        df,
        preferred
    )


    if result:

        return result


    # 컬럼명 자동 탐색
    for column in df.columns:

        name = str(
            column
        )


        if (
            "표본" not in name
            and
            "거래" not in name
        ):

            continue


        numeric = pd.to_numeric(
            df[
                column
            ],
            errors="coerce"
        )


        if numeric.notna().sum() < 20:

            continue


        # 우리가 알고 있는 저표본 4개 지역과
        # 실제 숫자가 일치하는지 확인
        success = True


        expected = {

            **EXPECTED_LOW_HOUSING_SAMPLES,
            **EXPECTED_INSUFFICIENT_HOUSING

        }


        for region, value in expected.items():

            row = df[
                df[
                    "지역"
                ]
                == region
            ]


            if len(
                row
            ) != 1:

                success = False
                break


            actual = pd.to_numeric(
                row.iloc[
                    0
                ][
                    column
                ],
                errors="coerce"
            )


            if pd.isna(
                actual
            ):

                success = False
                break


            if int(
                actual
            ) != value:

                success = False
                break


        if success:

            return column


    return None


# =========================================================
# 10. HL 컬럼 자동 탐색
# =========================================================

def find_hl_column(
    df
):

    preferred = [

        "HL_Score",
        "HL-Score",
        "HL_SCORE",
        "HL점수",
        "HL_점수"

    ]


    result = find_existing_column(
        df,
        preferred
    )


    if result:

        return result


    for column in df.columns:

        name = str(
            column
        ).lower()


        if (
            "hl"
            in name
            and
            "score"
            in name
        ):

            return column


    return None


# =========================================================
# 11. 주거 점수 컬럼 탐색
# =========================================================

def find_housing_score_column(
    df
):

    preferred = [

        "주거가성비점수",
        "주거_가성비점수",
        "주거점수",
        "주거_점수",
        "주거비점수",
        "주거비_점수"

    ]


    result = find_existing_column(
        df,
        preferred
    )


    if result:

        return result


    for column in df.columns:

        name = str(
            column
        )


        if (
            "주거"
            in name
            and
            "점수"
            in name
        ):

            return column


    return None


# =========================================================
# 12. 시작
# =========================================================

print()

print(
    "=" * 65
)

print(
    "광주 25개 동 최종 정책통합 품질검사"
)

print(
    "=" * 65
)


# =========================================================
# 13. 파일 존재 확인
# =========================================================

if not FINAL_FILE.exists():

    print()
    print(
        "최종 정책통합 파일이 없습니다."
    )

    print(
        FINAL_FILE
    )

    sys.exit(
        1
    )


if not BASELINE_FILE.exists():

    print()
    print(
        "비교용 기존 정책통합 파일이 없습니다."
    )

    print(
        BASELINE_FILE
    )

    sys.exit(
        1
    )


# =========================================================
# 14. 데이터 읽기
# =========================================================

df = pd.read_csv(
    FINAL_FILE,
    encoding="utf-8-sig"
)


baseline = pd.read_csv(
    BASELINE_FILE,
    encoding="utf-8-sig"
)


print()
print(
    f"최종 통합 지역 : "
    f"{len(df)}개"
)

print(
    f"최종 통합 컬럼 : "
    f"{len(df.columns)}개"
)


# =========================================================
# 15. 지역 컬럼 확인
# =========================================================

if "지역" not in df.columns:

    add_error(
        "지역 컬럼이 없습니다."
    )


if "지역" not in baseline.columns:

    add_error(
        "기준 파일에 지역 컬럼이 없습니다."
    )


if errors:

    print()
    print(
        "초기 검사 실패"
    )

    for error in errors:

        print(
            "X",
            error
        )

    sys.exit(
        1
    )


# =========================================================
# 16. 지역 수 / 중복
# =========================================================

if len(
    df
) != 25:

    add_error(
        f"최종 데이터가 25개 동이 아닙니다. "
        f"현재 {len(df)}개"
    )


if df[
    "지역"
].duplicated().any():

    duplicated = (

        df.loc[
            df[
                "지역"
            ].duplicated(
                keep=False
            ),
            "지역"
        ]

        .unique()

        .tolist()

    )


    add_error(
        "중복 지역 존재 : "
        + ", ".join(
            duplicated
        )
    )


# =========================================================
# 17. 정확한 25개 지역 확인
# =========================================================

actual_regions = set(
    df[
        "지역"
    ]
)


missing_regions = (
    EXPECTED_REGIONS
    -
    actual_regions
)


extra_regions = (
    actual_regions
    -
    EXPECTED_REGIONS
)


if missing_regions:

    add_error(
        "누락 지역 : "
        + ", ".join(
            sorted(
                missing_regions
            )
        )
    )


if extra_regions:

    add_error(
        "예상하지 않은 지역 : "
        + ", ".join(
            sorted(
                extra_regions
            )
        )
    )


# =========================================================
# 18. 첨단2동 프로젝트 표기 확인
# =========================================================

if (
    "북구 첨단2동"
    not in actual_regions
):

    add_error(
        "프로젝트 표기 '북구 첨단2동'이 없습니다."
    )


if (
    "광산구 첨단2동"
    in actual_regions
):

    add_error(
        "최종 프로젝트 지역에 "
        "'광산구 첨단2동'이 별도 지역으로 존재합니다."
    )


# =========================================================
# 19. 기존 정책결과 변조 여부
# =========================================================

baseline_sorted = (

    baseline

    .sort_values(
        "지역"
    )

    .reset_index(
        drop=True
    )

)


final_sorted = (

    df

    .sort_values(
        "지역"
    )

    .reset_index(
        drop=True
    )

)


shared_columns = [

    column

    for column in baseline.columns

    if column in df.columns

]


try:

    pd.testing.assert_frame_equal(

        baseline_sorted[
            shared_columns
        ],

        final_sorted[
            shared_columns
        ],

        check_dtype=False,

        check_exact=False,

        rtol=1e-10,

        atol=1e-10

    )


except AssertionError:

    add_error(
        "버스정류소 최종 병합 과정에서 "
        "기존 정책통합 값이 변경되었습니다."
    )


# =========================================================
# 20. 최종 정책유형
# =========================================================

if (
    "최종정책유형"
    not in df.columns
):

    add_error(
        "최종정책유형 컬럼이 없습니다."
    )


else:

    actual_policy_counts = (

        df[
            "최종정책유형"
        ]

        .value_counts()

        .to_dict()

    )


    for (
        policy_type,
        expected_count
    ) in EXPECTED_POLICY_COUNTS.items():


        actual_count = int(

            actual_policy_counts.get(
                policy_type,
                0
            )

        )


        if (
            actual_count
            != expected_count
        ):

            add_error(
                f"'{policy_type}' 지역 수가 "
                f"{expected_count}개가 아닙니다. "
                f"현재 {actual_count}개"
            )


# =========================================================
# 21. 두암2동 예외처리
# =========================================================

duam = df[
    df[
        "지역"
    ]
    == "북구 두암2동"
]


if len(
    duam
) != 1:

    add_error(
        "북구 두암2동을 정확히 찾을 수 없습니다."
    )


else:

    if (
        "최종정책유형"
        in df.columns
    ):

        duam_policy = str(

            duam.iloc[
                0
            ][
                "최종정책유형"
            ]

        ).strip()


        if (
            duam_policy
            != "HL순위 제외"
        ):

            add_error(
                "두암2동의 최종정책유형이 "
                "'HL순위 제외'가 아닙니다."
            )


# =========================================================
# 22. HL-Score 검사
# =========================================================

hl_column = find_hl_column(
    df
)


if hl_column is None:

    add_error(
        "HL-Score 컬럼을 찾지 못했습니다."
    )


else:

    hl_values = pd.to_numeric(
        df[
            hl_column
        ],
        errors="coerce"
    )


    print()
    print(
        f"HL-Score 컬럼 감지 : "
        f"{hl_column}"
    )


    if hl_values.isna().any():

        add_error(
            "HL-Score에 결측값이 있습니다."
        )


    if (
        (
            hl_values
            < 0
        )
        |
        (
            hl_values
            > 100
        )
    ).any():

        add_error(
            "HL-Score에 0~100 범위를 벗어난 값이 있습니다."
        )


# =========================================================
# 23. 주거 표본수 검사
# =========================================================

housing_sample_column = (
    find_housing_sample_column(
        df
    )
)


if (
    housing_sample_column
    is None
):

    add_error(
        "주거 표본수 컬럼을 찾지 못했습니다."
    )


else:

    print(
        f"주거 표본수 컬럼 감지 : "
        f"{housing_sample_column}"
    )


    sample_values = pd.to_numeric(
        df[
            housing_sample_column
        ],
        errors="coerce"
    )


    # -----------------------------------------------
    # 저표본 5~19건
    # -----------------------------------------------

    low_sample_regions = set(

        df.loc[
            (
                sample_values
                >= 5
            )
            &
            (
                sample_values
                <= 19
            ),
            "지역"
        ]

    )


    if (
        low_sample_regions
        != set(
            EXPECTED_LOW_HOUSING_SAMPLES.keys()
        )
    ):

        add_error(
            "주거 저표본 지역이 예상 결과와 다릅니다. "
            f"현재: {sorted(low_sample_regions)}"
        )


    # -----------------------------------------------
    # 표본부족 0~4건
    # -----------------------------------------------

    insufficient_regions = set(

        df.loc[
            sample_values
            <= 4,
            "지역"
        ]

    )


    if (
        insufficient_regions
        != set(
            EXPECTED_INSUFFICIENT_HOUSING.keys()
        )
    ):

        add_error(
            "주거 표본부족 지역이 예상 결과와 다릅니다. "
            f"현재: {sorted(insufficient_regions)}"
        )


    normal_count = int(

        (
            sample_values
            >= 20
        ).sum()

    )


    low_count = int(

        (
            (
                sample_values
                >= 5
            )
            &
            (
                sample_values
                <= 19
            )
        ).sum()

    )


    insufficient_count = int(

        (
            sample_values
            <= 4
        ).sum()

    )


    if (
        normal_count
        != 21
    ):

        add_error(
            f"주거 정상표본 지역이 "
            f"21개가 아닙니다. "
            f"현재 {normal_count}개"
        )


    if (
        low_count
        != 3
    ):

        add_error(
            f"주거 저표본 지역이 "
            f"3개가 아닙니다. "
            f"현재 {low_count}개"
        )


    if (
        insufficient_count
        != 1
    ):

        add_error(
            f"주거 표본부족 지역이 "
            f"1개가 아닙니다. "
            f"현재 {insufficient_count}개"
        )


# =========================================================
# 24. 두암2동 주거점수 미사용 확인
# =========================================================

housing_score_column = (
    find_housing_score_column(
        df
    )
)


if (
    housing_score_column
    is None
):

    add_warning(
        "주거가성비점수 컬럼을 자동으로 찾지 못했습니다."
    )


else:

    print(
        f"주거점수 컬럼 감지 : "
        f"{housing_score_column}"
    )


    duam_score = pd.to_numeric(

        duam.iloc[
            0
        ][
            housing_score_column
        ],

        errors="coerce"

    )


    if not pd.isna(
        duam_score
    ):

        add_error(
            "두암2동 주거 표본이 1건인데 "
            "주거가성비점수가 사용되고 있습니다."
        )


# =========================================================
# 25. 청년 공공시설 검사
# =========================================================

facility_count_column = (
    find_facility_count_column(
        df
    )
)


if (
    facility_count_column
    is None
):

    add_error(
        "청년 공공시설 수 컬럼을 찾지 못했습니다."
    )


else:

    print(
        f"청년 공공시설 컬럼 감지 : "
        f"{facility_count_column}"
    )


    facility_values = pd.to_numeric(
        df[
            facility_count_column
        ],
        errors="coerce"
    )


    facility_total = int(

        facility_values
        .fillna(0)
        .sum()

    )


    if (
        facility_total
        != EXPECTED_TOTAL_YOUTH_FACILITIES
    ):

        add_error(
            f"25개 동 청년 공공시설 합계가 "
            f"57개가 아닙니다. "
            f"현재 {facility_total}개"
        )


    zero_facility_regions = set(

        df.loc[
            facility_values
            == 0,
            "지역"
        ]

    )


    if (
        zero_facility_regions
        != EXPECTED_FACILITY_ZERO
    ):

        add_error(
            "청년 공공시설 0개 지역이 "
            "예상 결과와 다릅니다. "
            f"현재: {sorted(zero_facility_regions)}"
        )


# =========================================================
# 26. 청년 공공시설 후보 검사
#
# 기준:
# 2030 인구 TOP10 + 공공시설 상대부족
# =========================================================

if (
    "2030인구_TOP10" not in df.columns
    or
    "공공시설_상대부족" not in df.columns
):

    add_error(
        "청년 공공시설 후보 계산에 필요한 "
        "컬럼이 없습니다."
    )


else:

    top10_values = (
        df[
            "2030인구_TOP10"
        ]
        .apply(
            to_bool
        )
    )


    facility_shortage_values = (
        df[
            "공공시설_상대부족"
        ]
        .apply(
            to_bool
        )
    )


    facility_candidate_mask = (
        top10_values
        &
        facility_shortage_values
    )


    facility_candidates = set(
        df.loc[
            facility_candidate_mask,
            "지역"
        ]
    )


    print(
        "청년 공공시설 후보 계산 : "
        "2030인구 TOP10 + 공공시설 상대부족"
    )


    if (
        facility_candidates
        != EXPECTED_FACILITY_CANDIDATES
    ):

        add_error(
            "청년 공공시설 후보지역이 "
            "예상 결과와 다릅니다. "
            f"현재: {sorted(facility_candidates)}"
        )


    else:

        print(
            f"청년 공공시설 점검후보 : "
            f"{len(facility_candidates)}개"
        )

        for region in sorted(
            facility_candidates
        ):

            print(
                "-",
                region
            )


# =========================================================
# 27. 공공임대 검사
# =========================================================

required_rental_columns = [

    "공공임대_세대수",

    "청년주거지원_점검후보",

    "공공임대_HL반영여부"

]


for column in required_rental_columns:

    if column not in df.columns:

        add_error(
            f"공공임대 필수 컬럼 누락 : {column}"
        )


if all(
    column in df.columns
    for column
    in required_rental_columns
):

    rental_total = int(

        pd.to_numeric(
            df[
                "공공임대_세대수"
            ],
            errors="coerce"
        )

        .fillna(0)

        .sum()

    )


    if (
        rental_total
        != EXPECTED_TOTAL_PUBLIC_RENTAL
    ):

        add_error(
            f"공공임대 총 세대수가 "
            f"22,855세대가 아닙니다. "
            f"현재 {rental_total:,}세대"
        )


    rental_candidates = (
        get_true_regions(
            df,
            "청년주거지원_점검후보"
        )
    )


    if (
        rental_candidates
        != EXPECTED_RENTAL_CANDIDATES
    ):

        add_error(
            "청년주거지원 점검후보가 "
            "예상 결과와 다릅니다. "
            f"현재: {sorted(rental_candidates)}"
        )


    if (

        df[
            "공공임대_HL반영여부"
        ]

        .apply(
            to_bool
        )

        .any()

    ):

        add_error(
            "공공임대 지표가 HL-Score에 반영된 지역이 있습니다."
        )


# =========================================================
# 28. 공식 버스정류소 검사
# =========================================================

required_bus_columns = [

    "공식정류소수",

    "청년1000명당_정류소수",

    "청년교통공급_점검후보",

    "버스정류소_HL반영여부",

    "버스노선_정책분석사용여부",

    "버스노선데이터_안전매칭률"

]


for column in required_bus_columns:

    if column not in df.columns:

        add_error(
            f"버스정류소 필수 컬럼 누락 : {column}"
        )


if all(
    column in df.columns
    for column
    in required_bus_columns
):

    bus_total = int(

        pd.to_numeric(
            df[
                "공식정류소수"
            ],
            errors="coerce"
        )

        .fillna(0)

        .sum()

    )


    if (
        bus_total
        != EXPECTED_TOTAL_BUS_STOPS
    ):

        add_error(
            f"25개 동 공식 정류소 합계가 "
            f"570개가 아닙니다. "
            f"현재 {bus_total}개"
        )


    bus_candidates = (
        get_true_regions(
            df,
            "청년교통공급_점검후보"
        )
    )


    if (
        bus_candidates
        != EXPECTED_BUS_CANDIDATES
    ):

        add_error(
            "청년교통공급 점검후보가 "
            "예상 결과와 다릅니다. "
            f"현재: {sorted(bus_candidates)}"
        )


    if (

        df[
            "버스정류소_HL반영여부"
        ]

        .apply(
            to_bool
        )

        .any()

    ):

        add_error(
            "버스정류소 보조지표가 "
            "HL-Score에 반영된 지역이 있습니다."
        )


    if (

        df[
            "버스노선_정책분석사용여부"
        ]

        .apply(
            to_bool
        )

        .any()

    ):

        add_error(
            "신뢰도가 낮은 버스 노선 데이터가 "
            "정책분석에 사용되고 있습니다."
        )


    match_rates = (

        pd.to_numeric(
            df[
                "버스노선데이터_안전매칭률"
            ],
            errors="coerce"
        )

        .dropna()

        .unique()

    )


    if len(
        match_rates
    ) != 1:

        add_error(
            "버스노선 안전 매칭률 값이 "
            "지역별로 일관되지 않습니다."
        )


    else:

        match_rate = float(
            match_rates[
                0
            ]
        )


        if abs(
            match_rate
            -
            EXPECTED_ROUTE_MATCH_RATE
        ) > 0.01:

            add_error(
                f"버스노선 안전 매칭률이 "
                f"0.54%가 아닙니다. "
                f"현재 {match_rate:.2f}%"
            )


# =========================================================
# 29. 주요 지역 정책유형 재확인
# =========================================================

important_regions = {

    "서구 풍암동":
        "복합 최우선 검토",

    "남구 진월동":
        "복합 관심 검토",

    "서구 금호1동":
        "복합 관심 검토",

    "남구 송암동":
        "복합 관심 검토",

    "북구 두암2동":
        "HL순위 제외"

}


if (
    "최종정책유형"
    in df.columns
):

    for (
        region,
        expected_type
    ) in important_regions.items():


        row = df[
            df[
                "지역"
            ]
            == region
        ]


        if len(
            row
        ) != 1:

            add_error(
                f"{region}을 찾을 수 없습니다."
            )

            continue


        actual_type = str(

            row.iloc[
                0
            ][
                "최종정책유형"
            ]

        ).strip()


        if (
            actual_type
            != expected_type
        ):

            add_error(
                f"{region} 정책유형 변경: "
                f"기대 '{expected_type}' "
                f"/ 현재 '{actual_type}'"
            )


# =========================================================
# 30. 최종 검사 요약
# =========================================================

print()
print(
    "-" * 65
)

print(
    "최종 검사 요약"
)

print(
    "-" * 65
)


print(
    f"분석 지역 : "
    f"{len(df)}개"
)


if (
    "최종정책유형"
    in df.columns
):

    print()
    print(
        "[최종 정책유형]"
    )


    policy_counts = (

        df[
            "최종정책유형"
        ]

        .value_counts()

    )


    for (
        policy_type,
        count
    ) in policy_counts.items():

        print(
            f"- {policy_type} : "
            f"{count}개"
        )


if (
    facility_count_column
    is not None
):

    print()
    print(
        f"청년 공공시설 : "
        f"{int(pd.to_numeric(df[facility_count_column], errors='coerce').fillna(0).sum())}개"
    )


if (
    "공공임대_세대수"
    in df.columns
):

    print(
        f"공공임대 : "
        f"{int(pd.to_numeric(df['공공임대_세대수'], errors='coerce').fillna(0).sum()):,}세대"
    )


if (
    "공식정류소수"
    in df.columns
):

    print(
        f"공식 버스정류소 : "
        f"{int(pd.to_numeric(df['공식정류소수'], errors='coerce').fillna(0).sum())}개"
    )


if (
    "청년주거지원_점검후보"
    in df.columns
):

    print(
        f"청년주거지원 점검후보 : "
        f"{len(get_true_regions(df, '청년주거지원_점검후보'))}개"
    )


if (
    "청년교통공급_점검후보"
    in df.columns
):

    print(
        f"청년교통공급 점검후보 : "
        f"{len(get_true_regions(df, '청년교통공급_점검후보'))}개"
    )


# =========================================================
# 31. 최종 판정
# =========================================================

print()
print(
    "=" * 65
)

print(
    "최종 통합 품질검사 결과"
)

print(
    "=" * 65
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
        f"총 오류 : "
        f"{len(errors)}개"
    )


    print()
    print(
        "최종 정책통합 품질검사 : FAIL"
    )


    sys.exit(
        1
    )


else:

    print()
    print(
        "모든 핵심 검사 통과"
    )


    print(
        "25개 행정동의 누락·중복이 없습니다."
    )


    print(
        "기존 HL-Score와 정책유형이 유지되었습니다."
    )


    print(
        "주거 표본 정상 21개 / 저표본 3개 / "
        "표본부족 1개 구조가 유지되었습니다."
    )


    print(
        "두암2동은 주거 표본 1건으로 "
        "HL 정책순위에서 정상 제외되어 있습니다."
    )


    print(
        "청년 공공시설 57개가 정상 반영되어 있습니다."
    )


    print(
        "공공임대 22,855세대가 정상 반영되어 있습니다."
    )


    print(
        "공식 버스정류소 570개가 정상 반영되어 있습니다."
    )


    print(
        "신뢰도가 낮은 버스 노선 데이터는 "
        "정책분석에서 정상 제외되어 있습니다."
    )


    print(
        "공공임대와 버스정류소 보조지표가 "
        "HL-Score에 혼입되지 않았습니다."
    )


    print(
        "첨단2동 프로젝트 표기와 "
        "두암2동 예외처리도 정상입니다."
    )


    if not warnings:

        print(
            "추가 경고사항도 없습니다."
        )


    print()
    print(
        "최종 정책통합 품질검사 : PASS"
    )