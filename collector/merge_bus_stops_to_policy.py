from pathlib import Path

import pandas as pd


# =========================================================
# 1. 경로 설정
# =========================================================

BASE_DIR = Path(__file__).resolve().parent.parent

PROCESSED_DIR = BASE_DIR / "data" / "processed"

POLICY_FILE = (
    PROCESSED_DIR
    / "청년주거환경_정책통합분석_공공시설_공공임대반영.csv"
)

BUS_FILE = (
    PROCESSED_DIR
    / "동별_버스서비스수준_검토용.csv"
)

OUTPUT_FILE = (
    PROCESSED_DIR
    / "청년주거환경_정책통합분석_공공시설_공공임대_버스정류소반영.csv"
)


# =========================================================
# 2. 보조 함수
# =========================================================

def clean_text(value):
    if pd.isna(value):
        return ""

    text = str(value).strip()

    if text.lower() in ["nan", "none"]:
        return ""

    return text


def to_bool(value):
    if isinstance(value, bool):
        return value

    text = str(value).strip().lower()

    return text in ["true", "1", "yes", "y"]


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
        and "행정동" in result.columns
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


def has_existing_policy_signal(policy_type):
    policy_type = clean_text(policy_type)

    return (
        policy_type
        not in [
            "",
            "일반 관찰",
            "HL순위 제외"
        ]
    )


# =========================================================
# 3. 새 정책방향의 버스정류소 보조근거
# =========================================================

def make_bus_note(row):
    vulnerable = to_bool(
        row.get(
            "청년인구_상대취약",
            False
        )
    )

    stop_count = int(
        row.get(
            "공식정류소수",
            0
        )
    )

    stop_median = float(
        row.get(
            "공식정류소수_중앙값",
            0
        )
    )

    per_1000 = float(
        row.get(
            "청년1000명당_정류소수",
            0
        )
    )

    candidate = to_bool(
        row.get(
            "청년유입정착_교통지원후보",
            False
        )
    )

    if not vulnerable:
        return (
            "청년인구 상대취약지역이 아니므로 "
            "청년 유입·정착 교통지원 후보에서 제외. "
            f"공식 정류소 {stop_count:,}개, "
            f"청년 1,000명당 {per_1000:.2f}개는 참고값으로만 사용."
        )

    if candidate:
        return (
            f"2030 인구수와 비율이 모두 상대적으로 낮고, "
            f"행정동 내부 공식 버스정류소가 {stop_count:,}개로 "
            f"25개 동 중앙값 {stop_median:.0f}개보다 적어 "
            "청년 유입·정착을 위한 이동환경과 대중교통 접근성의 "
            "추가 점검이 필요한 지역."
        )

    return (
        f"2030 인구수와 비율은 모두 상대적으로 낮지만, "
        f"공식 버스정류소가 {stop_count:,}개로 "
        f"25개 동 중앙값 {stop_median:.0f}개 이상이어서 "
        "정류소 절대 공급 부족 신호는 확인되지 않음. "
        "다만 정류소 수만으로 배차간격·노선다양성·환승편의까지 "
        "판단할 수는 없음."
    )


# =========================================================
# 4. 기존 정책 + 교통 보조신호
# =========================================================

def make_bus_combined_signal(row):
    policy_type = clean_text(
        row.get(
            "최종정책유형",
            ""
        )
    )

    candidate = to_bool(
        row.get(
            "청년유입정착_교통지원후보",
            False
        )
    )

    vulnerable = to_bool(
        row.get(
            "청년인구_상대취약",
            False
        )
    )

    existing_signal = has_existing_policy_signal(
        policy_type
    )

    if candidate and existing_signal:
        return (
            "기존 정책신호 + "
            "청년 유입·정착 교통환경 점검"
        )

    if candidate:
        return (
            "청년 유입·정착 교통환경 점검"
        )

    if vulnerable:
        return (
            "청년인구 상대취약 · "
            "정류소 절대공급 부족신호 없음"
        )

    if existing_signal:
        return "기존 정책신호"

    return "버스정류소 보조지표 참고"


# =========================================================
# 5. 메인
# =========================================================

