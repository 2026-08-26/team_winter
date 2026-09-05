import os
import json
import time

from pathlib import Path
from urllib.parse import unquote, urlencode

import pandas as pd
import requests

from dotenv import load_dotenv


# =========================================================
# 1. 기본 경로
# =========================================================

BASE_DIR = Path(__file__).resolve().parent.parent

RAW_DIR = BASE_DIR / "data" / "raw"

RAW_DIR.mkdir(
    parents=True,
    exist_ok=True
)

OUTPUT_FILE = (
    RAW_DIR
    / "공공임대주택_광주_원본.csv"
)


# =========================================================
# 2. 국토교통부 마이홈포털 API
# =========================================================

API_URL = (
    "https://apis.data.go.kr/"
    "1613000/HWSPR04/"
    "rentalHouseGwList"
)


# =========================================================
# 3. 광주 5개 자치구 코드
#
# 국토교통부 마이홈포털
# 요청 파라미터 코드표 260701 기준
#
# 전남광주통합특별시 = 12
# =========================================================

BRTC_CODE = "12"

GWANGJU_GU = {

    "동구": "210",

    "서구": "240",

    "남구": "270",

    "북구": "300",

    "광산구": "330"
}


# =========================================================
# 4. 페이지당 조회 개수
# =========================================================

NUM_OF_ROWS = 100


# =========================================================
# 5. .env 인증키 읽기
#
# override=True
# → .env에 현재 저장된 값을 우선 사용
# =========================================================

load_dotenv(
    BASE_DIR / ".env",
    override=True
)


RAW_SERVICE_KEY = os.getenv(
    "DATA_GO_KR_SERVICE_KEY"
)


if not RAW_SERVICE_KEY:

    raise ValueError(
        ".env에서 "
        "DATA_GO_KR_SERVICE_KEY를 "
        "찾을 수 없습니다."
    )


RAW_SERVICE_KEY = (
    RAW_SERVICE_KEY
    .strip()
)


# Encoding 인증키가 들어있어도
# requests가 정상적으로 처리하도록 디코딩
DECODED_SERVICE_KEY = unquote(
    RAW_SERVICE_KEY
)


# =========================================================
# 6. 인증 방식
#
# 최초 성공한 방식을 이후 계속 사용
# =========================================================

AUTH_MODE = None


# =========================================================
# 7. 값 정리
# =========================================================

def clean_value(value):

    if value is None:

        return ""


    if isinstance(
        value,
        dict
    ):

        if len(value) == 0:

            return ""

        return json.dumps(
            value,
            ensure_ascii=False
        )


    if isinstance(
        value,
        list
    ):

        return json.dumps(
            value,
            ensure_ascii=False
        )


    return value


# =========================================================
# 8. 인증 오류 확인
# =========================================================

def is_auth_error(
    text,
    data=None
):

    upper_text = (
        str(text)
        .upper()
    )


    messages = [

        "SERVICE_KEY_IS_NOT_REGISTERED",

        "SERVICE KEY IS NOT REGISTERED",

        "SERVICE_ACCESS_DENIED",

        "SERVICE_KEY_IS_NULL",

        "SERVICE KEY IS NULL",

        "PERMISSION_DENIED"
    ]


    for message in messages:

        if message in upper_text:

            return True


    if isinstance(
        data,
        dict
    ):

        code = str(
            data.get(
                "code",
                ""
            )
        ).strip()


        if code == "30":

            return True


    return False


# =========================================================
# 9. API 결과코드 검사
# =========================================================

