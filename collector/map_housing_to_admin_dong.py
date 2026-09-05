import os
import time
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv


# =========================================================
# 1. 기본 경로
# =========================================================

BASE_DIR = Path(__file__).resolve().parent.parent

RAW_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed"

PROCESSED_DIR.mkdir(
    parents=True,
    exist_ok=True
)


INPUT_FILE = (
    RAW_DIR
    / "전체_주거실거래_202507_202606.csv"
)

CACHE_FILE = (
    RAW_DIR
    / "주거주소_행정동_캐시.csv"
)

OUTPUT_ALL_FILE = (
    PROCESSED_DIR
    / "청년소형주택_행정동매핑.csv"
)

OUTPUT_TARGET_FILE = (
    PROCESSED_DIR
    / "청년소형주택_25개동_실거래.csv"
)


# =========================================================
# 2. 분석 기준
# =========================================================

# 18평 ≈ 59.5㎡
MAX_AREA_M2 = 59.5


# =========================================================
# 3. 환경변수
# =========================================================

load_dotenv(
    BASE_DIR / ".env"
)

KAKAO_REST_API_KEY = os.getenv(
    "KAKAO_REST_API_KEY"
)


if not KAKAO_REST_API_KEY:

    raise ValueError(
        "KAKAO_REST_API_KEY를 .env에서 찾을 수 없습니다."
    )


# =========================================================
# 4. 카카오 API
# =========================================================

ADDRESS_URL = (
    "https://dapi.kakao.com/"
    "v2/local/search/address.json"
)

REGION_URL = (
    "https://dapi.kakao.com/"
    "v2/local/geo/coord2regioncode.json"
)

HEADERS = {
    "Authorization":
        f"KakaoAK {KAKAO_REST_API_KEY}"
}


# =========================================================
# 5. 프로젝트 25개 동
#
# key:
# 실제 공식 행정구역
#
# value:
# 프로젝트 내부 표기
# =========================================================

TARGET_DONGS = {

    # 동구
    ("동구", "충장동"):
        ("동구", "충장동"),

    ("동구", "계림1동"):
        ("동구", "계림1동"),

    ("동구", "지산2동"):
        ("동구", "지산2동"),

    ("동구", "학동"):
        ("동구", "학동"),

    ("동구", "지원1동"):
        ("동구", "지원1동"),


    # 서구
    ("서구", "치평동"):
        ("서구", "치평동"),

    ("서구", "풍암동"):
        ("서구", "풍암동"),

    ("서구", "화정2동"):
        ("서구", "화정2동"),

    ("서구", "농성1동"):
        ("서구", "농성1동"),

    ("서구", "금호1동"):
        ("서구", "금호1동"),


    # 남구
    ("남구", "봉선2동"):
        ("남구", "봉선2동"),

    ("남구", "진월동"):
        ("남구", "진월동"),

    ("남구", "방림1동"):
        ("남구", "방림1동"),

    ("남구", "효덕동"):
        ("남구", "효덕동"),

    ("남구", "송암동"):
        ("남구", "송암동"),


    # 북구
    ("북구", "용봉동"):
        ("북구", "용봉동"),

    ("북구", "두암2동"):
        ("북구", "두암2동"),

    ("북구", "운암1동"):
        ("북구", "운암1동"),

    ("북구", "문흥1동"):
        ("북구", "문흥1동"),


    # 첨단2동
    #
    # 공식 = 광산구 첨단2동
    # 프로젝트 내부 = 북구 첨단2동
    ("광산구", "첨단2동"):
        ("북구", "첨단2동"),


    # 광산구
    ("광산구", "첨단1동"):
        ("광산구", "첨단1동"),

    ("광산구", "수완동"):
        ("광산구", "수완동"),

    ("광산구", "신가동"):
        ("광산구", "신가동"),

    ("광산구", "우산동"):
        ("광산구", "우산동"),

    ("광산구", "송정1동"):
        ("광산구", "송정1동")
}


# =========================================================
# 6. 숫자 변환
# =========================================================

def to_number(value):

    if value is None:

        return None


    value = (
        str(value)
        .strip()
        .replace(",", "")
    )


    if value == "":

        return None


    try:

        return float(value)


    except ValueError:

        return None


