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

RAW_DIR.mkdir(
    parents=True,
    exist_ok=True
)

load_dotenv(
    BASE_DIR / ".env"
)

SERVICE_KEY = os.getenv(
    "DATA_GO_KR_SERVICE_KEY"
)


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
#
# 2025년 7월 ~ 2026년 6월
# 정확히 12개월
# =========================================================

DEAL_MONTHS = [
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
]

PERIOD_NAME = "202507_202606"


# =========================================================
# 4. 전월세 API 4종
#
# 청년 주거비 분석에는 매매를 사용하지 않으므로
# 전월세 데이터만 수집
# =========================================================

HOUSING_APIS = [

    {
        "name": "아파트 전월세",

        "housing_type": "아파트",

        "transaction_type": "전월세",

        "url": (
            "https://apis.data.go.kr/1613000/"
            "RTMSDataSvcAptRent/"
            "getRTMSDataSvcAptRent"
        ),

        "filename":
            f"아파트_전월세_{PERIOD_NAME}.csv"
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

        "filename":
            f"오피스텔_전월세_{PERIOD_NAME}.csv"
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

        "filename":
            f"단독다가구_전월세_{PERIOD_NAME}.csv"
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

        "filename":
            f"연립다세대_전월세_{PERIOD_NAME}.csv"
    }
]


# =========================================================
# 5. API 한 페이지 요청
# =========================================================

def request_page(
    api,
    lawd_cd,
    deal_ymd,
    page_no
):

    request_url = (
        f"{api['url']}"
        f"?serviceKey={SERVICE_KEY}"
    )


    params = {

        "LAWD_CD":
            lawd_cd,

        "DEAL_YMD":
            deal_ymd,

        "numOfRows":
            1000,

        "pageNo":
            page_no
    }


    try:

        response = requests.get(
            request_url,
            params=params,
            timeout=30
        )


    except requests.RequestException as e:

        print(
            "   ❌ 요청 오류 :",
            e
        )

        return None


    if response.status_code != 200:

        print(
            "   ❌ 상태 코드 :",
            response.status_code
        )

        print(
            response.text[:500]
        )

        return None


    try:

        root = ET.fromstring(
            response.text
        )


    except ET.ParseError:

        print(
            "   ❌ XML 해석 실패"
        )

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
            f"{result_code} / "
            f"{result_msg}"
        )

        return None


    return root


# =========================================================
# 6. 특정 구 + 특정 월 데이터 수집
# =========================================================

def collect_region_month(
    api,
    gu_name,
    lawd_cd,
    deal_ymd
):

    rows = []

    page_no = 1


    while True:

        root = request_page(
            api,
            lawd_cd,
            deal_ymd,
            page_no
        )


        if root is None:

            break


        total_count_text = (
            root.findtext(
                ".//totalCount"
            )
        )


        try:

            total_count = int(
                total_count_text
                or 0
            )


        except ValueError:

            total_count = 0


        items = root.findall(
            ".//item"
        )


        # -------------------------------------------------
        # 거래 한 건씩 저장
        # -------------------------------------------------

        for item in items:

            row = {}


            for child in item:

                row[
                    child.tag
                ] = (

                    child.text.strip()

                    if child.text

                    else ""
                )


            # ---------------------------------------------
            # 프로젝트용 공통 정보
            # ---------------------------------------------

            row["gu_name"] = (
                gu_name
            )

            row["lawd_cd"] = (
                lawd_cd
            )

            row["housing_type"] = (
                api[
                    "housing_type"
                ]
            )

            row[
                "transaction_type"
            ] = (
                api[
                    "transaction_type"
                ]
            )

            row["query_ym"] = (
                deal_ymd
            )

            row["source_api"] = (
                api["name"]
            )


            rows.append(
                row
            )


        # -------------------------------------------------
        # 다음 페이지 여부
        # -------------------------------------------------

        if not items:

            break


        if len(rows) >= total_count:

            break


        page_no += 1


        time.sleep(
            0.1
        )


    return rows


# =========================================================
# 7. CSV 저장 함수
# =========================================================