def check_api_result(
    data,
    text
):

    # -----------------------------------------------------
    # 인증 오류
    # -----------------------------------------------------

    if is_auth_error(
        text,
        data
    ):

        return False, (
            "SERVICE KEY 인증 오류"
        )


    # -----------------------------------------------------
    # 최상위 code가 존재하는 API 대응
    # -----------------------------------------------------

    if isinstance(
        data,
        dict
    ):

        code = str(
            data.get(
                "code",
                ""
            )
        ).strip()


        if code == "30":

            return False, (
                "인증키 오류(code=30)"
            )


        if code == "03":

            return True, "NODATA"


        if (
            code
            and
            code not in [
                "0",
                "00",
                "000"
            ]
        ):

            return False, (
                f"API 오류(code={code})"
            )


    # -----------------------------------------------------
    # 현재 마이홈포털 구조
    #
    # response.header.resultCode
    # -----------------------------------------------------

    if isinstance(
        data,
        dict
    ):

        response = data.get(
            "response"
        )


        if isinstance(
            response,
            dict
        ):

            header = response.get(
                "header"
            )


            if isinstance(
                header,
                dict
            ):

                result_code = str(
                    header.get(
                        "resultCode",
                        ""
                    )
                ).strip()


                result_msg = str(
                    header.get(
                        "resultMsg",
                        ""
                    )
                ).strip()


                if result_code in [

                    "",
                    "0",
                    "00",
                    "000",
                    "0000"

                ]:

                    return True, ""


                if result_code == "03":

                    return True, "NODATA"


                return False, (

                    f"{result_code} / "
                    f"{result_msg}"

                )


    return True, ""


# =========================================================
# 10. 실제 단지 목록 추출
#
# 현재 실제 API 응답:
#
# response
#   └─ body
#       └─ item
#
# 여기서 item을 읽어야 함
# =========================================================

def extract_items(
    data
):

    if not isinstance(
        data,
        dict
    ):

        return []


    # -----------------------------------------------------
    # 현재 실제 구조
    # response.body.item
    # -----------------------------------------------------

    response = data.get(
        "response"
    )


    if isinstance(
        response,
        dict
    ):

        body = response.get(
            "body"
        )


        if isinstance(
            body,
            dict
        ):

            # ★ 현재 실제 API 구조
            item = body.get(
                "item"
            )


            if isinstance(
                item,
                list
            ):

                return item


            if isinstance(
                item,
                dict
            ):

                return [
                    item
                ]


            # 혹시 items.item 형태로 변경되는 경우 대비
            items = body.get(
                "items"
            )


            if isinstance(
                items,
                list
            ):

                return items


            if isinstance(
                items,
                dict
            ):

                nested_item = items.get(
                    "item"
                )


                if isinstance(
                    nested_item,
                    list
                ):

                    return nested_item


                if isinstance(
                    nested_item,
                    dict
                ):

                    return [
                        nested_item
                    ]


    # -----------------------------------------------------
    # body가 최상위에 있는 경우 대비
    # -----------------------------------------------------

    body = data.get(
        "body"
    )


    if isinstance(
        body,
        dict
    ):

        item = body.get(
            "item"
        )


        if isinstance(
            item,
            list
        ):

            return item


        if isinstance(
            item,
            dict
        ):

            return [
                item
            ]


    # -----------------------------------------------------
    # 예전 API 형식도 대비
    # -----------------------------------------------------

    hsmp_list = data.get(
        "hsmpList"
    )


    if isinstance(
        hsmp_list,
        list
    ):

        return hsmp_list


    if isinstance(
        hsmp_list,
        dict
    ):

        return [
            hsmp_list
        ]


    return []


# =========================================================
# 11. 전체 조회 건수 추출
# =========================================================

def extract_total_count(
    data
):

    if not isinstance(
        data,
        dict
    ):

        return None


    # -----------------------------------------------------
    # 현재 실제 구조
    # response.body.totalCount
    # -----------------------------------------------------

    response = data.get(
        "response"
    )


    if isinstance(
        response,
        dict
    ):

        body = response.get(
            "body"
        )


        if isinstance(
            body,
            dict
        ):

            value = body.get(
                "totalCount"
            )


            if value is not None:

                try:

                    return int(
                        value
                    )

                except Exception:

                    pass


    # -----------------------------------------------------
    # 다른 구조 대비
    # -----------------------------------------------------

    value = data.get(
        "totalCount"
    )


    if value is not None:

        try:

            return int(
                value
            )

        except Exception:

            pass


    return None


# =========================================================
# 12. decoded 인증키 요청
# =========================================================

