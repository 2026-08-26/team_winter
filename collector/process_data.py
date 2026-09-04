import csv
import math
from pathlib import Path


# =========================================================
# 1. 폴더 설정
# =========================================================

BASE_DIR = Path(__file__).resolve().parent.parent

RAW_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed"

PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


# =========================================================
# 2. 사용할 파일
# =========================================================

DONG_CENTER_FILE = RAW_DIR / "25개동_대표위치.csv"

# 팀장님이 전달한 생활 인프라 집계 데이터
TEAM_INFRA_FILE = RAW_DIR / "raw_category_coords_gwangju_5districts.csv"

# 우리가 추가 수집한 2030 선호시설
YOUTH_FILE = RAW_DIR / "2030_선호시설.csv"

# 광주 BIS 버스 정류소 원본
BUS_STOP_FILE = RAW_DIR / "버스_정류소.csv"


# =========================================================
# 3. CSV 읽기
# =========================================================

def read_csv(file_path):

    if not file_path.exists():
        print(f"❌ 파일을 찾을 수 없습니다: {file_path}")
        return []

    with open(
        file_path,
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        return list(csv.DictReader(file))


# =========================================================
# 4. CSV 저장
# =========================================================

def save_csv(file_path, rows):

    if not rows:
        print(f"⚠️ 저장할 데이터가 없습니다: {file_path.name}")
        return

    with open(
        file_path,
        "w",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=rows[0].keys()
        )

        writer.writeheader()
        writer.writerows(rows)

    print(f"✅ 저장 완료: {file_path.name}")
    print(f"   → {len(rows)}개 동")


# =========================================================
# 5. 거리 계산
# =========================================================

def calculate_distance(lat1, lng1, lat2, lng2):

    earth_radius = 6371000

    lat1 = math.radians(float(lat1))
    lng1 = math.radians(float(lng1))
    lat2 = math.radians(float(lat2))
    lng2 = math.radians(float(lng2))

    d_lat = lat2 - lat1
    d_lng = lng2 - lng1

    a = (
        math.sin(d_lat / 2) ** 2
        +
        math.cos(lat1)
        * math.cos(lat2)
        * math.sin(d_lng / 2) ** 2
    )

    c = 2 * math.atan2(
        math.sqrt(a),
        math.sqrt(1 - a)
    )

    return earth_radius * c


# =========================================================
# 6. 팀장님 생활 인프라 데이터 가공
# =========================================================

def process_team_infrastructure(centers):

    print()
    print("========================================")
    print("🏪 팀장님 생활 인프라 데이터 가공")
    print("========================================")

    infra = read_csv(TEAM_INFRA_FILE)

    if not infra:
        return []

    # 팀장님 파일에 실제 존재하는 카테고리
    categories = [
        "편의점",
        "카페",
        "음식점",
        "병원",
        "대형마트",
        "지하철역",
        "문화시설",
        "학원",
        "버스정류장",
        "올리브영",
        "다이소",
        "코인노래방",
        "PC방",
        "백화점",
        "유니클로",
        "탑텐"
    ]

    result = []

    for center in centers:

        gu = center["gu_name"]
        dong = center["dong_name"]

        row = {
            "자치구": gu,
            "행정동": dong
        }

        for category in categories:

            matched = [
                item
                for item in infra
                if item["gu_name"] == gu
                and item["dong_name"] == dong
                and item["category_name"] == category
            ]

            if matched:

                item = matched[0]

                try:
                    count = int(float(item["place_count"]))
                except (ValueError, TypeError):
                    count = 0

                try:
                    distance = round(
                        float(item["min_distance_m"]),
                        1
                    )
                except (ValueError, TypeError):
                    distance = ""

            else:
                count = 0
                distance = ""

            row[f"{category}_개수"] = count
            row[f"{category}_최소거리_m"] = distance

        result.append(row)

    save_csv(
        PROCESSED_DIR / "동별_생활인프라_상세.csv",
        result
    )

    return result


# =========================================================
# 7. 우리가 수집한 2030 추가시설 가공
# =========================================================

def process_youth_places(centers):

    print()
    print("========================================")
    print("🛍️ 2030 추가 선호시설 가공")
    print("========================================")

    places = read_csv(YOUTH_FILE)

    if not places:
        return []

    categories = [
        "H&B/뷰티",
        "생활쇼핑",
        "SPA패션",
        "영화/문화",
        "대형쇼핑",
        "운동",
        "문화생활",
        "패스트푸드"
    ]

    result = []

    for center in centers:

        gu = center["gu_name"]
        dong = center["dong_name"]

        dong_places = [
            place
            for place in places
            if place["gu_name"] == gu
            and place["dong_name"] == dong
        ]

        # 같은 시설이 여러 검색어에 걸린 경우 중복 제거
        unique_places = {}

        for place in dong_places:

            key = (
                place["place_id"],
                place["analysis_category"]
            )

            if key not in unique_places:
                unique_places[key] = place

        row = {
            "자치구": gu,
            "행정동": dong
        }

        for category in categories:

            category_places = [
                place
                for place in unique_places.values()
                if place["analysis_category"] == category
            ]

            row[f"{category}_개수"] = len(category_places)

            # 해당 카테고리 중 가장 가까운 시설 거리
            distances = []

            for place in category_places:

                try:
                    distances.append(
                        float(place["distance_m"])
                    )
                except (ValueError, TypeError):
                    pass

            if distances:
                row[f"{category}_최소거리_m"] = round(
                    min(distances),
                    1
                )
            else:
                row[f"{category}_최소거리_m"] = ""

        result.append(row)

    save_csv(
        PROCESSED_DIR / "동별_2030추가시설.csv",
        result
    )

    return result


# =========================================================
# 8. BIS 버스 정류소 접근성
# =========================================================

def process_bus_stops(centers):

    print()
    print("========================================")
    print("🚏 BIS 버스 정류소 접근성 계산")
    print("========================================")

    bus_stops = read_csv(BUS_STOP_FILE)

    if not bus_stops:
        return []

    result = []

    for index, center in enumerate(centers, start=1):

        gu = center["gu_name"]
        dong = center["dong_name"]

        center_lat = center["center_lat"]
        center_lng = center["center_lng"]

        nearby_stops = {}

        minimum_distance = None

        for stop in bus_stops:

            try:

                distance = calculate_distance(
                    center_lat,
                    center_lng,
                    stop["LATITUDE"],
                    stop["LONGITUDE"]
                )

            except (ValueError, TypeError, KeyError):
                continue

            # 가장 가까운 정류소 거리
            if minimum_distance is None:
                minimum_distance = distance

            elif distance < minimum_distance:
                minimum_distance = distance

            # 반경 1.5km 정류소
            if distance <= 1500:

                stop_id = stop["BUSSTOP_ID"]

                if stop_id not in nearby_stops:
                    nearby_stops[stop_id] = stop

        row = {
            "자치구": gu,
            "행정동": dong,
            "버스정류소_1500m_개수": len(nearby_stops),
            "가장가까운_버스정류소_m": (
                round(minimum_distance, 1)
                if minimum_distance is not None
                else ""
            )
        }

        result.append(row)

        print(
            f"[{index}/{len(centers)}] "
            f"{gu} {dong} "
            f"→ {len(nearby_stops)}개"
        )

    save_csv(
        PROCESSED_DIR / "동별_교통접근성.csv",
        result
    )

    return result


# =========================================================
# 9. 세 데이터를 하나로 병합
# =========================================================

def merge_infrastructure(
    centers,
    team_rows,
    youth_rows,
    bus_rows
):

    print()
    print("========================================")
    print("🔗 인프라 데이터 병합")
    print("========================================")

    result = []

    for center in centers:

        gu = center["gu_name"]
        dong = center["dong_name"]

        final_row = {
            "자치구": gu,
            "행정동": dong
        }

        # -----------------------------
        # 팀장님 생활 인프라
        # -----------------------------

        team = next(
            (
                row
                for row in team_rows
                if row["자치구"] == gu
                and row["행정동"] == dong
            ),
            None
        )

        if team:

            for key, value in team.items():

                if key not in ["자치구", "행정동"]:
                    final_row[key] = value

        # -----------------------------
        # 2030 추가시설
        # -----------------------------

        youth = next(
            (
                row
                for row in youth_rows
                if row["자치구"] == gu
                and row["행정동"] == dong
            ),
            None
        )

        if youth:

            for key, value in youth.items():

                if key not in ["자치구", "행정동"]:
                    final_row[f"추가_{key}"] = value

        # -----------------------------
        # BIS 버스
        # -----------------------------

        bus = next(
            (
                row
                for row in bus_rows
                if row["자치구"] == gu
                and row["행정동"] == dong
            ),
            None
        )

        if bus:

            for key, value in bus.items():

                if key not in ["자치구", "행정동"]:
                    final_row[key] = value

        result.append(final_row)

    save_csv(
        PROCESSED_DIR / "동별_통합인프라.csv",
        result
    )

    return result


# =========================================================
# 10. 실행
# =========================================================

if __name__ == "__main__":

    print()
    print("========================================")
    print("📊 25개 동 통합 인프라 가공 시작")
    print("========================================")

    centers = read_csv(DONG_CENTER_FILE)

    if not centers:
        print("❌ 25개 동 대표위치 데이터를 읽지 못했습니다.")
        exit()

    print(f"분석 대상: {len(centers)}개 동")

    team_rows = process_team_infrastructure(centers)

    youth_rows = process_youth_places(centers)

    bus_rows = process_bus_stops(centers)

    final_rows = merge_infrastructure(
        centers,
        team_rows,
        youth_rows,
        bus_rows
    )

    print()
    print("========================================")
    print("🎉 통합 인프라 데이터 가공 완료")
    print("========================================")

    print()
    print("생성 파일:")
    print("1. 동별_생활인프라_상세.csv")
    print("2. 동별_2030추가시설.csv")
    print("3. 동별_교통접근성.csv")
    print("4. 동별_통합인프라.csv")

    print()
    print(f"최종 분석 대상: {len(final_rows)}개 동")