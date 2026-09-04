from flask import Flask, render_template

app = Flask(__name__)

# 메인 페이지
@app.route('/')
def index():
    return render_template('index.html')

# 1. 팀원 개인 페이지 (templates/ 폴더 안에 위치하는 것을 권장)
@app.route('/seunghyeon')
def seunghyeon():
    return render_template('승현.html')

@app.route('/miseon')
def miseon():
    return render_template('미선.html')

@app.route('/younggeun')
def younggeun():
    return render_template('영근.html')

@app.route('/seunghee')
def seunghee():
    return render_template('승희.html')

# 2. 프로젝트 주요 문서
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

# 3. Git 가이드
@app.route('/git-command-guide')
def git_command_guide():
    return render_template('Git_command_guide.html')

@app.route('/git-team-guide')
def git_team_guide():
    return render_template('Git_team_guide.html')

if __name__ == '__main__':
    app.run(debug=True)