def request_decoded(
    session,
    other_params
):

    params = {

        "serviceKey":
            DECODED_SERVICE_KEY,

        **other_params
    }


    return session.get(

        API_URL,

        params=params,

        headers={
            "Accept":
                "application/json"
        },

        timeout=30
    )


# =========================================================
# 13. raw Encoding 인증키 요청
# =========================================================

def request_raw(
    session,
    other_params
):

    query_string = urlencode(
        other_params
    )


    request_url = (

        API_URL

        + "?serviceKey="

        + RAW_SERVICE_KEY

        + "&"

        + query_string

    )


    return session.get(

        request_url,

        headers={
            "Accept":
                "application/json"
        },

        timeout=30
    )


# =========================================================
# 14. 응답 JSON 변환
# =========================================================

def parse_response(
    response,
    gu_name
):

    text = (
        response.text
        .strip()
    )


    if response.status_code != 200:

        raise RuntimeError(

            f"{gu_name} HTTP 오류\n"
            f"상태코드 : "
            f"{response.status_code}\n"
            f"응답 : "
            f"{text[:500]}"

        )


    try:

        data = response.json()


    except ValueError:

        raise RuntimeError(

            f"{gu_name} 응답이 "
            f"JSON 형식이 아닙니다.\n"
            f"응답 : "
            f"{text[:500]}"

        )


    return (
        text,
        data
    )


# =========================================================
# 15. 인증 방식 자동 선택
# =========================================================

def request_api(
    session,
    gu_name,
    other_params
):

    global AUTH_MODE


    # -----------------------------------------------------
    # 이미 decoded 방식 성공
    # -----------------------------------------------------

    if AUTH_MODE == "decoded":

        response = request_decoded(
            session,
            other_params
        )


        text, data = parse_response(
            response,
            gu_name
        )


        success, message = (
            check_api_result(
                data,
                text
            )
        )


        if not success:

            raise RuntimeError(

                f"{gu_name} API 오류\n"
                f"{message}\n"
                f"응답 : "
                f"{text[:500]}"

            )


        return data


    # -----------------------------------------------------
    # 이미 raw 방식 성공
    # -----------------------------------------------------

    if AUTH_MODE == "raw":

        response = request_raw(
            session,
            other_params
        )


        text, data = parse_response(
            response,
            gu_name
        )


        success, message = (
            check_api_result(
                data,
                text
            )
        )


        if not success:

            raise RuntimeError(

                f"{gu_name} API 오류\n"
                f"{message}\n"
                f"응답 : "
                f"{text[:500]}"

            )


        return data


    # -----------------------------------------------------
    # 최초 요청
    # decoded 방식 먼저 확인
    # -----------------------------------------------------

    print(
        "  인증 방식 확인 : "
        "serviceKey / decoded"
    )


    response = request_decoded(
        session,
        other_params
    )


    text, data = parse_response(
        response,
        gu_name
    )


    success, message = (
        check_api_result(
            data,
            text
        )
    )


    if success:

        AUTH_MODE = "decoded"

        print(
            "  → 인증 성공 : "
            "serviceKey / decoded"
        )

        return data


    # -----------------------------------------------------
    # raw 방식 재시도
    # -----------------------------------------------------

    print(
        "  인증 방식 확인 : "
        "serviceKey / raw"
    )


    response = request_raw(
        session,
        other_params
    )


    text, data = parse_response(
        response,
        gu_name
    )


    success, message = (
        check_api_result(
            data,
            text
        )
    )


    if success:

        AUTH_MODE = "raw"

        print(
            "  → 인증 성공 : "
            "serviceKey / raw"
        )

        return data


    raise RuntimeError(

        f"{gu_name} API 인증 실패\n\n"

        f"오류 : {message}\n"

        f"응답 : {text[:500]}\n\n"

        "※ 인증키 값은 "
        "채팅에 보내지 마세요."

    )


# =========================================================
# 16. 한 페이지 조회
# =========================================================

def request_page(
    session,
    gu_name,
    signgu_code,
    page_no
):

    params = {

        "brtcCode":
            BRTC_CODE,

        "signguCode":
            signgu_code,

        "numOfRows":
            NUM_OF_ROWS,

        "pageNo":
            page_no
    }


    data = request_api(

        session,

        gu_name,

        params

    )


    items = extract_items(
        data
    )


    total_count = extract_total_count(
        data
    )


    return (
        items,
        total_count
    )


