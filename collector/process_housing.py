import csv
from pathlib import Path
from statistics import median, mean


# =========================================================
# 1. 경로
# =========================================================

BASE_DIR = Path(__file__).resolve().parent.parent

RAW_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed"

HOUSING_FILE = (
    RAW_DIR
    / "전체_주거실거래_202507_202606.csv"
)

OUTPUT_FILE = (
    PROCESSED_DIR
    / "동별_주거비.csv"
)


# =========================================================
# 2. 분석 기준
# =========================================================

# 18평 ≈ 59.5㎡
MAX_AREA_M2 = 59.5

# 프로젝트 분석 가정
DEPOSIT_ANNUAL_RATE = 0.05


# =========================================================
# 3. 행정동 → 법정동 연결
# =========================================================

DONG_MAPPING = {

    # 동구
    ("동구", "충장동"): [
        "충장로1가", "충장로2가", "충장로3가",
        "충장로4가", "충장로5가",
        "금남로1가", "금남로2가", "금남로3가",
        "금남로4가", "금남로5가",
        "황금동", "불로동", "호남동",
        "수기동", "대인동", "궁동", "장동"
    ],

    ("동구", "계림1동"): ["계림동"],
    ("동구", "지산2동"): ["지산동"],
    ("동구", "학동"): ["학동"],
    ("동구", "지원1동"): ["소태동", "용산동"],

    # 서구
    ("서구", "치평동"): ["치평동"],
    ("서구", "풍암동"): ["풍암동"],
    ("서구", "화정2동"): ["화정동"],
    ("서구", "농성1동"): ["농성동"],
    ("서구", "금호1동"): ["금호동"],

    # 남구
    ("남구", "봉선2동"): ["봉선동"],
    ("남구", "진월동"): ["진월동"],
    ("남구", "방림1동"): ["방림동"],
    ("남구", "효덕동"): ["노대동", "덕남동", "행암동"],
    ("남구", "송암동"): ["송하동", "임암동"],

    # 북구
    ("북구", "용봉동"): ["용봉동"],
    ("북구", "두암2동"): ["두암동"],
    ("북구", "운암1동"): ["운암동"],

    # 프로젝트 내부 표기만 북구
    # 공식 조회는 광산구
    ("북구", "첨단2동"): [
        "쌍암동", "산월동", "월계동"
    ],

    ("북구", "문흥1동"): ["문흥동"],

    # 광산구
    ("광산구", "첨단1동"): ["월계동"],
    ("광산구", "수완동"): [
        "수완동", "장덕동", "흑석동"
    ],
    ("광산구", "신가동"): ["신가동"],
    ("광산구", "우산동"): ["우산동"],
    ("광산구", "송정1동"): ["송정동"],
}


# =========================================================
# 4. CSV 읽기
# =========================================================

