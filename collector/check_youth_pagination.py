import re
import requests
from bs4 import BeautifulSoup


URL = "https://youth.gwangju.go.kr/www/areaResve/resveList"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 "
        "(Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/120 Safari/537.36"
    )
}


response = requests.get(
    URL,
    headers=HEADERS,
    timeout=30
)

response.raise_for_status()
response.encoding = "utf-8"

html = response.text

soup = BeautifulSoup(
    html,
    "html.parser"
)


print("\n========================================")
print("1. pageIndex가 들어있는 FORM")
print("========================================")


page_input = soup.find(
    "input",
    attrs={"name": "pageIndex"}
)


if page_input is None:

    print("pageIndex를 찾지 못했습니다.")

else:

    form = page_input.find_parent(
        "form"
    )


    if form is None:

        print("pageIndex의 부모 FORM을 찾지 못했습니다.")

    else:

        print(
            "FORM id     =",
            form.get("id")
        )

        print(
            "FORM name   =",
            form.get("name")
        )

        print(
            "FORM action =",
            form.get("action")
        )

        print(
            "FORM method =",
            form.get("method")
        )


        print("\n[FORM 안의 input]")


        for tag in form.find_all(
            "input"
        ):

            print(
                "name =",
                tag.get("name"),
                "/ value =",
                tag.get("value"),
                "/ type =",
                tag.get("type")
            )


        print("\n[FORM 안의 select]")


        for tag in form.find_all(
            "select"
        ):

            print(
                "name =",
                tag.get("name"),
                "/ id =",
                tag.get("id")
            )


print("\n========================================")
print("2. resveList 함수 찾기")
print("========================================")


# script 태그를 하나씩 확인
found = False


for script in soup.find_all(
    "script"
):

    script_text = script.string


    if not script_text:

        script_text = script.get_text(
            "\n",
            strip=False
        )


    if (
        script_text
        and "resveList" in script_text
    ):

        found = True

        print("\n----------------------------------------")
        print("resveList가 포함된 SCRIPT")
        print("----------------------------------------")

        # 너무 길게 출력되지 않도록
        # resveList 주변만 출력
        position = script_text.find(
            "resveList"
        )

        start = max(
            0,
            position - 500
        )

        end = min(
            len(script_text),
            position + 1500
        )

        print(
            script_text[
                start:end
            ]
        )


if not found:

    print(
        "HTML 내부 script에서는 "
        "resveList 함수 정의를 찾지 못했습니다."
    )


print("\n========================================")
print("3. JS 파일 목록")
print("========================================")


for script in soup.find_all(
    "script",
    src=True
):

    src = script.get(
        "src"
    )

    if src:

        print(src)


print("\n========================================")
print("확인 완료")
print("========================================")