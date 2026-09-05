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

RAW_FILE = (
    BASE_DIR
    / "data"
    / "raw"
    / "공공임대주택_광주_원본.csv"
)

PROCESSED_DIR = (
    BASE_DIR
    / "data"
    / "processed"
)

PROCESSED_DIR.mkdir(
    parents=True,
    exist_ok=True
)


CACHE_FILE = (
    PROCESSED_DIR
    / "공공임대_주소행정동_캐시.csv"
)

DETAIL_FILE = (
    PROCESSED_DIR
    / "공공임대주택_공급단위_행정동매핑.csv"
)

SUMMARY_FILE = (
    PROCESSED_DIR
    / "동별_공공임대주택.csv"
)

FAIL_FILE = (
    PROCESSED_DIR
    / "공공임대_주소매핑실패_점검.csv"
)

AMBIGUOUS_FILE = (
    PROCESSED_DIR
    / "공공임대_공급단위_다중행정동_점검.csv"
)

HOUSEHOLD_MISMATCH_FILE = (
    PROCESSED_DIR
    / "공공임대_공급단위_세대수불일치_점검.csv"
)


# =========================================================
# 2. 프로젝트 25개 동
# =========================================================

TARGET_DONGS = [

    ("동구", "충장동"),
    ("동구", "계림1동"),
    ("동구", "지산2동"),
    ("동구", "학동"),
    ("동구", "지원1동"),

    ("서구", "치평동"),
    ("서구", "풍암동"),
    ("서구", "화정2동"),
    ("서구", "농성1동"),
    ("서구", "금호1동"),

    ("남구", "봉선2동"),
    ("남구", "진월동"),
    ("남구", "방림1동"),
    ("남구", "효덕동"),
    ("남구", "송암동"),

    ("북구", "용봉동"),
    ("북구", "두암2동"),
    ("북구", "운암1동"),
    ("북구", "첨단2동"),
    ("북구", "문흥1동"),

    ("광산구", "첨단1동"),
    ("광산구", "수완동"),
    ("광산구", "신가동"),
    ("광산구", "우산동"),
    ("광산구", "송정1동")
]

TARGET_SET = set(
    TARGET_DONGS
)


# =========================================================
# 3. Kakao API
# =========================================================

load_dotenv(
    BASE_DIR / ".env",
    override=True
)

KAKAO_KEY = os.getenv(
    "KAKAO_REST_API_KEY"
)

if not KAKAO_KEY:

    raise ValueError(
        ".env에서 KAKAO_REST_API_KEY를 "
        "찾을 수 없습니다."
    )


HEADERS = {
    "Authorization":
        f"KakaoAK {KAKAO_KEY}"
}


ADDRESS_API = (
    "https://dapi.kakao.com/"
    "v2/local/search/address.json"
)

REGION_API = (
    "https://dapi.kakao.com/"
    "v2/local/geo/coord2regioncode.json"
)


# =========================================================
# 4. 주소 정리
# =========================================================

def clean_text(value):

    if pd.isna(value):
        return ""

    return str(
        value
    ).strip()


def normalize_address(address):

    address = clean_text(
        address
    )

    if not address:

        return ""

    # 새 공공데이터 주소 표기 → Kakao 검색용 주소명
    address = address.replace(
        "전남광주통합특별시",
        "광주광역시"
    )

    address = address.replace(
        "광주통합특별시",
        "광주광역시"
    )

    return " ".join(
        address.split()
    )


# =========================================================
# 5. Kakao 주소 검색
# =========================================================

def search_address(
    session,
    address
):

    normalized = normalize_address(
        address
    )

    candidates = []

    for candidate in [
        normalized,
        clean_text(address)
    ]:

        if (
            candidate
            and candidate not in candidates
        ):
            candidates.append(
                candidate
            )


    for query in candidates:

        response = session.get(
            ADDRESS_API,
            headers=HEADERS,
            params={
                "query":
                    query
            },
            timeout=20
        )

        response.raise_for_status()

        data = response.json()

        documents = data.get(
            "documents",
            []
        )

        if documents:

            first = documents[0]

            return {
                "검색주소":
                    query,

                "경도":
                    float(
                        first["x"]
                    ),

                "위도":
                    float(
                        first["y"]
                    ),

                "카카오매칭주소":
                    clean_text(
                        first.get(
                            "address_name",
                            ""
                        )
                    )
            }


    return None


