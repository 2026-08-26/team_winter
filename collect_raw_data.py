import requests
import pandas as pd
from datetime import datetime

# 발급받으신 카카오 REST API 키
KAKAO_REST_API_KEY = "44801000df6feb1adfcd7f899b06f271"

# 광주 5개 구별 대표 동 중심 좌표 (위도: lat, 경도: lng)
TARGET_DONGS = [
    # 동구
    {"gu": "동구", "dong": "충장동", "lat": 35.1478, "lng": 126.9171},
    {"gu": "동구", "dong": "계림1동", "lat": 35.1565, "lng": 126.9192},
    {"gu": "동구", "dong": "지산2동", "lat": 35.1431, "lng": 126.9315},
    {"gu": "동구", "dong": "학동", "lat": 35.1382, "lng": 126.9248},
    {"gu": "동구", "dong": "지원1동", "lat": 35.1278, "lng": 126.9295},
    
    # 서구
    {"gu": "서구", "dong": "치평동", "lat": 35.1532, "lng": 126.8521},
    {"gu": "서구", "dong": "풍암동", "lat": 35.1275, "lng": 126.8773},
    {"gu": "서구", "dong": "화정2동", "lat": 35.1485, "lng": 126.8812},
    {"gu": "서구", "dong": "농성1동", "lat": 35.1558, "lng": 126.8856},
    {"gu": "서구", "dong": "금호1동", "lat": 35.1381, "lng": 126.8584},

    # 남구
    {"gu": "남구", "dong": "봉선2동", "lat": 35.1261, "lng": 126.9070},
    {"gu": "남구", "dong": "진월동", "lat": 35.1189, "lng": 126.8968},
    {"gu": "남구", "dong": "방림1동", "lat": 35.1352, "lng": 126.9112},
    {"gu": "남구", "dong": "효덕동", "lat": 35.1118, "lng": 126.8891},
    {"gu": "남구", "dong": "송암동", "lat": 35.1012, "lng": 126.8745},

    # 북구
    {"gu": "북구", "dong": "용봉동", "lat": 35.1782, "lng": 126.9085},
    {"gu": "북구", "dong": "두암2동", "lat": 35.1652, "lng": 126.9320},
    {"gu": "북구", "dong": "운암1동", "lat": 35.1765, "lng": 126.8821},
    {"gu": "북구", "dong": "첨단2동", "lat": 35.2162, "lng": 126.8532},
    {"gu": "북구", "dong": "문흥1동", "lat": 35.1882, "lng": 126.9231},

    # 광산구
    {"gu": "광산구", "dong": "첨단1동", "lat": 35.2175, "lng": 126.8431},
    {"gu": "광산구", "dong": "수완동", "lat": 35.1912, "lng": 126.8228},
    {"gu": "광산구", "dong": "신가동", "lat": 35.1821, "lng": 126.8142},
    {"gu": "광산구", "dong": "우산동", "lat": 35.1598, "lng": 126.8095},
    {"gu": "광산구", "dong": "송정1동", "lat": 35.1382, "lng": 126.7932}
]

# 1. 카테고리 코드로 수집할 항목들
CATEGORY_CODES = {
    "편의점": "CS2",
    "카페": "CE7",
    "음식점": "FD6",
    "병원": "HP8",
    "대형마트": "MT1",
    "지하철역": "SW8",
    "문화시설": "CT1",
    "학원": "AC5"
}

# 2. 키워드 검색으로 수집할 2030 라이프스타일 항목들
KEYWORD_TARGETS = [
    "버스정류장",
    "올리브영",
    "다이소",
    "코인노래방",
    "PC방",
    "백화점",
    "유니클로",
    "탑텐"
]

def fetch_kakao_api(url, params):
    """카카오 API 공통 요청 함수"""
    headers = {"Authorization": f"KakaoAK {KAKAO_REST_API_KEY}"}
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        data = response.json()
        total_count = data['meta']['total_count']
        documents = data['documents']
        min_distance = float(documents[0]['distance']) if documents else None
        return total_count, min_distance
    else:
        print(f"API 요청 실패 (코드 {response.status_code}): {response.text}")
        return 0, None

def fetch_category_data(lat, lng, category_code):
    """카테고리 코드로 수집"""
    url = "https://dapi.kakao.com/v2/local/search/category.json"
    params = {
        "category_group_code": category_code,
        "x": str(lng),
        "y": str(lat),
        "radius": 1000,
        "sort": "distance"
    }
    return fetch_kakao_api(url, params)

def fetch_keyword_data(lat, lng, keyword):
    """키워드로 수집"""
    url = "https://dapi.kakao.com/v2/local/search/keyword.json"
    params = {
        "query": keyword,
        "x": str(lng),
        "y": str(lat),
        "radius": 1000,
        "sort": "distance"
    }
    return fetch_kakao_api(url, params)

raw_data = []
collected_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

for target in TARGET_DONGS:
    gu = target["gu"]
    dong = target["dong"]
    lat = target["lat"]
    lng = target["lng"]
    
    print(f"수집 중: {gu} {dong}...")
    
    # 1. 카테고리 코드 수집
    for cat_name, cat_code in CATEGORY_CODES.items():
        count, min_dist = fetch_category_data(lat, lng, cat_code)
        raw_data.append({
            "gu_name": gu,
            "dong_name": dong,
            "lat": lat,
            "lng": lng,
            "category_name": cat_name,
            "place_count": count,
            "min_distance_m": min_dist,
            "collected_at": collected_time
        })

    # 2. 키워드 수집
    for kw in KEYWORD_TARGETS:
        count, min_dist = fetch_keyword_data(lat, lng, kw)
        raw_data.append({
            "gu_name": gu,
            "dong_name": dong,
            "lat": lat,
            "lng": lng,
            "category_name": kw,
            "place_count": count,
            "min_distance_m": min_dist,
            "collected_at": collected_time
        })

df = pd.DataFrame(raw_data)
filename = "raw_category_coords_gwangju_5districts.csv"
df.to_csv(filename, index=False, encoding='utf-8-sig')

print(f"\n데이터 수집 완료! 총 {len(df)}개 항목 수집됨 (저장된 파일명: {filename})")