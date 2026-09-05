import os
import re
import time

import pandas as pd
import requests
from dotenv import load_dotenv


# =========================================================
# 1. 파일 경로
# =========================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

INPUT_FILE = os.path.join(
    BASE_DIR,
    "data",
    "raw",
    "청년_공공시설_좌표.csv"
)

OUTPUT_FILE = os.path.join(
    BASE_DIR,
    "data",
    "raw",
    "청년_공공시설_좌표_보완.csv"
)


# =========================================================
# 2. 환경변수
# =========================================================

load_dotenv(
    os.path.join(
        BASE_DIR,
        ".env"
    )
)

KAKAO_REST_API_KEY = os.getenv(
    "KAKAO_REST_API_KEY"
)

if not KAKAO_REST_API_KEY:

    raise ValueError(
        "KAKAO_REST_API_KEY를 .env에서 찾을 수 없습니다."
    )


# =========================================================
# 3. 카카오 API 설정
# =========================================================

ADDRESS_URL = (
    "https://dapi.kakao.com/"
    "v2/local/search/address.json"
)

KEYWORD_URL = (
    "https://dapi.kakao.com/"
    "v2/local/search/keyword.json"
)

HEADERS = {
    "Authorization":
        f"KakaoAK {KAKAO_REST_API_KEY}"
}


# =========================================================
# 4. 주소 정리
# =========================================================

def clean_text(text):

    if pd.isna(text):
        return ""

    return re.sub(
        r"\s+",
        " ",
        str(text)
    ).strip()


# =========================================================
# 5. 검색용 주소 후보 만들기
# =========================================================

def make_address_candidates(address):

    address = clean_text(
        address
    )

    candidates = []


    # -----------------------------------------------------
    # 원본 주소
    # -----------------------------------------------------

    if address:

        candidates.append(
            address
        )


    # -----------------------------------------------------
    # 괄호 내용 제거
    # -----------------------------------------------------

    no_parentheses = re.sub(
        r"\([^)]*\)",
        "",
        address
    )

    no_parentheses = clean_text(
        no_parentheses
    )


    if no_parentheses:

        candidates.append(
            no_parentheses
        )


    # -----------------------------------------------------
    # 층수 표현 제거
    # 예: 2~3층 / 2층 / 3F
    # -----------------------------------------------------

    no_floor = re.sub(
        r"\s+\d+\s*~\s*\d+\s*층.*$",
        "",
        no_parentheses
    )

    no_floor = re.sub(
        r"\s+\d+\s*층.*$",
        "",
        no_floor
    )

    no_floor = re.sub(
        r"\s+\d+\s*[Ff].*$",
        "",
        no_floor
    )

    no_floor = clean_text(
        no_floor
    )


    if no_floor:

        candidates.append(
            no_floor
        )


    # -----------------------------------------------------
    # 도로명 + 건물번호까지만 추출
    #
    # 예:
    # 광주 서구 무진대로 919 ...
    # →
    # 광주 서구 무진대로 919
    # -----------------------------------------------------

    road_match = re.search(
        r"(.+?(?:로|길|대로)\s+\d+(?:-\d+)?)",
        address
    )


    if road_match:

        road_address = clean_text(
            road_match.group(1)
        )

        candidates.append(
            road_address
        )


    # -----------------------------------------------------
    # 중복 제거
    # -----------------------------------------------------

    unique_candidates = []

    seen = set()


    for candidate in candidates:

        if (
            candidate
            and candidate not in seen
        ):

            seen.add(
                candidate
            )

            unique_candidates.append(
                candidate
            )


    return unique_candidates


# =========================================================
# 6. 주소검색
# =========================================================

def search_address(query):

    response = requests.get(
        ADDRESS_URL,
        headers=HEADERS,
        params={
            "query": query
        },
        timeout=15
    )

    response.raise_for_status()

    data = response.json()

    documents = data.get(
        "documents",
        []
    )


    if not documents:

        return None


    item = documents[0]


    road_address = item.get(
        "road_address"
    )

    basic_address = item.get(
        "address"
    )


    if road_address:

        matched_address = (
            road_address.get(
                "address_name",
                ""
            )
        )

    elif basic_address:

        matched_address = (
            basic_address.get(
                "address_name",
                ""
            )
        )

    else:

        matched_address = ""


    return {
        "위도":
            float(item["y"]),

        "경도":
            float(item["x"]),

        "검색주소":
            query,

        "매칭주소":
            matched_address,

        "검색방식":
            "주소검색"
    }


# =========================================================
# 7. 시설명 키워드 검색
# =========================================================