# =========================================================
# 6. 좌표 → 공식 행정동
# =========================================================

def reverse_admin_dong(
    session,
    longitude,
    latitude
):

    response = session.get(
        REGION_API,
        headers=HEADERS,
        params={
            "x":
                longitude,

            "y":
                latitude
        },
        timeout=20
    )

    response.raise_for_status()

    data = response.json()

    documents = data.get(
        "documents",
        []
    )


    # H = 행정동
    for document in documents:

        if (
            clean_text(
                document.get(
                    "region_type",
                    ""
                )
            )
            == "H"
        ):

            return {
                "공식시도":
                    clean_text(
                        document.get(
                            "region_1depth_name",
                            ""
                        )
                    ),

                "공식자치구":
                    clean_text(
                        document.get(
                            "region_2depth_name",
                            ""
                        )
                    ),

                "공식행정동":
                    clean_text(
                        document.get(
                            "region_3depth_name",
                            ""
                        )
                    ),

                "공식행정동코드":
                    clean_text(
                        document.get(
                            "code",
                            ""
                        )
                    )
            }


    return None


# =========================================================
# 7. 공식 행정동 → 프로젝트 표기
# =========================================================

def to_project_region(
    official_gu,
    official_dong
):

    official_gu = clean_text(
        official_gu
    )

    official_dong = clean_text(
        official_dong
    )


    # 프로젝트 내부 표기 유지
    # 공식 첨단2동은 광산구
    if (
        official_gu == "광산구"
        and official_dong == "첨단2동"
    ):

        return (
            "북구",
            "첨단2동"
        )


    return (
        official_gu,
        official_dong
    )


# =========================================================
# 8. 주소 캐시 저장
# =========================================================

CACHE_COLUMNS = [

    "원본주소",
    "정규화주소",

    "검색주소",

    "경도",
    "위도",

    "카카오매칭주소",

    "공식시도",
    "공식자치구",
    "공식행정동",
    "공식행정동코드",

    "프로젝트자치구",
    "프로젝트행정동",

    "매핑상태",
    "오류내용"
]


def save_cache(
    rows
):

    cache_df = pd.DataFrame(
        rows
    )

    for column in CACHE_COLUMNS:

        if column not in cache_df.columns:

            cache_df[
                column
            ] = ""


    cache_df = cache_df[
        CACHE_COLUMNS
    ]


    cache_df.to_csv(
        CACHE_FILE,
        index=False,
        encoding="utf-8-sig"
    )


# =========================================================
# 9. 주소 전체 매핑
# =========================================================

