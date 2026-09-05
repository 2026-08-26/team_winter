from pathlib import Path

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

DETAIL_FILE = (
    PROCESSED_DIR
    / "청년소형주택_25개동_실거래.csv"
)

SUMMARY_FILE = (
    PROCESSED_DIR
    / "동별_주거비.csv"
)

LOW_SAMPLE_FILE = (
    PROCESSED_DIR
    / "주거_저표본지역_점검.csv"
)

DUPLICATE_FILE = (
    PROCESSED_DIR
    / "주거_중복의심거래_점검.csv"
)


# =========================================================
# 2. 분석 기준
# =========================================================

MAX_AREA_M2 = 59.5

DEPOSIT_ANNUAL_RATE = 0.05

LOW_SAMPLE_WARNING = 20

VERY_LOW_SAMPLE = 5


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
# 5. 파일 읽기
# =========================================================

def load_data():

    if not DETAIL_FILE.exists():

        raise FileNotFoundError(
            f"실거래 상세 파일이 없습니다.\n"
            f"{DETAIL_FILE}"
        )


    if not SUMMARY_FILE.exists():

        raise FileNotFoundError(
            f"동별 주거비 파일이 없습니다.\n"
            f"{SUMMARY_FILE}"
        )


    detail = pd.read_csv(
        DETAIL_FILE,
        encoding="utf-8-sig",
        dtype=str,
        keep_default_na=False
    )


    summary = pd.read_csv(
        SUMMARY_FILE,
        encoding="utf-8-sig"
    )


    return detail, summary


# =========================================================
# 6. 메인
# =========================================================

