from flask import Flask, render_template

app = Flask(__name__)

# 메인 페이지 연동
@app.route('/')
def home():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)