def save_csv(
    rows,
    filename
):

    if not rows:

        print(
            f"⚠️ {filename} : "
            "저장할 데이터 없음"
        )

        return


    output_file = (
        RAW_DIR / filename
    )


    # API 종류마다 컬럼이 조금씩 다르기 때문에
    # 실제 데이터에 존재하는 컬럼을 전부 수집
    columns = []


    for row in rows:

        for key in row.keys():

            if key not in columns:

                columns.append(
                    key
                )


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

        writer.writerows(
            rows
        )


    print(
        f"💾 저장 완료 : "
        f"{filename} "
        f"({len(rows):,}건)"
    )


# =========================================================
# 8. 프로그램 실행
# =========================================================

if __name__ == "__main__":


    # =====================================================
    # API KEY 확인
    # =====================================================

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
        "광주 전월세 실거래 1년치 수집 시작"
    )

    print(
        "========================================"
    )


    print(
        "수집 기간 : "
        "2025년 7월 ~ 2026년 6월"
    )

    print(
        "수집 개월 :",
        len(DEAL_MONTHS),
        "개월"
    )

    print(
        "지역 : 광주 5개 구"
    )

    print(
        "수집 대상 : 전월세 4종"
    )


    # =====================================================
    # 전체 통합 데이터
    # =====================================================

    all_housing_rows = []


    # =====================================================
    # 주거유형 반복
    # =====================================================

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


        # =================================================
        # 12개월 반복
        # =================================================

        for month_index, deal_ymd in enumerate(
            DEAL_MONTHS,
            start=1
        ):


            print()
            print(
                f"▶ [{month_index}/12] "
                f"{deal_ymd} 수집"
            )


            # =============================================
            # 광주 5개 구 반복
            # =============================================

            for gu_name, lawd_cd in (
                REGIONS.items()
            ):


                print(
                    f"   - {gu_name}...",
                    end=""
                )


                region_rows = (
                    collect_region_month(
                        api,
                        gu_name,
                        lawd_cd,
                        deal_ymd
                    )
                )


                print(
                    f" {len(region_rows):,}건"
                )


                api_rows.extend(
                    region_rows
                )


                all_housing_rows.extend(
                    region_rows
                )


                time.sleep(
                    0.15
                )


        # =================================================
        # 주택 유형별 1년치 CSV
        # =================================================

        print()

        save_csv(
            api_rows,
            api["filename"]
        )


        print(
            f"✅ {api['name']} "
            f"1년치 : "
            f"{len(api_rows):,}건"
        )


    # =====================================================
    # 9. 전체 전월세 통합 CSV
    # =====================================================

    print()
    print(
        "========================================"
    )

    print(
        "전체 전월세 통합 CSV 생성"
    )

    print(
        "========================================"
    )


    combined_filename = (
        f"전체_주거실거래_"
        f"{PERIOD_NAME}.csv"
    )


    save_csv(
        all_housing_rows,
        combined_filename
    )


    # =====================================================
    # 10. 간단한 검증
    # =====================================================

    print()
    print(
        "========================================"
    )

    print(
        "수집 결과 검증"
    )

    print(
        "========================================"
    )


    print(
        f"총 거래 데이터 : "
        f"{len(all_housing_rows):,}건"
    )


    # 월별 건수
    print(
        "\n[월별 거래 건수]"
    )


    for deal_ymd in DEAL_MONTHS:

        count = sum(

            1

            for row in all_housing_rows

            if row.get(
                "query_ym"
            ) == deal_ymd
        )


        print(
            f"{deal_ymd} : "
            f"{count:,}건"
        )


    # 주택유형별 건수
    print(
        "\n[주택유형별 거래 건수]"
    )


    for api in HOUSING_APIS:

        housing_type = (
            api[
                "housing_type"
            ]
        )


        count = sum(

            1

            for row in all_housing_rows

            if row.get(
                "housing_type"
            ) == housing_type
        )


        print(
            f"{housing_type} : "
            f"{count:,}건"
        )


    # =====================================================
    # 11. 최종 출력
    # =====================================================

    print()
    print(
        "========================================"
    )

    print(
        "🎉 전월세 1년치 수집 완료"
    )

    print(
        "========================================"
    )


    print(
        "기간 : "
        "2025-07 ~ 2026-06"
    )

    print(
        "전체 거래 :",
        f"{len(all_housing_rows):,}",
        "건"
    )

    print(
        "최종 통합 파일 :"
    )

    print(
        RAW_DIR
        / combined_filename
    )