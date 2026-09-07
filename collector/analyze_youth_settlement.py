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

INPUT_FILE = os.path.join(
    PROCESSED_DIR,
    "25개동_통합분석.csv"
)

OUTPUT_FILE = os.path.join(
    PROCESSED_DIR,
    "2030_청년유입정착_정책분석.csv"
)


# =========================================================
# 2. 보조 함수
# =========================================================

def safe_bool(value):
    if isinstance(value, bool):
        return value

    text = str(value).strip().lower()

    return text in [
        "true",
        "1",
        "yes",
        "y"
    ]


def make_weak_fields(row):
    weak = []

    if row["생활인프라_취약"]:
        weak.append("생활 인프라")

    if row["2030선호시설_취약"]:
        weak.append("2030 선호시설")

    if row["교통접근성_취약"]:
        weak.append("교통 접근성")

    if row["주거가성비_취약"]:
        weak.append("주거 가성비")

    if not weak:
        return "뚜렷한 취약신호 없음"

    return ", ".join(weak)


def make_policy_direction(row):
    if not row["청년인구_상대취약"]:
        return (
            "2030 인구수와 인구비율이 모두 상대적으로 낮은 지역이 아니므로 "
            "청년 유입·정착 지원 후보에서 제외"
        )

    weak_count = int(row["청년정착_취약신호수"])

    directions = []

    if row["생활인프라_취약"]:
        directions.append(
            "생활SOC·의료·편의·문화시설 접근성 개선 검토"
        )

    if row["2030선호시설_취약"]:
        directions.append(
            "청년 문화·운동·생활편의시설 확충 가능성 검토"
        )

    if row["교통접근성_취약"]:
        directions.append(
            "대중교통 접근성과 이동환경 개선 검토"
        )

    if row["주거가성비_취약"]:
        directions.append(
            "청년 주거비 부담 완화 및 부담 가능한 주택 공급 검토"
        )

    if weak_count == 0:
        return (
            "청년 인구수와 비율은 모두 상대적으로 낮지만 현재 HL 세부지표에서 "
            "뚜렷한 취약신호가 확인되지 않아 일자리·교육·주택유형·지역이미지 등 "
            "추가 원인조사 필요"
        )

    return " / ".join(directions)


def make_policy_level(row):
    if not row["청년인구_상대취약"]:
        return "일반 관찰"

    weak_count = int(row["청년정착_취약신호수"])

    if weak_count >= 2:
        return "청년 유입·정착 지원 우선"

    if weak_count == 1:
        return "청년 유입·정착 지원 검토"

    return "청년비중 낮음 · 원인 추가점검"


# =========================================================
# 3. 메인
# =========================================================

