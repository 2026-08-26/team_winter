from pathlib import Path

import numpy as np
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

INTEGRATED_FILE = (
    PROCESSED_DIR
    / "25개동_통합분석.csv"
)

HOUSING_FILE = (
    PROCESSED_DIR
    / "동별_주거비.csv"
)

OUTPUT_INTEGRATED = (
    PROCESSED_DIR
    / "25개동_통합분석_주거재계산.csv"
)

OUTPUT_SCORE = (
    PROCESSED_DIR
    / "HL_Score_재계산결과.csv"
)


# =========================================================
# 2. HL 가중치
#
# 프로젝트 분석용 가정
# =========================================================

WEIGHT_LIFE = 0.30
WEIGHT_YOUTH = 0.25
WEIGHT_TRANSPORT = 0.15
WEIGHT_HOUSING = 0.30


# =========================================================
# 3. 주거 표본 기준
#
# 프로젝트 내부 품질관리 기준
# =========================================================

NORMAL_SAMPLE = 20
MIN_USABLE_SAMPLE = 5


# =========================================================
# 4. 숫자 변환
# =========================================================

def to_numeric(series):

    return pd.to_numeric(
        series.astype(str)
        .str.replace(
            ",",
            "",
            regex=False
        ),
        errors="coerce"
    )


# =========================================================
# 5. 값이 클수록 좋은 지표
#
# 0 ~ 100
# =========================================================

def normalize_positive(
    series,
    use_log=False
):

    series = pd.to_numeric(
        series,
        errors="coerce"
    ).fillna(0)


    if use_log:

        series = np.log1p(
            series
        )


    min_value = series.min()
    max_value = series.max()


    if max_value == 0:

        return pd.Series(
            [0.0] * len(series),
            index=series.index
        )


    if max_value == min_value:

        return pd.Series(
            [50.0] * len(series),
            index=series.index
        )


    return (

        (
            series
            - min_value
        )

        /

        (
            max_value
            - min_value
        )

        * 100

    )


# =========================================================
# 6. 거리가 짧을수록 좋은 지표
#
# 0 ~ 100
# =========================================================

def normalize_distance(
    series
):

    series = pd.to_numeric(
        series,
        errors="coerce"
    )


    if not series.notna().any():

        return pd.Series(
            [0.0] * len(series),
            index=series.index
        )


    # 거리가 없는 경우
    # 현재 데이터에서 가장 먼 거리로 처리
    worst_distance = (
        series.max()
    )


    series = series.fillna(
        worst_distance
    )


    min_value = series.min()
    max_value = series.max()


    if max_value == min_value:

        return pd.Series(
            [50.0] * len(series),
            index=series.index
        )


    return (

        1

        -

        (
            (
                series
                - min_value
            )

            /

            (
                max_value
                - min_value
            )
        )

    ) * 100


# =========================================================
# 7. 주거 표본상태
# =========================================================

def housing_sample_status(
    count
):

    if pd.isna(
        count
    ):

        return "표본부족"


    count = int(
        count
    )


    if count < MIN_USABLE_SAMPLE:

        return "표본부족"


    if count < NORMAL_SAMPLE:

        return "저표본 주의"


    return "정상"


# =========================================================
# 8. 필수 컬럼 검사
# =========================================================

def validate_required_columns(
    df,
    required_columns,
    file_name
):

    missing = [

        column

        for column
        in required_columns

        if column not in df.columns

    ]


    if missing:

        print()
        print(
            "========================================"
        )

        print(
            f"{file_name} 필수 컬럼 누락"
        )

        print(
            "========================================"
        )


        for column in missing:

            print(
                "-",
                column
            )


        raise ValueError(
            "필수 컬럼이 없어 계산을 중단합니다."
        )


# =========================================================
# 9. 메인
# =========================================================

