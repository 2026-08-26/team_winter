import os
import csv
import time
import requests
import xml.etree.ElementTree as ET

from pathlib import Path
from dotenv import load_dotenv


# =========================================================
# 1. 기본 설정
# =========================================================

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"

RAW_DIR.mkdir(parents=True, exist_ok=True)

load_dotenv(BASE_DIR / ".env")

SERVICE_KEY = os.getenv("DATA_GO_KR_SERVICE_KEY")


# =========================================================
# 2. 광주 5개 구 법정동 코드
# =========================================================

REGIONS = {
    "동구": "12210",
    "서구": "12240",
    "남구": "12270",
    "북구": "12300",
    "광산구": "12330"
}


# =========================================================
# 3. 수집 기간
# =========================================================

DEAL_YMD = "202608"


# =========================================================
# 4. 주거 API 6종
# =========================================================

HOUSING_APIS = [

    {
        "name": "아파트 매매",
        "housing_type": "아파트",
        "transaction_type": "매매",
        "url": (
            "https://apis.data.go.kr/1613000/"
            "RTMSDataSvcAptTrade/"
            "getRTMSDataSvcAptTrade"
        ),
        "filename": f"raw_apartment_trade_{DEAL_YMD}.csv"
    },

    {
        "name": "아파트 전월세",
        "housing_type": "아파트",
        "transaction_type": "전월세",
        "url": (
            "https://apis.data.go.kr/1613000/"
            "RTMSDataSvcAptRent/"
            "getRTMSDataSvcAptRent"
        ),
        "filename": f"raw_apartment_rent_{DEAL_YMD}.csv"
    },

    {
        "name": "오피스텔 매매",
        "housing_type": "오피스텔",
        "transaction_type": "매매",
        "url": (
            "https://apis.data.go.kr/1613000/"
            "RTMSDataSvcOffiTrade/"
            "getRTMSDataSvcOffiTrade"
        ),
        "filename": f"raw_officetel_trade_{DEAL_YMD}.csv"
    },

    {
        "name": "오피스텔 전월세",
        "housing_type": "오피스텔",
        "transaction_type": "전월세",
        "url": (
            "https://apis.data.go.kr/1613000/"
            "RTMSDataSvcOffiRent/"
            "getRTMSDataSvcOffiRent"
        ),
        "filename": f"raw_officetel_rent_{DEAL_YMD}.csv"
    },

    {
        "name": "단독/다가구 전월세",
        "housing_type": "단독/다가구",
        "transaction_type": "전월세",
        "url": (
            "https://apis.data.go.kr/1613000/"
            "RTMSDataSvcSHRent/"
            "getRTMSDataSvcSHRent"
        ),
        "filename": f"raw_single_house_rent_{DEAL_YMD}.csv"
    },

    {
        "name": "연립다세대 전월세",
        "housing_type": "연립다세대",
        "transaction_type": "전월세",
        "url": (
            "https://apis.data.go.kr/1613000/"
            "RTMSDataSvcRHRent/"
            "getRTMSDataSvcRHRent"
        ),
        "filename": f"raw_row_house_rent_{DEAL_YMD}.csv"
    }
]


# =========================================================
# 5. API 한 페이지 요청
# =========================================================

def request_page(
    api,
    gu_name,
    lawd_cd,
    page_no
):

    # 공공데이터포털 키는 이미 URL Encoding 되어 있으므로
    # serviceKey만 URL에 직접 붙임
    request_url = (
        f"{api['url']}?serviceKey={SERVICE_KEY}"
    )

    params = {
        "LAWD_CD": lawd_cd,
        "DEAL_YMD": DEAL_YMD,
        "numOfRows": 1000,
        "pageNo": page_no
    }

    try:

        response = requests.get(
            request_url,
            params=params,
            timeout=30
        )

    except requests.RequestException as e:

        print("   ❌ 요청 오류 :", e)

        return None


    if response.status_code != 200:

        print(
            "   ❌ 상태 코드 :",
            response.status_code
        )

        print(
            "   응답 :",
            response.text[:500]
        )

        return None


    try:

        root = ET.fromstring(
            response.text
        )

    except ET.ParseError:

        print("   ❌ XML 해석 실패")

        return None


    result_code = root.findtext(
        ".//resultCode"
    )

    result_msg = root.findtext(
        ".//resultMsg"
    )


    if result_code != "000":

        print(
            f"   ❌ API 오류 "
            f"{result_code} / {result_msg}"
        )

        return None


    return root


# =========================================================
# 6. 구 하나의 데이터 수집
# =========================================================

