import os
import re
import time

import requests
import pandas as pd
from bs4 import BeautifulSoup


# =========================================================
# 1. 기본 설정
# =========================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

OUTPUT_FILE = os.path.join(
    BASE_DIR,
    "data",
    "raw",
    "청년_공공시설.csv"
)

URL = (
    "https://youth.gwangju.go.kr/"
    "www/areaResve/resveList"
)


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 "
        "(Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/120 Safari/537.36"
    ),
    "Referer": URL
}


FACILITY_TYPES = [
    "통합지원형",
    "취업지원형",
    "창업지원형",
    "프로그램운영형",
    "기타공간"
]


DISTRICTS = [
    "동구",
    "서구",
    "남구",
    "북구",
    "광산구"
]


# =========================================================
# 2. 텍스트 정리
# =========================================================

def clean_text(value):

    if value is None:
        return ""

    return re.sub(
        r"\s+",
        " ",
        str(value)
    ).strip()


# =========================================================
# 3. 페이지 정보 추출
# =========================================================

def get_page_info(soup):

    text = clean_text(
        soup.get_text(
            " ",
            strip=True
        )
    )


    # 예:
    # 총 189건 (1/16페이지)

    match = re.search(
        r"총\s*([0-9,]+)건"
        r".*?"
        r"(\d+)\s*/\s*(\d+)\s*페이지",
        text
    )


    if match:

        total = int(
            match.group(1).replace(
                ",",
                ""
            )
        )

        current_page = int(
            match.group(2)
        )

        total_pages = int(
            match.group(3)
        )


        return {
            "total": total,
            "current": current_page,
            "pages": total_pages
        }


    return None


# =========================================================
# 4. 주소 추출
# =========================================================

def find_address(texts):

    for index, text in enumerate(
        texts
    ):

        text = clean_text(text)


        # -------------------------------------------------
        # "주소 광주광역시 ..."
        # -------------------------------------------------

        if text.startswith("주소"):

            address = clean_text(
                re.sub(
                    r"^주소\s*",
                    "",
                    text
                )
            )


            if address:

                return address, index


            # ---------------------------------------------
            # 주소와 실제 주소가 다른 태그일 경우
            # ---------------------------------------------

            if index + 1 < len(texts):

                next_text = clean_text(
                    texts[
                        index + 1
                    ]
                )


                if (
                    "광주" in next_text
                    or
                    "전남광주" in next_text
                ):

                    return (
                        next_text,
                        index
                    )


        # -------------------------------------------------
        # 주소라는 단어 없이 실제 주소만 있는 경우
        # -------------------------------------------------

        if (
            text.startswith("광주 ")
            or
            text.startswith("광주광역시 ")
            or
            text.startswith(
                "전남광주"
            )
        ):

            if any(
                district in text
                for district in DISTRICTS
            ):

                return (
                    text,
                    index
                )


    return "", -1


# =========================================================
# 5. 공공 표시가 있는 시설 카드 찾기
# =========================================================

def find_facility_card(
    public_node
):

    current = public_node.parent


    for _ in range(12):

        if current is None:
            break


        texts = [
            clean_text(x)
            for x
            in current.stripped_strings
            if clean_text(x)
        ]


        combined = " ".join(
            texts
        )


        has_public = (
            "공공" in texts
        )


        has_address = (
            "주소" in combined
            and
            "광주" in combined
        )


        has_type = any(
            facility_type in texts
            or
            facility_type in combined
            for facility_type
            in FACILITY_TYPES
        )


        has_district = any(
            district in texts
            or
            district in combined
            for district
            in DISTRICTS
        )


        has_detail = (
            "상세보기" in combined
        )


        if (
            has_public
            and
            has_address
            and
            has_type
            and
            has_district
            and
            has_detail
        ):

            return current


        current = current.parent


    return None


# =========================================================
# 6. 시설 카드 정보 추출
# =========================================================