# =========================================================
# 17. 자치구 전체 수집
# =========================================================

def collect_gu(
    session,
    gu_name,
    signgu_code
):

    print()
    print(
        "----------------------------------------"
    )

    print(
        f"{gu_name} 수집 시작"
    )

    print(
        "----------------------------------------"
    )


    collected = []

    page_no = 1


    while page_no <= 100:

        print(
            f"{gu_name} "
            f"{page_no}페이지 조회 중..."
        )


        (
            items,
            total_count
        ) = request_page(

            session,

            gu_name,

            signgu_code,

            page_no

        )


        # -------------------------------------------------
        # 실제 데이터가 없는 경우
        # -------------------------------------------------

        if len(
            items
        ) == 0:

            if page_no == 1:

                print(
                    "  → 조회 결과 0행"
                )

            break


        # -------------------------------------------------
        # 데이터 저장
        # -------------------------------------------------

        for item in items:

            if not isinstance(
                item,
                dict
            ):

                continue


            row = {}


            for (
                key,
                value
            ) in item.items():

                row[
                    key
                ] = clean_value(
                    value
                )


            row[
                "요청자치구"
            ] = gu_name


            row[
                "요청시군구코드"
            ] = signgu_code


            row[
                "수집페이지"
            ] = page_no


            collected.append(
                row
            )


        print(
            f"  → {len(items):,}행 수집"
        )


        if total_count is not None:

            print(
                f"  → API 전체 대상 : "
                f"{total_count:,}행"
            )


        # -------------------------------------------------
        # 전체 건수를 모두 받았으면 종료
        # -------------------------------------------------

        if (
            total_count is not None
            and
            len(collected) >= total_count
        ):

            break


        # -------------------------------------------------
        # 100건보다 적으면 마지막 페이지
        # -------------------------------------------------

        if len(
            items
        ) < NUM_OF_ROWS:

            break


        page_no += 1


        # API 연속 호출 간격
        time.sleep(
            0.15
        )


    print(
        f"{gu_name} 완료 : "
        f"{len(collected):,}행"
    )


    return collected


# =========================================================
# 18. 주요 컬럼 순서
# =========================================================

def reorder_columns(
    df
):

    priority_columns = [

        "요청자치구",

        "요청시군구코드",

        "brtcCode",

        "brtcNm",

        "signguCode",

        "signguNm",

        "hsmpSn",

        "hsmpNm",

        "insttNm",

        "rnAdres",

        "pnu",

        "hshldCo",

        "suplyTyNm",

        "styleNm",

        "suplyPrvuseAr",

        "suplyCmnuseAr",

        "houseTyNm",

        "competDe",

        "bassRentGtn",

        "bassMtRntchrg",

        "bassCnvrsGtnLmt",

        "parkngCo",

        "수집페이지"
    ]


    front = [

        column

        for column in priority_columns

        if column in df.columns

    ]


    rest = [

        column

        for column in df.columns

        if column not in front

    ]


    return df[
        front + rest
    ]


# =========================================================
# 19. 메인 실행
# =========================================================

