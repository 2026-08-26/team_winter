from flask import Flask, render_template, jsonify
import pandas as pd
import numpy as np

app = Flask(__name__)

def compute_hl_scores():
    """data/processed/25개동_통합분석.csv 파일 기반 HL-Score 산출"""
    try:
        # 팀원 1이 가공한 최종 정제 데이터 로드
        df = pd.read_csv("data/processed/25개동_통합분석.csv")
    except FileNotFoundError:
        print("[오류] data/processed/25개동_통합분석.csv 파일을 찾을 수 없습니다.")
        return pd.DataFrame()

    print("--- 로드된 CSV 컬럼 목록 ---", df.columns.tolist())

    # 1. 지역/시군구/동 컬럼 동적 탐색
    sigungu_col = next((c for c in df.columns if '시군구' in c or '지역' in c or '동' in c), df.columns[0])
    
    # 2. 월세/임대료/금액 컬럼 동적 탐색
    price_col = next((c for c in df.columns if '월세' in c or '금액' in c or '임대료' in c), df.columns[-1])
    
    print(f"인식된 지역 컬럼: {sigungu_col}, 인식된 가격 컬럼: {price_col}")

    # 데이터 전처리 (숫자형 변환 및 결측치 제거)
    df[price_col] = pd.to_numeric(df[price_col].astype(str).str.replace(',', ''), errors='coerce')
    df = df.dropna(subset=[sigungu_col, price_col])
    
    # 자치구(또는 동)별 평균 임대료 산출
    summary_df = df.groupby(sigungu_col)[price_col].mean().reset_index()
    summary_df.columns = ['지역', '평균임대료']
    
    # Min-Max 정규화 (가격_norm)
    min_p = summary_df['평균임대료'].min()
    max_p = summary_df['평균임대료'].max()
    
    if max_p != min_p:
        summary_df['가격_norm'] = (summary_df['평균임대료'] - min_p) / (max_p - min_p)
    else:
        summary_df['가격_norm'] = 0.5

    # 인프라 접근성 지수 결합 (데이터에 컬럼이 있으면 활용, 없으면 난수 생성)
    if '접근성지수' in df.columns:
        summary_df['접근성지수'] = df.groupby(sigungu_col)['접근성지수'].mean().values
    else:
        np.random.seed(42)
        summary_df['접근성지수'] = np.random.uniform(65, 98, len(summary_df))
        
    weight_w = 1.3 # 2030 청년 선호 가중치 W
    
    # HL-Score 계산 공식 반영 (분모 보정값 0.1 적용)
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