def parse_facility_card(card):

    texts = [
        clean_text(x)
        for x
        in card.stripped_strings
        if clean_text(x)
    ]


    # =====================================================
    # 기관분류
    # =====================================================

    if "공공" not in texts:

        return None


    org_type = "공공"


    # =====================================================
    # 시설유형
    # =====================================================

    facility_type = ""


    for item in FACILITY_TYPES:

        if (
            item in texts
            or
            any(
                item in text
                for text in texts
            )
        ):

            facility_type = item
            break


    if not facility_type:

        return None


    # =====================================================
    # 주소
    # =====================================================

    address, address_index = (
        find_address(
            texts
        )
    )


    if not address:

        return None


    # =====================================================
    # 자치구
    # =====================================================

    district = ""


    for item in DISTRICTS:

        if item in address:

            district = item
            break


    if not district:

        for item in DISTRICTS:

            if item in texts:

                district = item
                break


    if not district:

        return None


    # =====================================================
    # 시설명
    # =====================================================

    ignore_words = set(

        FACILITY_TYPES
        +
        DISTRICTS
        +
        [
            "공공",
            "민간",
            "주소",
            "상세보기",
            "Thumbnail Image"
        ]
    )


    facility_name = ""


    search_end = (
        address_index
        if address_index >= 0
        else len(texts)
    )


    # 주소 바로 앞의 정상 텍스트를
    # 시설명으로 사용

    for i in range(
        search_end - 1,
        -1,
        -1
    ):

        text = texts[i]


        if not text:
            continue


        if text in ignore_words:
            continue


        if text.startswith(
            "주소"
        ):
            continue


        if "Thumbnail" in text:
            continue


        if len(text) > 100:
            continue


        facility_name = text

        break


    if not facility_name:

        return None


    return {

        "시설명":
            facility_name,

        "시설유형":
            facility_type,

        "기관분류":
            org_type,

        "주소":
            address,

        "자치구":
            district
    }


# =========================================================
# 7. HTML에서 공공시설 추출
# =========================================================

def extract_public_facilities(
    html
):

    soup = BeautifulSoup(
        html,
        "html.parser"
    )


    results = []

    seen = set()


    # -----------------------------------------------------
    # 사이트의 '공공' 표시를 기준으로 탐색
    # -----------------------------------------------------

    public_nodes = soup.find_all(

        string=lambda text:
        clean_text(text)
        == "공공"

    )


    for node in public_nodes:

        card = find_facility_card(
            node
        )


        if card is None:
            continue


        facility = parse_facility_card(
            card
        )


        if facility is None:
            continue


        key = (

            facility["시설명"],
            facility["주소"]

        )


        if key in seen:
            continue


        seen.add(key)

        results.append(
            facility
        )


    return (
        results,
        soup
    )


# =========================================================
# 8. 페이지 요청
# =========================================================

def request_page(
    session,
    page_number
):

    # -----------------------------------------------------
    # 실제 사이트 FORM 구조
    #
    # form id     = searchForm
    # method      = POST
    # pageIndex   = 페이지 번호
    # pageUnit2   = 12
    # -----------------------------------------------------

    payload = {

        "svc": "/",

        "siteId": "www",

        "pageIndex":
            str(page_number),

        "pageUnit2":
            "12",

        "keyword":
            ""
    }


    response = session.post(

        URL,

        data=payload,

        headers=HEADERS,

        timeout=30
    )


    response.raise_for_status()

    response.encoding = "utf-8"


    return response.text


# =========================================================
# 9. 전체 시설 수집
# =========================================================

