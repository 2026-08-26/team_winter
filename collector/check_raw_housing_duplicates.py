from pathlib import Path

import pandas as pd


# =========================================================
# 경로
# =========================================================

BASE_DIR = Path(__file__).resolve().parent.parent

RAW_FILE = (
    BASE_DIR
    / "data"
    / "raw"
    / "전체_주거실거래_202507_202606.csv"
)


# =========================================================
# 메인
# =========================================================

def main():

    print()
    print("=" * 50)
    print("원본 주거 실거래 중복 검사")
    print("=" * 50)

    if not RAW_FILE.exists():

        print("원본 파일이 없습니다.")
        print(RAW_FILE)
        return


    df = pd.read_csv(
        RAW_FILE,
        encoding="utf-8-sig",
        dtype=str,
        keep_default_na=False
    )


    # 앞뒤 공백 제거
    for column in df.columns:

        df[column] = (
            df[column]
            .astype(str)
            .str.strip()
        )


    print(
        f"\n원본 전체 거래 : {len(df):,}건"
    )


    # =====================================================
    # 1. 모든 원본 컬럼이 완전히 동일한 행
    # =====================================================

    exact_mask = df.duplicated(
        subset=list(df.columns),
        keep=False
    )


    exact_df = df[
        exact_mask
    ].copy()


    if len(exact_df) > 0:

        group_count = (
            exact_df
            .groupby(
                list(df.columns),
                dropna=False
            )
            .ngroups
        )

    else:

        group_count = 0


    print()
    print("-" * 50)
    print("원본 완전 동일 검사")
    print("-" * 50)

    print(
        f"완전히 동일한 원본 행 : "
        f"{len(exact_df):,}건"
    )

    print(
        f"완전 동일 그룹 : "
        f"{group_count:,}개"
    )


    # =====================================================
    # 2. 주택유형별 확인
    # =====================================================

    if (
        len(exact_df) > 0
        and "housing_type" in exact_df.columns
    ):

        print()
        print("-" * 50)
        print("주택유형별 완전 동일 행")
        print("-" * 50)

        counts = (
            exact_df[
                "housing_type"
            ]
            .value_counts()
        )

        for housing_type, count in counts.items():

            print(
                f"{housing_type} : "
                f"{count:,}건"
            )


    # =====================================================
    # 3. 수집월별 확인
    # =====================================================

    if (
        len(exact_df) > 0
        and "query_ym" in exact_df.columns
    ):

        print()
        print("-" * 50)
        print("월별 완전 동일 행")
        print("-" * 50)

        counts = (
            exact_df[
                "query_ym"
            ]
            .value_counts()
            .sort_index()
        )

        for month, count in counts.items():

            print(
                f"{month} : "
                f"{count:,}건"
            )


    # =====================================================
    # 4. 저장
    # =====================================================

    if len(exact_df) > 0:

        output_file = (
            BASE_DIR
            / "data"
            / "processed"
            / "주거_원본완전중복_점검.csv"
        )


        exact_df.to_csv(
            output_file,
            index=False,
            encoding="utf-8-sig"
        )


        print()
        print("점검 파일 저장 :")
        print(output_file)


    # =====================================================
    # 최종 안내
    # =====================================================

    print()
    print("=" * 50)

    if len(exact_df) > 0:

        print(
            "원본 수집 데이터 단계부터 "
            "완전히 동일한 행이 존재합니다."
        )

    else:

        print(
            "원본에는 완전 동일 행이 없습니다."
        )

        print(
            "후속 처리 과정에서 중복이 "
            "발생했을 가능성이 있습니다."
        )

    print("=" * 50)


if __name__ == "__main__":

    main()