def main():

    print()
    print(
        "========================================"
    )

    print(
        "광주 공공임대주택 데이터 수집"
    )

    print(
        "========================================"
    )


    print()
    print(
        "사용 API : "
        "국토교통부 마이홈포털"
    )

    print(
        "상세기능 : "
        "/rentalHouseGwList"
    )

    print(
        f"API 주소 : "
        f"{API_URL}"
    )


    print()
    print(
        "※ 아직 청년 대상 여부는 "
        "임의로 필터링하지 않습니다."
    )


    session = requests.Session()


    all_rows = []


    # =====================================================
    # 광주 5개 자치구 수집
    # =====================================================

    try:

        for (
            gu_name,
            signgu_code
        ) in GWANGJU_GU.items():


            rows = collect_gu(

                session,

                gu_name,

                signgu_code

            )


            all_rows.extend(
                rows
            )


    except RuntimeError as e:

        print()
        print(
            "========================================"
        )

        print(
            "수집 중단"
        )

        print(
            "========================================"
        )

        print()
        print(e)

        return


    # =====================================================
    # 수집 결과 없음
    # =====================================================

    if len(
        all_rows
    ) == 0:

        print()
        print(
            "========================================"
        )

        print(
            "수집 데이터 없음"
        )

        print(
            "========================================"
        )

        return


    # =====================================================
    # DataFrame 생성
    # =====================================================

    df = pd.DataFrame(
        all_rows
    )


    df = reorder_columns(
        df
    )


    # =====================================================
    # CSV 저장
    # =====================================================

    df.to_csv(

        OUTPUT_FILE,

        index=False,

        encoding="utf-8-sig"

    )


    # =====================================================
    # 결과 출력
    # =====================================================

    print()
    print(
        "========================================"
    )

    print(
        "공공임대주택 수집 완료"
    )

    print(
        "========================================"
    )


    print()
    print(
        f"전체 API 응답 행 : "
        f"{len(df):,}행"
    )


    # =====================================================
    # 자치구별 응답 행
    # =====================================================

    print()
    print(
        "[자치구별 응답 행]"
    )


    gu_counts = (

        df[
            "요청자치구"
        ]

        .value_counts()

    )


    for (
        gu,
        count
    ) in gu_counts.items():

        print(
            f"- {gu} : "
            f"{count:,}행"
        )


    # =====================================================
    # 실제 응답 컬럼
    # =====================================================

    print()
    print(
        "[실제 응답 컬럼]"
    )


    for column in df.columns:

        print(
            "-",
            column
        )


    # =====================================================
    # 고유 단지 ID
    # =====================================================

    if (
        "hsmpSn"
        in df.columns
    ):

        unique_complexes = (

            df[
                "hsmpSn"
            ]

            .replace(
                "",
                pd.NA
            )

            .dropna()

            .astype(str)

            .nunique()

        )


        print()
        print(
            f"고유 단지 ID : "
            f"{unique_complexes:,}개"
        )


    # =====================================================
    # 고유 주소
    # =====================================================

    if (
        "rnAdres"
        in df.columns
    ):

        unique_addresses = (

            df[
                "rnAdres"
            ]

            .replace(
                "",
                pd.NA
            )

            .dropna()

            .astype(str)

            .nunique()

        )


        print(
            f"고유 주소 : "
            f"{unique_addresses:,}개"
        )


    # =====================================================
    # 공급 유형
    # =====================================================

    if (
        "suplyTyNm"
        in df.columns
    ):

        print()
        print(
            "[공급유형]"
        )


        supply_counts = (

            df[
                "suplyTyNm"
            ]

            .fillna(
                ""
            )

            .astype(str)

            .replace(
                "",
                "미상"
            )

            .value_counts()

        )


        for (
            supply_type,
            count
        ) in supply_counts.items():

            print(
                f"- {supply_type} : "
                f"{count:,}행"
            )


    # =====================================================
    # 세대수 상태
    # =====================================================

    if (
        "hshldCo"
        in df.columns
    ):

        household_values = (
            pd.to_numeric(
                df[
                    "hshldCo"
                ],
                errors="coerce"
            )
        )


        print()
        print(
            "[세대수 데이터 확인]"
        )

        print(
            f"- 세대수 값 존재 : "
            f"{household_values.notna().sum():,}행"
        )

        print(
            f"- 세대수 값 없음 : "
            f"{household_values.isna().sum():,}행"
        )


    # =====================================================
    # 안내
    # =====================================================

    print()
    print(
        "----------------------------------------"
    )

    print(
        "중요:"
    )

    print(
        "같은 hsmpSn이 여러 면적·주택형으로 "
        "반복될 수 있습니다."
    )

    print(
        "따라서 아직 hshldCo를 "
        "단순 합산하면 안 됩니다."
    )

    print(
        "다음 단계에서 단지 중복 구조를 "
        "먼저 검사합니다."
    )


    print()
    print(
        "저장 위치:"
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