from flask import Flask, render_template, jsonify
import pandas as pd
import numpy as np

app = Flask(__name__)

def compute_hl_scores():
    """광주 2030 주거 가성비 및 생활 인프라 통합 지수(HL-Score) 산출"""
    try:
        # 정제된 실거래가 데이터 로드
        df = pd.read_csv("raw_gwangju_oneroom_rent.csv")
    except FileNotFoundError:
        return pd.DataFrame()

    # 컬럼 정확히 매칭 (사용자분이 공유해주신 실제 CSV 컬럼 기준)
    sigungu_col = '시군구' if '시군구' in df.columns else df.columns[1]
    price_col = '월세금(만원)' if '월세금(만원)' in df.columns else [c for c in df.columns if '월세' in c][0]
    
    # 데이터 전처리 (숫자형 변환 및 결측치 제거)
    df[price_col] = pd.to_numeric(df[price_col].astype(str).str.replace(',', ''), errors='coerce')
    df = df.dropna(subset=[sigungu_col, price_col])
    
    # 자치구별 평균 임대료 산출 (시군구 문자열에서 앞 두세 글자나 자치구 단위 추출 가공)
    # 예: '광주광역시 북구 용봉동' -> '북구' 또는 전체 시군구 명칭 활용
    summary_df = df.groupby(sigungu_col)[price_col].mean().reset_index()
    summary_df.columns = ['지역', '평균임대료']
    
    # Min-Max 정규화 (가격_norm)
    min_p = summary_df['평균임대료'].min()
    max_p = summary_df['평균임대료'].max()
    
    if max_p != min_p:
        summary_df['가격_norm'] = (summary_df['평균임대료'] - min_p) / (max_p - min_p)
    else:
        summary_df['가격_norm'] = 0.5

    # 인프라 접근성 지수 결합 (임시 점수, 추후 Kakao API 결과와 연동)
    np.random.seed(42)
    summary_df['접근성지수'] = np.random.uniform(65, 98, len(summary_df))
    weight_w = 1.3 # 2030 청년 선호 가중치 W
    
    # HL-Score 계산 공식 반영 (안정적인 분모 보정값 0.1 적용)
    summary_df['HL_Score'] = (summary_df['접근성지수'] * weight_w) / (summary_df['가격_norm'] + 0.1)
    summary_df['HL_Score'] = summary_df['HL_Score'].round(1)
    
    return summary_df.sort_values(by='HL_Score', ascending=False)

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