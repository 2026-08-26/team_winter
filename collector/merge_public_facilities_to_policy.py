import os
import pandas as pd


# =========================================================
# 1. 파일 경로
# =========================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

PROCESSED_DIR = os.path.join(
    BASE_DIR,
    "data",
    "processed"
)

POLICY_FILE = os.path.join(
    PROCESSED_DIR,
    "청년주거환경_정책통합분석.csv"
)

PUBLIC_FACILITY_FILE = os.path.join(
    PROCESSED_DIR,
    "2030_청년인구_대비_공공시설_분석.csv"
)

OUTPUT_FILE = os.path.join(
    PROCESSED_DIR,
    "청년주거환경_정책통합분석_공공시설반영.csv"
)


# =========================================================
# 2. 보조 함수
# =========================================================

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
    if "지역" not in df.columns:
        if (
            "자치구" not in df.columns
            or "행정동" not in df.columns
        ):
            raise ValueError(
                "지역 컬럼도 없고 자치구/행정동 컬럼도 없습니다."
            )

        df["지역"] = (
            df["자치구"]
            .astype(str)
            .str.strip()
            + " "
            + df["행정동"]
            .astype(str)
            .str.strip()
        )

    return df


# =========================================================
# 3. 메인
# =========================================================

def main():
    print()
    print("=" * 68)
    print("청년 공공시설 → 정책통합분석 병합")
    print("정책방향: 청년이 상대적으로 적은 지역의 유입·정착 지원")
    print("=" * 68)

    if not os.path.exists(POLICY_FILE):
        raise FileNotFoundError(
            f"정책통합 파일이 없습니다: {POLICY_FILE}"
        )

    if not os.path.exists(PUBLIC_FACILITY_FILE):
        raise FileNotFoundError(
            f"공공시설 분석 파일이 없습니다: {PUBLIC_FACILITY_FILE}"
        )

    policy_df = pd.read_csv(
        POLICY_FILE,
        encoding="utf-8-sig"
    )

    facility_df = pd.read_csv(
        PUBLIC_FACILITY_FILE,
        encoding="utf-8-sig"
    )

    policy_df = ensure_region(policy_df)
    facility_df = ensure_region(facility_df)

    if len(policy_df) != 25:
        raise ValueError(
            f"정책통합 지역 수가 25개가 아닙니다: {len(policy_df)}"
        )

    if len(facility_df) != 25:
        raise ValueError(
            f"공공시설 분석 지역 수가 25개가 아닙니다: {len(facility_df)}"
        )

    if policy_df["지역"].duplicated().any():
        raise ValueError(
            "정책통합 파일에 중복 지역이 있습니다."
        )

    if facility_df["지역"].duplicated().any():
        raise ValueError(
            "공공시설 파일에 중복 지역이 있습니다."
        )

    # -----------------------------------------------------
    # 필요한 공공시설 컬럼 확인
    # -----------------------------------------------------

    required_facility_cols = [
        "지역",
        "청년공공시설수"
    ]

    missing = [
        col
        for col in required_facility_cols
        if col not in facility_df.columns
    ]

    if missing:
        raise ValueError(
            "공공시설 필수 컬럼 누락: "
            + ", ".join(missing)
        )

    # -----------------------------------------------------
    # 기존 1,000명당 지표는 설명용 참고값으로 보존
    # 새 정책후보 판정에는 사용하지 않음
    # -----------------------------------------------------

    keep_cols = [
        "지역",
        "청년공공시설수"
    ]

    optional_cols = [
        "청년공공시설_1000명당",
        "청년공공시설_0개",
        "공공시설_상대부족",
        "공공시설_HL반영여부",
        "공공시설지표_역할"
    ]

    for col in optional_cols:
        if col in facility_df.columns:
            keep_cols.append(col)

    merged = pd.merge(
        policy_df,
        facility_df[keep_cols],
        on="지역",
        how="left",
        validate="one_to_one"
    )

    if merged["청년공공시설수"].isna().any():
        missing_regions = (
            merged[
                merged["청년공공시설수"]
                .isna()
            ]["지역"]
            .tolist()
        )

        raise ValueError(
            "공공시설 데이터가 연결되지 않은 지역: "
            + ", ".join(missing_regions)
        )

    # -----------------------------------------------------
    # 새 방향의 공공시설 지원 신호
    #
    # 기존:
    # 2030 인구 TOP10 + 1,000명당 시설 부족
    #
    # 변경:
    # 청년인구 상대취약지역
    # + 청년공공시설 절대 공급량이 25개 동 중앙값 미만
    #
    # 이유:
    # 청년인구가 적은 지역은 분모가 작아
    # '1,000명당 시설 수'가 높게 보일 수 있으므로,
    # 유입·정착 지원 분석에서는 절대 시설 수를 주기준으로 사용.
    # -----------------------------------------------------

    facility_median = float(
        merged["청년공공시설수"].median()
    )

    merged["청년공공시설수_중앙값"] = round(
        facility_median,
        2
    )

    merged["청년공공시설_절대공급부족"] = (
        merged["청년공공시설수"]
        < facility_median
    )

    merged["청년공공시설_0개"] = (
        merged["청년공공시설수"]
        == 0
    )

    if "청년인구_상대취약" not in merged.columns:
        raise ValueError(
            "정책통합 파일에 '청년인구_상대취약' 컬럼이 없습니다."
        )

    merged["청년인구_상대취약"] = (
        merged["청년인구_상대취약"]
        .apply(to_bool)
    )

    merged["청년유입정착_공공시설지원후보"] = (
        merged["청년인구_상대취약"]
        & merged["청년공공시설_절대공급부족"]
    )

    # -----------------------------------------------------
    # 보조 근거 / 통합 신호
    # -----------------------------------------------------

    def make_support_reason(row):
        if not row["청년인구_상대취약"]:
            return (
                "청년인구 상대취약지역이 아니므로 "
                "청년 유입·정착 공공시설 지원후보에서 제외"
            )

        count = int(row["청년공공시설수"])

        if row["청년유입정착_공공시설지원후보"]:
            if count == 0:
                return (
                    "2030 인구수와 비율이 모두 상대적으로 낮고, "
                    "분석대상 행정동 내 청년 공공시설이 확인되지 않아 "
                    "청년 유입·정착을 위한 공공지원 공간 확충 필요성을 검토할 수 있는 지역."
                )

            return (
                f"2030 인구수와 비율이 모두 상대적으로 낮고, "
                f"청년 공공시설이 {count}개로 25개 동 중앙값 "
                f"{facility_median:.0f}개보다 적어 "
                "청년 활동·지원공간의 추가 공급 필요성을 검토할 수 있는 지역."
            )

        return (
            "2030 인구수와 비율은 모두 상대적으로 낮지만, "
            "청년 공공시설 절대 공급량은 25개 동 중앙값 이상으로 "
            "공공시설 공급 부족 신호는 확인되지 않음."
        )

    merged["공공시설_청년정착지원근거"] = merged.apply(
        make_support_reason,
        axis=1
    )

    def make_signal(row):
        if row["청년유입정착_공공시설지원후보"]:
            return (
                "청년인구 상대취약 + 청년 공공시설 공급 부족"
            )

        if row["청년인구_상대취약"]:
            return (
                "청년인구 상대취약 · 공공시설 공급 부족신호 없음"
            )

        return "공공시설 보조지표 참고"

    merged["공공시설_통합신호"] = merged.apply(
        make_signal,
        axis=1
    )

    # HL에는 절대 혼입하지 않음
    merged["공공시설_HL반영여부"] = False
    merged["공공시설지표_역할"] = (
        "청년 유입·정착 정책 보조지표"
    )

    # -----------------------------------------------------
    # 저장
    # -----------------------------------------------------

    merged.to_csv(
        OUTPUT_FILE,
        index=False,
        encoding="utf-8-sig"
    )

    candidates = merged[
        merged["청년유입정착_공공시설지원후보"]
        == True
    ].copy()

    zero_facility = merged[
        merged["청년공공시설_0개"]
        == True
    ].copy()

    print()
    print("=" * 68)
    print("공공시설 정책통합 완료")
    print("=" * 68)

    print()
    print("최종 지역 수 :", len(merged), "개")
    print(
        "전체 청년공공시설 :",
        int(merged["청년공공시설수"].sum()),
        "개"
    )
    print(
        "청년공공시설 절대 공급 중앙값 :",
        f"{facility_median:.0f}개"
    )
    print(
        "청년 유입·정착 공공시설 지원후보 :",
        len(candidates),
        "개"
    )

    print()
    print("-" * 68)
    print("[청년 유입·정착 공공시설 지원후보]")
    print("-" * 68)

    if candidates.empty:
        print("해당 지역 없음")
    else:
        candidates = candidates.sort_values(
            [
                "청년공공시설수",
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
                "청년공공시설 :",
                f"{int(row['청년공공시설수'])}개"
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
                row["공공시설_통합신호"]
            )

    print()
    print("-" * 68)
    print("[청년 공공시설 0개 지역 - 참고]")
    print("-" * 68)

    for _, row in zero_facility.iterrows():
        print(
            f"- {row['지역']} "
            f"→ {row.get('최종정책유형', '-')}"
        )

    print()
    print("=" * 68)
    print("주의")
    print("=" * 68)
    print("※ 기존 2030인구 TOP10 기준은 사용하지 않습니다.")
    print("※ 1,000명당 청년공공시설 수는 설명용 참고값으로만 유지합니다.")
    print("※ 청년 유입·정착 지원후보는 청년인구 상대취약 + 절대 시설수 중앙값 미만 기준입니다.")
    print("※ 청년 공공시설 수는 이용인원·수용능력·서비스 품질을 직접 반영하지 않습니다.")
    print("※ 청년 공공시설 지표는 HL-Score에 추가하지 않습니다.")

    print()
    print("새 파일 저장:")
    print(OUTPUT_FILE)
    print()


if __name__ == "__main__":
    main()