# =========================================================
# 7. 컬럼 이름 대소문자 관계없이 찾기
# =========================================================

def get_value(
    row,
    candidates
):

    column_map = {
        str(column).lower():
            column

        for column in row.index
    }


    for candidate in candidates:

        real_column = column_map.get(
            candidate.lower()
        )


        if real_column is None:

            continue


        value = row.get(
            real_column,
            ""
        )


        if str(value).strip() != "":

            return str(value).strip()


    return ""


# =========================================================
# 8. 건물번호 정리
# =========================================================

def clean_number(value):

    value = str(
        value
    ).strip()


    if value == "":

        return ""


    try:

        number = float(
            value
        )


        if number.is_integer():

            return str(
                int(number)
            )


    except ValueError:

        pass


    return value


# =========================================================
# 9. 18평 이하 전월세 여부
# =========================================================

def is_target_transaction(row):

    transaction_type = (
        get_value(
            row,
            [
                "transaction_type"
            ]
        )
    )


    if transaction_type != "전월세":

        return False


    area = to_number(
        get_value(
            row,
            [
                "excluUseAr"
            ]
        )
    )


    # 전용면적을 알 수 없는 거래는 제외
    if area is None:

        return False


    if area > MAX_AREA_M2:

        return False


    deposit = to_number(
        get_value(
            row,
            [
                "deposit"
            ]
        )
    )


    monthly_rent = to_number(
        get_value(
            row,
            [
                "monthlyRent"
            ]
        )
    )


    if (
        deposit is None
        or monthly_rent is None
    ):

        return False


    return True


# =========================================================
# 10. 주소 후보 만들기
# =========================================================

def make_address_candidates(row):

    gu_name = get_value(
        row,
        [
            "gu_name"
        ]
    )


    umd_name = get_value(
        row,
        [
            "umdNm",
            "umdnm"
        ]
    )


    jibun = get_value(
        row,
        [
            "jibun"
        ]
    )


    road_name = get_value(
        row,
        [
            "roadNm",
            "roadnm"
        ]
    )


    road_bonbun = get_value(
        row,
        [
            "roadNmBonbun",
            "roadnmbonbun"
        ]
    )


    road_bubun = get_value(
        row,
        [
            "roadNmBubun",
            "roadnmbubun"
        ]
    )


    candidates = []


    # =====================================================
    # 1순위: 지번주소
    # =====================================================

    if (
        gu_name
        and umd_name
        and jibun
    ):

        candidates.append(
            f"광주광역시 "
            f"{gu_name} "
            f"{umd_name} "
            f"{jibun}"
        )


        # 광주광역시 대신 광주 표현도 보조
        candidates.append(
            f"광주 "
            f"{gu_name} "
            f"{umd_name} "
            f"{jibun}"
        )


    # =====================================================
    # 2순위: 도로명주소
    # =====================================================

    bonbun = clean_number(
        road_bonbun
    )

    bubun = clean_number(
        road_bubun
    )


    if (
        gu_name
        and road_name
        and bonbun
    ):

        if (
            bubun
            and bubun != "0"
        ):

            building_number = (
                f"{bonbun}-{bubun}"
            )

        else:

            building_number = (
                bonbun
            )


        candidates.append(
            f"광주광역시 "
            f"{gu_name} "
            f"{road_name} "
            f"{building_number}"
        )


    # =====================================================
    # 중복 제거
    # =====================================================

    unique_candidates = []

    seen = set()


    for address in candidates:

        address = " ".join(
            address.split()
        )


        if (
            address
            and address not in seen
        ):

            seen.add(
                address
            )

            unique_candidates.append(
                address
            )


    return unique_candidates


# =========================================================
# 11. 주소 고유키 만들기
# =========================================================

def make_address_key(row):

    gu_name = get_value(
        row,
        ["gu_name"]
    )

    umd_name = get_value(
        row,
        [
            "umdNm",
            "umdnm"
        ]
    )

    jibun = get_value(
        row,
        ["jibun"]
    )

    road_name = get_value(
        row,
        [
            "roadNm",
            "roadnm"
        ]
    )

    road_bonbun = get_value(
        row,
        [
            "roadNmBonbun",
            "roadnmbonbun"
        ]
    )

    road_bubun = get_value(
        row,
        [
            "roadNmBubun",
            "roadnmbubun"
        ]
    )


    return (
        f"{gu_name}|"
        f"{umd_name}|"
        f"{jibun}|"
        f"{road_name}|"
        f"{road_bonbun}|"
        f"{road_bubun}"
    )


