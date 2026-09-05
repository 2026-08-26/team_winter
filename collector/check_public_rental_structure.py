from pathlib import Path

import pandas as pd


# =========================================================
# 1. 경로 설정
# =========================================================

BASE_DIR = Path(__file__).resolve().parent.parent

RAW_FILE = (
    BASE_DIR
    / "data"
    / "raw"
    / "공공임대주택_광주_원본.csv"
)

PROCESSED_DIR = (
    BASE_DIR
    / "data"
    / "processed"
)

PROCESSED_DIR.mkdir(
    parents=True,
    exist_ok=True
)


OUTPUT_COMPLEX = (
    PROCESSED_DIR
    / "공공임대_단지반복구조_점검.csv"
)

OUTPUT_INCONSISTENT = (
    PROCESSED_DIR
    / "공공임대_세대수불일치단지_점검.csv"
)

OUTPUT_ADDRESS = (
    PROCESSED_DIR
    / "공공임대_주소다중단지_점검.csv"
)

OUTPUT_SUPPLY = (
    PROCESSED_DIR
    / "공공임대_공급유형구조_요약.csv"
)


# =========================================================
# 2. 숫자 변환
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
# 3. 문자열 정리
# =========================================================

def clean_text(series):

    return (
        series
        .fillna("")
        .astype(str)
        .str.strip()
    )


# =========================================================
# 4. 메인
# =========================================================

