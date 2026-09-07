from pathlib import Path

import pandas as pd


# =========================================================
# 1. 경로 설정
# =========================================================

BASE_DIR = Path(__file__).resolve().parent.parent

PROCESSED_DIR = (
    BASE_DIR
    / "data"
    / "processed"
)

# 새 정책방향 + 청년 공공시설까지 반영된 파일
POLICY_FILE = (
    PROCESSED_DIR
    / "청년주거환경_정책통합분석_공공시설반영.csv"
)

# 기존 공공임대 분석 결과
# ※ 여기의 1,000명당 / TOP10 후보값은 참고용으로만 보존
RENTAL_FILE = (
    PROCESSED_DIR
    / "2030_청년인구_대비_공공임대_분석.csv"
)

OUTPUT_FILE = (
    PROCESSED_DIR
    / "청년주거환경_정책통합분석_공공시설_공공임대반영.csv"
)


# =========================================================
# 2. 보조 함수
# =========================================================

def clean_text(value):

    if pd.isna(value):
        return ""

    text = str(value).strip()

    if text.lower() in [
        "nan",
        "none"
    ]:
        return ""

    return text


def to_bool(value):

    if isinstance(value, bool):
        return value

    text = str(value).strip().lower()

    return text in [
        "true",
        "1",
        "yes",
        "y"
    ]


def ensure_region(df):

    result = df.copy()

    if "지역" in result.columns:

        result["지역"] = (
            result["지역"]
            .astype(str)
            .str.strip()
        )

        return result

    if (
        "자치구" in result.columns
        and
        "행정동" in result.columns
    ):

        result["지역"] = (
            result["자치구"]
            .astype(str)
            .str.strip()
            + " "
            + result["행정동"]
            .astype(str)
            .str.strip()
        )

        return result

    raise ValueError(
        "지역 컬럼을 만들 수 없습니다."
    )


# =========================================================
# 3. 새 정책방향의 공공임대 보조근거
# =========================================================

def make_rental_evidence(row):

    vulnerable = to_bool(
        row.get(
            "청년인구_상대취약",
            False
        )
    )

    rental_count = int(
        row.get(
            "공공임대_세대수",
            0
        )
    )

    rental_median = float(
        row.get(
            "공공임대_세대수_중앙값",
            0
        )
    )

    happy_count = int(
        row.get(
            "행복주택_세대수",
            0
        )
    )

    candidate = to_bool(
        row.get(
            "청년유입정착_공공임대지원후보",
            False
        )
    )

    if not vulnerable:

        return (
            "청년인구 상대취약지역이 아니므로 "
            "청년 유입·정착 공공주거 지원후보에서 제외. "
            "공공임대 공급량은 정책 참고자료로만 사용."
        )

    if candidate:

        text = (
            f"2030 인구수와 비율이 모두 상대적으로 낮고, "
            f"공공임대가 {rental_count:,}세대로 "
            f"25개 동 중앙값 {rental_median:,.0f}세대보다 적어 "
            "청년 유입·정착을 위한 공공주거 공급여건의 "
            "추가 점검이 필요한 지역."
        )

        if happy_count == 0:

            text += (
                " 수집된 자료에서 행복주택 공급도 확인되지 않아 "
                "청년 입주 가능 주택의 실제 공급여건을 별도 확인할 필요가 있음."
            )

        return text

    return (
        f"2030 인구수와 비율은 모두 상대적으로 낮지만, "
        f"공공임대 {rental_count:,}세대로 25개 동 중앙값 "
        f"{rental_median:,.0f}세대 이상이어서 "
        "전체 공공임대 절대 공급 부족 신호는 확인되지 않음. "
        "다만 전체 공공임대는 청년 전용 공급량이 아니므로 "
        "실제 청년 입주 가능 물량은 별도 확인이 필요함."
    )


# =========================================================
# 4. 통합 신호
# =========================================================

def make_rental_signal(row):

    vulnerable = to_bool(
        row.get(
            "청년인구_상대취약",
            False
        )
    )

    candidate = to_bool(
        row.get(
            "청년유입정착_공공임대지원후보",
            False
        )
    )

    policy_type = clean_text(
        row.get(
            "최종정책유형",
            ""
        )
    )

    existing_signal = (
        policy_type
        not in [
            "",
            "일반 관찰",
            "HL순위 제외"
        ]
    )

    if candidate and existing_signal:

        return (
            "기존 정책신호 + "
            "청년 유입·정착 공공주거 공급 점검"
        )

    if candidate:

        return (
            "청년 유입·정착 공공주거 공급 점검"
        )

    if vulnerable:

        return (
            "청년인구 상대취약 · "
            "전체 공공임대 절대 공급 부족신호 없음"
        )

    return "공공임대 보조지표 참고"


