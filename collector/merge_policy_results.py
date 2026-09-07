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

HL_POLICY_FILE = os.path.join(
    PROCESSED_DIR,
    "청년주거환경_정책검토지역.csv"
)

SETTLEMENT_FILE = os.path.join(
    PROCESSED_DIR,
    "2030_청년유입정착_정책분석.csv"
)

# 기존 1,000명당 지표는 설명용 참고값으로만 보존
# 정책후보 판정에는 사용하지 않음
LEGACY_INFRA_FILE = os.path.join(
    PROCESSED_DIR,
    "2030_청년인구_대비_인프라_분석결과.csv"
)

OUTPUT_FILE = os.path.join(
    PROCESSED_DIR,
    "청년주거환경_정책통합분석.csv"
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


def ensure_region(df):
    if "지역" not in df.columns:
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


def add_sample_warning(text, row):
    sample_status = clean_text(
        row.get(
            "HL주거표본판정",
            ""
        )
    )

    if sample_status == "저표본 주의":
        return (
            text
            + " 단, 주거 실거래 표본이 "
            + "5~19건으로 주거비 해석에 주의가 필요함."
        )

    return text


# =========================================================
# 3. 최종 정책유형
# =========================================================

def make_final_policy_type(row):
    hl_grade = clean_text(
        row.get(
            "HL정책검토등급",
            ""
        )
    )

    settlement_priority = to_bool(
        row.get(
            "청년유입정착_우선후보",
            False
        )
    )

    settlement_review = to_bool(
        row.get(
            "청년유입정착_지원검토",
            False
        )
    )

    cause_check = to_bool(
        row.get(
            "청년인구감소원인_추가점검",
            False
        )
    )

    # -----------------------------------------------------
    # A. HL 정책순위 제외
    # -----------------------------------------------------

    if hl_grade == "정책순위 제외":
        if settlement_priority:
            return (
                "청년 유입·정착 지원 우선 · HL순위 제외"
            )

        if settlement_review:
            return (
                "청년 유입·정착 지원 검토 · HL순위 제외"
            )

        if cause_check:
            return (
                "청년비중 낮음 · 원인 추가점검 · HL순위 제외"
            )

        return "HL순위 제외"

    # -----------------------------------------------------
    # B. HL + 청년 유입·정착 신호가 동시에 강한 지역
    # -----------------------------------------------------

    if (
        hl_grade == "우선 개선 검토"
        and settlement_priority
    ):
        return "복합 최우선 검토"

    if (
        hl_grade == "관심 검토"
        and settlement_priority
    ):
        return "복합 관심 검토"

    if (
        hl_grade == "우선 개선 검토"
        and settlement_review
    ):
        return "복합 정책검토"

    if (
        hl_grade == "관심 검토"
        and settlement_review
    ):
        return "복합 관심 검토"

    # -----------------------------------------------------
    # C. HL 단독 신호
    # -----------------------------------------------------

    if hl_grade == "우선 개선 검토":
        return "주거환경 개선 우선"

    if hl_grade == "관심 검토":
        return "주거환경 관심 검토"

    # -----------------------------------------------------
    # D. 청년 유입·정착 단독 신호
    # -----------------------------------------------------

    if settlement_priority:
        return "청년 유입·정착 지원 우선"

    if settlement_review:
        return "청년 유입·정착 지원 검토"

    if cause_check:
        return "청년비중 낮음 · 원인 추가점검"

    return "일반 관찰"


# =========================================================
# 4. 정책근거 요약
# =========================================================

def make_policy_evidence(row):
    hl_grade = clean_text(
        row.get(
            "HL정책검토등급",
            ""
        )
    )

    hl_weak = clean_text(
        row.get(
            "HL주요취약요인",
            ""
        )
    )

    settlement_vulnerable = to_bool(
        row.get(
            "청년인구_상대취약",
            False
        )
    )

    settlement_priority = to_bool(
        row.get(
            "청년유입정착_우선후보",
            False
        )
    )

    settlement_review = to_bool(
        row.get(
            "청년유입정착_지원검토",
            False
        )
    )

    cause_check = to_bool(
        row.get(
            "청년인구감소원인_추가점검",
            False
        )
    )

    settlement_weak = clean_text(
        row.get(
            "청년정착_부족분야",
            ""
        )
    )

    youth_count = row.get(
        "2030인구수",
        None
    )

    youth_ratio = row.get(
        "2030인구비율",
        None
    )

    count_median = row.get(
        "2030인구수_중앙값",
        None
    )

    ratio_median = row.get(
        "2030인구비율_중앙값",
        None
    )

    # -----------------------------------------------------
    # 청년인구 상대취약 신호가 있는 경우
    # -----------------------------------------------------

    if settlement_vulnerable:
        base = (
            f"2030 인구수 {int(round(youth_count)):,}명과 "
            f"2030 인구비율 {float(youth_ratio):.2f}%가 모두 "
            f"25개 동 중앙값 "
            f"({int(round(count_median)):,}명, "
            f"{float(ratio_median):.2f}%)보다 낮은 지역."
        )

        if settlement_priority or settlement_review:
            base += (
                f" HL 세부지표에서는 {settlement_weak} 부문이 "
                "25개 동 중앙값보다 낮아 청년 유입·정착 여건의 "
                "추가 개선 필요성을 검토할 수 있음."
            )

        elif cause_check:
            base += (
                " 다만 현재 HL 세부지표에서는 뚜렷한 상대 취약신호가 "
                "확인되지 않아, 청년 비중이 낮은 이유를 "
                "일자리·교육·주택유형·지역이미지 등 다른 요인까지 "
                "확장해 추가 조사할 필요가 있음."
            )

        if hl_grade == "정책순위 제외":
            base += (
                " 주거 실거래 표본부족으로 HL 정책순위 비교에서는 "
                "제외되며 HL-Score는 참고값으로만 사용함."
            )

        return add_sample_warning(
            base,
            row
        )

    # -----------------------------------------------------
    # 청년인구 상대취약은 아니지만 HL 신호가 있는 경우
    # -----------------------------------------------------

    if hl_grade == "우선 개선 검토":
        if hl_weak and hl_weak != "없음":
            text = (
                "2030 인구수와 비율이 모두 상대적으로 낮은 지역은 아니지만, "
                f"HL-Score 상대 하위권이며 {hl_weak} 부문의 "
                "주거환경 개선 필요성이 확인된 지역."
            )
        else:
            text = (
                "2030 인구수와 비율이 모두 상대적으로 낮은 지역은 아니지만, "
                "HL-Score 상대 하위권으로 종합적인 주거환경 점검이 필요한 지역."
            )

        return add_sample_warning(
            text,
            row
        )

    if hl_grade == "관심 검토":
        if hl_weak and hl_weak != "없음":
            text = (
                "청년인구 상대취약지역은 아니지만, "
                f"HL 분석에서 {hl_weak} 부문의 추가 점검 필요성이 확인된 지역."
            )
        else:
            text = (
                "청년인구 상대취약지역은 아니지만, "
                "HL-Score 상대 비교에서 관심 검토권에 포함된 지역."
            )

        return add_sample_warning(
            text,
            row
        )

    if hl_grade == "정책순위 제외":
        return (
            "주거 실거래 표본이 5건 미만으로 "
            "HL 정책순위 비교에서 제외된 지역. "
            "충분한 민간임대 거래 표본 확보 후 재평가가 필요함."
        )

    return (
        "현재 프로젝트 상대비교 기준에서는 "
        "청년인구 상대취약 또는 높은 HL 정책 우선 신호가 "
        "확인되지 않은 지역."
    )


# =========================================================
# 5. 통합 정책제안
# =========================================================

def make_integrated_policy_recommendation(row):
    suggestions = []

    hl_grade = clean_text(
        row.get(
            "HL정책검토등급",
            ""
        )
    )

    hl_factors = clean_text(
        row.get(
            "HL주요취약요인",
            ""
        )
    )

    settlement_vulnerable = to_bool(
        row.get(
            "청년인구_상대취약",
            False
        )
    )

    settlement_weak = clean_text(
        row.get(
            "청년정착_부족분야",
            ""
        )
    )

    cause_check = to_bool(
        row.get(
            "청년인구감소원인_추가점검",
            False
        )
    )

    if settlement_vulnerable:
        suggestions.append(
            "청년 유입·정착 여건 현장진단"
        )

    if hl_grade == "정책순위 제외":
        suggestions.append(
            "민간임대 실거래 표본 추가 확보 후 HL-Score 재평가"
        )

    combined_text = (
        hl_factors
        + " "
        + settlement_weak
    )

    if (
        "생활인프라" in combined_text
        or "생활 인프라" in combined_text
    ):
        suggestions.append(
            "생활SOC·의료·편의·문화시설 접근성 개선 검토"
        )

    if (
        "2030선호시설" in combined_text
        or "2030 선호시설" in combined_text
    ):
        suggestions.append(
            "청년 문화·운동·생활편의시설 확충 가능성 검토"
        )

    if (
        "교통접근성" in combined_text
        or "교통 접근성" in combined_text
    ):
        suggestions.append(
            "대중교통 접근성과 이동환경 개선 검토"
        )

    if (
        "주거가성비" in combined_text
        or "주거 가성비" in combined_text
    ):
        suggestions.append(
            "청년 주거비 부담 완화 및 부담 가능한 주택 공급 검토"
        )

    if cause_check:
        suggestions.append(
            "일자리·교육·주택유형·지역이미지 등 청년 유입 저해요인 추가 조사"
        )

    if not suggestions:
        suggestions.append(
            "청년 인구와 주거환경 변화 지속 모니터링"
        )

    unique = []

    for suggestion in suggestions:
        if suggestion not in unique:
            unique.append(
                suggestion
            )

    return " · ".join(
        unique
    )


# =========================================================
# 6. 메인
# =========================================================

def main():
    print()
    print("=" * 68)
    print("정책 분석 결과 통합 시작 - 청년 유입·정착 방향")
    print("=" * 68)

    for path, label in [
        (
            HL_POLICY_FILE,
            "HL 정책분석"
        ),
        (
            SETTLEMENT_FILE,
            "청년 유입·정착 분석"
        )
    ]:
        if not os.path.exists(path):
            raise FileNotFoundError(
                f"{label} 파일이 없습니다: {path}"
            )

    hl_df = pd.read_csv(
        HL_POLICY_FILE,
        encoding="utf-8-sig"
    )

    settlement_df = pd.read_csv(
        SETTLEMENT_FILE,
        encoding="utf-8-sig"
    )

    hl_df = ensure_region(
        hl_df
    )

    settlement_df = ensure_region(
        settlement_df
    )

    if hl_df["지역"].duplicated().any():
        raise ValueError(
            "HL 정책분석 데이터에 중복 지역이 있습니다."
        )

    if settlement_df["지역"].duplicated().any():
        raise ValueError(
            "청년 유입·정착 데이터에 중복 지역이 있습니다."
        )

    print(
        "HL 분석 지역 수:",
        len(hl_df)
    )

    print(
        "청년 유입·정착 분석 지역 수:",
        len(settlement_df)
    )

    # -----------------------------------------------------
    # HL 컬럼 이름 정리
    # -----------------------------------------------------

    hl_df = hl_df.rename(
        columns={
            "정책검토등급":
                "HL정책검토등급",
            "취약유형":
                "HL취약유형",
            "취약요인수":
                "HL취약요인수",
            "주요취약요인":
                "HL주요취약요인",
            "정책검토방향":
                "HL정책검토방향",
            "주거표본판정":
                "HL주거표본판정",
            "정책순위포함여부":
                "HL정책순위포함여부",
            "데이터주의사항":
                "HL데이터주의사항"
        }
    )

    if (
        "월환산주거비"
        not in hl_df.columns
        and
        "월환산주거비_평균값_만원"
        in hl_df.columns
    ):
        hl_df["월환산주거비"] = (
            hl_df[
                "월환산주거비_평균값_만원"
            ]
        )

    if (
        "HL정책순위포함여부"
        in hl_df.columns
    ):
        hl_df["HL정책순위포함여부"] = (
            hl_df[
                "HL정책순위포함여부"
            ]
            .apply(
                to_bool
            )
        )

    # -----------------------------------------------------
    # 청년 유입·정착 Boolean
    # -----------------------------------------------------

    settlement_bool_columns = [
        "2030인구수_상대부족",
        "2030인구비율_상대부족",
        "청년인구_상대취약",
        "생활인프라_취약",
        "2030선호시설_취약",
        "교통접근성_취약",
        "주거가성비_평가가능",
        "주거가성비_취약",
        "청년유입정착_정책후보",
        "청년유입정착_우선후보",
        "청년유입정착_지원검토",
        "청년인구감소원인_추가점검"
    ]

    for column in settlement_bool_columns:
        if column in settlement_df.columns:
            settlement_df[column] = (
                settlement_df[column]
                .apply(
                    to_bool
                )
            )

    # -----------------------------------------------------
    # 중복되는 HL 점수는 HL 정책파일 값을 기준으로 사용
    # 청년 유입·정착 파일에서는 정책분석 관련 컬럼만 선택
    # -----------------------------------------------------

    settlement_columns = [
        "지역",
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

    missing_settlement = [
        col
        for col
        in settlement_columns
        if col
        not in settlement_df.columns
    ]

    if missing_settlement:
        raise ValueError(
            "청년 유입·정착 분석 필수 컬럼 누락: "
            + ", ".join(
                missing_settlement
            )
        )

    merged = pd.merge(
        hl_df,
        settlement_df[
            settlement_columns
        ],
        on="지역",
        how="left",
        validate="one_to_one"
    )

    if merged["2030인구수"].isna().any():
        missing_regions = (
            merged[
                merged["2030인구수"]
                .isna()
            ]["지역"]
            .tolist()
        )

        raise ValueError(
            "청년 유입·정착 데이터가 연결되지 않은 지역: "
            + ", ".join(
                missing_regions
            )
        )

    # -----------------------------------------------------
    # 기존 1,000명당 지표는 설명용 참고값으로만 유지
    # 정책 후보 생성에는 절대 사용하지 않음
    # -----------------------------------------------------

    if os.path.exists(
        LEGACY_INFRA_FILE
    ):
        infra_df = pd.read_csv(
            LEGACY_INFRA_FILE,
            encoding="utf-8-sig"
        )

        infra_df = ensure_region(
            infra_df
        )

        reference_columns = [
            "지역",
            "생활시설_1000명당",
            "버스정류소_1000명당",
            "선호시설_1000명당",
            "가장가까운_버스정류소_m"
        ]

        reference_columns = [
            col
            for col
            in reference_columns
            if col
            in infra_df.columns
        ]

        if len(
            reference_columns
        ) > 1:
            merged = pd.merge(
                merged,
                infra_df[
                    reference_columns
                ],
                on="지역",
                how="left",
                validate="one_to_one"
            )

    # -----------------------------------------------------
    # 두 분석 동시 신호
    # -----------------------------------------------------

    merged["청년정착_실행신호"] = (
        merged[
            "청년유입정착_우선후보"
        ]
        |
        merged[
            "청년유입정착_지원검토"
        ]
    )

    merged["두분석_동시신호"] = (
        merged[
            "HL정책검토등급"
        ]
        .isin(
            [
                "우선 개선 검토",
                "관심 검토"
            ]
        )
        &
        merged[
            "청년정착_실행신호"
        ]
    )

    # -----------------------------------------------------
    # 최종 정책유형 / 근거 / 제안
    # -----------------------------------------------------

    merged["최종정책유형"] = merged.apply(
        make_final_policy_type,
        axis=1
    )

    merged["정책근거요약"] = merged.apply(
        make_policy_evidence,
        axis=1
    )

    merged["통합정책제안"] = merged.apply(
        make_integrated_policy_recommendation,
        axis=1
    )

    # -----------------------------------------------------
    # 최종 컬럼
    # -----------------------------------------------------

    final_columns = [
        "지역",

        "HL_Score",
        "HL정책비교순위",
        "HL정책검토등급",
        "HL정책순위포함여부",
        "HL비교가능성",
        "HL산출유형",

        "월환산주거비",
        "월환산주거비_평균값_만원",
        "전체거래건수",
        "HL주거표본판정",
        "HL데이터주의사항",

        "생활인프라점수",
        "2030선호시설점수",
        "교통접근성점수",
        "주거가성비점수",

        "HL취약유형",
        "HL취약요인수",
        "HL주요취약요인",
        "HL정책검토방향",

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
        "청년정착_정책방향",

        # 설명용 참고지표
        "생활시설_1000명당",
        "버스정류소_1000명당",
        "선호시설_1000명당",
        "가장가까운_버스정류소_m",

        "청년정착_실행신호",
        "두분석_동시신호",

        "최종정책유형",
        "정책근거요약",
        "통합정책제안"
    ]

    final_columns = [
        col
        for col
        in final_columns
        if col
        in merged.columns
    ]

    final_df = merged[
        final_columns
    ].copy()

    policy_order = {
        "복합 최우선 검토": 1,
        "복합 정책검토": 2,
        "복합 관심 검토": 3,
        "청년 유입·정착 지원 우선": 4,
        "청년 유입·정착 지원 우선 · HL순위 제외": 5,
        "주거환경 개선 우선": 6,
        "청년 유입·정착 지원 검토": 7,
        "청년 유입·정착 지원 검토 · HL순위 제외": 8,
        "주거환경 관심 검토": 9,
        "청년비중 낮음 · 원인 추가점검": 10,
        "청년비중 낮음 · 원인 추가점검 · HL순위 제외": 11,
        "일반 관찰": 12,
        "HL순위 제외": 13
    }

    final_df["정책정렬순서"] = (
        final_df[
            "최종정책유형"
        ]
        .map(
            policy_order
        )
        .fillna(
            99
        )
    )

    final_df = (
        final_df
        .sort_values(
            [
                "정책정렬순서",
                "청년인구_취약참고순위",
                "HL_Score"
            ],
            ascending=[
                True,
                True,
                True
            ],
            na_position="last"
        )
        .drop(
            columns=[
                "정책정렬순서"
            ]
        )
        .reset_index(
            drop=True
        )
    )

    final_df.to_csv(
        OUTPUT_FILE,
        index=False,
        encoding="utf-8-sig"
    )

    # -----------------------------------------------------
    # 결과 출력
    # -----------------------------------------------------

    print()
    print("=" * 68)
    print("통합 정책 분석 완료")
    print("=" * 68)

    print()
    print("[청년인구 상대취약 지역]")

    vulnerable = final_df[
        final_df[
            "청년인구_상대취약"
        ]
        == True
    ]

    for _, row in vulnerable.iterrows():
        print()
        print("-" * 50)
        print(
            "지역 :",
            row["지역"]
        )
        print(
            "2030 인구 :",
            f"{int(row['2030인구수']):,}명",
            "/",
            f"{float(row['2030인구비율']):.2f}%"
        )
        print(
            "취약신호 :",
            int(
                row[
                    "청년정착_취약신호수"
                ]
            ),
            "개"
        )
        print(
            "부족분야 :",
            row[
                "청년정착_부족분야"
            ]
        )
        print(
            "최종정책유형 :",
            row[
                "최종정책유형"
            ]
        )

    print()
    print("=" * 68)
    print("최종 정책유형별 지역 수")
    print("=" * 68)

    counts = (
        final_df[
            "최종정책유형"
        ]
        .value_counts()
    )

    for policy_type, count in counts.items():
        print(
            f"{policy_type} : {count}개 지역"
        )

    print()
    print("=" * 68)
    print("검증")
    print("=" * 68)

    print(
        "최종 지역 수 :",
        len(
            final_df
        )
    )

    print(
        "청년인구 상대취약 :",
        int(
            final_df[
                "청년인구_상대취약"
            ]
            .sum()
        )
    )

    print(
        "청년 유입·정착 지원 우선 :",
        int(
            final_df[
                "청년유입정착_우선후보"
            ]
            .sum()
        )
    )

    print(
        "원인 추가점검 :",
        int(
            final_df[
                "청년인구감소원인_추가점검"
            ]
            .sum()
        )
    )

    print(
        "두 분석 동시 신호 :",
        int(
            final_df[
                "두분석_동시신호"
            ]
            .sum()
        )
    )

    print()
    print("-" * 68)
    print("저장 완료")
    print(OUTPUT_FILE)
    print("-" * 68)

    print()
    print("※ 기존 2030 인구 TOP10은 정책후보 기준에서 사용하지 않습니다.")
    print("※ 1,000명당 시설 지표는 설명용 참고값으로만 보존합니다.")
    print("※ 청년인구 상대취약은 인구수·비율이 모두 25개 동 중앙값 미만인 프로젝트 내부 기준입니다.")
    print("※ 청년인구가 적다는 사실과 HL 취약신호 사이의 인과관계는 단정하지 않습니다.")
    print()


if __name__ == "__main__":
    main()