def collect_all():

    os.makedirs(
        os.path.dirname(
            OUTPUT_FILE
        ),
        exist_ok=True
    )


    print("\n========================================")

    print(
        "광주 청년 공공시설 수집 시작"
    )

    print(
        "========================================"
    )


    print(
        "\n출처 : 광주청년통합플랫폼"
    )


    print(
        "수집방식 : searchForm POST"
    )


    session = requests.Session()


    # =====================================================
    # 1페이지 먼저 확인
    # =====================================================

    first_html = request_page(
        session,
        1
    )


    first_results, first_soup = (
        extract_public_facilities(
            first_html
        )
    )


    page_info = get_page_info(
        first_soup
    )


    # =====================================================
    # 페이지 정보
    # =====================================================

    if page_info:

        total_pages = (
            page_info["pages"]
        )

        total_records = (
            page_info["total"]
        )


        print(
            f"\n사이트 전체 등록시설 : "
            f"{total_records}건"
        )

        print(
            f"전체 페이지 : "
            f"{total_pages}페이지"
        )


    else:

        print(
            "\n페이지 정보를 자동으로 "
            "읽지 못했습니다."
        )

        print(
            "기본값 16페이지를 사용합니다."
        )

        total_pages = 16


    # =====================================================
    # 실제 전체 페이지 수집
    # =====================================================

    all_results = []


    for page_number in range(
        1,
        total_pages + 1
    ):

        print(
            f"\n{page_number}/"
            f"{total_pages} "
            f"페이지 수집 중..."
        )


        try:

            html = request_page(
                session,
                page_number
            )


            facilities, soup = (
                extract_public_facilities(
                    html
                )
            )


            current_info = (
                get_page_info(
                    soup
                )
            )


            if current_info:

                print(

                    "사이트 표시 페이지 : "
                    f"{current_info['current']}"
                    f"/"
                    f"{current_info['pages']}"

                )


            print(
                f"공공시설 : "
                f"{len(facilities)}개"
            )


            all_results.extend(
                facilities
            )


            time.sleep(
                0.4
            )


        except Exception as e:

            print(
                f"[오류] "
                f"{page_number}페이지"
            )

            print(e)


    # =====================================================
    # 결과 없음
    # =====================================================

    if not all_results:

        print(
            "\n수집된 공공시설이 없습니다."
        )

        return


    # =====================================================
    # DataFrame
    # =====================================================

    df = pd.DataFrame(
        all_results
    )


    # =====================================================
    # 중복 제거
    # =====================================================

    before_count = len(df)


    df = (

        df

        .drop_duplicates(
            subset=[
                "시설명",
                "주소"
            ]
        )

        .reset_index(
            drop=True
        )

    )


    duplicate_count = (
        before_count
        -
        len(df)
    )


    # =====================================================
    # 출처 정보
    # =====================================================

    df["출처"] = (
        "광주청년통합플랫폼"
    )


    df["출처URL"] = URL


    df["수집기준"] = (

        "광주청년통합플랫폼에서 "
        "기관분류가 공공으로 표시된 시설"

    )


    df["수집일"] = (

        pd.Timestamp.today()

        .strftime(
            "%Y-%m-%d"
        )

    )


    # =====================================================
    # 정렬
    # =====================================================

    df = (

        df

        .sort_values(
            [
                "자치구",
                "시설유형",
                "시설명"
            ]
        )

        .reset_index(
            drop=True
        )

    )


    # =====================================================
    # 저장
    # =====================================================

    df.to_csv(

        OUTPUT_FILE,

        index=False,

        encoding="utf-8-sig"

    )


    # =====================================================
    # 결과 출력
    # =====================================================

    print(
        "\n========================================"
    )

    print(
        "청년 공공시설 수집 완료"
    )

    print(
        "========================================"
    )


    print(
        f"\n최종 공공시설 : "
        f"{len(df)}개"
    )


    print(
        f"중복 제거 : "
        f"{duplicate_count}개"
    )


    # =====================================================
    # 자치구별
    # =====================================================

    print(
        "\n[자치구별 공공시설]"
    )


    district_count = (

        df["자치구"]

        .value_counts()

    )


    print(
        district_count.to_string()
    )


    # =====================================================
    # 유형별
    # =====================================================

    print(
        "\n[시설유형별]"
    )


    type_count = (

        df["시설유형"]

        .value_counts()

    )


    print(
        type_count.to_string()
    )


    # =====================================================
    # 데이터 미리보기
    # =====================================================

    print(
        "\n[시설 미리보기]"
    )


    print(

        df[
            [
                "시설명",
                "시설유형",
                "자치구",
                "주소"
            ]
        ]

        .head(20)

        .to_string(
            index=False
        )

    )


    print(
        "\n----------------------------------------"
    )

    print(
        "저장 완료"
    )

    print(
        OUTPUT_FILE
    )

    print(
        "----------------------------------------"
    )


# =========================================================
# 실행
# =========================================================

if __name__ == "__main__":

    collect_all()