def main():
    print()
    print("=" * 68)
    print("2030 청년 유입·정착 정책분석 시작")
    print("=" * 68)

    if not os.path.exists(INPUT_FILE):
        raise FileNotFoundError(
            f"파일이 없습니다: {INPUT_FILE}"
        )

    df = pd.read_csv(INPUT_FILE)

    required_columns = [
        "자치구",
        "행정동",
        "2030인구수",
        "2030인구비율",
        "생활인프라점수",
        "2030선호시설점수",
        "교통접근성점수",
        "주거가성비점수"
    ]

    missing = [
        col for col in required_columns
        if col not in df.columns
    ]

    if missing:
        raise ValueError(
            "필수 컬럼 누락: "
            + ", ".join(missing)
        )

    if len(df) != 25:
        raise ValueError(
            f"분석 대상이 25개 동이 아닙니다: {len(df)}개"
        )

    # -----------------------------------------------------
    # 4. 청년인구 정책 대상 기준
    #
    # 팀 인사이트:
    # "청년이 이미 많은 곳에 공급을 더하는 것이 아니라,
    # 청년이 상대적으로 적은 지역을 찾아
    # 유입·정착 지원 필요성을 검토한다."
    #
    # 따라서 2030인구수와 2030인구비율이
    # 모두 25개 동 중앙값보다 낮은 지역을
    # '청년인구 상대취약지역'으로 정의한다.
    #
    # 공식 정책 선정 기준이 아니라
    # 프로젝트 내부 상대비교 기준이다.
    # -----------------------------------------------------

    youth_count_median = float(
        df["2030인구수"].median()
    )

    youth_ratio_median = float(
        df["2030인구비율"].median()
    )

    df["2030인구수_중앙값"] = round(
        youth_count_median,
        2
    )

    df["2030인구비율_중앙값"] = round(
        youth_ratio_median,
        2
    )

    df["2030인구수_상대부족"] = (
        df["2030인구수"]
        < youth_count_median
    )

    df["2030인구비율_상대부족"] = (
        df["2030인구비율"]
        < youth_ratio_median
    )

    df["청년인구_상대취약"] = (
        df["2030인구수_상대부족"]
        & df["2030인구비율_상대부족"]
    )

    # 중앙값 대비 부족폭
    df["2030인구수_부족폭"] = (
        youth_count_median
        - df["2030인구수"]
    ).round(0)

    df["2030인구비율_부족폭_p"] = (
        youth_ratio_median
        - df["2030인구비율"]
    ).round(2)

    df.loc[
        ~df["2030인구수_상대부족"],
        "2030인구수_부족폭"
    ] = 0

    df.loc[
        ~df["2030인구비율_상대부족"],
        "2030인구비율_부족폭_p"
    ] = 0.0

    # -----------------------------------------------------
    # 5. HL 세부지표 취약 기준
    #
    # 기존의 '청년 1,000명당 시설 수'는
    # 청년 인구가 적은 지역에서 분모가 작아져
    # 공급이 충분한 것처럼 보일 수 있으므로
    # 새 정책방향에서는 주된 취약판정에 사용하지 않는다.
    #
    # 대신 25개 동의 HL 세부점수 중앙값을 기준으로
    # 상대적으로 낮은 영역을 취약신호로 사용한다.
    # -----------------------------------------------------

    infra_median = float(
        df["생활인프라점수"].median()
    )

    preference_median = float(
        df["2030선호시설점수"].median()
    )

    transport_median = float(
        df["교통접근성점수"].median()
    )

    # 주거가성비점수는 표본부족 지역이 NaN일 수 있으므로
    # 유효한 값만으로 중앙값 계산
    cost_median = float(
        df["주거가성비점수"]
        .dropna()
        .median()
    )

    df["생활인프라점수_중앙값"] = round(
        infra_median,
        2
    )

    df["2030선호시설점수_중앙값"] = round(
        preference_median,
        2
    )

    df["교통접근성점수_중앙값"] = round(
        transport_median,
        2
    )

    df["주거가성비점수_중앙값"] = round(
        cost_median,
        2
    )

    df["생활인프라_취약"] = (
        df["생활인프라점수"]
        < infra_median
    )

    df["2030선호시설_취약"] = (
        df["2030선호시설점수"]
        < preference_median
    )

    df["교통접근성_취약"] = (
        df["교통접근성점수"]
        < transport_median
    )

    # 주거점수가 없는 표본부족 지역은
    # '취약'으로 단정하지 않고 '평가불가'로 분리
    df["주거가성비_평가가능"] = (
        df["주거가성비점수"]
        .notna()
    )

    df["주거가성비_취약"] = (
        df["주거가성비_평가가능"]
        & (
            df["주거가성비점수"]
            < cost_median
        )
    )

    # -----------------------------------------------------
    # 6. 취약신호 개수
    # -----------------------------------------------------

    weak_columns = [
        "생활인프라_취약",
        "2030선호시설_취약",
        "교통접근성_취약",
        "주거가성비_취약"
    ]

    df["청년정착_취약신호수"] = (
        df[weak_columns]
        .astype(int)
        .sum(axis=1)
    )

    df["청년정착_부족분야"] = df.apply(
        make_weak_fields,
        axis=1
    )

    # -----------------------------------------------------
    # 7. 정책후보 분류
    #
    # 청년인구 상대취약 + 취약신호 2개 이상
    # → 청년 유입·정착 지원 우선
    #
    # 청년인구 상대취약 + 취약신호 1개
    # → 청년 유입·정착 지원 검토
    #
    # 청년인구 상대취약 + 취약신호 0개
    # → 청년비중 낮음 · 원인 추가점검
    # -----------------------------------------------------

    df["청년유입정착_정책후보"] = (
        df["청년인구_상대취약"]
    )

    df["청년유입정착_우선후보"] = (
        df["청년인구_상대취약"]
        & (
            df["청년정착_취약신호수"]
            >= 2
        )
    )

    df["청년유입정착_지원검토"] = (
        df["청년인구_상대취약"]
        & (
            df["청년정착_취약신호수"]
            == 1
        )
    )

    df["청년인구감소원인_추가점검"] = (
        df["청년인구_상대취약"]
        & (
            df["청년정착_취약신호수"]
            == 0
        )
    )

    df["청년정착_정책등급"] = df.apply(
        make_policy_level,
        axis=1
    )

    df["청년정착_정책방향"] = df.apply(
        make_policy_direction,
        axis=1
    )

    # -----------------------------------------------------
    # 8. 청년인구 취약 참고순위
    #
    # 청년인구 상대취약지역 안에서
    # 2030인구비율이 낮은 순,
    # 그다음 2030인구수가 낮은 순
    # -----------------------------------------------------

    df["청년인구_취약참고순위"] = pd.NA

    vulnerable_df = (
        df[
            df["청년인구_상대취약"]
            == True
        ]
        .sort_values(
            [
                "2030인구비율",
                "2030인구수"
            ],
            ascending=[
                True,
                True
            ]
        )
    )

    for rank, idx in enumerate(
        vulnerable_df.index,
        start=1
    ):
        df.loc[
            idx,
            "청년인구_취약참고순위"
        ] = rank

    # -----------------------------------------------------
    # 9. 기존 QA / 정책 관련 컬럼 있으면 보존
    # -----------------------------------------------------

    optional_columns = [
        "HL_Score",
        "전체거래건수",
        "주거표본판정",
        "HL정책순위포함여부",
        "정책순위포함여부",
        "HL산출유형"
    ]

    # -----------------------------------------------------
    # 10. 저장
    # -----------------------------------------------------

    output_columns = [
        "자치구",
        "행정동",

        "2030인구수",
        "2030인구비율",

        "2030인구수_중앙값",
        "2030인구비율_중앙값",

        "2030인구수_상대부족",
        "2030인구비율_상대부족",
        "청년인구_상대취약",

        "2030인구수_부족폭",
        "2030인구비율_부족폭_p",
        "청년인구_취약참고순위",

        "생활인프라점수",
        "2030선호시설점수",
        "교통접근성점수",
        "주거가성비점수",

        "생활인프라점수_중앙값",
        "2030선호시설점수_중앙값",
        "교통접근성점수_중앙값",
        "주거가성비점수_중앙값",

        "생활인프라_취약",
        "2030선호시설_취약",
        "교통접근성_취약",
        "주거가성비_평가가능",
        "주거가성비_취약",

        "청년정착_취약신호수",
        "청년정착_부족분야",

        "청년유입정착_정책후보",
        "청년유입정착_우선후보",
        "청년유입정착_지원검토",
        "청년인구감소원인_추가점검",

        "청년정착_정책등급",
        "청년정착_정책방향"
    ]

    for col in optional_columns:
        if col in df.columns:
            output_columns.append(col)

    result = df[
        output_columns
    ].copy()

    result.to_csv(
        OUTPUT_FILE,
        index=False,
        encoding="utf-8-sig"
    )

    # -----------------------------------------------------
    # 11. 결과 출력
    # -----------------------------------------------------

    target_df = result[
        result["청년인구_상대취약"]
        == True
    ].copy()

    priority_df = result[
        result["청년유입정착_우선후보"]
        == True
    ].copy()

    support_df = result[
        result["청년유입정착_지원검토"]
        == True
    ].copy()

    cause_df = result[
        result["청년인구감소원인_추가점검"]
        == True
    ].copy()

    print()
    print("2030 인구수 중앙값 :", int(round(youth_count_median)), "명")
    print("2030 인구비율 중앙값 :", round(youth_ratio_median, 2), "%")

    print()
    print("[HL 세부지표 중앙값]")
    print("생활 인프라 :", round(infra_median, 2))
    print("2030 선호시설 :", round(preference_median, 2))
    print("교통 접근성 :", round(transport_median, 2))
    print("주거 가성비 :", round(cost_median, 2))

    print()
    print("청년인구 상대취약 :", len(target_df), "개 지역")
    print("유입·정착 지원 우선 :", len(priority_df), "개 지역")
    print("유입·정착 지원 검토 :", len(support_df), "개 지역")
    print("원인 추가점검 :", len(cause_df), "개 지역")

    print()
    print("-" * 68)
    print("[청년 유입·정착 지원 우선]")
    print("-" * 68)

    if priority_df.empty:
        print("해당 지역 없음")
    else:
        priority_df = priority_df.sort_values(
            [
                "청년정착_취약신호수",
                "2030인구비율",
                "2030인구수"
            ],
            ascending=[
                False,
                True,
                True
            ]
        )

        for _, row in priority_df.iterrows():
            print()
            print(
                f"{row['자치구']} {row['행정동']}"
            )

            print(
                f"2030 인구수 : {int(row['2030인구수']):,}명"
            )

            print(
                f"2030 인구비율 : {row['2030인구비율']:.2f}%"
            )

            print(
                f"취약신호 : {int(row['청년정착_취약신호수'])}개"
            )

            print(
                f"부족분야 : {row['청년정착_부족분야']}"
            )

            if not row["주거가성비_평가가능"]:
                print(
                    "주거가성비 : 표본부족으로 취약판정에서 제외"
                )

    print()
    print("-" * 68)
    print("[청년 유입·정착 지원 검토]")
    print("-" * 68)

    if support_df.empty:
        print("해당 지역 없음")
    else:
        support_df = support_df.sort_values(
            "2030인구비율",
            ascending=True
        )

        for _, row in support_df.iterrows():
            print(
                f"- {row['자치구']} {row['행정동']} "
                f"/ {int(row['2030인구수']):,}명 "
                f"/ {row['2030인구비율']:.2f}% "
                f"/ {row['청년정착_부족분야']}"
            )

    print()
    print("-" * 68)
    print("[청년비중 낮음 · 원인 추가점검]")
    print("-" * 68)

    if cause_df.empty:
        print("해당 지역 없음")
    else:
        cause_df = cause_df.sort_values(
            [
                "2030인구비율",
                "2030인구수"
            ],
            ascending=[
                True,
                True
            ]
        )

        for _, row in cause_df.iterrows():
            print(
                f"- {row['자치구']} {row['행정동']} "
                f"/ {int(row['2030인구수']):,}명 "
                f"/ {row['2030인구비율']:.2f}%"
            )

    print()
    print("=" * 68)
    print("저장 완료")
    print(OUTPUT_FILE)
    print("=" * 68)

    print()
    print("※ 2030 인구수와 인구비율 중앙값 미만은 프로젝트 내부 상대비교 기준입니다.")
    print("※ 청년 인구가 적다는 사실만으로 원인을 단정하지 않습니다.")
    print("※ 취약원인은 HL 세부점수의 25개 동 중앙값과 비교해 탐색합니다.")
    print("※ 주거 표본부족 지역은 주거가성비 취약 여부를 판정하지 않습니다.")
    print()


if __name__ == "__main__":
    main()
