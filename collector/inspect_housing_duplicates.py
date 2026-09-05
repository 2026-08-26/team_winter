from pathlib import Path

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
    / "청년소형주택_25개동_실거래.csv"
)

OUTPUT_EXACT = (
    PROCESSED_DIR
    / "주거_완전동일행_점검.csv"
)

OUTPUT_SUSPECT = (
    PROCESSED_DIR
    / "주거_중복의심그룹_상세.csv"
)


# =========================================================
# 2. 매핑 과정에서 추가된 컬럼
#
# 실제 국토부 거래 원본 비교에서는 제외
# =========================================================

MAPPING_COLUMNS = [

    "주소키",

    "위도",
    "경도",

    "검색주소",
    "카카오매칭주소",

    "공식자치구",
    "공식행정동",
    "행정동코드",

    "매핑상태",

    "프로젝트자치구",
    "프로젝트행정동",

    "분석대상여부",

    "공식지역",
    "프로젝트지역"
]


# =========================================================
# 3. 기존 중복 의심 기준
# =========================================================

SUSPECT_COLUMNS_CANDIDATES = [

    "gu_name",
    "umdNm",
    "jibun",

    "housing_type",

    "excluUseAr",
    "deposit",
    "monthlyRent",

    "dealYear",
    "dealMonth",
    "dealDay",

    "floor",

    "query_ym"
]


# =========================================================
# 4. 값 정리
# =========================================================

def normalize_dataframe(df):

    result = df.copy()


    for column in result.columns:

        result[column] = (

            result[column]

            .fillna("")

            .astype(str)

            .str.strip()

        )


    return result


# =========================================================
# 5. 메인
# =========================================================

