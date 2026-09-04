import os
import csv
import requests

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
# 2. 광주 BIS API 주소
# =========================================================

BASE_URL = "https://apis.data.go.kr/6290000/gj_bis"

STATION_URL = f"{BASE_URL}/stationInfo"
LINE_URL = f"{BASE_URL}/lineInfo"


# =========================================================
# 3. 공통 API 호출
# =========================================================

def request_api(url):

    if not SERVICE_KEY:
        print("❌ 공공데이터포털 API 키를 찾지 못했습니다.")
        return None

    request_url = f"{url}?serviceKey={SERVICE_KEY}"

    params = {
        "resultType": "json"
    }

    try:
        response = requests.get(
            request_url,
            params=params,
            timeout=30
        )

    except requests.RequestException as e:
        print("❌ API 요청 오류 :", e)
        return None

    print("상태 코드 :", response.status_code)

    if response.status_code != 200:
        print("❌ API 요청 실패")
        print(response.text[:1000])
        return None

    try:
        return response.json()

    except ValueError:
        print("❌ JSON 변환 실패")
        print(response.text[:1000])
        return None


# =========================================================
# 4. JSON 내부 리스트 자동 탐색
# =========================================================

def find_list(data):

    if isinstance(data, list):
        return data

    if isinstance(data, dict):

        for value in data.values():

            result = find_list(value)

            if result:
                return result

    return []


# =========================================================
# 5. 정류소 정보 수집
# =========================================================

def collect_stations():

    print()
    print("========================================")
    print("광주 버스 정류소 정보 수집")
    print("========================================")

    data = request_api(STATION_URL)

    if data is None:
        return []

    rows = find_list(data)

    print("✅ 정류소 수집 :", len(rows), "건")

    return rows


# =========================================================
# 6. 노선 정보 수집
# =========================================================

def collect_lines():

    print()
    print("========================================")
    print("광주 버스 노선 정보 수집")
    print("========================================")

    data = request_api(LINE_URL)

    if data is None:
        return []

    rows = find_list(data)

    print("✅ 노선 수집 :", len(rows), "건")

    return rows


# =========================================================
# 7. CSV 저장
# =========================================================

def save_csv(rows, filename):

    if not rows:
        print(f"⚠️ {filename} 저장할 데이터가 없습니다.")
        return

    output_file = RAW_DIR / filename

    columns = []

    for row in rows:

        if isinstance(row, dict):

            for key in row.keys():

                if key not in columns:
                    columns.append(key)

    if not columns:
        print(f"⚠️ {filename} 열 정보를 찾지 못했습니다.")
        return

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

    print("💾 저장 완료 :", output_file)
    print("   →", len(rows), "건")


# =========================================================
# 8. 실행
# =========================================================

if __name__ == "__main__":

    print()
    print("========================================")
    print("광주 버스 데이터 수집 시작")
    print("========================================")

    stations = collect_stations()

    save_csv(
        stations,
        "버스_정류소.csv"
    )

    lines = collect_lines()

    save_csv(
        lines,
        "버스_노선.csv"
    )

    print()
    print("========================================")
    print("🎉 광주 버스 데이터 수집 완료")
    print("========================================")

    print("정류소 :", len(stations), "건")
    print("노선 :", len(lines), "건")