def collect_region(
    api,
    gu_name,
    lawd_cd
):

    rows = []

    page_no = 1


    while True:

        root = request_page(
            api,
            gu_name,
            lawd_cd,
            page_no
        )


        if root is None:
            break


        total_count_text = root.findtext(
            ".//totalCount"
        )


        try:
            total_count = int(
                total_count_text or 0
            )
        except ValueError:
            total_count = 0


        items = root.findall(
            ".//item"
        )


        # -----------------------------------------
        # 거래 한 건씩 저장
        # -----------------------------------------

        for item in items:

            row = {}


            for child in item:

                row[child.tag] = (
                    child.text.strip()
                    if child.text
                    else ""
                )


            # 프로젝트용 공통 정보
            row["gu_name"] = gu_name

            row["lawd_cd"] = lawd_cd

            row["housing_type"] = (
                api["housing_type"]
            )

            row["transaction_type"] = (
                api["transaction_type"]
            )

            row["query_ym"] = DEAL_YMD

            row["source_api"] = api["name"]


            rows.append(row)


        # -----------------------------------------
        # 다음 페이지 필요 여부 확인
        # -----------------------------------------

        if not items:
            break


        if len(rows) >= total_count:
            break


        page_no += 1


        time.sleep(0.1)


    return rows


# =========================================================
# 7. CSV 저장
# =========================================================

def save_csv(
    rows,
    filename
):

    if not rows:

        print(
            f"⚠️ {filename} : "
            f"저장할 데이터 없음"
        )

        return


    output_file = (
        RAW_DIR / filename
    )


    # API마다 항목명이 다르므로
    # 실제 데이터에서 모든 열 이름 자동 수집
    columns = []


    for row in rows:

        for key in row.keys():

            if key not in columns:

                columns.append(key)


    with open(
        output_file,
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=columns,
            extrasaction="ignore"
        )

        writer.writeheader()

        writer.writerows(rows)


    print(
        f"💾 저장 완료 : "
        f"{filename} "
        f"({len(rows)}건)"
    )


# =========================================================
# 8. 프로그램 실행
# =========================================================

if __name__ == "__main__":


    # -----------------------------------------
    # API KEY 확인
    # -----------------------------------------

    if not SERVICE_KEY:

        print(
            "❌ 공공데이터포털 "
            "API 키를 찾지 못했습니다."
        )

        exit()


    print()
    print(
        "========================================"
    )
    print(
        "광주 주거 실거래가 전체 수집 시작"
    )
    print(
        "========================================"
    )

    print(
        "수집 기준 :",
        DEAL_YMD
    )

    print(
        "지역 : 광주 5개 구"
    )

    print(
        "주거 데이터 :",
        len(HOUSING_APIS),
        "종류"
    )


    # 모든 주거 데이터 통합용
    all_housing_rows = []


    # =========================================
    # API 6종 반복
    # =========================================

    for api_index, api in enumerate(
        HOUSING_APIS,
        start=1
    ):


        print()
        print(
            "========================================"
        )

        print(
            f"[{api_index}/"
            f"{len(HOUSING_APIS)}] "
            f"{api['name']}"
        )

        print(
            "========================================"
        )


        api_rows = []


        # =====================================
        # 광주 5개 구 반복
        # =====================================

        for gu_name, lawd_cd in (
            REGIONS.items()
        ):


            print()
            print(
                f"▶ {gu_name} 수집 중..."
            )


            region_rows = collect_region(
                api,
                gu_name,
                lawd_cd
            )


            print(
                f"   → "
                f"{len(region_rows)}건"
            )


            api_rows.extend(
                region_rows
            )


            all_housing_rows.extend(
                region_rows
            )


            time.sleep(0.2)


        # =====================================
        # 주거 유형별 CSV 저장
        # =====================================

        print()

        save_csv(
            api_rows,
            api["filename"]
        )


        print(
            f"✅ {api['name']} "
            f"전체 : "
            f"{len(api_rows)}건"
        )


    # =====================================================
    # 9. 모든 주거 데이터 통합 CSV
    # =====================================================

    print()
    print(
        "========================================"
    )

    print(
        "주거 데이터 통합 CSV 생성"
    )

    print(
        "========================================"
    )


    save_csv(
        all_housing_rows,
        f"raw_housing_transactions_{DEAL_YMD}.csv"
    )


    # =====================================================
    # 10. 최종 결과
    # =====================================================

    print()
    print(
        "========================================"
    )

    print(
        "🎉 주거 데이터 전체 수집 완료!"
    )

    print(
        "========================================"
    )


    print(
        "수집 지역 :",
        len(REGIONS),
        "개 구"
    )


    print(
        "수집 주거 유형 :",
        len(HOUSING_APIS),
        "개"
    )


    print(
        "전체 거래 데이터 :",
        len(all_housing_rows),
        "건"
    )