from pathlib import Path
import re
import unicodedata

import pandas as pd


# =========================================================
# 1. 경로
# =========================================================

BASE_DIR = Path(__file__).resolve().parent.parent

RAW_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed"

PROCESSED_DIR.mkdir(
    parents=True,
    exist_ok=True
)


STOP_FILE = (
    RAW_DIR
    / "전남광주통합특별시_시내버스 정류소 현황_20251231.csv"
)

ROUTE_FILE = (
    RAW_DIR
    / "광주_시내버스_노선자료_변환.xlsx"
)

POPULATION_FILE = (
    PROCESSED_DIR
    / "동별_2030인구.csv"
)


OUTPUT_SUMMARY = (
    PROCESSED_DIR
    / "동별_버스서비스수준_검토용.csv"
)

OUTPUT_MATCH = (
    PROCESSED_DIR
    / "버스노선_정류소명_매칭점검.csv"
)

OUTPUT_UNMATCHED = (
    PROCESSED_DIR
    / "버스노선_미매칭정류소명.csv"
)

OUTPUT_AMBIGUOUS = (
    PROCESSED_DIR
    / "버스노선_행정동다중매칭점검.csv"
)

OUTPUT_SHEETS = (
    PROCESSED_DIR
    / "버스노선_시트점검.csv"
)