def read_csv(path):

    with open(
        path,
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        return list(
            csv.DictReader(file)
        )


# =========================================================
# 5. 숫자 변환
# =========================================================

def to_number(value):

    if value is None:
        return None

    value = (
        str(value)
        .strip()
        .replace(",", "")
    )

    if value == "":
        return None

    try:
        return float(value)

    except ValueError:
        return None


# =========================================================
# 6. 중앙값
# =========================================================

def get_median(values):

    values = [
        value
        for value in values
        if value is not None
    ]

    if not values:
        return ""

    return round(
        median(values),
        2
    )


# =========================================================
# 7. 평균값
# =========================================================

def get_average(values):

    values = [
        value
        for value in values
        if value is not None
    ]

    if not values:
        return ""

    return round(
        mean(values),
        2
    )


# =========================================================
# 8. 전용면적
# =========================================================

def get_area(row):

    return to_number(
        row.get("excluUseAr")
    )


# =========================================================
# 9. 월환산주거비
# =========================================================

def get_monthly_equivalent(row):

    deposit = to_number(
        row.get("deposit")
    )

    monthly_rent = to_number(
        row.get("monthlyRent")
    )

    if (
        deposit is None
        or monthly_rent is None
    ):
        return None


    # 단위: 만원
    return (

        monthly_rent

        +

        (
            deposit
            * DEPOSIT_ANNUAL_RATE
            / 12
        )

    )


# =========================================================
# 10. 18평 이하 전월세 필터
# =========================================================

def is_target(row):

    if (
        row.get("transaction_type")
        != "전월세"
    ):
        return False


    area = get_area(row)


    # 전용면적을 확인할 수 없는 거래 제외
    if area is None:
        return False


    if area > MAX_AREA_M2:
        return False


    deposit = to_number(
        row.get("deposit")
    )

    monthly = to_number(
        row.get("monthlyRent")
    )


    if (
        deposit is None
        or monthly is None
    ):
        return False


    return True


# =========================================================
# 11. 실행
# =========================================================

def process_housing():

    print()
    print("========================================")
    print("18평 이하 전월세 주거비 평균 분석")
    print("========================================")

    print("기간 : 2025-07 ~ 2026-06")
    print("면적 : 전용면적 59.5㎡ 이하")
    print("거래 : 전세 + 월세")


    if not HOUSING_FILE.exists():

        print("원본 파일이 없습니다.")
        print(HOUSING_FILE)

        return


    rows = read_csv(
        HOUSING_FILE
    )


    print(
        f"\n전체 원본 : {len(rows):,}건"
    )


    # =====================================================
    # 전체 필터
    # =====================================================

    filtered_rows = [
        row
        for row in rows
        if is_target(row)
    ]


    print(
        f"18평 이하 유효 전월세 : "
        f"{len(filtered_rows):,}건"
    )


    result = []


    # =====================================================
    # 동별 집계
    # =====================================================

    for (
        project_gu,
        project_dong
    ), legal_dongs in DONG_MAPPING.items():


        if project_dong == "첨단2동":

            search_gu = "광산구"

        else:

            search_gu = project_gu


        dong_rows = [

            row

            for row in filtered_rows

            if (
                row.get("gu_name") == search_gu
                and
                row.get("umdNm") in legal_dongs
            )
        ]


        # =================================================
        # 전세 / 월세 구분
        # =================================================

        jeonse_rows = []

        monthly_rows = []


        for row in dong_rows:

            rent = to_number(
                row.get("monthlyRent")
            )


            if rent == 0:

                jeonse_rows.append(row)


            elif (
                rent is not None
                and rent > 0
            ):

                monthly_rows.append(row)


        # =================================================
        # 값 추출
        # =================================================

        areas = [
            get_area(row)
            for row in dong_rows
        ]


        all_deposits = [

            to_number(
                row.get("deposit")
            )

            for row in dong_rows
        ]


        jeonse_deposits = [

            to_number(
                row.get("deposit")
            )

            for row in jeonse_rows
        ]


        monthly_deposits = [

            to_number(
                row.get("deposit")
            )

            for row in monthly_rows
        ]


        monthly_rents = [

            to_number(
                row.get("monthlyRent")
            )

            for row in monthly_rows
        ]


        equivalents = [

            get_monthly_equivalent(row)

            for row in dong_rows
        ]


        # =================================================
        # 주택 유형별 건수
        # =================================================

        apartment_count = sum(
            1
            for row in dong_rows
            if row.get("housing_type") == "아파트"
        )

        officetel_count = sum(
            1
            for row in dong_rows
            if row.get("housing_type") == "오피스텔"
        )

        rowhouse_count = sum(
            1
            for row in dong_rows
            if row.get("housing_type") == "연립다세대"
        )

        single_count = sum(
            1
            for row in dong_rows
            if row.get("housing_type") == "단독/다가구"
        )


        # =================================================
        # 표본상태
        # =================================================

        count = len(dong_rows)


        if count == 0:
            sample_status = "거래없음"

        elif count < 5:
            sample_status = "주의"

        elif count < 20:
            sample_status = "보통"

        else:
            sample_status = "충분"


        # =================================================
        # 결과
        # =================================================

        output = {

            "자치구":
                project_gu,

            "행정동":
                project_dong,

            "주거비_연결법정동":
                "|".join(legal_dongs),

            "전체거래건수":
                count,

            "전세거래건수":
                len(jeonse_rows),

            "월세거래건수":
                len(monthly_rows),


            # ---------------------------------------------
            # 평균값
            # ---------------------------------------------

            "전세보증금_평균값_만원":
                get_average(
                    jeonse_deposits
                ),

            "월세보증금_평균값_만원":
                get_average(
                    monthly_deposits
                ),

            "월세_평균값_만원":
                get_average(
                    monthly_rents
                ),

            "전체임대차보증금_평균값_만원":
                get_average(
                    all_deposits
                ),

            "월환산주거비_평균값_만원":
                get_average(
                    equivalents
                ),

            "전용면적_평균값_m2":
                get_average(
                    areas
                ),


            # ---------------------------------------------
            # 비교용 중앙값도 같이 보존
            # ---------------------------------------------

            "전세보증금_중앙값_만원":
                get_median(
                    jeonse_deposits
                ),

            "월세보증금_중앙값_만원":
                get_median(
                    monthly_deposits
                ),

            "월세_중앙값_만원":
                get_median(
                    monthly_rents
                ),

            "월환산주거비_중앙값_만원":
                get_median(
                    equivalents
                ),


            # ---------------------------------------------
            # 주택유형
            # ---------------------------------------------

            "아파트거래건수":
                apartment_count,

            "오피스텔거래건수":
                officetel_count,

            "연립다세대거래건수":
                rowhouse_count,

            "단독다가구거래건수":
                single_count,


            # ---------------------------------------------
            # 기준
            # ---------------------------------------------

            "표본상태":
                sample_status,

            "면적기준":
                "전용면적 59.5㎡ 이하",

            "평수기준":
                "18평 이하",

            "거래유형기준":
                "전세+월세",

            "분석시작월":
                "202507",

            "분석종료월":
                "202606",

            "보증금환산율":
                DEPOSIT_ANNUAL_RATE
        }


        result.append(output)


        print(
            f"{project_gu} {project_dong}"
            f" → {count}건"
            f" / 월환산 평균 "
            f"{output['월환산주거비_평균값_만원']}만원"
        )


    # =====================================================
    # 12. CSV 저장
    # =====================================================

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=result[0].keys()
        )

        writer.writeheader()

        writer.writerows(result)


    # =====================================================
    # 13. 농성1동 / 계림1동 비교
    # =====================================================

    print()
    print("========================================")
    print("농성1동 / 계림1동 평균값 확인")
    print("========================================")


    for row in result:

        if row["행정동"] not in [
            "농성1동",
            "계림1동"
        ]:
            continue


        print()
        print(
            f"[{row['자치구']} "
            f"{row['행정동']}]"
        )

        print(
            "유효 거래 :",
            row["전체거래건수"],
            "건"
        )

        print(
            "전세보증금 평균 :",
            row[
                "전세보증금_평균값_만원"
            ],
            "만원"
        )

        print(
            "월세보증금 평균 :",
            row[
                "월세보증금_평균값_만원"
            ],
            "만원"
        )

        print(
            "월세 평균 :",
            row[
                "월세_평균값_만원"
            ],
            "만원"
        )

        print(
            "월환산주거비 평균 :",
            row[
                "월환산주거비_평균값_만원"
            ],
            "만원"
        )


    print()
    print("========================================")
    print("평균 주거비 계산 완료")
    print("========================================")

    print(
        OUTPUT_FILE
    )


# =========================================================
# 실행
# =========================================================

if __name__ == "__main__":

    process_housing()