def map_addresses(
    addresses
):

    print()
    print(
        "========================================"
    )

    print(
        "공공임대 주소 → 행정동 매핑"
    )

    print(
        "========================================"
    )


    # -----------------------------------------------------
    # 기존 성공 캐시 불러오기
    # -----------------------------------------------------

    cache_rows = []

    success_cache = {}


    if CACHE_FILE.exists():

        old_cache = pd.read_csv(
            CACHE_FILE,
            encoding="utf-8-sig"
        )


        for _, row in old_cache.iterrows():

            row_dict = row.to_dict()

            address = clean_text(
                row_dict.get(
                    "원본주소",
                    ""
                )
            )

            status = clean_text(
                row_dict.get(
                    "매핑상태",
                    ""
                )
            )


            # 실패 주소는 재시도
            if (
                address
                and status == "성공"
            ):

                success_cache[
                    address
                ] = row_dict


        cache_rows.extend(
            success_cache.values()
        )


    session = requests.Session()


    total = len(
        addresses
    )

    success_count = len(
        success_cache
    )


    print(
        f"전체 고유 주소 : "
        f"{total:,}개"
    )

    print(
        f"기존 성공 캐시 : "
        f"{success_count:,}개"
    )


    new_count = 0


    for index, address in enumerate(
        addresses,
        start=1
    ):

        if address in success_cache:

            continue


        result = {

            "원본주소":
                address,

            "정규화주소":
                normalize_address(
                    address
                ),

            "검색주소":
                "",

            "경도":
                pd.NA,

            "위도":
                pd.NA,

            "카카오매칭주소":
                "",

            "공식시도":
                "",

            "공식자치구":
                "",

            "공식행정동":
                "",

            "공식행정동코드":
                "",

            "프로젝트자치구":
                "",

            "프로젝트행정동":
                "",

            "매핑상태":
                "실패",

            "오류내용":
                ""
        }


        try:

            geocode = search_address(
                session,
                address
            )


            if geocode is None:

                result[
                    "오류내용"
                ] = "주소검색 결과 없음"


            else:

                admin = reverse_admin_dong(

                    session,

                    geocode[
                        "경도"
                    ],

                    geocode[
                        "위도"
                    ]

                )


                if admin is None:

                    result[
                        "오류내용"
                    ] = "행정동 변환 결과 없음"


                else:

                    (
                        project_gu,
                        project_dong
                    ) = to_project_region(

                        admin[
                            "공식자치구"
                        ],

                        admin[
                            "공식행정동"
                        ]

                    )


                    result.update(
                        geocode
                    )

                    result.update(
                        admin
                    )

                    result[
                        "프로젝트자치구"
                    ] = project_gu

                    result[
                        "프로젝트행정동"
                    ] = project_dong

                    result[
                        "매핑상태"
                    ] = "성공"


        except requests.RequestException as error:

            result[
                "오류내용"
            ] = (
                "Kakao API 오류: "
                + str(error)
            )


        except Exception as error:

            result[
                "오류내용"
            ] = str(
                error
            )


        cache_rows.append(
            result
        )

        new_count += 1


        if (
            new_count % 25 == 0
        ):

            save_cache(
                cache_rows
            )


            print(
                f"진행 : "
                f"{index:,}/{total:,}"
            )


        # API 연속 호출 간격
        time.sleep(
            0.05
        )


    save_cache(
        cache_rows
    )


    cache_df = pd.read_csv(
        CACHE_FILE,
        encoding="utf-8-sig"
    )


    success = cache_df[
        cache_df[
            "매핑상태"
        ]
        == "성공"
    ]


    fail = cache_df[
        cache_df[
            "매핑상태"
        ]
        != "성공"
    ]


    print()
    print(
        "----------------------------------------"
    )

    print(
        "주소 매핑 결과"
    )

    print(
        "----------------------------------------"
    )


    print(
        f"성공 : "
        f"{len(success):,}개"
    )

    print(
        f"실패 : "
        f"{len(fail):,}개"
    )


    fail.to_csv(
        FAIL_FILE,
        index=False,
        encoding="utf-8-sig"
    )


    return cache_df


# =========================================================
# 10. 공급단위 생성
#
# 최종 세대수 집계 단위:
# hsmpSn + suplyTyNm
# =========================================================

