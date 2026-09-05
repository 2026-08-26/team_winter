import os
import sys
import pandas as pd


# =========================================================
# 1. 파일 경로
# =========================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

INPUT_FILE = os.path.join(
    BASE_DIR,
    "data",
    "raw",
    "청년_공공시설.csv"
)


# =========================================================
# 2. 기본 설정
# =========================================================

VALID_DISTRICTS = [
    "동구",
    "서구",
    "남구",
    "북구",
    "광산구"
]

VALID_TYPES = [
    "통합지원형",
    "취업지원형",
    "창업지원형",
    "프로그램운영형",
    "기타공간"
]

errors = []
warnings = []


# =========================================================
# 3. CSV 불러오기
# =========================================================

print("\n========================================")
print("청년 공공시설 데이터 품질검사")
print("========================================")


if not os.path.exists(INPUT_FILE):

    print("\n[오류]")
    print("청년_공공시설.csv 파일을 찾을 수 없습니다.")
    print(INPUT_FILE)

    sys.exit(1)


try:

    df = pd.read_csv(
        INPUT_FILE,
        encoding="utf-8-sig"
    )

except Exception as e:

    print("\n[오류]")
    print("CSV 파일을 읽지 못했습니다.")
    print(e)

    sys.exit(1)


print(f"\n검사 파일 : {INPUT_FILE}")
print(f"전체 행 수 : {len(df)}")
print(f"전체 열 수 : {len(df.columns)}")


# =========================================================
# 4. 필수 컬럼 검사
# =========================================================

required_columns = [
    "시설명",
    "시설유형",
    "기관분류",
    "주소",
    "자치구",
    "출처",
    "출처URL",
    "수집기준",
    "수집일"
]


missing_columns = [
    col
    for col in required_columns
    if col not in df.columns
]


if missing_columns:

    errors.append(
        "필수 컬럼 누락 : "
        + ", ".join(missing_columns)
    )


if errors:

    print("\n[검사 실패]")

    for error in errors:
        print("X", error)

    sys.exit(1)


# =========================================================
# 5. 빈 데이터 검사
# =========================================================

important_columns = [
    "시설명",
    "시설유형",
    "기관분류",
    "주소",
    "자치구"
]


for col in important_columns:

    blank = (
        df[col]
        .fillna("")
        .astype(str)
        .str.strip()
        == ""
    )

    count = blank.sum()

    if count > 0:

        errors.append(
            f"{col} 빈 값 : {count}개"
        )


# =========================================================
# 6. 공공시설 여부 검사
# =========================================================

not_public = df[
    df["기관분류"]
    .fillna("")
    .astype(str)
    .str.strip()
    != "공공"
]


if len(not_public) > 0:

    errors.append(
        f"'공공'이 아닌 데이터가 {len(not_public)}개 포함되어 있습니다."
    )


# =========================================================
# 7. 자치구 검사
# =========================================================

invalid_districts = df[
    ~df["자치구"].isin(
        VALID_DISTRICTS
    )
]


if len(invalid_districts) > 0:

    values = (
        invalid_districts["자치구"]
        .astype(str)
        .unique()
        .tolist()
    )

    errors.append(
        "잘못된 자치구 : "
        + ", ".join(values)
    )


# =========================================================
# 8. 시설유형 검사
# =========================================================

invalid_types = df[
    ~df["시설유형"].isin(
        VALID_TYPES
    )
]


if len(invalid_types) > 0:

    values = (
        invalid_types["시설유형"]
        .astype(str)
        .unique()
        .tolist()
    )

    warnings.append(
        "예상하지 못한 시설유형 : "
        + ", ".join(values)
    )


# =========================================================
# 9. 시설명 + 주소 중복 검사
# =========================================================

duplicate_rows = df[
    df.duplicated(
        subset=[
            "시설명",
            "주소"
        ],
        keep=False
    )
]


