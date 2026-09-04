import os
import csv
import time
import requests

from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv


# =========================================================
# 1. 기본 경로 / API KEY 설정
# =========================================================

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"

RAW_DIR.mkdir(parents=True, exist_ok=True)

load_dotenv(BASE_DIR / ".env")

KAKAO_API_KEY = os.getenv("KAKAO_REST_API_KEY")

if not KAKAO_API_KEY:
    raise ValueError("❌ .env에서 KAKAO_REST_API_KEY를 찾지 못했습니다.")


HEADERS = {
    "Authorization": f"KakaoAK {KAKAO_API_KEY}"
}


# =========================================================
# 2. 카카오 API 주소
# =========================================================

KEYWORD_URL = "https://dapi.kakao.com/v2/local/search/keyword.json"

CATEGORY_URL = "https://dapi.kakao.com/v2/local/search/category.json"


# =========================================================
# 3. 프로젝트 대상 25개 동
# =========================================================
#
# gu_name
#   → 우리 프로젝트에서 사용하는 구 이름
#
# search_gu_name
#   → 카카오에서 행정복지센터를 검색할 때 사용하는 구 이름
#
# ※ 첨단2동은 실제 검색 시 광산구로 검색하도록 별도 처리
# =========================================================

DONGS = [

    # -------------------------
    # 동구
    # -------------------------
    {
        "gu_name": "동구",
        "dong_name": "충장동",
        "search_gu_name": "동구"
    },
    {
        "gu_name": "동구",
        "dong_name": "계림1동",
        "search_gu_name": "동구"
    },
    {
        "gu_name": "동구",
        "dong_name": "지산2동",
        "search_gu_name": "동구"
    },
    {
        "gu_name": "동구",
        "dong_name": "학동",
        "search_gu_name": "동구"
    },
    {
        "gu_name": "동구",
        "dong_name": "지원1동",
        "search_gu_name": "동구"
    },


    # -------------------------
    # 서구
    # -------------------------
    {
        "gu_name": "서구",
        "dong_name": "치평동",
        "search_gu_name": "서구"
    },
    {
        "gu_name": "서구",
        "dong_name": "풍암동",
        "search_gu_name": "서구"
    },
    {
        "gu_name": "서구",
        "dong_name": "화정2동",
        "search_gu_name": "서구"
    },
    {
        "gu_name": "서구",
        "dong_name": "농성1동",
        "search_gu_name": "서구"
    },
    {
        "gu_name": "서구",
        "dong_name": "금호1동",
        "search_gu_name": "서구"
    },


    # -------------------------
    # 남구
    # -------------------------
    {
        "gu_name": "남구",
        "dong_name": "봉선2동",
        "search_gu_name": "남구"
    },
    {
        "gu_name": "남구",
        "dong_name": "진월동",
        "search_gu_name": "남구"
    },
    {
        "gu_name": "남구",
        "dong_name": "방림1동",
        "search_gu_name": "남구"
    },
    {
        "gu_name": "남구",
        "dong_name": "효덕동",
        "search_gu_name": "남구"
    },
    {
        "gu_name": "남구",
        "dong_name": "송암동",
        "search_gu_name": "남구"
    },


    # -------------------------
    # 북구
    # -------------------------
    {
        "gu_name": "북구",
        "dong_name": "용봉동",
        "search_gu_name": "북구"
    },
    {
        "gu_name": "북구",
        "dong_name": "두암2동",
        "search_gu_name": "북구"
    },
    {
        "gu_name": "북구",
        "dong_name": "운암1동",
        "search_gu_name": "북구"
    },

    # 프로젝트 계획상 북구 첨단2동으로 되어 있지만
    # 실제 행정복지센터 검색은 광산구로 수행
    {
        "gu_name": "북구",
        "dong_name": "첨단2동",
        "search_gu_name": "광산구"
    },

    {
        "gu_name": "북구",
        "dong_name": "문흥1동",
        "search_gu_name": "북구"
    },


    # -------------------------
    # 광산구
    # -------------------------
    {
        "gu_name": "광산구",
        "dong_name": "첨단1동",
        "search_gu_name": "광산구"
    },
    {
        "gu_name": "광산구",
        "dong_name": "수완동",
        "search_gu_name": "광산구"
    },
    {
        "gu_name": "광산구",
        "dong_name": "신가동",
        "search_gu_name": "광산구"
    },
    {
        "gu_name": "광산구",
        "dong_name": "우산동",
        "search_gu_name": "광산구"
    },
    {
        "gu_name": "광산구",
        "dong_name": "송정1동",
        "search_gu_name": "광산구"
    }
]