def make_supply_units(
    raw_df,
    cache_df
):

    print()
    print(
        "========================================"
    )

    print(
        "공공임대 공급단위 생성"
    )

    print(
        "========================================"
    )


    mapping_columns = [

        "원본주소",

        "공식자치구",
        "공식행정동",

        "프로젝트자치구",
        "프로젝트행정동",

        "매핑상태"
    ]


    mapping = cache_df[
        mapping_columns
    ].copy()


    mapping = mapping.rename(
        columns={
            "원본주소":
                "rnAdres"
        }
    )


    df = pd.merge(
        raw_df,
        mapping,
        on="rnAdres",
        how="left",
        validate="many_to_one"
    )


    # -----------------------------------------------------
    # 숫자형
    # -----------------------------------------------------

    df[
        "hshldCo"
    ] = pd.to_numeric(
        df[
            "hshldCo"
        ],
        errors="coerce"
    )


    if (
        "suplyPrvuseAr"
        in df.columns
    ):

        df[
            "suplyPrvuseAr"
        ] = pd.to_numeric(
            df[
                "suplyPrvuseAr"
            ],
            errors="coerce"
        )


    # -----------------------------------------------------
    # 그룹 생성
    # -----------------------------------------------------

    supply_rows = []

    household_mismatch_rows = []

    ambiguous_rows = []


    for (
        hsmp_sn,
        supply_type
    ), group in df.groupby(
        [
            "hsmpSn",
            "suplyTyNm"
        ],
        dropna=False
    ):


        household_values = (

            group[
                "hshldCo"
            ]

            .dropna()

            .unique()

        )


        if len(
            household_values
        ) != 1:

            household_mismatch_rows.append(
                {
                    "hsmpSn":
                        hsmp_sn,

                    "공급유형":
                        supply_type,

                    "원본행수":
                        len(group),

                    "세대수_고유값":
                        ", ".join(
                            [
                                str(value)
                                for value
                                in household_values
                            ]
                        )
                }
            )

            continue


        # -------------------------------------------------
        # 프로젝트 행정동 확인
        # -------------------------------------------------

        mapped_group = group[
            group[
                "매핑상태"
            ]
            == "성공"
        ].copy()


        project_locations = (

            mapped_group[
                [
                    "프로젝트자치구",
                    "프로젝트행정동"
                ]
            ]

            .drop_duplicates()

        )


        official_locations = (

            mapped_group[
                [
                    "공식자치구",
                    "공식행정동"
                ]
            ]

            .drop_duplicates()

        )


        if len(
            project_locations
        ) > 1:

            ambiguous_rows.append(
                {
                    "hsmpSn":
                        hsmp_sn,

                    "공급유형":
                        supply_type,

                    "대표세대수":
                        household_values[0],

                    "프로젝트행정동수":
                        len(
                            project_locations
                        ),

                    "프로젝트행정동":
                        " | ".join(
                            (
                                project_locations[
                                    "프로젝트자치구"
                                ].astype(str)
                                + " "
                                + project_locations[
                                    "프로젝트행정동"
                                ].astype(str)
                            ).tolist()
                        ),

                    "주소":
                        " | ".join(
                            group[
                                "rnAdres"
                            ]
                            .dropna()
                            .astype(str)
                            .drop_duplicates()
                            .tolist()
                        )
                }
            )

            continue


        if len(
            project_locations
        ) == 1:

            project_gu = clean_text(
                project_locations.iloc[
                    0
                ][
                    "프로젝트자치구"
                ]
            )

            project_dong = clean_text(
                project_locations.iloc[
                    0
                ][
                    "프로젝트행정동"
                ]
            )


        else:

            project_gu = ""

            project_dong = ""


        if len(
            official_locations
        ) == 1:

            official_gu = clean_text(
                official_locations.iloc[
                    0
                ][
                    "공식자치구"
                ]
            )

            official_dong = clean_text(
                official_locations.iloc[
                    0
                ][
                    "공식행정동"
                ]
            )


        else:

            official_gu = ""

            official_dong = ""


        addresses = (

            group[
                "rnAdres"
            ]

            .dropna()

            .astype(str)

            .drop_duplicates()

            .tolist()

        )


        source_gu_values = (

            group[
                "signguNm"
            ]

            .dropna()

            .astype(str)

            .drop_duplicates()

            .tolist()

        )


        areas = []

        if (
            "suplyPrvuseAr"
            in group.columns
        ):

            areas = (

                group[
                    "suplyPrvuseAr"
                ]

                .dropna()

                .tolist()

            )


        supply_rows.append(
            {
                "hsmpSn":
                    hsmp_sn,

                "공급유형":
                    clean_text(
                        supply_type
                    ),

                "대표세대수":
                    float(
                        household_values[0]
                    ),

                "원본행수":
                    len(group),

                "원본자치구":
                    " | ".join(
                        source_gu_values
                    ),

                "주소수":
                    len(
                        addresses
                    ),

                "주소":
                    " | ".join(
                        addresses
                    ),

                "전용면적_최소":
                    (
                        min(areas)
                        if areas
                        else pd.NA
                    ),

                "전용면적_최대":
                    (
                        max(areas)
                        if areas
                        else pd.NA
                    ),

                "공식자치구":
                    official_gu,

                "공식행정동":
                    official_dong,

                "프로젝트자치구":
                    project_gu,

                "프로젝트행정동":
                    project_dong,

                "25개동포함여부":
                    (
                        project_gu,
                        project_dong
                    )
                    in TARGET_SET
            }
        )


    supply_df = pd.DataFrame(
        supply_rows
    )


    mismatch_df = pd.DataFrame(
        household_mismatch_rows
    )


    ambiguous_df = pd.DataFrame(
        ambiguous_rows
    )


    mismatch_df.to_csv(
        HOUSEHOLD_MISMATCH_FILE,
        index=False,
        encoding="utf-8-sig"
    )


    ambiguous_df.to_csv(
        AMBIGUOUS_FILE,
        index=False,
        encoding="utf-8-sig"
    )


    supply_df.to_csv(
        DETAIL_FILE,
        index=False,
        encoding="utf-8-sig"
    )


    print()
    print(
        f"공급단위 전체 : "
        f"{len(supply_df):,}개"
    )

    print(
        f"세대수 불일치 공급단위 : "
        f"{len(mismatch_df):,}개"
    )

    print(
        f"여러 행정동에 걸친 공급단위 : "
        f"{len(ambiguous_df):,}개"
    )


    return (
        supply_df,
        mismatch_df,
        ambiguous_df
    )