def main():

    print()
    print(
        "========================================"
    )

    print(
        "주거 실거래 중복 의심 데이터 정밀검사"
    )

    print(
        "========================================"
    )


    # =====================================================
    # 파일 확인
    # =====================================================

    if not INPUT_FILE.exists():

        print(
            "\n입력 파일을 찾을 수 없습니다."
        )

        print(
            INPUT_FILE
        )

        return


    # =====================================================
    # 데이터 읽기
    # =====================================================

    df = pd.read_csv(
        INPUT_FILE,
        encoding="utf-8-sig",
        dtype=str,
        keep_default_na=False
    )


    df = normalize_dataframe(
        df
    )


    print(
        f"\n전체 실거래 : "
        f"{len(df):,}건"
    )


    # =====================================================
    # 6. 실제 원본 데이터 컬럼만 선택
    # =====================================================

    raw_columns = [

        column

        for column in df.columns

        if column not in MAPPING_COLUMNS

    ]


    print(
        f"원본 비교 컬럼 : "
        f"{len(raw_columns)}개"
    )


    # =====================================================
    # 7. 완전히 동일한 원본 행 검사
    # =====================================================

    exact_duplicate_mask = (

        df.duplicated(
            subset=raw_columns,
            keep=False
        )

    )


    exact_duplicates = df[
        exact_duplicate_mask
    ].copy()


    exact_group_count = 0


    if not exact_duplicates.empty:

        exact_group_count = (

            exact_duplicates

            .groupby(
                raw_columns,
                dropna=False
            )

            .ngroups

        )


        exact_duplicates.to_csv(
            OUTPUT_EXACT,
            index=False,
            encoding="utf-8-sig"
        )


    # =====================================================
    # 8. 기존 방식의 중복 의심 그룹
    # =====================================================

    suspect_columns = [

        column

        for column
        in SUSPECT_COLUMNS_CANDIDATES

        if column in df.columns

    ]


    suspect_mask = (

        df.duplicated(
            subset=suspect_columns,
            keep=False
        )

    )


    suspect_df = df[
        suspect_mask
    ].copy()


    # =====================================================
    # 그룹 번호 추가
    # =====================================================

    if not suspect_df.empty:

        suspect_df[
            "중복의심그룹"
        ] = (

            suspect_df

            .groupby(
                suspect_columns,
                dropna=False
            )

            .ngroup()

            + 1

        )


        suspect_df[
            "그룹내행수"
        ] = (

            suspect_df

            .groupby(
                "중복의심그룹"
            )[
                "중복의심그룹"
            ]

            .transform(
                "size"
            )

        )


        suspect_df.to_csv(
            OUTPUT_SUSPECT,
            index=False,
            encoding="utf-8-sig"
        )


    # =====================================================
    # 9. 중복 의심 그룹 통계
    # =====================================================

    if not suspect_df.empty:

        group_sizes = (

            suspect_df

            .groupby(
                "중복의심그룹"
            )

            .size()

        )


        suspect_group_count = len(
            group_sizes
        )


        max_group_size = int(
            group_sizes.max()
        )


    else:

        suspect_group_count = 0

        max_group_size = 0


    # =====================================================
    # 10. 결과 출력
    # =====================================================

    print()
    print(
        "----------------------------------------"
    )

    print(
        "중복 검사 결과"
    )

    print(
        "----------------------------------------"
    )


    print(
        f"전체 거래 : "
        f"{len(df):,}건"
    )


    print(
        f"기존 기준 중복 의심 행 : "
        f"{len(suspect_df):,}건"
    )


    print(
        f"중복 의심 그룹 : "
        f"{suspect_group_count:,}개"
    )


    print(
        f"가장 큰 의심 그룹 : "
        f"{max_group_size}건"
    )


    print()
    print(
        f"모든 원본 컬럼까지 완전히 동일한 행 : "
        f"{len(exact_duplicates):,}건"
    )


    print(
        f"완전 동일 그룹 : "
        f"{exact_group_count:,}개"
    )


    # =====================================================
    # 11. 판단
    # =====================================================

    print()
    print(
        "========================================"
    )

    print(
        "중복 데이터 1차 판정"
    )

    print(
        "========================================"
    )


    if len(
        exact_duplicates
    ) == 0:

        print()
        print(
            "완전히 동일한 원본 거래는 발견되지 않았습니다."
        )

        print()
        print(
            "기존 243건은 동일 가격·면적·날짜 등이 "
            "겹친 거래일 가능성이 높습니다."
        )

        print()
        print(
            "따라서 현재 단계에서는 중복 삭제를 하면 안 됩니다."
        )


    else:

        print()
        print(
            "모든 원본 항목이 동일한 거래가 존재합니다."
        )

        print()
        print(
            "다만 실제 서로 다른 세대의 동일조건 계약일 수도 있으므로 "
            "자동 삭제하지 않습니다."
        )

        print()
        print(
            "완전 동일 거래 파일을 추가 확인해야 합니다."
        )


    # =====================================================
    # 12. 의심그룹 예시
    # =====================================================

    if not suspect_df.empty:

        print()
        print(
            "========================================"
        )

        print(
            "중복 의심 그룹 예시"
        )

        print(
            "========================================"
        )


        display_columns = [

            "중복의심그룹",
            "그룹내행수",

            "프로젝트지역",

            "gu_name",
            "umdNm",
            "jibun",

            "housing_type",

            "excluUseAr",
            "deposit",
            "monthlyRent",

            "dealYear",
            "dealMonth",
            "dealDay",

            "floor",

            "query_ym"
        ]


        display_columns = [

            column

            for column
            in display_columns

            if column
            in suspect_df.columns

        ]


        print(

            suspect_df[
                display_columns
            ]

            .sort_values(
                [
                    "중복의심그룹"
                ]
            )

            .head(30)

            .to_string(
                index=False
            )

        )


    # =====================================================
    # 13. 저장 위치
    # =====================================================

    print()
    print(
        "----------------------------------------"
    )


    if not exact_duplicates.empty:

        print(
            "완전 동일 행 점검 파일 :"
        )

        print(
            OUTPUT_EXACT
        )


    if not suspect_df.empty:

        print()
        print(
            "중복 의심 그룹 상세 파일 :"
        )

        print(
            OUTPUT_SUSPECT
        )


    print()
    print(
        "중복 검사는 데이터 수정 없이 완료되었습니다."
    )

    print(
        "----------------------------------------"
    )


if __name__ == "__main__":

    main()