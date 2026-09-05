from pathlib import Path

from flask import Flask, jsonify, render_template
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent

FINAL_DATA_FILE = (
    BASE_DIR
    / "data"
    / "processed"
    / "청년주거환경_정책통합분석_공공시설_공공임대_버스정류소반영.csv"
)

app = Flask(__name__)

try:
    app.json.ensure_ascii = False
except Exception:
    pass


TRUE_VALUES = {
    "true",
    "1",
    "yes",
    "y",
    "t",
    "예",
    "참",
}


def to_bool(value):
    if isinstance(value, bool):
        return value

    if pd.isna(value):
        return False

    return str(value).strip().lower() in TRUE_VALUES


def to_number(value, decimals=None):
    if pd.isna(value):
        return None

    number = pd.to_numeric(
        str(value).replace(",", ""),
        errors="coerce",
    )

    if pd.isna(number):
        return None

    number = float(number)

    if decimals is not None:
        number = round(number, decimals)

    return number


def format_manwon(value):
    number = to_number(value, 1)

    if number is None:
        return "표본부족"

    if float(number).is_integer():
        return f"{int(number):,}만원"

    return f"{number:,.1f}만원"


def first_value(row, candidates, default=None):
    for column in candidates:
        if column not in row.index:
            continue

        value = row[column]

        if pd.isna(value):
            continue

        return value

    return default


def split_region(region):
    text = str(region).strip()
    parts = text.split(" ", 1)

    if len(parts) == 2:
        return parts[0], parts[1]

    return "", text


def dataframe_to_records(df):
    safe_df = (
        df
        .astype(object)
        .where(pd.notna(df), None)
    )

    return safe_df.to_dict(orient="records")