# =========================================================
# 11. 25개 동별 집계
# =========================================================

def summarize_25_dongs(
    supply_df
):

    print()
    print(
        "========================================"
    )

    print(
        "25개 동 공공임대 집계"
    )

    print(
        "========================================"
    )


    base = pd.DataFrame(
        TARGET_DONGS,
        columns=[
            "자치구",
            "행정동"
        ]
    )


    base[
        "지역"
    ] = (

        base[
            "자치구"
        ]

        + " "

        + base[
            "행정동"
        ]

    )


    base[
        "공식조회자치구"
    ] = base[
        "자치구"
    ]


    base.loc[
        (
            base[
                "자치구"
            ]
            == "북구"
        )
        &
        (
            base[
                "행정동"
            ]
            == "첨단2동"
        ),
        "공식조회자치구"
    ] = "광산구"


    target = supply_df[
        supply_df[
            "25개동포함여부"
        ]
        == True
    ].copy()


    target[
        "지역"
    ] = (

        target[
            "프로젝트자치구"
        ]

        + " "

        + target[
            "프로젝트행정동"
        ]

    )


    # -----------------------------------------------------
    # 전체 집계
    # -----------------------------------------------------

    overall = (

        target

        .groupby(
            "지역"
        )

        .agg(
            공공임대_공급단위수=(
                "hsmpSn",
                "size"
            ),

            공공임대_세대수=(
                "대표세대수",
                "sum"
            )
        )

        .reset_index()

    )


    result = pd.merge(
        base,
        overall,
        on="지역",
        how="left"
    )


    result[
        "공공임대_공급단위수"
    ] = (

        result[
            "공공임대_공급단위수"
        ]

        .fillna(0)

        .astype(int)

    )


    result[
        "공공임대_세대수"
    ] = (

        result[
            "공공임대_세대수"
        ]

        .fillna(0)

        .round()

        .astype(int)

    )


    # -----------------------------------------------------
    # 공급유형별 세대수와 공급단위 수
    # -----------------------------------------------------

    supply_types = [

        "매입임대",
        "국민임대",
        "행복주택",
        "영구임대",
        "10년임대",
        "50년임대"
    ]


    for supply_type in supply_types:

        temp = target[
            target[
                "공급유형"
            ]
            == supply_type
        ]


        type_summary = (

            temp

            .groupby(
                "지역"
            )

            .agg(
                공급단위수=(
                    "hsmpSn",
                    "size"
                ),

                세대수=(
                    "대표세대수",
                    "sum"
                )
            )

            .reset_index()

        )


        type_summary = type_summary.rename(
            columns={
                "공급단위수":
                    (
                        supply_type
                        + "_공급단위수"
                    ),

                "세대수":
                    (
                        supply_type
                        + "_세대수"
                    )
            }
        )


        result = pd.merge(
            result,
            type_summary,
            on="지역",
            how="left"
        )


        for column in [

            supply_type
            + "_공급단위수",

            supply_type
            + "_세대수"

        ]:

            result[
                column
            ] = (

                result[
                    column
                ]

                .fillna(0)

                .round()

                .astype(int)

            )


    result.to_csv(
        SUMMARY_FILE,
        index=False,
        encoding="utf-8-sig"
    )


    # -----------------------------------------------------
    # 결과 출력
    # -----------------------------------------------------

    print()
    print(
        f"25개 동에 포함된 공급단위 : "
        f"{len(target):,}개"
    )

    print(
        f"25개 동 공공임대 세대수 : "
        f"{int(target['대표세대수'].sum()):,}세대"
    )


    zero = result[
        result[
            "공공임대_세대수"
        ]
        == 0
    ]


    print(
        f"공공임대 0세대 동 : "
        f"{len(zero)}개"
    )


    if not zero.empty:

        print()
        print(
            "[공공임대 0세대 동]"
        )

        for region in zero[
            "지역"
        ].tolist():

            print(
                "-",
                region
            )


    print()
    print(
        "[25개 동 공공임대 현황]"
    )


    display_columns = [

        "지역",

        "공공임대_공급단위수",

        "공공임대_세대수",

        "매입임대_세대수",

        "국민임대_세대수",

        "행복주택_세대수",

        "영구임대_세대수"
    ]


    print(
        result[
            display_columns
        ].to_string(
            index=False
        )
    )


    return result


