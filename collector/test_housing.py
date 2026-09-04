import os
import requests

from pathlib import Path
from dotenv import load_dotenv


# ==========================================
# 1. .env 불러오기
# ==========================================

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")

SERVICE_KEY = os.getenv("DATA_GO_KR_SERVICE_KEY")


# ==========================================
# 2. 테스트할 지역 / 기간
# ==========================================

# 광주 동구 법정동 코드 앞 5자리
LAWD_CD = "12210"

# 2026년 8월
DEAL_YMD = "202608"


# ==========================================
# 3. 아파트 매매 실거래가 API 주소
# ==========================================

URL = (
    "https://apis.data.go.kr/1613000/"
    "RTMSDataSvcAptTrade/"
    "getRTMSDataSvcAptTrade"
)


# ==========================================
# 4. API 테스트
# ==========================================

def test_apartment_trade():

    if not SERVICE_KEY:
        print("❌ 공공데이터포털 API 키를 찾지 못했습니다.")
        return


    params = {
        "LAWD_CD": LAWD_CD,
        "DEAL_YMD": DEAL_YMD,
        "numOfRows": 10,
        "pageNo": 1
    }

    request_url = f"{URL}?serviceKey={SERVICE_KEY}"

    response = requests.get(
        request_url,
        params=params,
        timeout=20
    )


    print()
    print("================================")
    print("아파트 매매 API 테스트")
    print("================================")

    print("상태 코드 :", response.status_code)
    print()

    print("응답 내용")
    print(response.text[:3000])


# ==========================================
# 5. 실행
# ==========================================

if __name__ == "__main__":
    test_apartment_trade()