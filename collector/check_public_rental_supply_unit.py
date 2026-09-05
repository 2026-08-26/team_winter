from pathlib import Path

import pandas as pd


# =========================================================
# 1. 경로
# =========================================================

BASE_DIR = Path(__file__).resolve().parent.parent

INPUT_FILE = (
    BASE_DIR
    / "data"
    / "raw"
    / "공공임대주택_광주_원본.csv"
)

OUTPUT_FILE = (
    BASE_DIR
    / "data"
    / "processed"
    / "공공임대_단지공급유형별_세대수점검.csv"
)


# =========================================================
# 2. 메인
# =========================================================

def main():

    print()
    print(
        "========================================"
    )

    print(
        "공공임대 단지+공급유형 세대수 검사"
    )

    print(
        "========================================"
    )


    df = pd.read_csv(
        INPUT_FILE,
        encoding="utf-8-sig"
    )


    # =====================================================
    # 값 정리
    # =====================================================

    df["hsmpSn"] = (
        df["hsmpSn"]
        .astype(str)
        .str.strip()
    )


    df["suplyTyNm"] = (
        df["suplyTyNm"]
        .fillna("")
        .astype(str)
        .str.strip()
    )


    df["rnAdres"] = (
        df["rnAdres"]
        .fillna("")
        .astype(str)
        .str.strip()
    )


    df["hshldCo"] = pd.to_numeric(
        df["hshldCo"],
        errors="coerce"
    )


    # =====================================================
    # hsmpSn + 공급유형 단위 검사
    # =====================================================

    rows = []


    for (
        hsmp_sn,
        supply_type
    ), group in df.groupby(
        [
            "hsmpSn",
            "suplyTyNm"
        ],
        dropna=False
    ):


        household_values = (

            group["hshldCo"]

            .dropna()

            .unique()

        )


        addresses = (

            group["rnAdres"]

            .replace(
                "",
                pd.NA
            )

            .dropna()

            .unique()

        )


        rows.append(
            {

                "hsmpSn":
                    hsmp_sn,

                "공급유형":
                    supply_type,

                "원본행수":
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

                            for value
                            in household_values
                        ]
                    ),

                "대표세대수":
                    (
                        household_values[0]
                        if len(
                            household_values
                        ) == 1
                        else pd.NA
                    ),

                "세대수일관성":
                    (
                        "일치"
                        if len(
                            household_values
                        ) == 1
                        else "불일치"
                    ),

                "주소":
                    " | ".join(
                        addresses
                    )
            }
        )


    result = pd.DataFrame(
        rows
    )


    # =====================================================
    # 결과
    # =====================================================

    inconsistent = result[
        result[
            "세대수일관성"
        ]
        == "불일치"
    ]


    repeated = result[
        result[
            "원본행수"
        ]
        > 1
    ]


    print()
    print(
        f"원본 행 : "
        f"{len(df):,}행"
    )

    print(
        f"hsmpSn + 공급유형 조합 : "
        f"{len(result):,}개"
    )

    print(
        f"2행 이상 반복 조합 : "
        f"{len(repeated):,}개"
    )


    print()
    print(
        "----------------------------------------"
    )

    print(
        "세대수 일관성"
    )

    print(
        "----------------------------------------"
    )


    print(
        f"일치 : "
        f"{len(result) - len(inconsistent):,}개"
    )

    print(
        f"불일치 : "
        f"{len(inconsistent):,}개"
    )


    # =====================================================
    # 불일치 상세
    # =====================================================

    if not inconsistent.empty:

        print()
        print(
            "[세대수 불일치 조합]"
        )

        print(
            inconsistent[
                [
                    "hsmpSn",
                    "공급유형",
                    "원본행수",
                    "세대수_고유값",
                    "주소"
                ]
            ]
            .to_string(
                index=False
            )
        )


    # =====================================================
    # 단지 하나에 여러 공급유형 있는 경우
    # =====================================================

    supply_count = (

        result

        .groupby(
            "hsmpSn"
        )["공급유형"]

        .nunique()

    )


    multi_supply_ids = (

        supply_count[
            supply_count > 1
        ]

        .index

        .tolist()

    )


    multi_supply = result[
        result[
            "hsmpSn"
        ].isin(
            multi_supply_ids
        )
    ]


    print()
    print(
        "----------------------------------------"
    )

    print(
        "여러 공급유형이 있는 단지"
    )

    print(
        "----------------------------------------"
    )


    print(
        f"해당 단지 : "
        f"{len(multi_supply_ids):,}개"
    )


    if len(
        multi_supply_ids
    ) > 0:

        print()

        print(
            multi_supply[
                [
                    "hsmpSn",
                    "공급유형",
                    "대표세대수",
                    "주소"
                ]
            ]
            .head(30)
            .to_string(
                index=False
            )
        )


    # =====================================================
    # 잠정 집계값
    #
    # hsmpSn + 공급유형별 대표 세대수를
    # 한 번씩만 합산
    # =====================================================

    valid = result[
        result[
            "세대수일관성"
        ]
        == "일치"
    ].copy()


    estimated_total = (

        pd.to_numeric(
            valid[
                "대표세대수"
            ],
            errors="coerce"
        )

        .fillna(0)

        .sum()

    )


    print()
    print(
        "----------------------------------------"
    )

    print(
        "잠정 세대수 집계"
    )

    print(
        "----------------------------------------"
    )


    print(
        "hsmpSn + 공급유형별 "
        "세대수를 한 번씩만 계산했을 때:"
    )

    print(
        f"{int(estimated_total):,}세대"
    )


    print()
    print(
        "※ 아직 최종 확정값은 아닙니다."
    )


    # =====================================================
    # 저장
    # =====================================================

    result.to_csv(
        OUTPUT_FILE,
        index=False,
        encoding="utf-8-sig"
    )


    print()
    print(
        "========================================"
    )

    print(
        "검사 완료"
    )

    print(
        "========================================"
    )


    if inconsistent.empty:

        print()
        print(
            "모든 hsmpSn + 공급유형 조합에서 "
            "hshldCo가 하나의 값으로 일치합니다."
        )

        print(
            "→ 공급유형 단위로 세대수를 "
            "1회 계산하는 방식이 유력합니다."
        )


    else:

        print()
        print(
            "일부 hsmpSn + 공급유형 안에서도 "
            "세대수가 다릅니다."
        )

        print(
            "→ 추가 구조 점검이 필요합니다."
        )


    print()
    print(
        "저장 파일:"
    )

    print(
        OUTPUT_FILE
    )


if __name__ == "__main__":

    main()