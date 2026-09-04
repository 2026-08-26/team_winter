import csv
from pathlib import Path


# =========================================================
# 1. 파일 위치 설정
# =========================================================

BASE_DIR = Path(__file__).resolve().parent.parent

FILE = (
    BASE_DIR
    / "data"
    / "processed"
    / "25개동_통합분석.csv"
)


# =========================================================
# 2. CSV 읽기
# =========================================================

with open(
    FILE,
    "r",
    encoding="utf-8-sig",
    newline=""
) as f:

    rows = list(csv.DictReader(f))


# =========================================================
# 3. 기본 정보 확인
# =========================================================

print("=" * 60)
print("📊 최종 데이터 검수")
print("=" * 60)

print(f"전체 행정동 수: {len(rows)}")

if rows:
    print(f"전체 컬럼 수: {len(rows[0])}")
else:
    print("❌ 데이터가 없습니다.")
    exit()


# =========================================================
# 4. 2030 인구비율 계산 및 확인
# =========================================================

print()
print("[동별 핵심 데이터]")

problems = []


for row in rows:

    gu = row.get("자치구", "")
    dong = row.get("행정동", "")

    total_population = row.get("총인구수", "")
    population_2030 = row.get("2030인구수", "")
    ratio_2030 = row.get("2030인구비율", "")
    housing_count = row.get("전체거래건수", "")


    # -----------------------------------------------------
    # 기존 통합파일에 2030 비율이 비어 있으면 직접 계산
    # -----------------------------------------------------

    if not ratio_2030:

        try:

            total = float(total_population)
            pop_2030 = float(population_2030)

            if total > 0:

                ratio_2030 = round(
                    pop_2030 / total * 100,
                    2
                )

                # 현재 메모리상의 데이터에도 반영
                row["2030인구비율"] = ratio_2030

        except (ValueError, TypeError):

            ratio_2030 = ""


    print(
        f"{gu} {dong}"
        f" | 거래: {housing_count}"
        f" | 2030인구: {population_2030}"
        f" | 2030비율: {ratio_2030}"
    )


    # -----------------------------------------------------
    # 문제 검사
    # -----------------------------------------------------

    name = f"{gu} {dong}"


    if not population_2030:

        problems.append(
            f"{name} → 2030 인구 없음"
        )


    if ratio_2030 == "":

        problems.append(
            f"{name} → 2030 인구비율 계산 불가"
        )


    if housing_count in ["", None]:

        problems.append(
            f"{name} → 주거 데이터 없음"
        )


# =========================================================
# 5. 계산한 2030 인구비율을 CSV에도 저장
# =========================================================

with open(
    FILE,
    "w",
    encoding="utf-8-sig",
    newline=""
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=rows[0].keys()
    )

    writer.writeheader()
    writer.writerows(rows)


# =========================================================
# 6. 최종 검사 결과
# =========================================================

print()
print("=" * 60)
print("[문제 확인]")
print("=" * 60)


if problems:

    for problem in problems:

        print("⚠️", problem)

else:

    print("✅ 핵심 데이터 누락 없음")


print()
print("✅ 2030 인구비율 계산 결과를")
print("   25개동_통합분석.csv에 저장했습니다.")

print("=" * 60)