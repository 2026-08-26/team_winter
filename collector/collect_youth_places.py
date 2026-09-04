import os
import csv
import time
import requests

from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv


# =========================================================
# 1. 기본 설정
# =========================================================

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"

RAW_DIR.mkdir(parents=True, exist_ok=True)

load_dotenv(BASE_DIR / ".env")

KAKAO_API_KEY = os.getenv("KAKAO_REST_API_KEY")

HEADERS = {
    "Authorization": f"KakaoAK {KAKAO_API_KEY}"
}

KEYWORD_URL = "https://dapi.kakao.com/v2/local/search/keyword.json"

RADIUS = 1500


# =========================================================
# 2. 2030 선호시설 검색어
# =========================================================

KEYWORDS = {

    # 뷰티 / H&B
    "올리브영": "H&B/뷰티",

    # 생활 쇼핑
    "다이소": "생활쇼핑",

    # SPA 패션
    "유니클로": "SPA패션",
    "스파오": "SPA패션",
    "탑텐": "SPA패션",

    # 영화관
    "CGV": "영화/문화",
    "메가박스": "영화/문화",
    "롯데시네마": "영화/문화",

    # 쇼핑시설
    "백화점": "대형쇼핑",
    "쇼핑몰": "대형쇼핑",
    "아울렛": "대형쇼핑",

    # 운동
    "헬스장": "운동",
    "피트니스": "운동",
    "필라테스": "운동",
    "요가": "운동",

    # 문화생활
    "서점": "문화생활",

    # 패스트푸드
    "맥도날드": "패스트푸드",
    "버거킹": "패스트푸드",
    "롯데리아": "패스트푸드"
}


# =========================================================
# 3. 기존 25개 동 중심점 CSV 불러오기
# =========================================================

def load_dong_centers():

    center_file = RAW_DIR / "25개동_대표위치.csv"

    if not center_file.exists():
        print("❌ 25개동_대표위치.csv 파일을 찾지 못했습니다.")
        return []

    centers = []

    with open(
        center_file,
        "r",
        encoding="utf-8-sig"
    ) as file:

        reader = csv.DictReader(file)

        for row in reader:
            centers.append(row)

    return centers


# =========================================================
# 4. 키워드 검색
# =========================================================

def search_keyword(center, keyword, analysis_category):

    rows = []

    params = {
        "query": keyword,
        "x": center["center_lng"],
        "y": center["center_lat"],
        "radius": RADIUS,
        "sort": "distance",
        "size": 15
    }

    seen_place_ids = set()

    for page in range(1, 46):

        params["page"] = page

        try:

            response = requests.get(
                KEYWORD_URL,
                headers=HEADERS,
                params=params,
                timeout=10
            )

        except requests.RequestException as e:

            print("❌ 요청 오류 :", e)
            break


        if response.status_code != 200:

            print(
                f"❌ {center['dong_name']} / {keyword} 검색 실패"
            )

            print("상태 코드 :", response.status_code)
            print(response.text[:500])

            break


        data = response.json()


        for place in data["documents"]:

            place_id = place["id"]

            if place_id in seen_place_ids:
                continue

            seen_place_ids.add(place_id)


            row = {
                "gu_name": center["gu_name"],
                "dong_name": center["dong_name"],

                "center_name": center["center_name"],
                "center_lat": center["center_lat"],
                "center_lng": center["center_lng"],

                "radius_m": RADIUS,

                "search_keyword": keyword,
                "analysis_category": analysis_category,

                "place_id": place["id"],
                "place_name": place["place_name"],

                "category_name_raw": place["category_name"],

                "address_name": place["address_name"],
                "road_address_name": place["road_address_name"],

                "place_lat": place["y"],
                "place_lng": place["x"],

                "distance_m": place["distance"],
                "place_url": place["place_url"],

                "collected_at": datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
            }

            rows.append(row)


        if data["meta"]["is_end"]:
            break


        time.sleep(0.05)


    return rows


# =========================================================
# 5. CSV 저장
# =========================================================

def save_csv(rows):

    output_file = RAW_DIR / "2030_선호시설.csv"

    if not rows:
        print("⚠️ 저장할 데이터가 없습니다.")
        return


    columns = [
        "gu_name",
        "dong_name",
        "center_name",
        "center_lat",
        "center_lng",
        "radius_m",
        "search_keyword",
        "analysis_category",
        "place_id",
        "place_name",
        "category_name_raw",
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
    print("✅ 2030 선호시설 CSV 저장 완료")
    print("========================================")
    print("저장 위치 :", output_file)
    print("총 데이터 :", len(rows), "건")


# =========================================================
# 6. 실행
# =========================================================

if __name__ == "__main__":

    if not KAKAO_API_KEY:
        print("❌ 카카오 API 키를 찾지 못했습니다.")
        exit()


    centers = load_dong_centers()

    if not centers:
        exit()


    print()
    print("========================================")
    print("2030 선호시설 데이터 수집 시작")
    print("========================================")

    all_rows = []


    for index, center in enumerate(centers, start=1):

        print()
        print(
            f"[{index}/{len(centers)}] "
            f"{center['gu_name']} {center['dong_name']}"
        )


        for keyword, category in KEYWORDS.items():

            print(
                f"▶ {keyword} 검색 중..."
            )


            rows = search_keyword(
                center,
                keyword,
                category
            )


            print(
                f"   → {len(rows)}건"
            )


            all_rows.extend(rows)


            time.sleep(0.1)


    # 전체 중복 제거
    unique_rows = {}

    for row in all_rows:

        key = (
            row["dong_name"],
            row["place_id"],
            row["analysis_category"]
        )

        if key not in unique_rows:
            unique_rows[key] = row


    final_rows = list(unique_rows.values())


    save_csv(final_rows)


    print()
    print("========================================")
    print("🎉 전체 수집 완료")
    print("========================================")

    print("수집 동 :", len(centers), "개")
    print("최종 시설 데이터 :", len(final_rows), "건")