if len(duplicate_rows) > 0:

    duplicate_count = (
        duplicate_rows[
            ["시설명", "주소"]
        ]
        .drop_duplicates()
        .shape[0]
    )

    errors.append(
        f"시설명+주소 중복 시설 : {duplicate_count}개"
    )


# =========================================================
# 10. 주소 형식 검사
# =========================================================

invalid_address = df[
    ~df["주소"]
    .fillna("")
    .astype(str)
    .str.contains(
        "광주",
        na=False
    )
]


if len(invalid_address) > 0:

    warnings.append(
        f"'광주'가 포함되지 않은 주소 : {len(invalid_address)}개"
    )


# =========================================================
# 11. 자치구와 주소 일치 검사
# =========================================================

district_mismatch = []


for _, row in df.iterrows():

    district = str(
        row["자치구"]
    ).strip()

    address = str(
        row["주소"]
    ).strip()


    if district and district not in address:

        district_mismatch.append(
            row["시설명"]
        )


if district_mismatch:

    warnings.append(
        f"자치구와 주소가 바로 일치하지 않는 시설 : "
        f"{len(district_mismatch)}개"
    )


# =========================================================
# 12. 이상한 시설명 검사
# =========================================================

suspicious_names = []


for _, row in df.iterrows():

    name = str(
        row["시설명"]
    ).strip()


    if (
        len(name) < 2
        or name in [
            "공공",
            "민간",
            "상세보기",
            "주소"
        ]
        or name.startswith("주소")
    ):

        suspicious_names.append(
            name
        )


if suspicious_names:

    errors.append(
        f"시설명 파싱이 이상해 보이는 데이터 : "
        f"{len(suspicious_names)}개"
    )


# =========================================================
# 13. 출처 검사
# =========================================================

wrong_source = df[
    df["출처"]
    .fillna("")
    .astype(str)
    .str.strip()
    != "광주청년통합플랫폼"
]


if len(wrong_source) > 0:

    warnings.append(
        f"출처명이 다른 행 : {len(wrong_source)}개"
    )


# =========================================================
# 14. 자치구별 시설 수
# =========================================================

district_count = (
    df["자치구"]
    .value_counts()
    .reindex(
        VALID_DISTRICTS,
        fill_value=0
    )
)


# =========================================================
# 15. 시설유형별 시설 수
# =========================================================

type_count = (
    df["시설유형"]
    .value_counts()
)


# =========================================================
# 16. 검사 결과 출력
# =========================================================

print("\n----------------------------------------")
print("자치구별 공공시설 수")
print("----------------------------------------")

print(
    district_count.to_string()
)


print("\n----------------------------------------")
print("시설유형별 시설 수")
print("----------------------------------------")

print(
    type_count.to_string()
)


print("\n----------------------------------------")
print("기본 검사 결과")
print("----------------------------------------")

print(
    f"전체 시설 수 : {len(df)}개"
)

print(
    f"시설명+주소 중복 행 : {len(duplicate_rows)}개"
)

print(
    f"공공이 아닌 행 : {len(not_public)}개"
)

print(
    f"주소 누락 : {df['주소'].isna().sum()}개"
)


# =========================================================
# 17. 경고 출력
# =========================================================

if warnings:

    print("\n[주의사항]")

    for warning in warnings:

        print(
            "!",
            warning
        )


# =========================================================
# 18. 최종 판정
# =========================================================

print("\n========================================")
print("최종 품질검사 결과")
print("========================================")


if errors:

    print("\n[검사 실패]")

    for error in errors:

        print(
            "X",
            error
        )


    print(
        f"\n총 {len(errors)}개의 오류가 있습니다."
    )

    print(
        "아직 정책분석에는 사용하지 마세요."
    )

    sys.exit(1)


else:

    print("\n모든 핵심 검사 통과")

    print(
        "청년 공공시설 원본 데이터의 "
        "기본 정합성이 확인되었습니다."
    )

    if not warnings:

        print(
            "추가 경고사항도 없습니다."
        )

    print(
        "\n청년 공공시설 데이터 품질검사 : PASS"
    )