def main():
    print()
    print("=" * 68)
    print("공식 버스정류소 → 정책통합분석 병합")
    print("정책방향: 청년이 상대적으로 적은 지역의 유입·정착 지원")
    print("=" * 68)

    if not POLICY_FILE.exists():
        raise FileNotFoundError(
            f"정책통합 파일이 없습니다: {POLICY_FILE}"
        )

    if not BUS_FILE.exists():
        raise FileNotFoundError(
            f"버스 서비스 분석 파일이 없습니다: {BUS_FILE}"
        )

    policy_df = pd.read_csv(
        POLICY_FILE,
        encoding="utf-8-sig"
    )

    bus_df = pd.read_csv(
        BUS_FILE,
        encoding="utf-8-sig"
    )

    policy_df = ensure_region(
        policy_df
    )

    bus_df = ensure_region(
        bus_df
    )

    print()
    print(
        f"기존 정책통합 : {len(policy_df)}개 지역"
    )
    print(
        f"버스 분석 : {len(bus_df)}개 지역"
    )

    if len(policy_df) != 25:
        raise ValueError(
            f"정책통합 데이터가 25개 동이 아닙니다: {len(policy_df)}"
        )

    if len(bus_df) != 25:
        raise ValueError(
            f"버스 분석 데이터가 25개 동이 아닙니다: {len(bus_df)}"
        )

    if policy_df["지역"].duplicated().any():
        raise ValueError(
            "정책통합 파일에 중복 지역이 있습니다."
        )

    if bus_df["지역"].duplicated().any():
        raise ValueError(
            "버스 분석 파일에 중복 지역이 있습니다."
        )

    required_bus_columns = [
        "지역",
        "공식정류소수",
        "청년1000명당_정류소수",
        "노선데이터_안전매칭률",
        "노선데이터_활용판정"
    ]

    missing = [
        column
        for column in required_bus_columns
        if column not in bus_df.columns
    ]

    if missing:
        raise ValueError(
            "버스 분석 필수 컬럼 누락: "
            + ", ".join(missing)
        )

    # -----------------------------------------------------
    # 기존 1,000명당 / 상대부족 지표는 참고용으로 보존
    # 새 정책후보 판정에는 사용하지 않음
    # -----------------------------------------------------

    optional_bus_columns = [
        "정류소공급_상대부족",
        "확인노선수",
        "노선정류소명_연결수",
        "청년1000명당_확인노선수",
        "정류소당_노선연결도_참고"
    ]

    keep_columns = required_bus_columns.copy()

    for column in optional_bus_columns:
        if column in bus_df.columns:
            keep_columns.append(column)

    bus_small = bus_df[
        keep_columns
    ].copy()

    bus_small = bus_small.rename(
        columns={
            "노선데이터_안전매칭률":
                "버스노선데이터_안전매칭률",
            "노선데이터_활용판정":
                "버스노선데이터_활용판정"
        }
    )

    merged = pd.merge(
        policy_df,
        bus_small,
        on="지역",
        how="left",
        validate="one_to_one"
    )

    if merged["공식정류소수"].isna().any():
        missing_regions = (
            merged[
                merged["공식정류소수"]
                .isna()
            ]["지역"]
            .tolist()
        )

        raise ValueError(
            "버스정류소 데이터가 연결되지 않은 지역: "
            + ", ".join(missing_regions)
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
        .apply(to_bool)
    )

    merged[
        "공식정류소수"
    ] = pd.to_numeric(
        merged[
            "공식정류소수"
        ],
        errors="coerce"
    )

    merged[
        "청년1000명당_정류소수"
    ] = pd.to_numeric(
        merged[
            "청년1000명당_정류소수"
        ],
        errors="coerce"
    )

    merged[
        "버스노선데이터_안전매칭률"
    ] = pd.to_numeric(
        merged[
            "버스노선데이터_안전매칭률"
        ],
        errors="coerce"
    )

    # =====================================================
    # 6. 새 정책방향의 버스정류소 기준
    #
    # 기존:
    # 2030 인구 TOP10
    # + 청년 1,000명당 정류소 부족
    #
    # 변경:
    # 청년인구 상대취약
    # + 공식 버스정류소 절대수가 25개 동 중앙값 미만
    #
    # 이유:
    # 청년인구가 적은 지역은 분모가 작아
    # 1,000명당 정류소 수가 높게 보일 수 있으므로,
    # 유입·정착 정책 후보 선정에는 절대 공급량을 사용.
    # =====================================================

    stop_median = float(
        merged[
            "공식정류소수"
        ]
        .median()
    )

    merged[
        "공식정류소수_중앙값"
    ] = round(
        stop_median,
        2
    )

    merged[
        "정류소_절대공급부족"
    ] = (
        merged[
            "공식정류소수"
        ]
        < stop_median
    )

    merged[
        "청년유입정착_교통지원후보"
    ] = (
        merged[
            "청년인구_상대취약"
        ]
        &
        merged[
            "정류소_절대공급부족"
        ]
    )

    # -----------------------------------------------------
    # 보조 해석
    # -----------------------------------------------------

    merged[
        "버스정류소_정책보조해석"
    ] = merged.apply(
        make_bus_note,
        axis=1
    )

    merged[
        "정책_교통공급_통합신호"
    ] = merged.apply(
        make_bus_combined_signal,
        axis=1
    )

    # -----------------------------------------------------
    # HL 미반영 / 노선데이터 제외 명시
    # -----------------------------------------------------

    merged[
        "버스정류소_HL반영여부"
    ] = False

    merged[
        "버스정류소지표_역할"
    ] = (
        "HL-Score 미반영 / "
        "청년 유입·정착 교통환경 보조지표"
    )

    merged[
        "버스노선_정책분석사용여부"
    ] = False

    merged[
        "버스노선_제외사유"
    ] = (
        "노선 정류소명과 공식 정류소 데이터의 "
        "안전 매칭률이 0.54%로 낮아 "
        "노선수·노선다양성 지표는 정책분석에서 제외"
    )

    merged[
        "버스정류소_정책유형변경여부"
    ] = False

    # -----------------------------------------------------
    # 저장
    # -----------------------------------------------------

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
            "청년유입정착_교통지원후보"
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
    print("버스정류소 정책통합 완료")
    print("=" * 68)

    print()
    print(
        f"최종 지역 수 : {len(merged)}개"
    )

    print(
        f"25개 동 공식 정류소 : "
        f"{int(merged['공식정류소수'].sum()):,}개"
    )

    print(
        f"공식 정류소 절대 공급 중앙값 : "
        f"{stop_median:.0f}개"
    )

    print(
        f"청년 유입·정착 교통지원 후보 : "
        f"{len(candidates)}개"
    )

    print()
    print("-" * 68)
    print("[청년 유입·정착 교통지원 후보]")
    print("-" * 68)

    if candidates.empty:
        print("해당 지역 없음")

    else:
        candidates = candidates.sort_values(
            [
                "공식정류소수",
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
                "공식 정류소 :",
                f"{int(row['공식정류소수'])}개"
            )

            print(
                "청년 1,000명당 :",
                f"{float(row['청년1000명당_정류소수']):.2f}개 "
                "(참고값)"
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
                    "정책_교통공급_통합신호"
                ]
            )

    print()
    print("-" * 68)
    print("[청년인구 상대취약 6개 지역 버스정류소 현황]")
    print("-" * 68)

    vulnerable = vulnerable.sort_values(
        "2030인구비율",
        ascending=True
    )

    for _, row in vulnerable.iterrows():
        candidate_text = (
            "교통지원 후보"
            if row[
                "청년유입정착_교통지원후보"
            ]
            else "절대공급 부족신호 없음"
        )

        print(
            f"- {row['지역']} "
            f"/ 정류소 {int(row['공식정류소수'])}개 "
            f"/ {candidate_text}"
        )

    print()
    print("-" * 68)
    print("[버스 노선 데이터 처리]")
    print("-" * 68)

    route_rates = (
        merged[
            "버스노선데이터_안전매칭률"
        ]
        .dropna()
    )

    route_match_rate = (
        float(route_rates.iloc[0])
        if not route_rates.empty
        else 0.54
    )

    print(
        f"안전 매칭률 : {route_match_rate:.2f}%"
    )

    print(
        "정책분석 사용 : False"
    )

    print(
        "노선수·노선다양성 지표는 "
        "최종 정책판단에서 제외합니다."
    )

    print()
    print("=" * 68)
    print("주의")
    print("=" * 68)

    print(
        "※ 기존 2030인구 TOP10 기준은 사용하지 않습니다."
    )

    print(
        "※ 청년 1,000명당 정류소 수는 설명용 참고값으로만 유지합니다."
    )

    print(
        "※ 교통지원 후보는 청년인구 상대취약 + 공식 정류소 절대수 중앙값 미만 기준입니다."
    )

    print(
        "※ 정류소 수는 노선 수·배차간격·환승편의·서비스 품질을 직접 반영하지 않습니다."
    )

    print(
        "※ 버스 노선 데이터는 안전 매칭률 0.54%로 정책분석에서 제외합니다."
    )

    print(
        "※ 버스정류소 지표는 HL-Score에 추가하지 않습니다."
    )

    print()
    print("새 파일 저장:")
    print(OUTPUT_FILE)
    print()


if __name__ == "__main__":
    main()
