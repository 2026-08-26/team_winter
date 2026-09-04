import requests
import xmltodict
import pandas as pd

# 1. 공공데이터포털 [일반 인증키 (Encoding)] 값을 복사해서 그대로 넣으세요.
# (%2Ba... 형태의 인코딩 키를 그대로 사용해야 URL 직접 조작 시 403이 안 납니다)
ENCODING_KEY = "2%2BaPU87TFwB4KEs2ydLmDB6NUGxdmZjKT5Bj%2BQALCdJcytkluBGRc6chjTmQBOQT9vSEb9WlPAZWLj0lT0MZEw%3D%3D"

# 2. 광주광역시 5개 구 시군구코드 (5자리)
GU_CODES = {
    "동구": "29110",
    "서구": "29140",
    "남구": "29150",
    "북구": "29170",
    "광산구": "29200"
}

# 3. 수집 대상 년월 (과거 1년치)
months = [
    "202401", "202402", "202403", "202404", "202405", "202406",
    "202407", "202408", "202409", "202410", "202411", "202412"
]

# 국토교통부 전월세 API Endpoints
URL_SINGLE = "http://apis.data.go.kr/1613000/RTMSDataSvcSHRent/getRTMSDataSvcSHRent"
URL_OFFI = "http://apis.data.go.kr/1613000/RTMSDataSvcOffiRent/getRTMSDataSvcOffiRent"

# 차단 방지용 브라우저 헤더
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def fetch_molit_data(base_url, gu_code, month):
    # serviceKey 이중 인코딩 차단 우회를 위해 URL 수동 생성
    request_url = f"{base_url}?serviceKey={ENCODING_KEY}&LAWD_CD={gu_code}&DEAL_YMD={month}&numOfRows=9999"
    try:
        response = requests.get(request_url, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            dict_data = xmltodict.parse(response.text)
            
            header = dict_data.get('response', {}).get('header', {})
            result_code = header.get('resultCode')

            if result_code == '00':
                body = dict_data.get('response', {}).get('body', {})
                items = body.get('items', {})
                if items and 'item' in items:
                    item_list = items['item']
                    if isinstance(item_list, dict):
                        item_list = [item_list]
                    return pd.DataFrame(item_list)
    except Exception:
        pass
    return pd.DataFrame()

all_rent_data = []

print("=== 광주광역시 주거(원룸/다가구/오피스텔) 전월세 실거래가 수집 시작 ===")

for gu_name, gu_code in GU_CODES.items():
    print(f"\n[{gu_name}] 데이터 수집 중...")
    
    for month in months:
        # A. 단독/다가구(원룸) 전월세
        df_single = fetch_molit_data(URL_SINGLE, gu_code, month)
        if not df_single.empty:
            df_single['주택유형'] = '단독다가구(원룸)'
            df_single['구이름'] = gu_name
            all_rent_data.append(df_single)

        # B. 오피스텔 전월세
        df_offi = fetch_molit_data(URL_OFFI, gu_code, month)
        if not df_offi.empty:
            df_offi['주택유형'] = '오피스텔'
            df_offi['구이름'] = gu_name
            all_rent_data.append(df_offi)

# 4. 저장 및 40㎡ 이하(원룸) 필터링
if all_rent_data:
    final_df = pd.concat(all_rent_data, ignore_index=True)
    
    area_cols = [c for c in final_df.columns if '면적' in c or 'area' in c.lower()]
    if area_cols:
        col = area_cols[0]
        final_df[col] = pd.to_numeric(final_df[col], errors='coerce')
        oneroom_df = final_df[final_df[col] <= 40.0].copy()
    else:
        oneroom_df = final_df

    filename = "raw_gwangju_oneroom_rent.csv"
    oneroom_df.to_csv(filename, index=False, encoding='utf-8-sig')
    print(f"\n수집 성공! 원룸/전월세 실거래가 저장 완료: {filename}")
    print(f"총 수집된 거래 건수: {len(oneroom_df)}건")
else:
    print("\n수집 실패: 키 재발급 후 1시간이 지나지 않았거나 API 신청 승인 대기 상태일 수 있습니다.")