def main():

    print()
    print(
        "========================================"
    )

    print(
        "HL-Score 재계산 시작"
    )

    print(
        "========================================"
    )


    print(
        "주거 기준:"
    )

    print(
        "- 2025-07 ~ 2026-06"
    )

    print(
        "- 전용면적 59.5㎡ 이하"
    )

    print(
        "- 전세 + 월세"
    )

    print(
        "- 월환산주거비 평균값 사용"
    )

    print(
        "- 실제 주소→공식 행정동 매핑"
    )


    # =====================================================
    # 10. 파일 존재 확인
    # =====================================================

    if not INTEGRATED_FILE.exists():

        print()
        print(
            "통합분석 파일이 없습니다."
        )

        print(
            INTEGRATED_FILE
        )

        return


    if not HOUSING_FILE.exists():

        print()
        print(
            "동별 주거비 파일이 없습니다."
        )

        print(
            HOUSING_FILE
        )

        return


    # =====================================================
    # 11. 파일 읽기
    # =====================================================

    integrated = pd.read_csv(
        INTEGRATED_FILE,
        encoding="utf-8-sig"
    )


    housing = pd.read_csv(
        HOUSING_FILE,
        encoding="utf-8-sig"
    )


    print()
    print(
        f"기존 통합분석 : "
        f"{len(integrated)}개 동"
    )

    print(
        f"새 주거비 : "
        f"{len(housing)}개 동"
    )


    # =====================================================
    # 12. 25개 동 검사
    # =====================================================

    if len(
        integrated
    ) != 25:

        raise ValueError(
            "기존 통합분석 데이터가 25개 동이 아닙니다."
        )


    if len(
        housing
    ) != 25:

        raise ValueError(
            "새 주거비 데이터가 25개 동이 아닙니다."
        )


    # =====================================================
    # 13. 중복 지역 검사
    # =====================================================

    if integrated.duplicated(
        subset=[
            "자치구",
            "행정동"
        ]
    ).any():

        raise ValueError(
            "기존 통합분석에 중복 지역이 있습니다."
        )


    if housing.duplicated(
        subset=[
            "자치구",
            "행정동"
        ]
    ).any():

        raise ValueError(
            "새 주거비 데이터에 중복 지역이 있습니다."
        )


    # =====================================================
    # 14. 생활인프라 필수 컬럼
    # =====================================================

    life_facilities = [

        "편의점",
        "카페",
        "음식점",
        "병원",
        "대형마트",
        "지하철역",
        "문화시설"

    ]


    life_required = []


    for facility in life_facilities:

        life_required.append(
            f"{facility}_개수"
        )

        life_required.append(
            f"{facility}_최소거리_m"
        )


    # =====================================================
    # 15. 2030 선호시설 필수 컬럼
    # =====================================================

    youth_categories = [

        "H&B/뷰티",
        "생활쇼핑",
        "SPA패션",
        "영화/문화",
        "대형쇼핑",
        "운동",
        "문화생활",
        "패스트푸드"

    ]


    youth_required = []


    for category in youth_categories:

        youth_required.append(
            f"추가_{category}_개수"
        )

        youth_required.append(
            f"추가_{category}_최소거리_m"
        )


    # =====================================================
    # 16. 교통 필수 컬럼
    # =====================================================

    transport_required = [

        "버스정류소_1500m_개수",
        "가장가까운_버스정류소_m"

    ]


    # =====================================================
    # 17. 필수 컬럼 검사
    # =====================================================

    validate_required_columns(

        integrated,

        [
            "자치구",
            "행정동"
        ]
        + life_required
        + youth_required
        + transport_required,

        "25개동_통합분석.csv"

    )


    validate_required_columns(

        housing,

        [

            "자치구",
            "행정동",

            "전체거래건수",

            "월환산주거비_평균값_만원",

            "월환산주거비_중앙값_만원",

            "표본상태"

        ],

        "동별_주거비.csv"

    )


    # =====================================================
    # 18. 기존 통합파일에서
    #     예전 주거비 컬럼 제거
    #
    # 새 주거비 CSV의 컬럼으로 교체
    # =====================================================

    housing_columns = [

        column

        for column in housing.columns

        if column not in [
            "자치구",
            "행정동"
        ]

    ]


    columns_to_drop = [

        column

        for column in housing_columns

        if column in integrated.columns

    ]


    integrated = integrated.drop(
        columns=columns_to_drop,
        errors="ignore"
    )


    # =====================================================
    # 19. 새 주거비 병합
    # =====================================================

    df = integrated.merge(

        housing,

        on=[
            "자치구",
            "행정동"
        ],

        how="left",

        validate="one_to_one"

    )


    # =====================================================
    # 20. 병합 검증
    # =====================================================

    missing_housing = df[
        df[
            "전체거래건수"
        ].isna()
    ]


    if not missing_housing.empty:

        print()
        print(
            "주거비가 연결되지 않은 지역:"
        )


        print(

            missing_housing[
                [
                    "자치구",
                    "행정동"
                ]
            ].to_string(
                index=False
            )

        )


        raise ValueError(
            "주거비 병합 실패 지역이 있습니다."
        )


    # =====================================================
    # 21. 지역명
    # =====================================================

    df[
        "지역"
    ] = (

        df[
            "자치구"
        ].astype(str)

        + " "

        + df[
            "행정동"
        ].astype(str)

    )


    # =====================================================
    # 22. 생활 인프라 점수
    #
    # 개수 60%
    # 거리 40%
    # =====================================================

    life_scores = []


    for facility in life_facilities:

        count_column = (
            f"{facility}_개수"
        )

        distance_column = (
            f"{facility}_최소거리_m"
        )


        count_score = normalize_positive(

            df[
                count_column
            ],

            use_log=True

        )


        distance_score = normalize_distance(

            df[
                distance_column
            ]

        )


        facility_score = (

            count_score
            * 0.60

            +

            distance_score
            * 0.40

        )


        life_scores.append(
            facility_score
        )


    생활인프라점수 = (

        pd.concat(
            life_scores,
            axis=1
        )

        .mean(
            axis=1
        )

    )


    # =====================================================
    # 23. 2030 선호시설 점수
    #
    # 개수 60%
    # 거리 40%
    # =====================================================

    youth_scores = []


    for category in youth_categories:

        count_column = (
            f"추가_{category}_개수"
        )

        distance_column = (
            f"추가_{category}_최소거리_m"
        )


        count_score = normalize_positive(

            df[
                count_column
            ],

            use_log=True

        )


        distance_score = normalize_distance(

            df[
                distance_column
            ]

        )


        category_score = (

            count_score
            * 0.60

            +

            distance_score
            * 0.40

        )


        youth_scores.append(
            category_score
        )


    청년선호시설점수 = (

        pd.concat(
            youth_scores,
            axis=1
        )

        .mean(
            axis=1
        )

    )


    # =====================================================
    # 24. 교통 접근성 점수
    # =====================================================

    bus_count_score = normalize_positive(

        df[
            "버스정류소_1500m_개수"
        ],

        use_log=True

    )


    bus_distance_score = normalize_distance(

        df[
            "가장가까운_버스정류소_m"
        ]

    )


    교통접근성점수 = (

        bus_count_score
        * 0.60

        +

        bus_distance_score
        * 0.40

    )


    # =====================================================
    # 25. 접근성 지수
    #
    # 주거비를 제외한 70%를
    # 다시 100점으로 환산
    #
    # 두암2동처럼 주거 표본부족인 경우
    # 이 점수를 HL-Score로 사용
    # =====================================================

    접근성지수 = (

        생활인프라점수
        * (30 / 70)

        +

        청년선호시설점수
        * (25 / 70)

        +

        교통접근성점수
        * (15 / 70)

    )


    # =====================================================
    # 26. 새 주거비
    # =====================================================

    housing_cost = to_numeric(

        df[
            "월환산주거비_평균값_만원"
        ]

    )


    housing_count = to_numeric(

        df[
            "전체거래건수"
        ]

    )


    # =====================================================
    # 27. 주거비 사용 가능 여부
    #
    # 5건 이상 = 사용
    # 0~4건 = 사용하지 않음
    # =====================================================

    housing_usable = (

        (
            housing_count
            >= MIN_USABLE_SAMPLE
        )

        &

        housing_cost.notna()

    )


    # =====================================================
    # 28. 주거 표본상태
    # =====================================================

    주거표본상태 = (

        housing_count

        .apply(
            housing_sample_status
        )

    )


    # =====================================================
    # 29. 주거 가성비 점수
    #
    # 반드시 사용 가능한 지역만으로
    # Min-Max 범위를 계산
    #
    # 주거비가 낮을수록 높은 점수
    # =====================================================

    valid_housing_cost = housing_cost[
        housing_usable
    ]


    housing_min = (
        valid_housing_cost.min()
    )

    housing_max = (
        valid_housing_cost.max()
    )


    주거가성비점수 = pd.Series(

        np.nan,

        index=df.index,

        dtype=float

    )


    가격_norm = pd.Series(

        np.nan,

        index=df.index,

        dtype=float

    )


    if (
        len(
            valid_housing_cost
        ) > 0

        and

        housing_max
        != housing_min
    ):


        가격_norm.loc[
            housing_usable
        ] = (

            (
                housing_cost[
                    housing_usable
                ]
                - housing_min
            )

            /

            (
                housing_max
                - housing_min
            )

        )


        주거가성비점수.loc[
            housing_usable
        ] = (

            1

            -

            가격_norm.loc[
                housing_usable
            ]

        ) * 100


    elif len(
        valid_housing_cost
    ) > 0:


        가격_norm.loc[
            housing_usable
        ] = 0.5


        주거가성비점수.loc[
            housing_usable
        ] = 50.0


    # =====================================================
    # 30. 일반 HL-Score
    #
    # 주거 데이터 사용 가능 지역
    # =====================================================

    full_hl_score = (

        생활인프라점수
        * WEIGHT_LIFE

        +

        청년선호시설점수
        * WEIGHT_YOUTH

        +

        교통접근성점수
        * WEIGHT_TRANSPORT

        +

        주거가성비점수
        * WEIGHT_HOUSING

    )


    # =====================================================
    # 31. 최종 HL-Score
    #
    # 주거 표본부족이면
    # 주거 30% 제외 후
    # 나머지 70% 재가중
    # =====================================================

    HL_Score = pd.Series(

        np.nan,

        index=df.index,

        dtype=float

    )


    HL_Score.loc[
        housing_usable
    ] = full_hl_score.loc[
        housing_usable
    ]


    HL_Score.loc[
        ~housing_usable
    ] = 접근성지수.loc[
        ~housing_usable
    ]


    # =====================================================
    # 32. HL 산출유형
    # =====================================================

    HL산출유형 = pd.Series(
        "",
        index=df.index,
        dtype=object
    )


    HL산출유형.loc[
        housing_usable
    ] = (
        "4개 영역 전체 반영"
    )


    HL산출유형.loc[
        ~housing_usable
    ] = (
        "주거비 제외·나머지 70% 재가중"
    )


    # =====================================================
    # 33. 비교 가능성
    # =====================================================

    HL비교가능성 = pd.Series(
        "",
        index=df.index,
        dtype=object
    )


    HL비교가능성.loc[
        housing_count >= NORMAL_SAMPLE
    ] = "정상"


    HL비교가능성.loc[
        (
            housing_count
            >= MIN_USABLE_SAMPLE
        )
        &
        (
            housing_count
            < NORMAL_SAMPLE
        )
    ] = "저표본 주의"


    HL비교가능성.loc[
        housing_count
        < MIN_USABLE_SAMPLE
    ] = "제한"


    # =====================================================
    # 34. 정책 순위 포함 여부
    #
    # 표본 5건 미만은
    # 공식 HL 상대순위에서 제외
    # =====================================================

    정책순위포함여부 = (
        housing_usable
    )


    # =====================================================
    # 35. HL 정책비교 순위
    #
    # 높은 점수 = 높은 순위
    #
    # 주거 표본부족 지역은
    # 순위에 포함하지 않음
    # =====================================================

    HL정책비교순위 = pd.Series(

        pd.NA,

        index=df.index,

        dtype="Int64"

    )


    eligible_scores = HL_Score[
        정책순위포함여부
    ]


    ranks = (

        eligible_scores

        .rank(
            ascending=False,
            method="min"
        )

        .astype(
            "Int64"
        )

    )


    HL정책비교순위.loc[
        정책순위포함여부
    ] = ranks


    # =====================================================
    # 36. 결과 컬럼 저장
    # =====================================================

    df[
        "생활인프라점수"
    ] = 생활인프라점수.round(1)


    df[
        "2030선호시설점수"
    ] = 청년선호시설점수.round(1)


    df[
        "교통접근성점수"
    ] = 교통접근성점수.round(1)


    df[
        "접근성지수"
    ] = 접근성지수.round(1)


    df[
        "주거가성비점수"
    ] = 주거가성비점수.round(1)


    df[
        "가격_norm"
    ] = 가격_norm.round(4)


    df[
        "HL_Score"
    ] = HL_Score.round(1)


    df[
        "주거표본판정"
    ] = 주거표본상태


    df[
        "주거점수사용여부"
    ] = housing_usable


    df[
        "HL산출유형"
    ] = HL산출유형


    df[
        "HL비교가능성"
    ] = HL비교가능성


    df[
        "정책순위포함여부"
    ] = 정책순위포함여부


    df[
        "HL정책비교순위"
    ] = HL정책비교순위


    # =====================================================
    # 37. 결과 저장
    #
    # 기존 통합파일은 아직 덮어쓰지 않음
    # =====================================================

    df.to_csv(

        OUTPUT_INTEGRATED,

        index=False,

        encoding="utf-8-sig"

    )


    # =====================================================
    # 38. HL 결과 요약 파일
    # =====================================================

    score_columns = [

        "자치구",
        "행정동",
        "지역",

        "전체거래건수",

        "월환산주거비_평균값_만원",

        "주거표본판정",

        "생활인프라점수",
        "2030선호시설점수",
        "교통접근성점수",

        "주거가성비점수",

        "접근성지수",

        "HL_Score",

        "HL정책비교순위",

        "HL산출유형",

        "HL비교가능성",

        "정책순위포함여부"

    ]


    score_df = df[
        score_columns
    ].copy()


    score_df = (

        score_df

        .sort_values(

            by=[
                "정책순위포함여부",
                "HL_Score"
            ],

            ascending=[
                False,
                False
            ]

        )

        .reset_index(
            drop=True
        )

    )


    score_df.to_csv(

        OUTPUT_SCORE,

        index=False,

        encoding="utf-8-sig"

    )


    # =====================================================
    # 39. 검증 결과
    # =====================================================

    print()
    print(
        "========================================"
    )

    print(
        "HL-Score 재계산 결과"
    )

    print(
        "========================================"
    )


    print(
        f"전체 분석지역 : "
        f"{len(df)}개"
    )


    normal_count = (
        주거표본상태
        == "정상"
    ).sum()


    low_count = (
        주거표본상태
        == "저표본 주의"
    ).sum()


    insufficient_count = (
        주거표본상태
        == "표본부족"
    ).sum()


    print(
        f"주거표본 정상 : "
        f"{normal_count}개"
    )

    print(
        f"저표본 주의 : "
        f"{low_count}개"
    )

    print(
        f"주거 표본부족 : "
        f"{insufficient_count}개"
    )


    print(
        f"HL 정책순위 포함 : "
        f"{정책순위포함여부.sum()}개"
    )


    print(
        f"HL 정책순위 제외 : "
        f"{(~정책순위포함여부).sum()}개"
    )


    # =====================================================
    # 40. 주거비 범위
    # =====================================================

    print()
    print(
        "----------------------------------------"
    )

    print(
        "주거가성비 점수 계산 범위"
    )

    print(
        "----------------------------------------"
    )


    print(
        f"최저 월환산주거비 : "
        f"{housing_min:.2f}만원"
    )

    print(
        f"최고 월환산주거비 : "
        f"{housing_max:.2f}만원"
    )


    # =====================================================
    # 41. 저표본 지역
    # =====================================================

    print()
    print(
        "========================================"
    )

    print(
        "저표본 지역"
    )

    print(
        "========================================"
    )


    low_sample_df = df[
        housing_count
        < NORMAL_SAMPLE
    ]


    for _, row in (

        low_sample_df

        .sort_values(
            "전체거래건수"
        )

        .iterrows()

    ):

        print()

        print(
            f"[{row['지역']}]"
        )

        print(
            f"거래건수 : "
            f"{int(row['전체거래건수'])}건"
        )

        print(
            f"월환산주거비 평균 : "
            f"{row['월환산주거비_평균값_만원']}만원"
        )

        print(
            f"주거표본판정 : "
            f"{row['주거표본판정']}"
        )

        print(
            f"HL산출유형 : "
            f"{row['HL산출유형']}"
        )

        print(
            f"HL-Score : "
            f"{row['HL_Score']}"
        )


    # =====================================================
    # 42. 정책비교 가능 지역 중
    #     HL 낮은 지역 5곳
    # =====================================================

    print()
    print(
        "========================================"
    )

    print(
        "HL-Score 낮은 지역 5곳"
    )

    print(
        "※ 정책순위 포함 지역만 비교"
    )

    print(
        "========================================"
    )


    eligible_df = (

        df[
            정책순위포함여부
        ]

        .sort_values(
            "HL_Score",
            ascending=True
        )

        .head(5)

    )


    for _, row in (
        eligible_df.iterrows()
    ):

        print()

        print(
            f"{row['지역']}"
        )

        print(
            f"HL-Score : "
            f"{row['HL_Score']}"
        )

        print(
            f"주거비 : "
            f"{row['월환산주거비_평균값_만원']}만원"
        )

        print(
            f"주거가성비점수 : "
            f"{row['주거가성비점수']}"
        )


    # =====================================================
    # 43. 두암2동 별도 확인
    # =====================================================

    print()
    print(
        "========================================"
    )

    print(
        "두암2동 표본부족 처리 확인"
    )

    print(
        "========================================"
    )


    duam = df[
        df[
            "행정동"
        ]
        == "두암2동"
    ]


    if not duam.empty:

        row = duam.iloc[0]


        print(
            f"거래건수 : "
            f"{int(row['전체거래건수'])}건"
        )

        print(
            f"실제 월환산주거비 : "
            f"{row['월환산주거비_평균값_만원']}만원"
        )

        print(
            f"주거가성비점수 : "
            f"{row['주거가성비점수']}"
        )

        print(
            f"접근성지수 : "
            f"{row['접근성지수']}"
        )

        print(
            f"HL-Score : "
            f"{row['HL_Score']}"
        )

        print(
            f"HL 산출유형 : "
            f"{row['HL산출유형']}"
        )

        print(
            f"정책순위 포함 : "
            f"{row['정책순위포함여부']}"
        )


    # =====================================================
    # 44. 저장 위치
    # =====================================================

    print()
    print(
        "========================================"
    )

    print(
        "재계산 완료"
    )

    print(
        "========================================"
    )


    print()
    print(
        "새 통합분석 파일:"
    )

    print(
        OUTPUT_INTEGRATED
    )


    print()
    print(
        "HL 점수 결과:"
    )

    print(
        OUTPUT_SCORE
    )


    print()
    print(
        "※ 기존 25개동_통합분석.csv는 "
        "아직 변경하지 않았습니다."
    )


# =========================================================
# 실행
# =========================================================

if __name__ == "__main__":

    main()