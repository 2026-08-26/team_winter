from flask import Flask, render_template, jsonify
import pandas as pd
import numpy as np

app = Flask(__name__)

def compute_hl_scores():

    """data/processed/25개동_통합분석.csv 파일 기반 HL-Score 산출"""

    try:
        df = pd.read_csv("data/processed/25개동_통합분석.csv")

    except FileNotFoundError:
        print("[오류] data/processed/25개동_통합분석.csv 파일을 찾을 수 없습니다.")
        return pd.DataFrame()


    print("==========================================")
    print("HL-Score 계산 시작")
    print("==========================================")
    print(f"분석 대상: {len(df)}개 동")


    # =====================================================
    # 1. 숫자 변환 함수
    # =====================================================

    def to_numeric_series(column_name):

        if column_name not in df.columns:
            return pd.Series(
                [np.nan] * len(df),
                index=df.index
            )

        return pd.to_numeric(
            df[column_name]
            .astype(str)
            .str.replace(",", "", regex=False),
            errors="coerce"
        )


    # =====================================================
    # 2. 값이 클수록 좋은 지표 정규화
    #    0 ~ 100점
    # =====================================================

    def normalize_positive(series, use_log=False):

        series = pd.to_numeric(
            series,
            errors="coerce"
        ).fillna(0)

        if use_log:
            series = np.log1p(series)

        min_value = series.min()
        max_value = series.max()

        # 모든 값이 0이면 점수도 0점
        if max_value == 0:
            return pd.Series(
                [0.0] * len(series),
                index=series.index
            )

        # 모든 지역 값이 동일하면 중간점수
        if max_value == min_value:
            return pd.Series(
                [50.0] * len(series),
                index=series.index
            )

        return (
            (series - min_value)
            /
            (max_value - min_value)
            * 100
        )


    # =====================================================
    # 3. 거리가 짧을수록 좋은 지표 정규화
    #    0 ~ 100점
    # =====================================================

    def normalize_distance(series):

        series = pd.to_numeric(
            series,
            errors="coerce"
        )

        if series.notna().any():

            # 시설이 없는 곳은 가장 먼 거리로 처리
            worst_distance = series.max()

            series = series.fillna(
                worst_distance
            )

        else:

            return pd.Series(
                [0.0] * len(series),
                index=series.index
            )


        min_value = series.min()
        max_value = series.max()

        if max_value == min_value:

            return pd.Series(
                [50.0] * len(series),
                index=series.index
            )

        return (
            1
            -
            (
                (series - min_value)
                /
                (max_value - min_value)
            )
        ) * 100


    # =====================================================
    # 4. 생활 인프라 점수
    #
    # 시설 개수 60%
    # 시설 최소거리 40%
    # =====================================================

    life_facilities = [
        "편의점",
        "카페",
        "음식점",
        "병원",
        "대형마트",
        "지하철역",
        "문화시설"
    ]


    life_scores = []


    for facility in life_facilities:

        count_col = f"{facility}_개수"
        distance_col = f"{facility}_최소거리_m"


        count_score = normalize_positive(
            to_numeric_series(count_col),
            use_log=True
        )


        distance_score = normalize_distance(
            to_numeric_series(distance_col)
        )


        facility_score = (
            count_score * 0.60
            +
            distance_score * 0.40
        )


        life_scores.append(
            facility_score
        )


    생활인프라점수 = pd.concat(
        life_scores,
        axis=1
    ).mean(axis=1)


    # =====================================================
    # 5. 2030 선호시설 점수
    #
    # 시설 개수 60%
    # 시설 최소거리 40%
    # =====================================================

    youth_categories = [
        "H&B/뷰티",
        "생활쇼핑",
        "SPA패션",
        "영화/문화",
        "대형쇼핑",
        "운동",
        "문화생활",
        "패스트푸드"
    ]


    youth_scores = []


    for category in youth_categories:

        count_col = f"추가_{category}_개수"
        distance_col = f"추가_{category}_최소거리_m"


        count_score = normalize_positive(
            to_numeric_series(count_col),
            use_log=True
        )


        distance_score = normalize_distance(
            to_numeric_series(distance_col)
        )


        category_score = (
            count_score * 0.60
            +
            distance_score * 0.40
        )


        youth_scores.append(
            category_score
        )


    청년선호시설점수 = pd.concat(
        youth_scores,
        axis=1
    ).mean(axis=1)


    # =====================================================
    # 6. 교통 접근성 점수
    #
    # 1.5km 내 버스정류소 개수 60%
    # 가장 가까운 버스정류소 거리 40%
    # =====================================================

    bus_count = to_numeric_series(
        "버스정류소_1500m_개수"
    )

    bus_distance = to_numeric_series(
        "가장가까운_버스정류소_m"
    )


    bus_count_score = normalize_positive(
        bus_count,
        use_log=True
    )


    bus_distance_score = normalize_distance(
        bus_distance
    )


    교통접근성점수 = (
        bus_count_score * 0.60
        +
        bus_distance_score * 0.40
    )


    # =====================================================
    # 7. 월세 주거비 계산
    #
    # 월세 + 월세보증금의 월 환산액
    #
    # 프로젝트 분석용 가정:
    # 보증금 연 5%를 월 비용으로 환산
    # =====================================================

    monthly_rent = to_numeric_series(
        "월세_중앙값_만원"
    )

    monthly_deposit = to_numeric_series(
        "월세보증금_중앙값_만원"
    )


    # 0원은 실제 가격이 아니라
    # 거래 데이터가 없는 것으로 처리
    monthly_rent = monthly_rent.replace(
        0,
        np.nan
    )

    monthly_deposit = monthly_deposit.replace(
        0,
        np.nan
    )


    # 거래가 없는 동은 전체 중앙값으로 보정
    if monthly_rent.notna().any():

        monthly_rent = monthly_rent.fillna(
            monthly_rent.median()
        )

    else:

        monthly_rent = pd.Series(
            [0.0] * len(df),
            index=df.index
        )


    if monthly_deposit.notna().any():

        monthly_deposit = monthly_deposit.fillna(
            monthly_deposit.median()
        )

    else:

        monthly_deposit = pd.Series(
            [0.0] * len(df),
            index=df.index
        )


    # =====================================================
    # 8. 보증금 월 환산
    # =====================================================

    DEPOSIT_ANNUAL_RATE = 0.05


    deposit_monthly_cost = (
        monthly_deposit
        * DEPOSIT_ANNUAL_RATE
        / 12
    )


    # 최종 월 환산 주거비
    equivalent_monthly_cost = (
        monthly_rent
        +
        deposit_monthly_cost
    )


    # =====================================================
    # 9. 주거 가성비 점수
    #
    # 월 환산 주거비가 낮을수록 높은 점수
    # =====================================================

    housing_min = equivalent_monthly_cost.min()
    housing_max = equivalent_monthly_cost.max()


    if housing_max != housing_min:

        주거가성비점수 = (
            1
            -
            (
                (equivalent_monthly_cost - housing_min)
                /
                (housing_max - housing_min)
            )
        ) * 100

    else:

        주거가성비점수 = pd.Series(
            [50.0] * len(df),
            index=df.index
        )


    # =====================================================
    # 10. 인프라 접근성 지수
    #
    # 생활 인프라 30
    # 2030 선호시설 25
    # 교통 15
    #
    # 합계 70을 다시 100점 기준으로 환산
    # =====================================================

    접근성지수 = (
        생활인프라점수 * (30 / 70)
        +
        청년선호시설점수 * (25 / 70)
        +
        교통접근성점수 * (15 / 70)
    )


    # =====================================================
    # 11. 가격_norm
    #
    # 기존 페이지 구조 호환용
    # 월 환산 주거비 기준 0 ~ 1
    # =====================================================

    if housing_max != housing_min:

        가격_norm = (
            (equivalent_monthly_cost - housing_min)
            /
            (housing_max - housing_min)
        )

    else:

        가격_norm = pd.Series(
            [0.5] * len(df),
            index=df.index
        )


    # =====================================================
    # 12. 최종 HL-Score
    #
    # 생활 인프라       30%
    # 2030 선호시설     25%
    # 교통 접근성       15%
    # 주거 가성비       30%
    # =====================================================

    HL_Score = (
        생활인프라점수 * 0.30
        +
        청년선호시설점수 * 0.25
        +
        교통접근성점수 * 0.15
        +
        주거가성비점수 * 0.30
    )


    # =====================================================
    # 13. 기존 페이지 반환 구조 유지
    # =====================================================

    summary_df = pd.DataFrame()


    summary_df["지역"] = (
        df["자치구"].astype(str)
        +
        " "
        +
        df["행정동"].astype(str)
    )


    # 페이지 기존 변수명은 호환을 위해 유지
    # 실제 값은 월세 중앙값
    summary_df["평균임대료"] = (
        monthly_rent.round(1)
    )


    summary_df["가격_norm"] = (
        가격_norm.round(4)
    )


    summary_df["접근성지수"] = (
        접근성지수.round(1)
    )


    summary_df["HL_Score"] = (
        HL_Score.round(1)
    )


    # =====================================================
    # 14. 검증용 세부 데이터
    # =====================================================

    summary_df["월세보증금"] = (
        monthly_deposit.round(1)
    )


    summary_df["월환산주거비"] = (
        equivalent_monthly_cost.round(1)
    )


    summary_df["생활인프라점수"] = (
        생활인프라점수.round(1)
    )


    summary_df["2030선호시설점수"] = (
        청년선호시설점수.round(1)
    )


    summary_df["교통접근성점수"] = (
        교통접근성점수.round(1)
    )


    summary_df["주거가성비점수"] = (
        주거가성비점수.round(1)
    )


    # =====================================================
    # 15. HL-Score 높은 순으로 정렬
    # =====================================================

    summary_df = summary_df.sort_values(
        by="HL_Score",
        ascending=False
    ).reset_index(drop=True)


    # =====================================================
    # 16. 터미널 검증 출력
    # =====================================================

    print()
    print("==========================================================================")
    print("HL-Score 세부 점수 검증")
    print("==========================================================================")

    print(
        summary_df[
            [
                "지역",
                "평균임대료",
                "월세보증금",
                "월환산주거비",
                "생활인프라점수",
                "2030선호시설점수",
                "교통접근성점수",
                "주거가성비점수",
                "HL_Score"
            ]
        ].to_string(index=False)
    )

    print()
    print("✅ HL-Score 계산 완료")
    print()

    return summary_df

