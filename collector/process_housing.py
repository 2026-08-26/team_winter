import csv
from pathlib import Path
from statistics import median


# =========================================================
# 1. 경로 설정
# =========================================================

BASE_DIR = Path(__file__).resolve().parent.parent

RAW_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed"

HOUSING_FILE = RAW_DIR / "전체_주거실거래_202608.csv"

OUTPUT_FILE = PROCESSED_DIR / "동별_주거비.csv"


# =========================================================
# 2. 행정동 → 주거 실거래 법정동 연결
#
# 주의:
# 실거래가는 법정동(umdNm) 기준이고
# 우리 프로젝트는 행정동 기준이므로 연결표가 필요함
# =========================================================

DONG_MAPPING = {

    # -------------------------
    # 동구
    # -------------------------
    ("동구", "충장동"): ["충장로1가", "충장로2가", "충장로3가",
                         "충장로4가", "충장로5가", "금남로1가",
                         "금남로2가", "금남로3가", "금남로4가",
                         "금남로5가", "황금동", "불로동", "호남동",
                         "수기동", "대인동", "궁동", "장동"],

    ("동구", "계림1동"): ["계림동"],

    ("동구", "지산2동"): ["지산동"],

    ("동구", "학동"): ["학동"],

    ("동구", "지원1동"): ["소태동", "용산동"],


    # -------------------------
    # 서구
    # -------------------------
    ("서구", "치평동"): ["치평동"],

    ("서구", "풍암동"): ["풍암동"],

    ("서구", "화정2동"): ["화정동"],

    ("서구", "농성1동"): ["농성동"],

    ("서구", "금호1동"): ["금호동"],


    # -------------------------
    # 남구
    # -------------------------
    ("남구", "봉선2동"): ["봉선동"],

    ("남구", "진월동"): ["진월동"],

    ("남구", "방림1동"): ["방림동"],

    ("남구", "효덕동"): ["노대동", "덕남동", "행암동"],

    ("남구", "송암동"): ["송하동", "임암동"],


    # -------------------------
    # 북구
    # -------------------------
    ("북구", "용봉동"): ["용봉동"],

    ("북구", "두암2동"): ["두암동"],

    ("북구", "운암1동"): ["운암동"],

    # 프로젝트 내부 기준: 첨단2동 = 북구
    # 실제 실거래 검색은 광산구의 관련 법정동을 사용
    ("북구", "첨단2동"): ["쌍암동", "산월동", "월계동"],

    ("북구", "문흥1동"): ["문흥동"],


    # -------------------------
    # 광산구
    # -------------------------
    ("광산구", "첨단1동"): ["월계동"],

    ("광산구", "수완동"): ["수완동", "장덕동", "흑석동"],

    ("광산구", "신가동"): ["신가동"],

    ("광산구", "우산동"): ["우산동"],

    ("광산구", "송정1동"): ["송정동"],
}


# =========================================================
# 3. CSV 읽기
# =========================================================

def read_csv(path):

    with open(
        path,
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        return list(csv.DictReader(file))


# =========================================================
# 4. 숫자 변환
# =========================================================

def to_number(value):

    if value is None:
        return None

    value = str(value).strip().replace(",", "")

    if value == "":
        return None

    try:
        return float(value)

    except ValueError:
        return None


# =========================================================
# 5. 중앙값 계산
# =========================================================

def get_median(values):

    values = [
        value
        for value in values
        if value is not None
    ]

    if not values:
        return ""

    return round(median(values), 1)


# =========================================================
# 6. 주거 데이터 처리
# =========================================================

def process_housing():

    print()
    print("========================================")
    print("🏠 주거 실거래 데이터 가공 시작")
    print("========================================")

    rows = read_csv(HOUSING_FILE)

    print(f"전체 실거래 데이터: {len(rows):,}건")

    result = []

    for (project_gu, project_dong), legal_dongs in DONG_MAPPING.items():

        # -------------------------------------------------
        # 첨단2동만 실제 데이터의 광산구를 조회
        # -------------------------------------------------

        if project_dong == "첨단2동":
            search_gu = "광산구"

        else:
            search_gu = project_gu


        # -------------------------------------------------
        # 해당 법정동의 거래만 추출
        # -------------------------------------------------

        dong_rows = [
            row
            for row in rows
            if row.get("gu_name") == search_gu
            and row.get("umdNm") in legal_dongs
        ]


        # -------------------------------------------------
        # 매매
        # -------------------------------------------------

        sale_rows = [
            row
            for row in dong_rows
            if row.get("transaction_type") == "매매"
        ]

        sale_prices = [
            to_number(row.get("dealAmount"))
            for row in sale_rows
        ]

        sale_prices = [
            price
            for price in sale_prices
            if price is not None
        ]


        # -------------------------------------------------
        # 전월세
        # -------------------------------------------------

        rent_rows = [
            row
            for row in dong_rows
            if row.get("transaction_type") == "전월세"
        ]


        # -------------------------------------------------
        # 전세
        # monthlyRent = 0
        # -------------------------------------------------

        jeonse_rows = []

        for row in rent_rows:

            monthly = to_number(
                row.get("monthlyRent")
            )

            if monthly == 0:
                jeonse_rows.append(row)


        jeonse_deposits = [
            to_number(row.get("deposit"))
            for row in jeonse_rows
        ]

        jeonse_deposits = [
            value
            for value in jeonse_deposits
            if value is not None
        ]


        # -------------------------------------------------
        # 월세
        # monthlyRent > 0
        # -------------------------------------------------

        monthly_rows = []

        for row in rent_rows:

            monthly = to_number(
                row.get("monthlyRent")
            )

            if monthly is not None and monthly > 0:
                monthly_rows.append(row)


        monthly_deposits = [
            to_number(row.get("deposit"))
            for row in monthly_rows
        ]

        monthly_rents = [
            to_number(row.get("monthlyRent"))
            for row in monthly_rows
        ]

        monthly_deposits = [
            value
            for value in monthly_deposits
            if value is not None
        ]

        monthly_rents = [
            value
            for value in monthly_rents
            if value is not None
        ]


        # -------------------------------------------------
        # 주택 유형별 거래 건수
        # -------------------------------------------------

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
            if row.get("housing_type") == "단독다가구"
        )


        # -------------------------------------------------
        # 결과
        # -------------------------------------------------

        output_row = {

            "자치구": project_gu,

            "행정동": project_dong,

            "주거비_연결법정동":
                "|".join(legal_dongs),

            "전체거래건수":
                len(dong_rows),

            "매매거래건수":
                len(sale_rows),

            "매매가격_중앙값_만원":
                get_median(sale_prices),

            "전세거래건수":
                len(jeonse_rows),

            "전세보증금_중앙값_만원":
                get_median(jeonse_deposits),

            "월세거래건수":
                len(monthly_rows),

            "월세보증금_중앙값_만원":
                get_median(monthly_deposits),

            "월세_중앙값_만원":
                get_median(monthly_rents),

            "아파트거래건수":
                apartment_count,

            "오피스텔거래건수":
                officetel_count,

            "연립다세대거래건수":
                rowhouse_count,

            "단독다가구거래건수":
                single_count,
        }

        result.append(output_row)

        print(
            f"{project_gu} {project_dong}"
            f" → {len(dong_rows):,}건"
        )


    # =====================================================
    # 7. 저장
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


    print()
    print("========================================")
    print("✅ 주거비 가공 완료")
    print("========================================")

    print(f"생성 파일: {OUTPUT_FILE.name}")
    print(f"분석 대상: {len(result)}개 동")


# =========================================================
# 실행
# =========================================================

if __name__ == "__main__":

    process_housing()