OUTPUT_ROUTE_STOP = (
    PROCESSED_DIR
    / "버스노선_추출정류소.csv"
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
# 3. 제외할 보조/과거 시트
# =========================================================

def should_exclude_sheet(sheet_name):

    name = str(
        sheet_name
    ).strip()


    if name == "Sheet1":

        return True


    # 파일 안에 별도로 존재하는
    # 과거/변경안/계획안 성격의 시트
    keywords = [

        "예정",
        "변경",
        "(8대)"
    ]


    for keyword in keywords:

        if keyword in name:

            return True


    return False


# =========================================================
# 4. 문자열 정리
# =========================================================

def clean_text(value):

    if pd.isna(value):

        return ""

    text = str(
        value
    ).strip()


    if text.lower() in [
        "nan",
        "none"
    ]:

        return ""


    return text


# =========================================================
# 5. 정류소명 기본 정규화
# =========================================================

def normalize_stop_name(value):

    text = clean_text(
        value
    )

    if not text:

        return ""


    text = unicodedata.normalize(
        "NFKC",
        text
    )


    # 여러 공백 → 한 칸
    text = re.sub(
        r"\s+",
        " ",
        text
    )


    return text.strip()


# =========================================================
# 6. 정류소명 느슨한 정규화
#
# 정확히 일치하지 않는 경우에만
# 보조적으로 사용
# =========================================================

def relaxed_stop_name(value):

    text = normalize_stop_name(
        value
    )


    # 공백 제거
    text = re.sub(
        r"\s+",
        "",
        text
    )


    # 일부 표기 차이만 제거
    text = text.replace(
        "·",
        ""
    )

    text = text.replace(
        ".",
        ""
    )


    return text


# =========================================================
# 7. 노선번호 정리
# =========================================================

def normalize_route_name(value):

    text = clean_text(
        value
    )


    if not text:

        return ""


    # Excel에서 숫자 노선이
    # 518.0처럼 읽히는 경우
    if re.fullmatch(
        r"\d+\.0",
        text
    ):

        text = text[:-2]


    # 순환01-A / 순환01-B
    # 같은 노선으로 처리
    text = re.sub(
        r"-(A|B)$",
        "",
        text,
        flags=re.IGNORECASE
    )


    return text.strip()


# =========================================================
# 8. CSV 읽기
# =========================================================

def read_stop_csv():

    encodings = [

        "cp949",
        "euc-kr",
        "utf-8-sig",
        "utf-8"
    ]


    last_error = None


    for encoding in encodings:

        try:

            df = pd.read_csv(
                STOP_FILE,
                encoding=encoding
            )

            print(
                f"정류소 CSV 인코딩 : "
                f"{encoding}"
            )

            return df


        except UnicodeDecodeError as error:

            last_error = error


    raise last_error


# =========================================================
# 9. 공식 지역 → 프로젝트 지역
# =========================================================

def to_project_region(
    gu,
    dong
):

    gu = clean_text(
        gu
    )

    dong = clean_text(
        dong
    )


    # 공식 광산구 첨단2동
    # → 프로젝트 내부 북구 첨단2동
    if (
        gu == "광산구"
        and dong == "첨단2동"
    ):

        return (
            "북구",
            "첨단2동"
        )


    return (
        gu,
        dong
    )


# =========================================================
# 10. 공식 정류소 데이터 준비
# =========================================================

def prepare_stops():

    print()
    print(
        "=" * 55
    )

    print(
        "공식 버스정류소 데이터"
    )

    print(
        "=" * 55
    )


    df = read_stop_csv()


    required = [

        "자치구",
        "정류소번호",
        "정류소명",
        "행정동"
    ]


    missing = [

        column

        for column in required

        if column not in df.columns
    ]


    if missing:

        raise ValueError(
            "정류소 파일 필수 컬럼 누락: "
            + ", ".join(
                missing
            )
        )


    df[
        "정류소번호"
    ] = (

        df[
            "정류소번호"
        ]

        .astype(str)

        .str.replace(
            ".0",
            "",
            regex=False
        )

        .str.strip()

    )


    df[
        "정류소명"
    ] = df[
        "정류소명"
    ].apply(
        normalize_stop_name
    )


    df[
        "정류소명_key"
    ] = df[
        "정류소명"
    ]


    df[
        "정류소명_relaxed"
    ] = df[
        "정류소명"
    ].apply(
        relaxed_stop_name
    )


    project_gu = []
    project_dong = []


    for _, row in df.iterrows():

        gu, dong = to_project_region(

            row[
                "자치구"
            ],

            row[
                "행정동"
            ]

        )


        project_gu.append(
            gu
        )

        project_dong.append(
            dong
        )


    df[
        "프로젝트자치구"
    ] = project_gu


    df[
        "프로젝트행정동"
    ] = project_dong


    df[
        "지역"
    ] = (

        df[
            "프로젝트자치구"
        ]

        + " "

        + df[
            "프로젝트행정동"
        ]

    )


    df[
        "25개동포함여부"
    ] = [

        (
            gu,
            dong
        )
        in TARGET_SET

        for gu, dong in zip(
            df[
                "프로젝트자치구"
            ],
            df[
                "프로젝트행정동"
            ]
        )

    ]


    print()
    print(
        f"전체 공식 정류소 : "
        f"{len(df):,}개"
    )


    print(
        f"고유 정류소번호 : "
        f"{df['정류소번호'].nunique():,}개"
    )


    target_count = int(
        df[
            "25개동포함여부"
        ].sum()
    )


    print(
        f"25개 동 내부 정류소 : "
        f"{target_count:,}개"
    )


    return df


# =========================================================
# 11. 버스 노선 엑셀에서
#     노선 + 정류소 추출
# =========================================================

def extract_route_stops():

    print()
    print(
        "=" * 55
    )

    print(
        "버스 노선 엑셀 분석"
    )

    print(
        "=" * 55
    )


    excel = pd.ExcelFile(
        ROUTE_FILE
    )


    print()
    print(
        f"전체 시트 : "
        f"{len(excel.sheet_names)}개"
    )


    route_stop_rows = []
    sheet_rows = []


    for sheet_name in excel.sheet_names:

        excluded = should_exclude_sheet(
            sheet_name
        )


        if excluded:

            sheet_rows.append(
                {
                    "시트명":
                        sheet_name,

                    "사용여부":
                        "제외",

                    "제외사유":
                        "과거·변경·계획·빈 시트 가능성",

                    "추출행수":
                        0
                }
            )

            continue


        sheet_df = pd.read_excel(
            ROUTE_FILE,
            sheet_name=sheet_name,
            header=None
        )


        if sheet_df.empty:

            sheet_rows.append(
                {
                    "시트명":
                        sheet_name,

                    "사용여부":
                        "제외",

                    "제외사유":
                        "빈 시트",

                    "추출행수":
                        0
                }
            )

            continue


        # -------------------------------------------------
        # 첫 5줄에서 '노선번호' 위치 탐색
        # -------------------------------------------------

        header_positions = []


        max_header_rows = min(
            5,
            len(sheet_df)
        )


        for row_index in range(
            max_header_rows
        ):

            for col_index in range(
                sheet_df.shape[1]
            ):

                value = clean_text(
                    sheet_df.iloc[
                        row_index,
                        col_index
                    ]
                )


                if value == "노선번호":

                    # 바로 오른쪽 열이
                    # 정류소명 열이라고 판단
                    if (
                        col_index + 1
                        < sheet_df.shape[1]
                    ):

                        header_positions.append(
                            (
                                row_index,
                                col_index,
                                col_index + 1
                            )
                        )


        if not header_positions:

            sheet_rows.append(
                {
                    "시트명":
                        sheet_name,

                    "사용여부":
                        "제외",

                    "제외사유":
                        "노선번호 헤더 없음",

                    "추출행수":
                        0
                }
            )

            continue


        extracted_count = 0


        for (
            header_row,
            route_col,
            stop_col
        ) in header_positions:


            for row_index in range(
                header_row + 1,
                len(sheet_df)
            ):

                route = normalize_route_name(
                    sheet_df.iloc[
                        row_index,
                        route_col
                    ]
                )


                stop_name = normalize_stop_name(
                    sheet_df.iloc[
                        row_index,
                        stop_col
                    ]
                )


                if not route:

                    continue


                if not stop_name:

                    continue


                if route == "노선번호":

                    continue


                route_stop_rows.append(
                    {
                        "시트명":
                            sheet_name,

                        "노선":
                            route,

                        "정류소명":
                            stop_name,

                        "정류소명_key":
                            stop_name,

                        "정류소명_relaxed":
                            relaxed_stop_name(
                                stop_name
                            )
                    }
                )


                extracted_count += 1


        sheet_rows.append(
            {
                "시트명":
                    sheet_name,

                "사용여부":
                    "사용",

                "제외사유":
                    "",

                "추출행수":
                    extracted_count
            }
        )


    route_df = pd.DataFrame(
        route_stop_rows
    )


    sheet_check_df = pd.DataFrame(
        sheet_rows
    )


    # 동일 노선이 같은 정류소명을
    # 왕복 방향에서 반복하는 경우 제거
    route_df = (

        route_df

        .drop_duplicates(
            subset=[
                "노선",
                "정류소명_key"
            ]
        )

        .reset_index(
            drop=True
        )

    )


    route_df.to_csv(
        OUTPUT_ROUTE_STOP,
        index=False,
        encoding="utf-8-sig"
    )


    sheet_check_df.to_csv(
        OUTPUT_SHEETS,
        index=False,
        encoding="utf-8-sig"
    )


    used_sheets = int(
        (
            sheet_check_df[
                "사용여부"
            ]
            == "사용"
        ).sum()
    )


    excluded_sheets = len(
        sheet_check_df
    ) - used_sheets


    print()
    print(
        f"사용 시트 : "
        f"{used_sheets}개"
    )

    print(
        f"제외 시트 : "
        f"{excluded_sheets}개"
    )


    excluded_names = (

        sheet_check_df[
            sheet_check_df[
                "사용여부"
            ]
            == "제외"
        ][
            "시트명"
        ]

        .tolist()

    )


    if excluded_names:

        print()
        print(
            "[제외 시트]"
        )

        for name in excluded_names:

            print(
                "-",
                name
            )


    print()
    print(
        f"고유 노선 : "
        f"{route_df['노선'].nunique():,}개"
    )


    print(
        f"고유 노선-정류소명 조합 : "
        f"{len(route_df):,}개"
    )


    return route_df


# =========================================================
# 12. 노선 정류소명 ↔ 공식 정류소 매칭
# =========================================================

def match_route_stops(
    route_df,
    stop_df
):

    print()
    print(
        "=" * 55
    )

    print(
        "노선 정류소명 ↔ 공식 정류소 매칭"
    )

    print(
        "=" * 55
    )


    # -----------------------------------------------------
    # 정확 이름 매칭용
    # -----------------------------------------------------

    exact_map = {}


    for name, group in stop_df.groupby(
        "정류소명_key"
    ):

        exact_map[
            name
        ] = group


    # -----------------------------------------------------
    # 느슨한 이름 매칭용
    # -----------------------------------------------------

    relaxed_map = {}


    for name, group in stop_df.groupby(
        "정류소명_relaxed"
    ):

        relaxed_map[
            name
        ] = group


    match_rows = []


    for _, row in route_df.iterrows():

        route = row[
            "노선"
        ]

        route_stop = row[
            "정류소명"
        ]

        key = row[
            "정류소명_key"
        ]

        relaxed = row[
            "정류소명_relaxed"
        ]


        matched_group = None
        match_method = ""


        # -------------------------------------------------
        # 1차: 정확히 같은 이름
        # -------------------------------------------------

        if key in exact_map:

            matched_group = exact_map[
                key
            ]

            match_method = "정확일치"


        # -------------------------------------------------
        # 2차: 공백/일부 표기 차이
        # -------------------------------------------------

        elif relaxed in relaxed_map:

            candidate = relaxed_map[
                relaxed
            ]


            # 느슨한 키 하나가
            # 실제 서로 다른 정류소명 여러 개로
            # 합쳐지는 경우는 자동 사용하지 않음
            official_names = (

                candidate[
                    "정류소명"
                ]

                .drop_duplicates()

            )


            if len(
                official_names
            ) == 1:

                matched_group = candidate

                match_method = "보조일치"


        # -------------------------------------------------
        # 매칭 실패
        # -------------------------------------------------

        if matched_group is None:

            match_rows.append(
                {
                    "노선":
                        route,

                    "노선파일_정류소명":
                        route_stop,

                    "매칭상태":
                        "미매칭",

                    "매칭방식":
                        "",

                    "공식정류소명":
                        "",

                    "공식정류소수":
                        0,

                    "프로젝트지역수":
                        0,

                    "프로젝트지역":
                        ""
                }
            )

            continue


        # -------------------------------------------------
        # 동일 정류소명이 여러 물리 정류소에
        # 존재할 수 있음
        # -------------------------------------------------

        regions = (

            matched_group[
                [
                    "프로젝트자치구",
                    "프로젝트행정동"
                ]
            ]

            .drop_duplicates()

        )


        region_names = (

            regions[
                "프로젝트자치구"
            ]

            + " "

            + regions[
                "프로젝트행정동"
            ]

        ).tolist()


        official_names = (

            matched_group[
                "정류소명"
            ]

            .drop_duplicates()

            .tolist()

        )


        # -------------------------------------------------
        # 이름 하나가 여러 행정동에 있으면
        # 이름만으로 위치 확정 불가
        # -------------------------------------------------

        if len(
            regions
        ) > 1:

            match_rows.append(
                {
                    "노선":
                        route,

                    "노선파일_정류소명":
                        route_stop,

                    "매칭상태":
                        "행정동모호",

                    "매칭방식":
                        match_method,

                    "공식정류소명":
                        " | ".join(
                            official_names
                        ),

                    "공식정류소수":
                        len(
                            matched_group
                        ),

                    "프로젝트지역수":
                        len(
                            regions
                        ),

                    "프로젝트지역":
                        " | ".join(
                            region_names
                        )
                }
            )

            continue


        region = regions.iloc[
            0
        ]


        project_gu = clean_text(
            region[
                "프로젝트자치구"
            ]
        )

        project_dong = clean_text(
            region[
                "프로젝트행정동"
            ]
        )


        match_rows.append(
            {
                "노선":
                    route,

                "노선파일_정류소명":
                    route_stop,

                "매칭상태":
                    "성공",

                "매칭방식":
                    match_method,

                "공식정류소명":
                    " | ".join(
                        official_names
                    ),

                "공식정류소수":
                    len(
                        matched_group
                    ),

                "프로젝트지역수":
                    1,

                "프로젝트지역":
                    (
                        project_gu
                        + " "
                        + project_dong
                    )
            }
        )


    match_df = pd.DataFrame(
        match_rows
    )


    match_df.to_csv(
        OUTPUT_MATCH,
        index=False,
        encoding="utf-8-sig"
    )


    unmatched_df = match_df[
        match_df[
            "매칭상태"
        ]
        == "미매칭"
    ].copy()


    ambiguous_df = match_df[
        match_df[
            "매칭상태"
        ]
        == "행정동모호"
    ].copy()


    unmatched_df.to_csv(
        OUTPUT_UNMATCHED,
        index=False,
        encoding="utf-8-sig"
    )


    ambiguous_df.to_csv(
        OUTPUT_AMBIGUOUS,
        index=False,
        encoding="utf-8-sig"
    )


    total = len(
        match_df
    )


    success = int(
        (
            match_df[
                "매칭상태"
            ]
            == "성공"
        ).sum()
    )


    unmatched = len(
        unmatched_df
    )


    ambiguous = len(
        ambiguous_df
    )


    match_rate = (

        success
        /
        total
        *
        100

        if total > 0

        else 0

    )


    print()
    print(
        f"전체 노선-정류소명 : "
        f"{total:,}개"
    )

    print(
        f"성공 : "
        f"{success:,}개"
    )

    print(
        f"미매칭 : "
        f"{unmatched:,}개"
    )

    print(
        f"행정동 모호 : "
        f"{ambiguous:,}개"
    )

    print(
        f"안전 매칭률 : "
        f"{match_rate:.2f}%"
    )


    return (
        match_df,
        match_rate
    )


# =========================================================
# 13. 청년인구 준비
# =========================================================

def prepare_population():

    df = pd.read_csv(
        POPULATION_FILE,
        encoding="utf-8-sig"
    )


    if (
        "팀계획_자치구"
        in df.columns
    ):

        gu_column = (
            "팀계획_자치구"
        )


    elif (
        "자치구"
        in df.columns
    ):

        gu_column = (
            "자치구"
        )


    else:

        raise ValueError(
            "청년인구 파일에서 "
            "자치구 컬럼을 찾을 수 없습니다."
        )


    df[
        "지역"
    ] = (

        df[
            gu_column
        ]

        .astype(str)

        .str.strip()

        + " "

        + df[
            "행정동"
        ]

        .astype(str)

        .str.strip()

    )


    df[
        "2030인구수"
    ] = pd.to_numeric(
        df[
            "2030인구수"
        ],
        errors="coerce"
    )


    return df[
        [
            "지역",
            "2030인구수"
        ]
    ]


# =========================================================
# 14. 25개 동 서비스 요약
# =========================================================

def summarize_service(
    stop_df,
    match_df,
    match_rate
):

    print()
    print(
        "=" * 55
    )

    print(
        "25개 동 버스 서비스 수준"
    )

    print(
        "=" * 55
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


    # =====================================================
    # 공식 정류소 수
    # =====================================================

    target_stops = stop_df[
        stop_df[
            "25개동포함여부"
        ]
        == True
    ].copy()


    stop_summary = (

        target_stops

        .groupby(
            "지역"
        )

        .agg(
            공식정류소수=(
                "정류소번호",
                "nunique"
            )
        )

        .reset_index()

    )


    # =====================================================
    # 안전하게 행정동이 확정된 노선만 사용
    # =====================================================

    successful = match_df[
        match_df[
            "매칭상태"
        ]
        == "성공"
    ].copy()


    successful = successful[
        successful[
            "프로젝트지역"
        ].isin(
            base[
                "지역"
            ]
        )
    ].copy()


    route_summary = (

        successful

        .groupby(
            "프로젝트지역"
        )

        .agg(
            확인노선수=(
                "노선",
                "nunique"
            ),

            노선정류소명_연결수=(
                "노선파일_정류소명",
                "size"
            )
        )

        .reset_index()

        .rename(
            columns={
                "프로젝트지역":
                    "지역"
            }
        )

    )


    result = pd.merge(
        base,
        stop_summary,
        on="지역",
        how="left"
    )


    result = pd.merge(
        result,
        route_summary,
        on="지역",
        how="left"
    )


    # =====================================================
    # 청년인구 병합
    # =====================================================

    population_df = (
        prepare_population()
    )


    result = pd.merge(
        result,
        population_df,
        on="지역",
        how="left",
        validate="one_to_one"
    )


    # =====================================================
    # 결측치
    # =====================================================

    for column in [

        "공식정류소수",
        "확인노선수",
        "노선정류소명_연결수"

    ]:

        result[
            column
        ] = (

            result[
                column
            ]

            .fillna(0)

            .astype(int)

        )


    # =====================================================
    # 청년 1,000명당 정류소
    # =====================================================

    result[
        "청년1000명당_정류소수"
    ] = (

        result[
            "공식정류소수"
        ]

        /

        result[
            "2030인구수"
        ]

        * 1000

    ).round(
        2
    )


    # =====================================================
    # 청년 1,000명당 확인 노선 수
    # =====================================================

    result[
        "청년1000명당_확인노선수"
    ] = (

        result[
            "확인노선수"
        ]

        /

        result[
            "2030인구수"
        ]

        * 1000

    ).round(
        2
    )


    # =====================================================
    # 정류소당 노선 연결도
    #
    # 실제 배차빈도가 아니라
    # '노선 다양성' 참고값
    # =====================================================

    result[
        "정류소당_노선연결도_참고"
    ] = 0.0


    valid_stops = (

        result[
            "공식정류소수"
        ]
        > 0

    )


    result.loc[
        valid_stops,
        "정류소당_노선연결도_참고"
    ] = (

        result.loc[
            valid_stops,
            "노선정류소명_연결수"
        ]

        /

        result.loc[
            valid_stops,
            "공식정류소수"
        ]

    ).round(
        2
    )


    # =====================================================
    # 25개 동 상대비교
    # =====================================================

    stop_median = (

        result[
            "청년1000명당_정류소수"
        ]

        .median()

    )


    route_median = (

        result[
            "확인노선수"
        ]

        .median()

    )


    result[
        "정류소공급_상대부족"
    ] = (

        result[
            "청년1000명당_정류소수"
        ]

        < stop_median

    )


    # =====================================================
    # 노선 데이터 품질
    #
    # 매칭률 80% 이상일 때만
    # 상대비교 참고 신호 생성
    # =====================================================

    if match_rate >= 80:

        result[
            "노선다양성_상대부족_참고"
        ] = (

            result[
                "확인노선수"
            ]

            < route_median

        )

        route_quality = (
            "참고 활용 가능"
        )


    else:

        result[
            "노선다양성_상대부족_참고"
        ] = pd.NA

        route_quality = (
            "매칭률 부족 - 정책판단 사용 보류"
        )


    result[
        "노선데이터_안전매칭률"
    ] = round(
        match_rate,
        2
    )


    result[
        "노선데이터_활용판정"
    ] = route_quality


    result[
        "HL반영여부"
    ] = False


    result[
        "지표역할"
    ] = (
        "교통 서비스 보조지표 / "
        "기존 HL 교통점수 미변경"
    )


    result.to_csv(
        OUTPUT_SUMMARY,
        index=False,
        encoding="utf-8-sig"
    )


    print()
    print(
        f"청년 1,000명당 정류소 중앙값 : "
        f"{stop_median:.2f}개"
    )


    print(
        f"확인 노선 수 중앙값 : "
        f"{route_median:.1f}개"
    )


    print(
        f"노선데이터 활용판정 : "
        f"{route_quality}"
    )


    print()
    print(
        "[25개 동 버스서비스 현황]"
    )


    display_columns = [

        "지역",
        "2030인구수",
        "공식정류소수",
        "청년1000명당_정류소수",
        "확인노선수",
        "정류소당_노선연결도_참고"
    ]


    print(

        result[
            display_columns
        ]

        .sort_values(
            "청년1000명당_정류소수",
            ascending=True
        )

        .to_string(
            index=False
        )

    )


    print()
    print(
        "[청년 인구 대비 정류소 공급 낮은 지역 TOP10]"
    )


    low10 = (

        result

        .sort_values(
            "청년1000명당_정류소수",
            ascending=True
        )

        .head(10)

    )


    for _, row in low10.iterrows():

        print(

            f"- {row['지역']} : "
            f"{row['청년1000명당_정류소수']:.2f}개/1,000명 "
            f"({int(row['공식정류소수'])}개 정류소 / "
            f"{int(row['2030인구수']):,}명)"

        )


    return result


# =========================================================
# 15. 메인
# =========================================================

def main():

    print()
    print(
        "=" * 55
    )

    print(
        "광주 25개 동 버스 서비스 분석"
    )

    print(
        "=" * 55
    )


    # =====================================================
    # 파일 확인
    # =====================================================

    files = [

        STOP_FILE,
        ROUTE_FILE,
        POPULATION_FILE

    ]


    for file_path in files:

        if not file_path.exists():

            print()
            print(
                "파일이 없습니다:"
            )

            print(
                file_path
            )

            return


    # =====================================================
    # 공식 정류소
    # =====================================================

    stop_df = prepare_stops()


    # =====================================================
    # 노선 엑셀
    # =====================================================

    route_df = extract_route_stops()


    # =====================================================
    # 정류소명 매칭
    # =====================================================

    (
        match_df,
        match_rate
    ) = match_route_stops(
        route_df,
        stop_df
    )


    # =====================================================
    # 25개 동 분석
    # =====================================================

    summarize_service(
        stop_df,
        match_df,
        match_rate
    )


    # =====================================================
    # 완료
    # =====================================================

    print()
    print(
        "=" * 55
    )

    print(
        "버스 서비스 1차 분석 완료"
    )

    print(
        "=" * 55
    )


    print()
    print(
        "중요:"
    )

    print(
        "※ 공식 정류소 CSV는 "
        "2025-12-31 기준 데이터를 사용했습니다."
    )

    print(
        "※ 노선 엑셀에는 과거·변경안으로 보이는 "
        "보조 시트가 포함되어 있어 일부를 제외했습니다."
    )

    print(
        "※ 노선 엑셀의 정확한 기준시점은 "
        "추가 확인이 필요합니다."
    )

    print(
        "※ 이번 노선 수는 배차간격이나 운행횟수가 아니라 "
        "'노선 다양성' 참고값입니다."
    )

    print(
        "※ 아직 HL-Score에는 반영하지 않습니다."
    )


    print()
    print(
        "저장 파일:"
    )

    print(
        OUTPUT_SUMMARY
    )

    print(
        OUTPUT_MATCH
    )

    print(
        OUTPUT_UNMATCHED
    )

    print(
        OUTPUT_AMBIGUOUS
    )

    print(
        OUTPUT_SHEETS
    )


if __name__ == "__main__":

    main()