# 메인 페이지
@app.route('/')
def index():
    return render_template('index.html')

# HL-Score 대시보드 페이지 및 API 추가
@app.route('/hl-dashboard')
def hl_dashboard():
    df_score = compute_hl_scores()
    data_records = df_score.to_dict(orient='records') if not df_score.empty else []
    return render_template('hl_dashboard.html', districts=data_records)

@app.route('/api/hl-scores')
def api_hl_scores():
    df_score = compute_hl_scores()
    return jsonify(df_score.to_dict(orient='records'))

# 발표용 HL-Score 분석 / 시각화 페이지
@app.route('/hl-analysis')
def hl_analysis():
    df_score = compute_hl_scores()

    data_records = (
        df_score.to_dict(orient='records')
        if not df_score.empty
        else []
    )

    return render_template(
        'hl_analysis.html',
        districts=data_records
    )

# 1. 팀원 개인 페이지 (templates/미니프로젝트/ 하위 폴더 경로 반영)
@app.route('/seunghyeon')
def seunghyeon():
    return render_template('미니프로젝트/승현.html')

@app.route('/miseon')
def miseon():
    return render_template('미니프로젝트/미선.html')

@app.route('/younggeun')
def younggeun():
    return render_template('미니프로젝트/영근.html')

@app.route('/seunghee')
def seunghee():
    return render_template('미니프로젝트/승희.html')

# 2. 프로젝트 주요 문서 (templates/ 바로 아래 위치)
@app.route('/plan')
def plan():
    return render_template('plan.html')

@app.route('/plan2')
def plan2():
    return render_template('plan2.html')

@app.route('/plan3')
def plan3():
    return render_template('plan3.html')

@app.route('/business-model')
def business_model():
    return render_template('business_model.html')

# 3. Git 가이드 (templates/ 바로 아래 위치)
@app.route('/git-command-guide')
def git_command_guide():
    return render_template('Git_command_guide.html')

@app.route('/git-team-guide')
def git_team_guide():
    return render_template('Git_team_guide.html')

if __name__ == '__main__':
    app.run(debug=True)