# =========================================================
# 5. 메인
# =========================================================

def main():

    print()
    print("=" * 68)
    print("공공임대 → 정책통합분석 병합")
    print("정책방향: 청년이 상대적으로 적은 지역의 유입·정착 지원")
    print("=" * 68)

    if not POLICY_FILE.exists():

        raise FileNotFoundError(
            f"정책통합 파일이 없습니다: {POLICY_FILE}"
        )

    if not RENTAL_FILE.exists():

        raise FileNotFoundError(
            f"공공임대 분석 파일이 없습니다: {RENTAL_FILE}"
        )

    policy_df = pd.read_csv(
        POLICY_FILE,
        encoding="utf-8-sig"
    )

    rental_df = pd.read_csv(
        RENTAL_FILE,
        encoding="utf-8-sig"
    )

    policy_df = ensure_region(
        policy_df
    )

    rental_df = ensure_region(
        rental_df
    )

    print()
    print(
        f"기존 정책통합 : {len(policy_df)}개 지역"
    )

    print(
        f"공공임대 분석 : {len(rental_df)}개 지역"
    )

    if len(policy_df) != 25:

        raise ValueError(
            f"정책통합 데이터가 25개 동이 아닙니다: {len(policy_df)}"
        )

    if len(rental_df) != 25:

        raise ValueError(
            f"공공임대 분석 데이터가 25개 동이 아닙니다: {len(rental_df)}"
        )

    if policy_df["지역"].duplicated().any():

        raise ValueError(
            "정책통합 데이터에 중복 지역이 있습니다."
        )

    if rental_df["지역"].duplicated().any():

        raise ValueError(
            "공공임대 분석 데이터에 중복 지역이 있습니다."
        )

    required_rental_columns = [

        "지역",

        "공공임대_공급단위수",

        "공공임대_세대수",

        "매입임대_세대수",

        "국민임대_세대수",

        "행복주택_세대수",

        "영구임대_세대수"
    ]

    missing = [

        column

        for column
        in required_rental_columns

        if column
        not in rental_df.columns
    ]

    if missing:

        raise ValueError(
            "공공임대 필수 컬럼 누락: "
            + ", ".join(
                missing
            )
        )

    # -----------------------------------------------------
    # 기존 분석값은 참고용으로 최대한 보존
    # 단, 기존 TOP10 후보 컬럼은 새 정책판정에 사용하지 않음
    # -----------------------------------------------------

    rental_columns = [

        "지역",

        "공공임대_공급단위수",

        "공공임대_세대수",

        "매입임대_세대수",

        "국민임대_세대수",

        "행복주택_세대수",

        "영구임대_세대수",

        "공공임대_1000명당",

        "매입임대_1000명당",

        "국민임대_1000명당",

        "행복주택_1000명당",

        "영구임대_1000명당",

        "행복주택_공급비율"
    ]

    rental_columns = [

        column

        for column
        in rental_columns

        if column
        in rental_df.columns
    ]

    merged = pd.merge(

        policy_df,

        rental_df[
            rental_columns
        ],

        on="지역",

        how="left",

        validate="one_to_one"
    )

    if merged["공공임대_세대수"].isna().any():

        missing_regions = (

            merged[
                merged["공공임대_세대수"]
                .isna()
            ]["지역"]

            .tolist()
        )

        raise ValueError(
            "공공임대 데이터가 연결되지 않은 지역: "
            + ", ".join(
                missing_regions
            )
        )

    if "청년인구_상대취약" not in merged.columns:

        raise ValueError(
            "정책통합 파일에 '청년인구_상대취약' 컬럼이 없습니다."
        )

    merged[
        "청년인구_상대취약"
    ] = (
        merged[
            "청년인구_상대취약"
        ]
        .apply(
            to_bool
        )
    )

    # =====================================================
    # 6. 새 정책방향의 공공임대 기준
    #
    # 기존:
    # 2030 인구 TOP10
    # + 청년 1,000명당 공공임대 부족
    # + 행복주택 0
    #
    # 변경:
    # 청년인구 상대취약
    # + 공공임대 절대 세대수가 25개 동 중앙값 미만
    #
    # ※ 전체 공공임대는 청년 전용이 아니므로
    #    '지원후보'가 아니라 '공급여건 점검후보' 성격
    # =====================================================

    public_rental_median = float(
        merged[
            "공공임대_세대수"
        ]
        .median()
    )

    merged[
        "공공임대_세대수_중앙값"
    ] = round(
        public_rental_median,
        2
    )

    merged[
        "공공임대_절대공급부족"
    ] = (
        merged[
            "공공임대_세대수"
        ]
        < public_rental_median
    )

    merged[
        "행복주택_공급없음"
    ] = (
        merged[
            "행복주택_세대수"
        ]
        == 0
    )

    merged[
        "청년유입정착_공공임대지원후보"
    ] = (
        merged[
            "청년인구_상대취약"
        ]
        &
        merged[
            "공공임대_절대공급부족"
        ]
    )

    # 행복주택은 '청년 전용'으로 단정하지 않고 보조신호만 제공
    merged[
        "청년유입정착_행복주택공급공백"
    ] = (
        merged[
            "청년인구_상대취약"
        ]
        &
        merged[
            "행복주택_공급없음"
        ]
    )

    merged[
        "주거지원_보조근거"
    ] = merged.apply(
        make_rental_evidence,
        axis=1
    )

    merged[
        "정책_주거지원_통합신호"
    ] = merged.apply(
        make_rental_signal,
        axis=1
    )

    # HL에는 절대 혼입하지 않음
    merged[
        "공공임대_HL반영여부"
    ] = False

    merged[
        "공공임대지표_역할"
    ] = (
        "HL-Score 미반영 / "
        "청년 유입·정착 공공주거 지원환경 보조지표"
    )

    merged[
        "공공임대_정책유형변경여부"
    ] = False

    merged.to_csv(

        OUTPUT_FILE,

        index=False,

        encoding="utf-8-sig"
    )

    # =====================================================
    # 7. 결과 출력
    # =====================================================

    candidates = merged[
        merged[
            "청년유입정착_공공임대지원후보"
        ]
        == True
    ].copy()

    vulnerable = merged[
        merged[
            "청년인구_상대취약"
        ]
        == True
    ].copy()

    print()
    print("=" * 68)
    print("공공임대 정책통합 완료")
    print("=" * 68)

    print()
    print(
        f"최종 지역 수 : {len(merged)}개"
    )

    print(
        f"25개 동 전체 공공임대 : "
        f"{int(merged['공공임대_세대수'].sum()):,}세대"
    )

    print(
        f"공공임대 절대 공급 중앙값 : "
        f"{public_rental_median:,.0f}세대"
    )

    print(
        f"청년 유입·정착 공공임대 지원후보 : "
        f"{len(candidates)}개"
    )

    print()
    print("-" * 68)
    print("[청년 유입·정착 공공임대 지원후보]")
    print("-" * 68)

    if candidates.empty:

        print(
            "해당 지역 없음"
        )

    else:

        candidates = candidates.sort_values(
            [
                "공공임대_세대수",
                "2030인구비율"
            ],
            ascending=[
                True,
                True
            ]
        )

        for _, row in candidates.iterrows():

            print()

            print(
                f"[{row['지역']}]"
            )

            print(
                "2030 인구 :",
                f"{int(row['2030인구수']):,}명",
                "/",
                f"{float(row['2030인구비율']):.2f}%"
            )

            print(
                "공공임대 :",
                f"{int(row['공공임대_세대수']):,}세대"
            )

            print(
                "행복주택 :",
                f"{int(row['행복주택_세대수']):,}세대"
            )

            print(
                "기존 정책유형 :",
                row.get(
                    "최종정책유형",
                    "-"
                )
            )

            print(
                "통합신호 :",
                row[
                    "정책_주거지원_통합신호"
                ]
            )

    print()
    print("-" * 68)
    print("[청년인구 상대취약 6개 지역 공공임대 현황]")
    print("-" * 68)

    vulnerable = vulnerable.sort_values(
        "2030인구비율",
        ascending=True
    )

    for _, row in vulnerable.iterrows():

        candidate_text = (
            "지원후보"
            if row[
                "청년유입정착_공공임대지원후보"
            ]
            else "절대공급 부족신호 없음"
        )

        print(
            f"- {row['지역']} "
            f"/ 공공임대 {int(row['공공임대_세대수']):,}세대 "
            f"/ 행복주택 {int(row['행복주택_세대수']):,}세대 "
            f"/ {candidate_text}"
        )

    print()
    print("=" * 68)
    print("주의")
    print("=" * 68)

    print(
        "※ 기존 2030인구 TOP10 기준은 사용하지 않습니다."
    )

    print(
        "※ 청년 1,000명당 공공임대 수는 설명용 참고값으로만 유지합니다."
    )

    print(
        "※ 지원후보는 청년인구 상대취약 + 공공임대 절대 세대수 중앙값 미만 기준입니다."
    )

    print(
        "※ 전체 공공임대는 청년 전용 공급량이 아닙니다."
    )

    print(
        "※ 행복주택 역시 모든 세대가 2030 청년에게 배정되는 것은 아닙니다."
    )

    print(
        "※ 공공임대 지표는 HL-Score에 추가하지 않습니다."
    )

    print()
    print(
        "새 파일 저장:"
    )

    print(
        OUTPUT_FILE
    )

    print()


if __name__ == "__main__":
    main()