def main():

    print()
    print(
        "========================================"
    )

    print(
        "청년 소형주택 데이터 최종 품질점검"
    )

    print(
        "========================================"
    )


    # =====================================================
    # 파일 읽기
    # =====================================================

    detail, summary = load_data()


    print(
        f"\n상세 실거래 : "
        f"{len(detail):,}건"
    )

    print(
        f"동별 주거비 : "
        f"{len(summary)}개 동"
    )


    # =====================================================
    # 7. 필수 컬럼 검사
    # =====================================================

    required_detail = [

        "프로젝트자치구",
        "프로젝트행정동",

        "공식자치구",
        "공식행정동",

        "excluUseAr",
        "deposit",
        "monthlyRent",

        "housing_type",
        "query_ym",

        "매핑상태"
    ]


    missing_detail = [

        column

        for column in required_detail

        if column not in detail.columns

    ]


    if missing_detail:

        add_error(
            "상세 파일 필수 컬럼 누락 : "
            + ", ".join(
                missing_detail
            )
        )


    required_summary = [

        "자치구",
        "행정동",

        "전체거래건수",

        "월환산주거비_평균값_만원",

        "표본상태"
    ]


    missing_summary = [

        column

        for column in required_summary

        if column not in summary.columns

    ]


    if missing_summary:

        add_error(
            "동별 주거비 필수 컬럼 누락 : "
            + ", ".join(
                missing_summary
            )
        )


    if errors:

        print(
            "\n필수 컬럼 검사 실패"
        )

        for error in errors:

            print(
                "X",
                error
            )

        return


    # =====================================================
    # 8. 25개 동 여부
    # =====================================================

    if len(summary) != 25:

        add_error(
            f"동별 주거비가 25개 동이 아닙니다. "
            f"현재 {len(summary)}개"
        )


    summary[
        "지역"
    ] = (

        summary[
            "자치구"
        ].astype(str)

        + " "

        + summary[
            "행정동"
        ].astype(str)

    )


    detail[
        "지역"
    ] = (

        detail[
            "프로젝트자치구"
        ].astype(str)

        + " "

        + detail[
            "프로젝트행정동"
        ].astype(str)

    )


    # =====================================================
    # 9. 숫자형 변환
    # =====================================================

    detail[
        "전용면적_m2"
    ] = to_numeric(
        detail[
            "excluUseAr"
        ]
    )


    detail[
        "보증금_만원"
    ] = to_numeric(
        detail[
            "deposit"
        ]
    )


    detail[
        "월세_만원"
    ] = to_numeric(
        detail[
            "monthlyRent"
        ]
    )


    # =====================================================
    # 10. 18평 이하 조건 검사
    # =====================================================

    area_missing = (
        detail[
            "전용면적_m2"
        ].isna()
    ).sum()


    area_over = (
        detail[
            "전용면적_m2"
        ]
        > MAX_AREA_M2
    ).sum()


    if area_missing > 0:

        add_error(
            f"전용면적이 없는 거래가 "
            f"{area_missing}건 있습니다."
        )


    if area_over > 0:

        add_error(
            f"59.5㎡를 초과한 거래가 "
            f"{area_over}건 있습니다."
        )


    # =====================================================
    # 11. 보증금 / 월세 누락 검사
    # =====================================================

    deposit_missing = (
        detail[
            "보증금_만원"
        ].isna()
    ).sum()


    rent_missing = (
        detail[
            "월세_만원"
        ].isna()
    ).sum()


    if deposit_missing > 0:

        add_error(
            f"보증금 누락 : "
            f"{deposit_missing}건"
        )


    if rent_missing > 0:

        add_error(
            f"월세값 누락 : "
            f"{rent_missing}건"
        )


    # =====================================================
    # 12. 분석기간 검사
    # =====================================================

    allowed_months = {

        "202507",
        "202508",
        "202509",
        "202510",
        "202511",
        "202512",

        "202601",
        "202602",
        "202603",
        "202604",
        "202605",
        "202606"
    }


    invalid_months = detail[
        ~detail[
            "query_ym"
        ].isin(
            allowed_months
        )
    ]


    if len(
        invalid_months
    ) > 0:

        add_error(
            f"분석기간 밖 거래가 "
            f"{len(invalid_months)}건 있습니다."
        )


    # =====================================================
    # 13. 행정동 매핑 검사
    # =====================================================

    failed_mapping = detail[
        detail[
            "매핑상태"
        ]
        != "성공"
    ]


    if len(
        failed_mapping
    ) > 0:

        add_error(
            f"행정동 매핑 실패 거래가 "
            f"{len(failed_mapping)}건 있습니다."
        )


    # =====================================================
    # 14. 첨단2동 공식/프로젝트 표기 검사
    # =====================================================

    cheomdan2 = detail[
        detail[
            "프로젝트행정동"
        ]
        == "첨단2동"
    ]


    invalid_cheomdan2 = cheomdan2[
        (
            cheomdan2[
                "공식자치구"
            ]
            != "광산구"
        )
        |
        (
            cheomdan2[
                "공식행정동"
            ]
            != "첨단2동"
        )
        |
        (
            cheomdan2[
                "프로젝트자치구"
            ]
            != "북구"
        )
    ]


    if len(
        invalid_cheomdan2
    ) > 0:

        add_error(
            "첨단2동 공식/프로젝트 "
            "행정구역 변환이 일치하지 않는 거래가 있습니다."
        )


    # =====================================================
    # 15. 같은 주소가 여러 행정동으로 매핑됐는지 검사
    # =====================================================

    if "주소키" in detail.columns:

        address_mapping_count = (

            detail

            .groupby(
                "주소키"
            )[
                "공식지역"
            ]

            .nunique()

        )


        inconsistent_addresses = (
            address_mapping_count[
                address_mapping_count > 1
            ]
        )


        if len(
            inconsistent_addresses
        ) > 0:

            add_error(
                f"동일 주소가 여러 행정동으로 "
                f"매핑된 경우가 "
                f"{len(inconsistent_addresses)}개 있습니다."
            )


    # =====================================================
    # 16. 월환산주거비 다시 계산
    # =====================================================

    detail[
        "검증용_월환산주거비"
    ] = (

        detail[
            "월세_만원"
        ]

        +

        (
            detail[
                "보증금_만원"
            ]
            * DEPOSIT_ANNUAL_RATE
            / 12
        )

    )


    # =====================================================
    # 17. 동별 실제 거래건수와 요약 CSV 비교
    # =====================================================

    actual_counts = (

        detail[
            "지역"
        ]

        .value_counts()

        .to_dict()

    )


    count_mismatch = []


    for _, row in summary.iterrows():

        region = row[
            "지역"
        ]


        expected = int(
            row[
                "전체거래건수"
            ]
        )


        actual = int(
            actual_counts.get(
                region,
                0
            )
        )


        if expected != actual:

            count_mismatch.append(
                (
                    region,
                    expected,
                    actual
                )
            )


    if count_mismatch:

        for (
            region,
            expected,
            actual
        ) in count_mismatch:

            add_error(
                f"{region} 거래건수 불일치 : "
                f"동별CSV {expected}건 / "
                f"상세CSV {actual}건"
            )


    # =====================================================
    # 18. 평균 월환산주거비 재검증
    # =====================================================

    mean_check = (

        detail

        .groupby(
            "지역"
        )[
            "검증용_월환산주거비"
        ]

        .mean()

        .to_dict()

    )


    mean_mismatch = []


    for _, row in summary.iterrows():

        region = row[
            "지역"
        ]


        saved_value = pd.to_numeric(
            row[
                "월환산주거비_평균값_만원"
            ],
            errors="coerce"
        )


        actual_value = mean_check.get(
            region
        )


        if actual_value is None:

            continue


        if pd.isna(
            saved_value
        ):

            mean_mismatch.append(
                region
            )

            continue


        # 반올림 오차 고려
        if abs(
            float(saved_value)
            -
            float(actual_value)
        ) > 0.05:

            mean_mismatch.append(
                region
            )


    if mean_mismatch:

        add_error(
            "월환산주거비 평균값이 "
            "상세 거래와 일치하지 않는 지역 : "
            + ", ".join(
                mean_mismatch
            )
        )


    # =====================================================
    # 19. 저표본 지역
    # =====================================================

    low_sample = summary[
        summary[
            "전체거래건수"
        ]
        < LOW_SAMPLE_WARNING
    ].copy()


    very_low = summary[
        summary[
            "전체거래건수"
        ]
        < VERY_LOW_SAMPLE
    ].copy()


    if len(
        low_sample
    ) > 0:

        add_warning(
            f"20건 미만 저표본 지역 : "
            f"{len(low_sample)}곳"
        )


    if len(
        very_low
    ) > 0:

        add_warning(
            f"5건 미만 매우 낮은 표본 지역 : "
            f"{len(very_low)}곳"
        )


    # =====================================================
    # 20. 저표본 거래 상세 추출
    # =====================================================

    low_regions = set(
        low_sample[
            "지역"
        ].tolist()
    )


    low_detail = detail[
        detail[
            "지역"
        ].isin(
            low_regions
        )
    ].copy()


    low_detail.to_csv(
        LOW_SAMPLE_FILE,
        index=False,
        encoding="utf-8-sig"
    )


    # =====================================================
    # 21. 중복 의심 거래 검사
    # =====================================================

    possible_key_columns = [

        "gu_name",
        "umdNm",
        "jibun",

        "housing_type",

        "excluUseAr",
        "deposit",
        "monthlyRent",

        "query_ym",

        "dealYear",
        "dealMonth",
        "dealDay",

        "floor"
    ]


    duplicate_key = [

        column

        for column in possible_key_columns

        if column in detail.columns

    ]


    duplicate_rows = pd.DataFrame()


    if len(
        duplicate_key
    ) >= 5:

        duplicate_rows = detail[
            detail.duplicated(
                subset=duplicate_key,
                keep=False
            )
        ].copy()


        if len(
            duplicate_rows
        ) > 0:

            duplicate_rows.to_csv(
                DUPLICATE_FILE,
                index=False,
                encoding="utf-8-sig"
            )


            add_warning(
                f"완전히 동일해 보이는 "
                f"중복 의심 행 : "
                f"{len(duplicate_rows)}건"
            )


    # =====================================================
    # 22. 결과 출력
    # =====================================================

    print()
    print(
        "----------------------------------------"
    )

    print(
        "핵심 검사 결과"
    )

    print(
        "----------------------------------------"
    )


    print(
        f"분석 대상 동 : "
        f"{len(summary)}개"
    )

    print(
        f"상세 실거래 : "
        f"{len(detail):,}건"
    )

    print(
        f"59.5㎡ 초과 거래 : "
        f"{area_over}건"
    )

    print(
        f"행정동 매핑 실패 : "
        f"{len(failed_mapping)}건"
    )

    print(
        f"거래건수 불일치 지역 : "
        f"{len(count_mismatch)}곳"
    )

    print(
        f"평균값 불일치 지역 : "
        f"{len(mean_mismatch)}곳"
    )


    # =====================================================
    # 23. 저표본 지역 출력
    # =====================================================

    print()
    print(
        "========================================"
    )

    print(
        "저표본 지역 점검"
    )

    print(
        "========================================"
    )


    if low_sample.empty:

        print(
            "20건 미만 지역 없음"
        )


    else:

        for _, row in (
            low_sample

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
                "거래건수 :",
                row[
                    "전체거래건수"
                ],
                "건"
            )

            print(
                "월환산 평균 :",
                row[
                    "월환산주거비_평균값_만원"
                ],
                "만원"
            )

            print(
                "표본상태 :",
                row[
                    "표본상태"
                ]
            )


    # =====================================================
    # 24. 두암2동 실제 거래 출력
    # =====================================================

    print()
    print(
        "========================================"
    )

    print(
        "두암2동 거래 상세 확인"
    )

    print(
        "========================================"
    )


    duam = detail[
        detail[
            "지역"
        ]
        == "북구 두암2동"
    ]


    if duam.empty:

        print(
            "두암2동 거래 없음"
        )


    else:

        display_columns = [

            "gu_name",
            "umdNm",
            "jibun",

            "housing_type",

            "excluUseAr",
            "deposit",
            "monthlyRent",

            "query_ym",

            "검색주소",
            "카카오매칭주소",

            "공식자치구",
            "공식행정동",

            "프로젝트자치구",
            "프로젝트행정동"
        ]


        display_columns = [

            column

            for column in display_columns

            if column in duam.columns

        ]


        print(
            duam[
                display_columns
            ].to_string(
                index=False
            )
        )


    # =====================================================
    # 25. 첨단1/2동 확인
    # =====================================================

    print()
    print(
        "========================================"
    )

    print(
        "첨단1동 / 첨단2동 검증"
    )

    print(
        "========================================"
    )


    cheomdan = (

        detail[
            detail[
                "프로젝트행정동"
            ].isin(
                [
                    "첨단1동",
                    "첨단2동"
                ]
            )
        ]

        .groupby(
            [
                "공식자치구",
                "공식행정동",

                "프로젝트자치구",
                "프로젝트행정동"
            ]
        )

        .size()

        .reset_index(
            name="거래건수"
        )

    )


    print(
        cheomdan.to_string(
            index=False
        )
    )


    # =====================================================
    # 26. 최종 판정
    # =====================================================

    print()
    print(
        "========================================"
    )

    print(
        "최종 주거 데이터 검증 결과"
    )

    print(
        "========================================"
    )


    if errors:

        print()

        for error in errors:

            print(
                "X",
                error
            )


        print()
        print(
            "주거 데이터 품질검사 : FAIL"
        )


    else:

        print(
            "\n핵심 데이터 정합성 검사 통과"
        )


        if warnings:

            print()

            for warning in warnings:

                print(
                    "!",
                    warning
                )


            print(
                "\n데이터 자체는 정상이나 "
                "저표본 지역은 해석에 주의가 필요합니다."
            )


        print()
        print(
            "주거 데이터 품질검사 : PASS"
        )


    print()
    print(
        "저표본 상세 저장 :"
    )

    print(
        LOW_SAMPLE_FILE
    )


    if not duplicate_rows.empty:

        print()
        print(
            "중복 의심 거래 저장 :"
        )

        print(
            DUPLICATE_FILE
        )


# =========================================================
# 실행
# =========================================================

if __name__ == "__main__":

    main()