# =========================================================
# 12. 메인
# =========================================================

def main():

    print()
    print(
        "========================================"
    )

    print(
        "공공임대주택 행정동 매핑 시작"
    )

    print(
        "========================================"
    )


    if not RAW_FILE.exists():

        print()
        print(
            "원본 파일이 없습니다."
        )

        print(
            RAW_FILE
        )

        return


    raw_df = pd.read_csv(
        RAW_FILE,
        encoding="utf-8-sig"
    )


    required_columns = [

        "hsmpSn",
        "suplyTyNm",
        "hshldCo",
        "rnAdres",
        "signguNm"
    ]


    missing = [

        column

        for column
        in required_columns

        if column
        not in raw_df.columns

    ]


    if missing:

        print()
        print(
            "필수 컬럼이 없습니다."
        )

        for column in missing:

            print(
                "-",
                column
            )

        return


    raw_df[
        "rnAdres"
    ] = (

        raw_df[
            "rnAdres"
        ]

        .fillna("")

        .astype(str)

        .str.strip()

    )


    addresses = (

        raw_df[
            "rnAdres"
        ]

        .replace(
            "",
            pd.NA
        )

        .dropna()

        .drop_duplicates()

        .tolist()

    )


    # =====================================================
    # 주소 → 행정동
    # =====================================================

    cache_df = map_addresses(
        addresses
    )


    # =====================================================
    # 공급단위 생성
    # =====================================================

    (
        supply_df,
        mismatch_df,
        ambiguous_df
    ) = make_supply_units(
        raw_df,
        cache_df
    )


    # =====================================================
    # 품질 문제 있으면 집계 중단
    # =====================================================

    if not mismatch_df.empty:

        print()
        print(
            "========================================"
        )

        print(
            "집계 중단"
        )

        print(
            "========================================"
        )

        print()
        print(
            "hsmpSn + 공급유형 안에서 "
            "세대수가 다시 불일치했습니다."
        )

        print(
            HOUSEHOLD_MISMATCH_FILE
        )

        return


    if not ambiguous_df.empty:

        print()
        print(
            "========================================"
        )

        print(
            "집계 중단"
        )

        print(
            "========================================"
        )

        print()
        print(
            "하나의 공급단위가 여러 행정동에 "
            "걸쳐 있는 경우가 있습니다."
        )

        print(
            AMBIGUOUS_FILE
        )

        return


    # =====================================================
    # 주소 매핑 실패 개수
    # =====================================================

    failed_units = supply_df[
        (
            supply_df[
                "프로젝트자치구"
            ]
            == ""
        )
        |
        (
            supply_df[
                "프로젝트행정동"
            ]
            == ""
        )
    ]


    if not failed_units.empty:

        print()
        print(
            "========================================"
        )

        print(
            "집계 주의"
        )

        print(
            "========================================"
        )

        print()
        print(
            f"행정동을 확정하지 못한 공급단위 : "
            f"{len(failed_units):,}개"
        )

        print(
            "이 공급단위는 25개 동 집계에서 "
            "자동 제외됩니다."
        )


    # =====================================================
    # 25개 동 집계
    # =====================================================

    summarize_25_dongs(
        supply_df
    )


    print()
    print(
        "========================================"
    )

    print(
        "행정동 매핑 및 집계 완료"
    )

    print(
        "========================================"
    )


    print()
    print(
        "공급단위 상세:"
    )

    print(
        DETAIL_FILE
    )


    print()
    print(
        "25개 동 요약:"
    )

    print(
        SUMMARY_FILE
    )


    print()
    print(
        "주소 매핑 실패:"
    )

    print(
        FAIL_FILE
    )


    print()
    print(
        "※ 아직 이 공공임대 세대수를 "
        "HL-Score에 반영하지 않습니다."
    )

    print(
        "※ 다음 단계에서 청년 대상성 및 "
        "공급유형별 활용 기준을 검토합니다."
    )


# =========================================================
# 실행
# =========================================================

if __name__ == "__main__":

    main()