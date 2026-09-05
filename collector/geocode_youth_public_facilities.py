import os
import re
import time

import pandas as pd
import requests
from dotenv import load_dotenv


# =========================================================
# 1. 기본 경로
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
    "청년_공공시설.csv"
)

OUTPUT_FILE = os.path.join(
    BASE_DIR,
    "data",
    "raw",
    "청년_공공시설_좌표.csv"
)


# =========================================================
# 2. 환경변수 불러오기
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
# 3. 카카오 주소검색 API
# =========================================================

KAKAO_ADDRESS_URL = (
    "https://dapi.kakao.com/"
    "v2/local/search/address.json"
)

HEADERS = {
    "Authorization":
        f"KakaoAK {KAKAO_REST_API_KEY}"
}


# =========================================================
# 4. 주소 정리
# =========================================================

def clean_address(address):

    if pd.isna(address):
        return ""

    address = str(address).strip()

    # 여러 공백 정리
    address = re.sub(
        r"\s+",
        " ",
        address
    )

    return address


# =========================================================
# 5. 괄호 내용 제거한 보조 주소
# =========================================================

def remove_parentheses(address):

    cleaned = re.sub(
        r"\([^)]*\)",
        "",
        address
    )

    cleaned = re.sub(
        r"\s+",
        " ",
        cleaned
    ).strip()

    return cleaned


# =========================================================
# 6. 주소 → 좌표
# =========================================================

def geocode_address(address):

    address = clean_address(
        address
    )


    if not address:

        return {
            "위도": None,
            "경도": None,
            "카카오검색주소": "",
            "지오코딩상태": "주소없음"
        }


    # -----------------------------------------------------
    # 1차: 원본 주소 그대로 검색
    # -----------------------------------------------------

    search_addresses = [
        address
    ]


    # -----------------------------------------------------
    # 2차: 괄호 제거 주소
    # -----------------------------------------------------

    simplified = remove_parentheses(
        address
    )


    if (
        simplified
        and simplified != address
    ):

        search_addresses.append(
            simplified
        )


    # -----------------------------------------------------
    # 검색 실행
    # -----------------------------------------------------

    for search_address in search_addresses:

        try:

            response = requests.get(
                KAKAO_ADDRESS_URL,
                headers=HEADERS,
                params={
                    "query":
                        search_address
                },
                timeout=15
            )


            response.raise_for_status()


            data = response.json()


            documents = data.get(
                "documents",
                []
            )


            if documents:

                result = documents[0]


                # 도로명 주소 우선
                road_address = result.get(
                    "road_address"
                )

                basic_address = result.get(
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

                    matched_address = (
                        result.get(
                            "address_name",
                            ""
                        )
                    )


                return {
                    "위도":
                        float(
                            result["y"]
                        ),

                    "경도":
                        float(
                            result["x"]
                        ),

                    "카카오검색주소":
                        matched_address,

                    "지오코딩상태":
                        "성공"
                }


        except Exception as e:

            print(
                f"[주소 검색 오류] "
                f"{search_address}"
            )

            print(e)


        time.sleep(
            0.15
        )


    # =====================================================
    # 검색 결과 없음
    # =====================================================

    return {
        "위도": None,
        "경도": None,
        "카카오검색주소": "",
        "지오코딩상태": "검색결과없음"
    }


# =========================================================
# 7. 전체 시설 좌표 변환
# =========================================================

def main():

    print("\n========================================")
    print("청년 공공시설 주소 → 좌표 변환 시작")
    print("========================================")


    if not os.path.exists(
        INPUT_FILE
    ):

        raise FileNotFoundError(
            f"입력 파일이 없습니다.\n{INPUT_FILE}"
        )


    df = pd.read_csv(
        INPUT_FILE,
        encoding="utf-8-sig"
    )


    print(
        f"\n전체 시설 수 : {len(df)}개"
    )


    # =====================================================
    # 결과 저장용 리스트
    # =====================================================

    latitudes = []
    longitudes = []
    matched_addresses = []
    statuses = []


    # =====================================================
    # 시설별 좌표 검색
    # =====================================================

    for index, row in df.iterrows():

        facility_name = str(
            row["시설명"]
        ).strip()

        address = row[
            "주소"
        ]


        print(
            f"\n[{index + 1}/{len(df)}] "
            f"{facility_name}"
        )

        print(
            f"주소 : {address}"
        )


        result = geocode_address(
            address
        )


        latitudes.append(
            result["위도"]
        )

        longitudes.append(
            result["경도"]
        )

        matched_addresses.append(
            result["카카오검색주소"]
        )

        statuses.append(
            result["지오코딩상태"]
        )


        if result[
            "지오코딩상태"
        ] == "성공":

            print(
                "→ 좌표 변환 성공"
            )

        else:

            print(
                "→ 좌표 변환 실패"
            )


        # 너무 빠른 호출 방지
        time.sleep(
            0.15
        )


    # =====================================================
    # 8. 컬럼 추가
    # =====================================================

    df["위도"] = latitudes
    df["경도"] = longitudes

    df[
        "카카오검색주소"
    ] = matched_addresses

    df[
        "지오코딩상태"
    ] = statuses


    # =====================================================
    # 9. 저장
    # =====================================================

    df.to_csv(
        OUTPUT_FILE,
        index=False,
        encoding="utf-8-sig"
    )


    # =====================================================
    # 10. 결과 검증
    # =====================================================

    success_count = (
        df["지오코딩상태"]
        == "성공"
    ).sum()


    fail_count = (
        df["지오코딩상태"]
        != "성공"
    ).sum()


    print("\n========================================")
    print("좌표 변환 완료")
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
    # 실패 시설 확인
    # =====================================================

    failed_df = df[
        df["지오코딩상태"]
        != "성공"
    ]


    if len(
        failed_df
    ) > 0:

        print(
            "\n[좌표 변환 실패 시설]"
        )


        print(
            failed_df[
                [
                    "시설명",
                    "주소",
                    "지오코딩상태"
                ]
            ]
            .to_string(
                index=False
            )
        )


    # =====================================================
    # 자치구별 좌표 성공 수
    # =====================================================

    print(
        "\n[자치구별 좌표 확보 시설 수]"
    )


    success_df = df[
        df["지오코딩상태"]
        == "성공"
    ]


    print(
        success_df[
            "자치구"
        ]
        .value_counts()
        .to_string()
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