# =========================================================
# 4. 수집할 생활 인프라 카테고리
# =========================================================

CATEGORIES = {
    "MT1": "대형마트",
    "CS2": "편의점",
    "FD6": "음식점",
    "CE7": "카페",
    "HP8": "병원",
    "PM9": "약국",
    "SW8": "지하철역",
    "CT1": "문화시설"
}


# 검색 반경
RADIUS = 1500


# =========================================================
# 5. 행정복지센터 좌표 검색
# =========================================================

def get_dong_center(dong):

    query = (
        f"광주광역시 "
        f"{dong['search_gu_name']} "
        f"{dong['dong_name']} "
        f"행정복지센터"
    )

    params = {
        "query": query,
        "size": 5
    }

    try:

        response = requests.get(
            KEYWORD_URL,
            headers=HEADERS,
            params=params,
            timeout=10
        )

        if response.status_code != 200:
            print()
            print(f"❌ {dong['dong_name']} 좌표 검색 실패")
            print("상태 코드 :", response.status_code)
            print("응답 :", response.text)

            return None

        data = response.json()

        if not data["documents"]:
            print()
            print(f"❌ {dong['dong_name']} 행정복지센터 검색 결과 없음")

            return None


        # 가장 첫 번째 검색 결과 사용
        place = data["documents"][0]


        center = {

            "gu_name": dong["gu_name"],

            "search_gu_name": dong["search_gu_name"],

            "dong_name": dong["dong_name"],

            "center_name": place["place_name"],

            "center_address": place["address_name"],

            "center_road_address": place["road_address_name"],

            "center_lat": place["y"],

            "center_lng": place["x"]
        }

        return center


    except requests.RequestException as e:

        print()
        print(f"❌ {dong['dong_name']} 좌표 검색 중 오류")
        print(e)

        return None


# =========================================================
# 6. 카테고리별 장소 검색
# =========================================================

def collect_places(center, category_code, category_name):

    all_places = []

    params = {

        "category_group_code": category_code,

        # x = 경도
        "x": center["center_lng"],

        # y = 위도
        "y": center["center_lat"],

        # 반경 1500m
        "radius": RADIUS,

        # 가까운 순서
        "sort": "distance",

        # 한 페이지 최대 15개
        "size": 15
    }


    # 중복 제거용
    seen_place_ids = set()


    for page in range(1, 46):

        params["page"] = page

        try:

            response = requests.get(
                CATEGORY_URL,
                headers=HEADERS,
                params=params,
                timeout=10
            )


            if response.status_code != 200:

                print()
                print(
                    f"❌ {center['dong_name']} "
                    f"{category_name} 수집 실패"
                )

                print("상태 코드 :", response.status_code)
                print("응답 :", response.text)

                break


            data = response.json()


            for place in data["documents"]:

                place_id = place["id"]


                # 같은 장소 중복 저장 방지
                if place_id in seen_place_ids:
                    continue


                seen_place_ids.add(place_id)


                row = {

                    "gu_name":
                        center["gu_name"],

                    "search_gu_name":
                        center["search_gu_name"],

                    "dong_name":
                        center["dong_name"],

                    "center_name":
                        center["center_name"],

                    "center_lat":
                        center["center_lat"],

                    "center_lng":
                        center["center_lng"],

                    "radius_m":
                        RADIUS,

                    "category_code":
                        category_code,

                    "category_name":
                        category_name,

                    "place_id":
                        place["id"],

                    "place_name":
                        place["place_name"],

                    "address_name":
                        place["address_name"],

                    "road_address_name":
                        place["road_address_name"],

                    "place_lat":
                        place["y"],

                    "place_lng":
                        place["x"],

                    "distance_m":
                        place["distance"],

                    "place_url":
                        place["place_url"],

                    "collected_at":
                        datetime.now().strftime(
                            "%Y-%m-%d %H:%M:%S"
                        )
                }


                all_places.append(row)


            # 마지막 페이지라면 반복 종료
            if data["meta"]["is_end"]:
                break


            # API에 너무 빠르게 요청하지 않도록
            time.sleep(0.05)


        except requests.RequestException as e:

            print()
            print(
                f"❌ {center['dong_name']} "
                f"{category_name} 요청 오류"
            )

            print(e)

            break


    return all_places