# =========================================================
# 12. 주소 → 좌표
# =========================================================

def geocode_address(
    session,
    address
):

    try:

        response = session.get(
            ADDRESS_URL,
            headers=HEADERS,
            params={
                "query":
                    address
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


        matched_address = ""


        if item.get(
            "road_address"
        ):

            matched_address = (
                item[
                    "road_address"
                ].get(
                    "address_name",
                    ""
                )
            )


        if (
            not matched_address
            and item.get(
                "address"
            )
        ):

            matched_address = (
                item[
                    "address"
                ].get(
                    "address_name",
                    ""
                )
            )


        return {

            "위도":
                float(
                    item["y"]
                ),

            "경도":
                float(
                    item["x"]
                ),

            "카카오매칭주소":
                matched_address,

            "검색주소":
                address
        }


    except Exception:

        return None


# =========================================================
# 13. 좌표 → 실제 행정동
# =========================================================

def coord_to_admin_dong(
    session,
    longitude,
    latitude
):

    try:

        response = session.get(
            REGION_URL,
            headers=HEADERS,
            params={
                "x":
                    longitude,

                "y":
                    latitude
            },
            timeout=15
        )


        response.raise_for_status()


        data = response.json()


        documents = data.get(
            "documents",
            []
        )


        # H = 행정동
        for item in documents:

            if (
                item.get(
                    "region_type"
                )
                != "H"
            ):

                continue


            return {

                "공식자치구":
                    item.get(
                        "region_2depth_name",
                        ""
                    ),

                "공식행정동":
                    item.get(
                        "region_3depth_name",
                        ""
                    ),

                "행정동코드":
                    item.get(
                        "code",
                        ""
                    )
            }


    except Exception:

        pass


    return None


# =========================================================
# 14. 주소 1개 실제 행정동 조회
# =========================================================

def lookup_address(
    session,
    row
):

    candidates = (
        make_address_candidates(
            row
        )
    )


    if not candidates:

        return {
            "위도": "",
            "경도": "",
            "검색주소": "",
            "카카오매칭주소": "",
            "공식자치구": "",
            "공식행정동": "",
            "행정동코드": "",
            "매핑상태": "주소생성실패"
        }


    for address in candidates:

        geocode = (
            geocode_address(
                session,
                address
            )
        )


        if geocode is None:

            continue


        region = (
            coord_to_admin_dong(
                session,
                geocode[
                    "경도"
                ],
                geocode[
                    "위도"
                ]
            )
        )


        if region is None:

            continue


        return {

            "위도":
                geocode[
                    "위도"
                ],

            "경도":
                geocode[
                    "경도"
                ],

            "검색주소":
                geocode[
                    "검색주소"
                ],

            "카카오매칭주소":
                geocode[
                    "카카오매칭주소"
                ],

            "공식자치구":
                region[
                    "공식자치구"
                ],

            "공식행정동":
                region[
                    "공식행정동"
                ],

            "행정동코드":
                region[
                    "행정동코드"
                ],

            "매핑상태":
                "성공"
        }


    return {
        "위도": "",
        "경도": "",
        "검색주소": candidates[0],
        "카카오매칭주소": "",
        "공식자치구": "",
        "공식행정동": "",
        "행정동코드": "",
        "매핑상태": "검색실패"
    }


# =========================================================
# 15. 캐시 읽기
# =========================================================

def load_cache():

    if not CACHE_FILE.exists():

        return {}


    cache_df = pd.read_csv(
        CACHE_FILE,
        encoding="utf-8-sig",
        dtype=str,
        keep_default_na=False
    )


    cache = {}


    for _, row in (
        cache_df.iterrows()
    ):

        cache[
            row["주소키"]
        ] = row.to_dict()


    return cache


# =========================================================
# 16. 캐시 저장
# =========================================================

def save_cache(cache):

    if not cache:

        return


    cache_df = pd.DataFrame(
        list(
            cache.values()
        )
    )


    cache_df.to_csv(
        CACHE_FILE,
        index=False,
        encoding="utf-8-sig"
    )


# =========================================================
# 17. 프로젝트 지역 표기
# =========================================================

def get_project_region(
    official_gu,
    official_dong
):

    key = (
        official_gu,
        official_dong
    )


    if key not in TARGET_DONGS:

        return {
            "프로젝트자치구": "",
            "프로젝트행정동": "",
            "분석대상여부": False
        }


    project_gu, project_dong = (
        TARGET_DONGS[
            key
        ]
    )


    return {
        "프로젝트자치구":
            project_gu,

        "프로젝트행정동":
            project_dong,

        "분석대상여부":
            True
    }


# =========================================================
# 18. 메인
# =========================================================

def main():

    print()
    print(
        "========================================"
    )

    print(
        "주거 실거래 실제 행정동 매핑 시작"
    )

    print(
        "========================================"
    )


    # =====================================================
    # 입력파일 확인
    # =====================================================

    if not INPUT_FILE.exists():

        print(
            "원본 파일을 찾을 수 없습니다."
        )

        print(
            INPUT_FILE
        )

        return


    # =====================================================
    # 원본 읽기
    # =====================================================

    df = pd.read_csv(
        INPUT_FILE,
        encoding="utf-8-sig",
        dtype=str,
        keep_default_na=False
    )


    print(
        f"\n전체 원본 거래 : "
        f"{len(df):,}건"
    )


    # =====================================================
    # 18평 이하 전월세만 먼저 필터링
    # =====================================================

    target_mask = df.apply(
        is_target_transaction,
        axis=1
    )


    filtered = (
        df[
            target_mask
        ]
        .copy()
        .reset_index(
            drop=True
        )
    )


    print(
        f"18평 이하 유효 전월세 : "
        f"{len(filtered):,}건"
    )


    # =====================================================
    # 주소키 생성
    # =====================================================

    filtered[
        "주소키"
    ] = filtered.apply(
        make_address_key,
        axis=1
    )


    unique_addresses = (
        filtered[
            "주소키"
        ]
        .nunique()
    )


    print(
        f"고유 주소 : "
        f"{unique_addresses:,}개"
    )


    # =====================================================
    # 캐시
    # =====================================================

    cache = load_cache()


    print(
        f"기존 캐시 : "
        f"{len(cache):,}개"
    )


    session = (
        requests.Session()
    )


    # =====================================================
    # 고유 주소별 API 조회
    # =====================================================

    unique_rows = (

        filtered

        .drop_duplicates(
            subset=[
                "주소키"
            ]
        )

    )


    new_count = 0


    for index, (_, row) in enumerate(
        unique_rows.iterrows(),
        start=1
    ):

        key = row[
            "주소키"
        ]


        # 기존 성공 캐시는 다시 조회하지 않음
        if (
            key in cache
            and cache[
                key
            ].get(
                "매핑상태"
            ) == "성공"
        ):

            continue


        result = lookup_address(
            session,
            row
        )


        result[
            "주소키"
        ] = key


        cache[
            key
        ] = result


        new_count += 1


        if (
            index == 1
            or index % 20 == 0
            or index
            == len(
                unique_rows
            )
        ):

            print(
                f"[{index}/"
                f"{len(unique_rows)}] "
                f"주소 매핑 진행"
            )


        # 50건마다 중간 저장
        if new_count % 50 == 0:

            save_cache(
                cache
            )


        time.sleep(
            0.08
        )


    # 최종 캐시 저장
    save_cache(
        cache
    )


    # =====================================================
    # 캐시 DataFrame
    # =====================================================

    cache_df = pd.DataFrame(
        list(
            cache.values()
        )
    )


    # 기존 같은 이름 방지
    mapping_columns = [

        "주소키",
        "위도",
        "경도",
        "검색주소",
        "카카오매칭주소",
        "공식자치구",
        "공식행정동",
        "행정동코드",
        "매핑상태"
    ]


    cache_df = cache_df[
        mapping_columns
    ]


    # =====================================================
    # 실거래에 행정동 붙이기
    # =====================================================

    mapped = filtered.merge(
        cache_df,
        on="주소키",
        how="left"
    )


    # =====================================================
    # 프로젝트 25개 동 표시
    # =====================================================

    project_results = []


    for _, row in mapped.iterrows():

        result = (
            get_project_region(
                str(
                    row.get(
                        "공식자치구",
                        ""
                    )
                ).strip(),

                str(
                    row.get(
                        "공식행정동",
                        ""
                    )
                ).strip()
            )
        )


        project_results.append(
            result
        )


    project_df = pd.DataFrame(
        project_results
    )


    mapped = pd.concat(
        [
            mapped.reset_index(
                drop=True
            ),

            project_df.reset_index(
                drop=True
            )
        ],
        axis=1
    )


    # =====================================================
    # 지역 컬럼
    # =====================================================

    mapped[
        "공식지역"
    ] = (

        mapped[
            "공식자치구"
        ].fillna(
            ""
        ).astype(
            str
        )

        + " "

        + mapped[
            "공식행정동"
        ].fillna(
            ""
        ).astype(
            str
        )

    ).str.strip()


    mapped[
        "프로젝트지역"
    ] = (

        mapped[
            "프로젝트자치구"
        ].fillna(
            ""
        ).astype(
            str
        )

        + " "

        + mapped[
            "프로젝트행정동"
        ].fillna(
            ""
        ).astype(
            str
        )

    ).str.strip()


    # =====================================================
    # 전체 상세 저장
    # =====================================================

    mapped.to_csv(
        OUTPUT_ALL_FILE,
        index=False,
        encoding="utf-8-sig"
    )


    # =====================================================
    # 25개 동 거래만 추출
    # =====================================================

    target_df = (

        mapped[
            mapped[
                "분석대상여부"
            ] == True
        ]

        .copy()

    )


    target_df.to_csv(
        OUTPUT_TARGET_FILE,
        index=False,
        encoding="utf-8-sig"
    )


    # =====================================================
    # 결과 검증
    # =====================================================

    mapping_success = (

        mapped[
            "매핑상태"
        ]
        == "성공"

    ).sum()


    mapping_fail = (

        mapped[
            "매핑상태"
        ]
        != "성공"

    ).sum()


    covered_dongs = (

        target_df[
            "프로젝트지역"
        ]
        .nunique()

    )


    print()
    print(
        "========================================"
    )

    print(
        "행정동 매핑 완료"
    )

    print(
        "========================================"
    )


    print(
        f"\n18평 이하 전월세 : "
        f"{len(mapped):,}건"
    )

    print(
        f"행정동 매핑 성공 : "
        f"{mapping_success:,}건"
    )

    print(
        f"행정동 매핑 실패 : "
        f"{mapping_fail:,}건"
    )

    print(
        f"25개 분석대상 동 거래 : "
        f"{len(target_df):,}건"
    )

    print(
        f"거래가 연결된 대상 동 : "
        f"{covered_dongs}/25"
    )


    # =====================================================
    # 동별 거래 건수
    # =====================================================

    print()
    print(
        "[25개 동 실제 행정동 기준 거래건수]"
    )


    counts = (

        target_df[
            "프로젝트지역"
        ]

        .value_counts()

    )


    for region, count in (
        counts.items()
    ):

        print(
            f"- {region} : "
            f"{count:,}건"
        )


    # =====================================================
    # 첨단1동 / 첨단2동 확인
    # =====================================================

    print()
    print(
        "[첨단동 매핑 확인]"
    )


    cheomdan = target_df[
        target_df[
            "프로젝트행정동"
        ].isin(
            [
                "첨단1동",
                "첨단2동"
            ]
        )
    ]


    if not cheomdan.empty:

        check = (

            cheomdan

            .groupby(
                [
                    "공식자치구",
                    "공식행정동",
                    "프로젝트자치구",
                    "프로젝트행정동"
                ]
            )

            .size()

            .reset_index(
                name="거래건수"
            )

        )


        print(
            check.to_string(
                index=False
            )
        )


    # =====================================================
    # 저장 위치
    # =====================================================

    print()
    print(
        "----------------------------------------"
    )

    print(
        "전체 상세 매핑 파일"
    )

    print(
        OUTPUT_ALL_FILE
    )


    print()
    print(
        "25개 동 실거래 파일"
    )

    print(
        OUTPUT_TARGET_FILE
    )

    print(
        "----------------------------------------"
    )


if __name__ == "__main__":

    main()