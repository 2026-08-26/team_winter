import csv
from pathlib import Path


# =========================================================
# 1. 경로 설정
# =========================================================

BASE_DIR = Path(__file__).resolve().parent.parent
PROCESSED_DIR = BASE_DIR / "data" / "processed"

INFRA_FILE = PROCESSED_DIR / "동별_통합인프라.csv"
HOUSING_FILE = PROCESSED_DIR / "동별_주거비.csv"
POPULATION_FILE = PROCESSED_DIR / "동별_2030인구.csv"

OUTPUT_FILE = PROCESSED_DIR / "25개동_통합분석.csv"


# =========================================================
# 2. CSV 읽기
# =========================================================

def read_csv(file_path):

    if not file_path.exists():
        print(f"❌ 파일 없음: {file_path.name}")
        return []

    with open(
        file_path,
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        return list(csv.DictReader(file))


# =========================================================
# 3. 자치구 이름 정리
# =========================================================

def clean_gu_name(value):

    if value is None:
        return ""

    value = value.strip()

    # 인구 원본에 긴 자치구명이 들어있는 경우 대비
    if "동구" in value:
        return "동구"

    if "서구" in value:
        return "서구"

    if "남구" in value:
        return "남구"

    if "북구" in value:
        return "북구"

    if "광산구" in value:
        return "광산구"

    return value


# =========================================================
# 4. 컬럼 찾기
# =========================================================

def find_value(row, possible_names):

    for name in possible_names:

        if name in row:
            return row[name]

    return ""


# =========================================================
# 5. 최종 통합
# =========================================================

def merge_final():

    print()
    print("========================================")
    print("📊 25개 동 최종 데이터 통합 시작")
    print("========================================")

    infra_rows = read_csv(INFRA_FILE)
    housing_rows = read_csv(HOUSING_FILE)
    population_rows = read_csv(POPULATION_FILE)

    if not infra_rows:
        return

    if not housing_rows:
        return

    if not population_rows:
        return

    print(f"인프라 데이터: {len(infra_rows)}개 동")
    print(f"주거비 데이터: {len(housing_rows)}개 동")
    print(f"인구 데이터: {len(population_rows)}개 동")

    # -----------------------------------------------------
    # 주거비 데이터 검색용
    # -----------------------------------------------------

    housing_dict = {}

    for row in housing_rows:

        gu = clean_gu_name(
            find_value(row, ["자치구", "gu_name"])
        )

        dong = find_value(
            row,
            ["행정동", "dong_name"]
        ).strip()

        housing_dict[(gu, dong)] = row


    # -----------------------------------------------------
    # 인구 데이터 검색용
    # -----------------------------------------------------

    population_dict = {}

    for row in population_rows:

        gu = clean_gu_name(
            find_value(
                row,
                [
                    "자치구",
                    "팀계획_자치구",
                    "gu_name"
                ]
            )
        )

        dong = find_value(
            row,
            [
                "행정동",
                "dong_name"
            ]
        ).strip()

        population_dict[(gu, dong)] = row


    # -----------------------------------------------------
    # 인프라를 기준으로 통합
    # -----------------------------------------------------

    final_rows = []

    missing_housing = []
    missing_population = []

    for infra in infra_rows:

        gu = clean_gu_name(
            find_value(infra, ["자치구", "gu_name"])
        )

        dong = find_value(
            infra,
            ["행정동", "dong_name"]
        ).strip()

        key = (gu, dong)

        final_row = {
            "자치구": gu,
            "행정동": dong
        }


        # -------------------------------------------------
        # 인프라 데이터
        # -------------------------------------------------

        for column, value in infra.items():

            if column not in ["자치구", "행정동"]:
                final_row[column] = value


        # -------------------------------------------------
        # 주거비 데이터
        # -------------------------------------------------

        housing = housing_dict.get(key)

        if housing:

            for column, value in housing.items():

                if column not in ["자치구", "행정동"]:
                    final_row[column] = value

        else:

            missing_housing.append(
                f"{gu} {dong}"
            )


        # -------------------------------------------------
        # 인구 데이터
        # -------------------------------------------------

        population = population_dict.get(key)

        if population:

            # 필요한 인구 항목만 최종 데이터에 추가
            final_row["총인구수"] = find_value(
                population,
                ["총인구수", "총 인구수"]
            )

            final_row["20대인구수"] = find_value(
                population,
                [
                    "20~29세",
                    "20대인구수",
                    "20대 인구수"
                ]
            )

            final_row["30대인구수"] = find_value(
                population,
                [
                    "30~39세",
                    "30대인구수",
                    "30대 인구수"
                ]
            )

            final_row["2030인구수"] = find_value(
                population,
                [
                    "2030인구수",
                    "2030 인구수"
                ]
            )

            final_row["2030인구비율"] = find_value(
                population,
                [
                    "2030인구비율",
                    "2030 인구비율"
                ]
            )

        else:

            missing_population.append(
                f"{gu} {dong}"
            )


        final_rows.append(final_row)


    # =====================================================
    # 6. CSV 저장
    # =====================================================

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=final_rows[0].keys()
        )

        writer.writeheader()
        writer.writerows(final_rows)


    # =====================================================
    # 7. 결과 확인
    # =====================================================

    print()
    print("========================================")
    print("✅ 최종 통합 완료")
    print("========================================")

    print(f"생성 파일: {OUTPUT_FILE.name}")
    print(f"최종 분석 대상: {len(final_rows)}개 동")

    if missing_housing:

        print()
        print("⚠️ 주거비 연결 실패:")
        for item in missing_housing:
            print(" -", item)

    else:
        print("✅ 주거비 25개 동 모두 연결")


    if missing_population:

        print()
        print("⚠️ 인구 연결 실패:")
        for item in missing_population:
            print(" -", item)

    else:
        print("✅ 인구 25개 동 모두 연결")


# =========================================================
# 실행
# =========================================================

if __name__ == "__main__":

    merge_final()