def search_keyword(
    facility_name,
    district
):

    query = clean_text(
        f"광주 {district} {facility_name}"
    )


    response = requests.get(
        KEYWORD_URL,
        headers=HEADERS,
        params={
            "query": query
        },
        timeout=15
    )

    response.raise_for_status()

    data = response.json()

    documents = data.get(
        "documents",
        []
    )


    if not documents:

        return None


    item = documents[0]


    return {
        "위도":
            float(item["y"]),

        "경도":
            float(item["x"]),

        "검색주소":
            query,

        "매칭주소":
            item.get(
                "road_address_name",
                ""
            )
            or
            item.get(
                "address_name",
                ""
            ),

        "검색방식":
            "시설명 키워드검색"
    }


# =========================================================
# 8. 실패한 시설 다시 검색
# =========================================================

def retry_geocode(row):

    facility_name = clean_text(
        row["시설명"]
    )

    address = clean_text(
        row["주소"]
    )

    district = clean_text(
        row["자치구"]
    )


    print(
        f"\n시설명 : {facility_name}"
    )

    print(
        f"원본 주소 : {address}"
    )


    # =====================================================
    # 1차: 주소 후보를 하나씩 검색
    # =====================================================

    candidates = make_address_candidates(
        address
    )


    for candidate in candidates:

        print(
            f"주소 검색 시도 → {candidate}"
        )


        try:

            result = search_address(
                candidate
            )


            if result:

                print(
                    "→ 성공"
                )

                return result


        except Exception as e:

            print(
                f"→ 오류 : {e}"
            )


        time.sleep(
            0.2
        )


    # =====================================================
    # 2차: 시설명 키워드 검색
    # =====================================================

    print(
        f"시설명 검색 시도 → "
        f"광주 {district} {facility_name}"
    )


    try:

        result = search_keyword(
            facility_name,
            district
        )


        if result:

            print(
                "→ 시설명 검색 성공"
            )

            return result


    except Exception as e:

        print(
            f"→ 오류 : {e}"
        )


    return None


# =========================================================
# 9. 메인 실행
# =========================================================

def main():

    print("\n========================================")
    print("청년 공공시설 좌표 실패건 재검색")
    print("========================================")


    if not os.path.exists(
        INPUT_FILE
    ):

        raise FileNotFoundError(
            INPUT_FILE
        )


    df = pd.read_csv(
        INPUT_FILE,
        encoding="utf-8-sig"
    )


    failed_mask = (
        df["지오코딩상태"]
        != "성공"
    )


    failed_count = (
        failed_mask.sum()
    )


    print(
        f"\n재검색 대상 : "
        f"{failed_count}개"
    )


    # =====================================================
    # 실패 건이 없을 경우
    # =====================================================

    if failed_count == 0:

        print(
            "\n실패 데이터가 없습니다."
        )

        df.to_csv(
            OUTPUT_FILE,
            index=False,
            encoding="utf-8-sig"
        )

        return


    # =====================================================
    # 실패건 재검색
    # =====================================================

    for index in df[
        failed_mask
    ].index:

        row = df.loc[
            index
        ]


        result = retry_geocode(
            row
        )


        if result:

            df.loc[
                index,
                "위도"
            ] = result[
                "위도"
            ]

            df.loc[
                index,
                "경도"
            ] = result[
                "경도"
            ]

            df.loc[
                index,
                "카카오검색주소"
            ] = result[
                "매칭주소"
            ]

            df.loc[
                index,
                "지오코딩상태"
            ] = "성공"


            # 보완 방식 기록
            df.loc[
                index,
                "좌표보완방식"
            ] = result[
                "검색방식"
            ]


            df.loc[
                index,
                "좌표보완검색어"
            ] = result[
                "검색주소"
            ]


        else:

            df.loc[
                index,
                "좌표보완방식"
            ] = "재검색실패"


        time.sleep(
            0.2
        )


    # =====================================================
    # 최종 결과
    # =====================================================

    success_count = (
        df["지오코딩상태"]
        == "성공"
    ).sum()


    fail_count = (
        df["지오코딩상태"]
        != "성공"
    ).sum()


    # =====================================================
    # 저장
    # =====================================================

    df.to_csv(
        OUTPUT_FILE,
        index=False,
        encoding="utf-8-sig"
    )


    print("\n========================================")
    print("좌표 보완 완료")
    print("========================================")


    print(
        f"\n전체 시설 : "
        f"{len(df)}개"
    )

    print(
        f"좌표 성공 : "
        f"{success_count}개"
    )

    print(
        f"좌표 실패 : "
        f"{fail_count}개"
    )


    # =====================================================
    # 아직 실패한 시설
    # =====================================================

    remaining = df[
        df["지오코딩상태"]
        != "성공"
    ]


    if len(
        remaining
    ) > 0:

        print(
            "\n[아직 좌표가 없는 시설]"
        )

        print(
            remaining[
                [
                    "시설명",
                    "주소"
                ]
            ]
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

    main()