def main():

    print()
    print(
        "========================================"
    )

    print(
        "공공임대주택 단지 구조 정밀점검"
    )

    print(
        "========================================"
    )


    # =====================================================
    # 파일 확인
    # =====================================================

    if not RAW_FILE.exists():

        print()
        print(
            "원본 파일이 없습니다."
        )

        print(
            RAW_FILE
        )

        return


    # =====================================================
    # 데이터 읽기
    # =====================================================

    df = pd.read_csv(
        RAW_FILE,
        encoding="utf-8-sig"
    )


    print()
    print(
        f"전체 원본 행 : "
        f"{len(df):,}행"
    )


    # =====================================================
    # 필수 컬럼 검사
    # =====================================================

    required_columns = [

        "hsmpSn",
        "hshldCo",
        "rnAdres",
        "suplyTyNm"
    ]


    missing = [

        column

        for column in required_columns

        if column not in df.columns
    ]


    if missing:

        print()
        print(
            "필수 컬럼이 없습니다."
        )

        for column in missing:

            print(
                "-",
                column
            )

        return


    # =====================================================
    # 값 정리
    # =====================================================

    df[
        "hsmpSn"
    ] = clean_text(
        df[
            "hsmpSn"
        ]
    )


    df[
        "rnAdres"
    ] = clean_text(
        df[
            "rnAdres"
        ]
    )


    df[
        "suplyTyNm"
    ] = clean_text(
        df[
            "suplyTyNm"
        ]
    )


    df[
        "hshldCo"
    ] = to_numeric(
        df[
            "hshldCo"
        ]
    )


    if "styleNm" in df.columns:

        df[
            "styleNm"
        ] = clean_text(
            df[
                "styleNm"
            ]
        )


    if "suplyPrvuseAr" in df.columns:

        df[
            "suplyPrvuseAr"
        ] = to_numeric(
            df[
                "suplyPrvuseAr"
            ]
        )


    # =====================================================
    # 5. 고유 단지 수
    # =====================================================

    unique_complex_count = (
        df[
            "hsmpSn"
        ]
        .replace(
            "",
            pd.NA
        )
        .dropna()
        .nunique()
    )


    print()
    print(
        f"고유 단지 ID : "
        f"{unique_complex_count:,}개"
    )


    # =====================================================
    # 6. 단지별 반복 구조
    # =====================================================

    complex_rows = []


    for hsmp_sn, group in df.groupby(
        "hsmpSn",
        dropna=False
    ):

        if str(
            hsmp_sn
        ).strip() == "":

            continue


        household_values = (

            group[
                "hshldCo"
            ]

            .dropna()

            .unique()

        )


        addresses = (

            group[
                "rnAdres"
            ]

            .replace(
                "",
                pd.NA
            )

            .dropna()

            .unique()

        )


        supply_types = (

            group[
                "suplyTyNm"
            ]

            .replace(
                "",
                pd.NA
            )

            .dropna()

            .unique()

        )


        row = {

            "hsmpSn":
                hsmp_sn,

            "행수":
                len(group),

            "세대수_고유값수":
                len(
                    household_values
                ),

            "세대수_고유값":
                ", ".join(
                    [
                        str(
                            int(value)
                        )
                        if float(value).is_integer()
                        else str(value)

                        for value in household_values
                    ]
                ),

            "주소_고유값수":
                len(
                    addresses
                ),

            "주소":
                " | ".join(
                    addresses
                ),

            "공급유형_고유값수":
                len(
                    supply_types
                ),

            "공급유형":
                " | ".join(
                    supply_types
                )
        }


        # -------------------------------------------------
        # 세대수가 단지 내에서 하나로 일관될 경우
        # 대표 세대수 후보로 기록
        # -------------------------------------------------

        if len(
            household_values
        ) == 1:

            row[
                "대표세대수_후보"
            ] = household_values[0]

            row[
                "세대수일관성"
            ] = "일치"


        elif len(
            household_values
        ) == 0:

            row[
                "대표세대수_후보"
            ] = pd.NA

            row[
                "세대수일관성"
            ] = "값없음"


        else:

            row[
                "대표세대수_후보"
            ] = pd.NA

            row[
                "세대수일관성"
            ] = "불일치"


        complex_rows.append(
            row
        )


    complex_df = pd.DataFrame(
        complex_rows
    )


    # =====================================================
    # 7. 반복 단지 수
    # =====================================================

    repeated_complex = complex_df[
        complex_df[
            "행수"
        ]
        > 1
    ]


    single_complex = complex_df[
        complex_df[
            "행수"
        ]
        == 1
    ]


    print()
    print(
        "----------------------------------------"
    )

    print(
        "단지 반복 구조"
    )

    print(
        "----------------------------------------"
    )


    print(
        f"1행만 존재하는 단지 : "
        f"{len(single_complex):,}개"
    )

    print(
        f"2행 이상 반복 단지 : "
        f"{len(repeated_complex):,}개"
    )


    if len(
        complex_df
    ) > 0:

        print(
            f"한 단지 최대 반복 행 : "
            f"{int(complex_df['행수'].max())}행"
        )


    # =====================================================
    # 8. 세대수 일관성 검사
    # =====================================================

    consistent = complex_df[
        complex_df[
            "세대수일관성"
        ]
        == "일치"
    ]


    inconsistent = complex_df[
        complex_df[
            "세대수일관성"
        ]
        == "불일치"
    ]


    print()
    print(
        "----------------------------------------"
    )

    print(
        "단지별 세대수 일관성"
    )

    print(
        "----------------------------------------"
    )


    print(
        f"세대수 하나로 일치 : "
        f"{len(consistent):,}개 단지"
    )

    print(
        f"세대수 여러 값 존재 : "
        f"{len(inconsistent):,}개 단지"
    )


    # =====================================================
    # 9. 단순합산 과대계상 가능성 비교
    # =====================================================

    raw_household_sum = (
        df[
            "hshldCo"
        ]
        .fillna(0)
        .sum()
    )


    consistent_household_sum = (

        consistent[
            "대표세대수_후보"
        ]

        .fillna(0)

        .sum()

    )


    print()
    print(
        "----------------------------------------"
    )

    print(
        "세대수 단순 합산 위험 확인"
    )

    print(
        "----------------------------------------"
    )


    print(
        f"원본 4,036행 hshldCo 단순합 : "
        f"{int(raw_household_sum):,}세대"
    )


    print(
        f"세대수가 일관된 단지를 "
        f"ID별 1회만 계산한 합 : "
        f"{int(consistent_household_sum):,}세대"
    )


    print()
    print(
        "※ 두 값의 차이가 크다고 해서 "
        "두 번째 값이 최종 정답이라는 뜻은 아닙니다."
    )

    print(
        "※ 세대수 불일치 단지는 "
        "별도 확인 후 집계방식을 결정합니다."
    )


    # =====================================================
    # 10. 같은 주소에 여러 단지 ID 검사
    # =====================================================

    address_rows = []


    valid_address_df = df[
        df[
            "rnAdres"
        ]
        != ""
    ]


    for address, group in (
        valid_address_df.groupby(
            "rnAdres"
        )
    ):

        complex_ids = (

            group[
                "hsmpSn"
            ]

            .replace(
                "",
                pd.NA
            )

            .dropna()

            .unique()

        )


        supply_types = (

            group[
                "suplyTyNm"
            ]

            .replace(
                "",
                pd.NA
            )

            .dropna()

            .unique()

        )


        if len(
            complex_ids
        ) > 1:

            address_rows.append(

                {

                    "주소":
                        address,

                    "단지ID수":
                        len(
                            complex_ids
                        ),

                    "단지ID":
                        ", ".join(
                            complex_ids.astype(str)
                        ),

                    "공급유형":
                        " | ".join(
                            supply_types
                        ),

                    "원본행수":
                        len(group)
                }

            )


    address_df = pd.DataFrame(
        address_rows
    )


    print()
    print(
        "----------------------------------------"
    )

    print(
        "같은 주소의 여러 단지 ID"
    )

    print(
        "----------------------------------------"
    )


    print(
        f"여러 hsmpSn이 존재하는 주소 : "
        f"{len(address_df):,}곳"
    )


    # =====================================================
    # 11. 공급유형별 구조 분석
    # =====================================================

    supply_rows = []


    for supply_type, group in df.groupby(
        "suplyTyNm",
        dropna=False
    ):

        complex_count = (
            group[
                "hsmpSn"
            ]
            .nunique()
        )


        raw_rows = len(
            group
        )


        household_sum = (
            group[
                "hshldCo"
            ]
            .fillna(0)
            .sum()
        )


        if complex_count > 0:

            avg_rows = (
                raw_rows
                /
                complex_count
            )

        else:

            avg_rows = 0


        supply_rows.append(

            {

                "공급유형":
                    supply_type,

                "원본행수":
                    raw_rows,

                "고유단지수":
                    complex_count,

                "단지당평균행수":
                    round(
                        avg_rows,
                        2
                    ),

                "원본세대수단순합":
                    int(
                        household_sum
                    )
            }

        )


    supply_df = pd.DataFrame(
        supply_rows
    )


    supply_df = (

        supply_df

        .sort_values(
            "원본행수",
            ascending=False
        )

        .reset_index(
            drop=True
        )

    )


    print()
    print(
        "----------------------------------------"
    )

    print(
        "공급유형별 반복 구조"
    )

    print(
        "----------------------------------------"
    )


    for _, row in (
        supply_df.iterrows()
    ):

        print()

        print(
            f"[{row['공급유형']}]"
        )

        print(
            f"원본 행 : "
            f"{int(row['원본행수']):,}"
        )

        print(
            f"고유 단지 : "
            f"{int(row['고유단지수']):,}"
        )

        print(
            f"단지당 평균 행 : "
            f"{row['단지당평균행수']}"
        )


    # =====================================================
    # 12. 세대수 불일치 단지 상세
    # =====================================================

    print()
    print(
        "========================================"
    )

    print(
        "세대수 불일치 단지"
    )

    print(
        "========================================"
    )


    if inconsistent.empty:

        print()
        print(
            "세대수가 서로 다른 단지는 없습니다."
        )


    else:

        print()
        print(
            f"총 {len(inconsistent):,}개 단지"
        )


        print()
        print(
            "앞부분 20개:"
        )


        display_columns = [

            "hsmpSn",

            "행수",

            "세대수_고유값수",

            "세대수_고유값",

            "주소",

            "공급유형"
        ]


        print(

            inconsistent[
                display_columns
            ]

            .head(20)

            .to_string(
                index=False
            )

        )


    # =====================================================
    # 13. 단지별 스타일/면적 예시
    # =====================================================

    print()
    print(
        "========================================"
    )

    print(
        "반복 단지 실제 예시"
    )

    print(
        "========================================"
    )


    sample_complexes = (

        complex_df

        .sort_values(
            "행수",
            ascending=False
        )

        .head(5)[
            "hsmpSn"
        ]

        .tolist()

    )


    sample_columns = [

        "hsmpSn",
        "rnAdres",
        "suplyTyNm",
        "hshldCo"
    ]


    if "styleNm" in df.columns:

        sample_columns.append(
            "styleNm"
        )


    if "suplyPrvuseAr" in df.columns:

        sample_columns.append(
            "suplyPrvuseAr"
        )


    for complex_id in (
        sample_complexes
    ):

        sample = df[
            df[
                "hsmpSn"
            ]
            == complex_id
        ]


        print()
        print(
            f"[단지 ID {complex_id}]"
        )


        print(

            sample[
                sample_columns
            ]

            .head(20)

            .to_string(
                index=False
            )

        )


    # =====================================================
    # 14. 결과 저장
    # =====================================================

    complex_df.to_csv(
        OUTPUT_COMPLEX,
        index=False,
        encoding="utf-8-sig"
    )


    inconsistent.to_csv(
        OUTPUT_INCONSISTENT,
        index=False,
        encoding="utf-8-sig"
    )


    address_df.to_csv(
        OUTPUT_ADDRESS,
        index=False,
        encoding="utf-8-sig"
    )


    supply_df.to_csv(
        OUTPUT_SUPPLY,
        index=False,
        encoding="utf-8-sig"
    )


    # =====================================================
    # 15. 최종 판정 안내
    # =====================================================

    print()
    print(
        "========================================"
    )

    print(
        "1차 구조 점검 완료"
    )

    print(
        "========================================"
    )


    if len(
        inconsistent
    ) == 0:

        print()
        print(
            "모든 단지에서 hshldCo가 "
            "하나의 값으로 일관됩니다."
        )

        print(
            "따라서 hsmpSn별 세대수를 "
            "한 번만 계산하는 방식이 "
            "유력합니다."
        )


    else:

        print()
        print(
            "일부 단지에서 하나의 hsmpSn 안에 "
            "여러 hshldCo 값이 존재합니다."
        )

        print(
            "따라서 지금 단계에서 "
            "hsmpSn별 첫 번째 세대수를 "
            "무조건 사용하는 것은 위험합니다."
        )

        print(
            "불일치 단지 구조를 확인한 뒤 "
            "최종 세대수 집계 기준을 결정해야 합니다."
        )


    print()
    print(
        "저장 파일:"
    )

    print(
        OUTPUT_COMPLEX
    )

    print(
        OUTPUT_INCONSISTENT
    )

    print(
        OUTPUT_ADDRESS
    )

    print(
        OUTPUT_SUPPLY
    )


# =========================================================
# 실행
# =========================================================

if __name__ == "__main__":

    main()