# =========================================================
# 7. 동 중심점 CSV 저장
# =========================================================

def save_centers_csv(centers):

    output_file = RAW_DIR / "25개동_대표위치.csv"


    columns = [

        "gu_name",
        "search_gu_name",
        "dong_name",

        "center_name",
        "center_address",
        "center_road_address",

        "center_lat",
        "center_lng"
    ]


    with open(
        output_file,
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=columns
        )

        writer.writeheader()
        writer.writerows(centers)


    print()
    print("✅ 동 중심점 CSV 저장 완료")
    print("   →", output_file)


# =========================================================
# 8. 생활 인프라 CSV 저장
# =========================================================

def save_places_csv(rows):

    output_file = RAW_DIR / "기본_생활인프라.csv"


    columns = [

        "gu_name",
        "search_gu_name",
        "dong_name",

        "center_name",

        "center_lat",
        "center_lng",

        "radius_m",

        "category_code",
        "category_name",

        "place_id",
        "place_name",

        "address_name",
        "road_address_name",

        "place_lat",
        "place_lng",

        "distance_m",

        "place_url",

        "collected_at"
    ]


    with open(
        output_file,
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=columns
        )

        writer.writeheader()
        writer.writerows(rows)


    print()
    print("========================================")
    print("✅ 생활 인프라 CSV 저장 완료!")
    print("========================================")

    print("저장 위치 :", output_file)

    print("총 데이터 :", len(rows), "건")


# =========================================================
# 9. 프로그램 실행
# =========================================================

if __name__ == "__main__":


    print()
    print("========================================")
    print("광주 25개 동 생활 인프라 데이터 수집")
    print("========================================")
    print()


    centers = []

    all_places = []


    # -----------------------------------------------------
    # 25개 동 반복
    # -----------------------------------------------------

    for index, dong in enumerate(DONGS, start=1):


        print()
        print("========================================")

        print(
            f"[{index}/{len(DONGS)}] "
            f"{dong['gu_name']} "
            f"{dong['dong_name']}"
        )

        print("========================================")


        # ---------------------------------------------
        # 1. 행정복지센터 좌표 찾기
        # ---------------------------------------------

        print("▶ 행정복지센터 좌표 검색 중...")


        center = get_dong_center(dong)


        if center is None:

            print(
                f"⚠️ {dong['dong_name']}은 "
                f"좌표를 찾지 못해서 건너뜁니다."
            )

            continue


        centers.append(center)


        print(
            f"   ✅ {center['center_name']}"
        )

        print(
            f"   위도 : {center['center_lat']}"
        )

        print(
            f"   경도 : {center['center_lng']}"
        )


        # ---------------------------------------------
        # 2. 생활 인프라 수집
        # ---------------------------------------------

        for code, name in CATEGORIES.items():


            print(
                f"▶ {name} 수집 중..."
            )


            places = collect_places(
                center,
                code,
                name
            )


            print(
                f"   → {len(places)}건"
            )


            all_places.extend(places)


            # 동별 / 카테고리별 요청 사이 잠깐 쉬기
            time.sleep(0.1)


    # -----------------------------------------------------
    # CSV 저장
    # -----------------------------------------------------

    save_centers_csv(centers)

    save_places_csv(all_places)


    print()
    print("========================================")
    print("🎉 전체 수집 작업 완료!")
    print("========================================")

    print()
    print(
        "정상적으로 좌표를 찾은 동 :",
        len(centers),
        "개"
    )

    print(
        "전체 생활 인프라 데이터 :",
        len(all_places),
        "건"
    )