def load_final_data():
    """
    최종 품질검사 PASS를 받은 통합 CSV를 그대로 사용합니다.
    Flask에서 HL-Score를 다시 계산하지 않습니다.
    """

    if not FINAL_DATA_FILE.exists():
        print()
        print("[오류] 최종 정책통합 CSV를 찾을 수 없습니다.")
        print(FINAL_DATA_FILE)
        return pd.DataFrame()

    try:
        df = pd.read_csv(
            FINAL_DATA_FILE,
            encoding="utf-8-sig",
        )

    except Exception as error:
        print()
        print("[오류] 최종 정책통합 CSV를 읽지 못했습니다.")
        print(error)
        return pd.DataFrame()

    required_columns = [
        "지역",
        "HL_Score",
        "생활인프라점수",
        "2030선호시설점수",
        "교통접근성점수",
        "주거가성비점수",
        "월환산주거비",
        "최종정책유형",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:
        print()
        print("[오류] 최종 CSV 필수 컬럼 누락:")

        for column in missing_columns:
            print("-", column)

        return pd.DataFrame()

    split_values = [
        split_region(region)
        for region in df["지역"].astype(str).str.strip()
    ]

    df["화면_자치구"] = [
        value[0]
        for value in split_values
    ]

    df["화면_행정동"] = [
        value[1]
        for value in split_values
    ]

    bool_columns = [
        "2030인구_TOP10",
        "수요대비인프라후보",
        "수요대비우선후보",
        "두분석_동시신호",
        "공공시설_상대부족",
        "공공시설_HL반영여부",
        "청년주거지원_점검후보",
        "공공임대_수요대비점검후보",
        "공공임대_HL반영여부",
        "청년교통공급_점검후보",
        "정류소공급_상대부족",
        "버스정류소_HL반영여부",
        "버스노선_정책분석사용여부",
    ]

    for column in bool_columns:
        if column in df.columns:
            df[column] = df[column].apply(to_bool)

    numeric_columns = [
        "HL_Score",
        "월환산주거비",
        "생활인프라점수",
        "2030선호시설점수",
        "교통접근성점수",
        "주거가성비점수",
        "2030인구수",
        "2030인구비율",
        "생활시설_1000명당",
        "버스정류소_1000명당",
        "선호시설_1000명당",
        "가장가까운_버스정류소_m",
        "전체거래건수",
        "청년공공시설수",
        "청년공공시설_1000명당",
        "공공임대_세대수",
        "공공임대_1000명당",
        "행복주택_세대수",
        "매입임대_세대수",
        "국민임대_세대수",
        "영구임대_세대수",
        "공식정류소수",
        "청년1000명당_정류소수",
    ]

    for column in numeric_columns:
        if column in df.columns:
            df[column] = pd.to_numeric(
                df[column],
                errors="coerce",
            )

    return df


def build_hl_frontend_data(df=None):
    if df is None:
        df = load_final_data()

    if df.empty:
        return []

    rows = []

    for index, row in df.iterrows():

        region = str(row["지역"]).strip()
        district = str(row["화면_자치구"]).strip()
        name = str(row["화면_행정동"]).strip()

        total_cost_value = to_number(
            row.get("월환산주거비"),
            1,
        )

        monthly_rent_raw = first_value(
            row,
            [
                "월세평균_만원",
                "월세_평균_만원",
                "평균월세_만원",
                "평균월세",
                "평균임대료",
            ],
        )

        deposit_raw = first_value(
            row,
            [
                "월세보증금평균_만원",
                "월세보증금_평균_만원",
                "평균보증금_만원",
                "월세보증금",
            ],
        )

        housing_sample = to_number(
            first_value(
                row,
                [
                    "전체거래건수",
                    "주거비_표본수",
                    "주거표본수",
                ],
            )
        )

        housing_score = to_number(
            row.get("주거가성비점수"),
            1,
        )

        rows.append(
            {
                "id": index + 1,
                "name": name,
                "district": district,
                "region": region,
                "지역": region,

                "hlScore": to_number(
                    row.get("HL_Score"),
                    1,
                ),
                "HL_Score": to_number(
                    row.get("HL_Score"),
                    1,
                ),

                "infra": to_number(
                    row.get("생활인프라점수"),
                    1,
                ),
                "preference": to_number(
                    row.get("2030선호시설점수"),
                    1,
                ),
                "transport": to_number(
                    row.get("교통접근성점수"),
                    1,
                ),
                "costEfficiency": housing_score,

                "monthlyRent": (
                    format_manwon(monthly_rent_raw)
                    if monthly_rent_raw is not None
                    else "—"
                ),
                "deposit": (
                    format_manwon(deposit_raw)
                    if deposit_raw is not None
                    else "—"
                ),
                "totalCost": (
                    format_manwon(total_cost_value)
                    if total_cost_value is not None
                    else "표본부족"
                ),
                "totalCostValue": total_cost_value,

                "housingSample": housing_sample,
                "housingSampleStatus": (
                    "표본부족"
                    if housing_sample is not None
                    and housing_sample <= 4
                    else (
                        "저표본 주의"
                        if housing_sample is not None
                        and housing_sample <= 19
                        else "정상"
                    )
                ),

                "youthPopulation": to_number(
                    row.get("2030인구수")
                ),
                "youthPopulationRate": to_number(
                    row.get("2030인구비율"),
                    2,
                ),

                "policyType": (
                    None
                    if pd.isna(row.get("최종정책유형"))
                    else str(row.get("최종정책유형"))
                ),

                "weakFactor": (
                    None
                    if pd.isna(row.get("HL주요취약요인"))
                    else str(row.get("HL주요취약요인"))
                ),

                "policyEvidence": (
                    None
                    if pd.isna(row.get("정책근거요약"))
                    else str(row.get("정책근거요약"))
                ),

                "policySuggestion": (
                    None
                    if pd.isna(row.get("통합정책제안"))
                    else str(row.get("통합정책제안"))
                ),

                "publicFacilityCount": to_number(
                    row.get("청년공공시설수")
                ),

                "publicRentalCount": to_number(
                    row.get("공공임대_세대수")
                ),

                "officialBusStops": to_number(
                    row.get("공식정류소수")
                ),

                "publicRentalCandidate": to_bool(
                    row.get(
                        "청년주거지원_점검후보",
                        False,
                    )
                ),

                "busSupplyCandidate": to_bool(
                    row.get(
                        "청년교통공급_점검후보",
                        False,
                    )
                ),

                "demandPriorityCandidate": to_bool(
                    row.get(
                        "수요대비우선후보",
                        False,
                    )
                ),

                "excludedFromPolicyRanking": (
                    str(
                        row.get(
                            "최종정책유형",
                            ""
                        )
                    ).strip()
                    == "HL순위 제외"
                ),
            }
        )

    rows.sort(
        key=lambda item: (
            item["hlScore"] is None,
            -(item["hlScore"] or 0),
        )
    )

    return rows


def compute_hl_scores():
    """
    기존 코드 호환용 함수.
    현재는 HL-Score를 새로 계산하지 않고 확정값만 반환합니다.
    """

    rows = build_hl_frontend_data()

    if not rows:
        return pd.DataFrame()

    return pd.DataFrame(rows)


def build_policy_summary(df=None):
    if df is None:
        df = load_final_data()

    if df.empty:
        return {
            "regionCount": 0,
            "policyTypeCounts": {},
            "publicFacilityCount": 0,
            "publicRentalCount": 0,
            "officialBusStopCount": 0,
            "housingSupportCandidateCount": 0,
            "busSupplyCandidateCount": 0,
        }

    def total_of(column):
        if column not in df.columns:
            return 0

        return int(
            pd.to_numeric(
                df[column],
                errors="coerce",
            )
            .fillna(0)
            .sum()
        )

    policy_counts = {}

    if "최종정책유형" in df.columns:
        policy_counts = (
            df["최종정책유형"]
            .fillna("미분류")
            .value_counts()
            .to_dict()
        )

    housing_candidates = 0

    if "청년주거지원_점검후보" in df.columns:
        housing_candidates = int(
            df["청년주거지원_점검후보"]
            .apply(to_bool)
            .sum()
        )

    bus_candidates = 0

    if "청년교통공급_점검후보" in df.columns:
        bus_candidates = int(
            df["청년교통공급_점검후보"]
            .apply(to_bool)
            .sum()
        )

    return {
        "regionCount": int(len(df)),
        "policyTypeCounts": policy_counts,
        "publicFacilityCount": total_of(
            "청년공공시설수"
        ),
        "publicRentalCount": total_of(
            "공공임대_세대수"
        ),
        "officialBusStopCount": total_of(
            "공식정류소수"
        ),
        "housingSupportCandidateCount": housing_candidates,
        "busSupplyCandidateCount": bus_candidates,
    }


# =========================================================
# 페이지 Route
#
# 최종 메뉴 노출 순서:
# 1. 시각화 대시보드
# 2. HL Score
# 3. 종합 분석
# =========================================================

@app.route("/")
def index():
    return render_template("index.html")


# 1. 시각화 대시보드
@app.route("/dashboard")
@app.route("/visual-dashboard")
def dashboard():
    df = load_final_data()

    records = (
        dataframe_to_records(df)
        if not df.empty
        else []
    )

    return render_template(
        "dashboard.html",
        districts=records,
    )


# 과거 시각화 주소 호환
@app.route("/hl-analysis")
def hl_analysis():
    df = load_final_data()

    records = (
        dataframe_to_records(df)
        if not df.empty
        else []
    )

    return render_template(
        "dashboard.html",
        districts=records,
    )


# 2. HL Score
@app.route("/hl-dashboard")
def hl_dashboard():
    records = build_hl_frontend_data()

    return render_template(
        "hl_dashboard.html",
        districts=records,
    )


# 3. 종합 분석
@app.route("/policy-dashboard")
@app.route("/policy-analysis")
def policy_dashboard():
    df = load_final_data()

    records = (
        dataframe_to_records(df)
        if not df.empty
        else []
    )

    summary = build_policy_summary(df)

    return render_template(
        "policy_dashboard.html",
        districts=records,
        summary=summary,
    )


# =========================================================
# API
# =========================================================

@app.route("/api/hl-scores")
def api_hl_scores():
    return jsonify(
        build_hl_frontend_data()
    )


@app.route("/api/final-data")
def api_final_data():
    df = load_final_data()

    if df.empty:
        return jsonify([])

    return jsonify(
        dataframe_to_records(df)
    )


@app.route("/api/policy-summary")
def api_policy_summary():
    return jsonify(
        build_policy_summary()
    )


# =========================================================
# 기존 팀원 페이지 / 문서 Route 유지
# =========================================================

@app.route("/seunghyeon")
def seunghyeon():
    return render_template(
        "미니프로젝트/승현.html"
    )


@app.route("/miseon")
def miseon():
    return render_template(
        "미니프로젝트/미선.html"
    )


@app.route("/younggeun")
def younggeun():
    return render_template(
        "미니프로젝트/영근.html"
    )


@app.route("/seunghee")
def seunghee():
    return render_template(
        "미니프로젝트/승희.html"
    )


@app.route("/plan")
def plan():
    return render_template("plan.html")


@app.route("/plan2")
def plan2():
    return render_template("plan2.html")


@app.route("/plan3")
def plan3():
    return render_template("plan3.html")


@app.route("/business-model")
def business_model():
    return render_template(
        "business_model.html"
    )


@app.route("/git-command-guide")
def git_command_guide():
    return render_template(
        "Git_command_guide.html"
    )


@app.route("/git-team-guide")
def git_team_guide():
    return render_template(
        "Git_team_guide.html"
    )


if __name__ == "__main__":
    app.run(debug=True)
