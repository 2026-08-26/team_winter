import csv
from pathlib import Path


# =========================================================
# 1. 파일 경로
# =========================================================

BASE_DIR = Path(__file__).resolve().parent.parent

INPUT_FILE = (
    BASE_DIR
    / "data"
    / "raw"
    / "전체_주거실거래_202507_202606.csv"
)


# =========================================================
# 2. 실행
# =========================================================

def main():

    print()
    print("========================================")
    print("주거 실거래 원본 컬럼 확인")
    print("========================================")


    if not INPUT_FILE.exists():

        print("파일을 찾을 수 없습니다.")
        print(INPUT_FILE)
        return


    with open(
        INPUT_FILE,
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        reader = csv.DictReader(file)

        columns = reader.fieldnames or []

        rows = list(reader)


    # =====================================================
    # 전체 컬럼 출력
    # =====================================================

    print()
    print("[전체 컬럼]")
    print()

    for index, column in enumerate(
        columns,
        start=1
    ):

        print(
            f"{index}. {column}"
        )


    # =====================================================
    # 주택유형별 샘플 한 건
    # =====================================================

    print()
    print("========================================")
    print("주택유형별 샘플")
    print("========================================")


    housing_types = [
        "아파트",
        "오피스텔",
        "연립다세대",
        "단독/다가구"
    ]


    for housing_type in housing_types:

        sample = next(

            (
                row
                for row in rows
                if row.get("housing_type")
                == housing_type
            ),

            None
        )


        print()
        print("----------------------------------------")
        print(housing_type)
        print("----------------------------------------")


        if sample is None:

            print("데이터 없음")
            continue


        # 주소/행정동 매핑에 중요해 보이는 컬럼 우선 출력
        important_columns = [
            "gu_name",
            "umdNm",
            "jibun",
            "aptNm",
            "offiNm",
            "mhouseNm",
            "sggCd",
            "umdCd",
            "roadNm",
            "roadNmBonbun",
            "roadNmBubun",
            "excluUseAr",
            "deposit",
            "monthlyRent",
            "housing_type",
            "query_ym"
        ]


        for column in important_columns:

            if column in sample:

                print(
                    f"{column} = "
                    f"{sample.get(column)}"
                )


    # =====================================================
    # 주소 관련 컬럼만 별도 확인
    # =====================================================

    print()
    print("========================================")
    print("주소 관련 가능성 있는 컬럼")
    print("========================================")


    keywords = [
        "umd",
        "jibun",
        "road",
        "addr",
        "dong",
        "bonbun",
        "bubun"
    ]


    address_columns = [

        column

        for column in columns

        if any(
            keyword.lower()
            in column.lower()

            for keyword in keywords
        )

    ]


    for column in address_columns:

        print(
            "-",
            column
        )


    print()
    print("========================================")
    print("확인 완료")
    print("========================================")


if __name__ == "__main__":

    main()