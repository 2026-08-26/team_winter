import re
import shutil
from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent
PROCESSED_DIR = BASE_DIR / "data" / "processed"

INPUT_FILE = PROCESSED_DIR / "청년소형주택_25개동_실거래.csv"
PUBLIC_RENTAL_FILE = PROCESSED_DIR / "공공임대주택_공급단위_행정동매핑.csv"
OUTPUT_FILE = PROCESSED_DIR / "동별_주거비.csv"
BACKUP_FILE = PROCESSED_DIR / "동별_주거비_공공임대제외전_백업.csv"
EXCLUDED_DETAIL_FILE = PROCESSED_DIR / "HL주거비_공공임대제외거래.csv"

MAX_AREA_M2 = 59.5
DEPOSIT_ANNUAL_RATE = 0.05
ANALYSIS_START = "202507"
ANALYSIS_END = "202606"

TARGET_DONGS = [
    ("동구", "충장동"), ("동구", "계림1동"), ("동구", "지산2동"),
    ("동구", "학동"), ("동구", "지원1동"),
    ("서구", "치평동"), ("서구", "풍암동"), ("서구", "화정2동"),
    ("서구", "농성1동"), ("서구", "금호1동"),
    ("남구", "봉선2동"), ("남구", "진월동"), ("남구", "방림1동"),
    ("남구", "효덕동"), ("남구", "송암동"),
    ("북구", "용봉동"), ("북구", "두암2동"), ("북구", "운암1동"),
    ("북구", "첨단2동"), ("북구", "문흥1동"),
    ("광산구", "첨단1동"), ("광산구", "수완동"), ("광산구", "신가동"),
    ("광산구", "우산동"), ("광산구", "송정1동"),
]


def to_numeric_series(series):
    return pd.to_numeric(
        series.astype(str).str.replace(",", "", regex=False),
        errors="coerce",
    )


def to_bool(value):
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def safe_mean(series):
    values = pd.to_numeric(series, errors="coerce").dropna()
    return "" if values.empty else round(values.mean(), 2)


def safe_median(series):
    values = pd.to_numeric(series, errors="coerce").dropna()
    return "" if values.empty else round(values.median(), 2)


def normalize_address(value):
    """공공임대 주소와 실거래 카카오 매칭주소를 같은 형태로 비교."""
    text = str(value or "").strip()
    for prefix in ("전남광주통합특별시 ", "광주광역시 "):
        if text.startswith(prefix):
            text = text[len(prefix):]
    text = re.sub(r"\s+", " ", text).strip()
    return text


def sample_status(count):
    if count == 0:
        return "거래없음"
    if count < 5:
        return "주의"
    if count < 20:
        return "보통"
    return "충분"


def backup_existing_file():
    if OUTPUT_FILE.exists() and not BACKUP_FILE.exists():
        shutil.copy2(OUTPUT_FILE, BACKUP_FILE)
        print(f"기존 동별_주거비.csv 백업: {BACKUP_FILE.name}")


def main():
    print("\n========================================")
    print("HL 주거비 재계산 - 공공임대 거래 제외")
    print("========================================")
    print("기준: 2025-07~2026-06 / 59.5㎡ 이하 / 전세+월세")
    print("HL 주거비: 민간 임대시장 실거래만 사용")
    print("공공임대: 별도 정책 보조지표로 유지")
    print(f"보증금 월환산율: 연 {DEPOSIT_ANNUAL_RATE*100:.1f}% (프로젝트 가정)")

    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"입력 파일 없음: {INPUT_FILE}")
    if not PUBLIC_RENTAL_FILE.exists():
        raise FileNotFoundError(f"공공임대 매핑 파일 없음: {PUBLIC_RENTAL_FILE}")

    backup_existing_file()

    df = pd.read_csv(
        INPUT_FILE,
        encoding="utf-8-sig",
        dtype=str,
        keep_default_na=False,
    )
    public = pd.read_csv(
        PUBLIC_RENTAL_FILE,
        encoding="utf-8-sig",
        dtype=str,
        keep_default_na=False,
    )

    required = [
        "프로젝트자치구", "프로젝트행정동", "deposit", "monthlyRent",
        "excluUseAr", "housing_type", "카카오매칭주소",
    ]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"실거래 필수 컬럼 누락: {missing}")
    if "주소" not in public.columns:
        raise ValueError("공공임대 매핑 파일에 '주소' 컬럼이 없습니다.")

    if "분석대상여부" in df.columns:
        df["분석대상여부"] = df["분석대상여부"].apply(to_bool)
        df = df[df["분석대상여부"] == True].copy()

    df["보증금_만원"] = to_numeric_series(df["deposit"])
    df["월세_만원"] = to_numeric_series(df["monthlyRent"])
    df["전용면적_m2"] = to_numeric_series(df["excluUseAr"])

    df = df[
        df["전용면적_m2"].notna()
        & (df["전용면적_m2"] <= MAX_AREA_M2)
        & df["보증금_만원"].notna()
        & df["월세_만원"].notna()
    ].copy()

    # 공공임대 단지 주소 세트 구성
    public_addresses = {
        normalize_address(addr)
        for addr in public["주소"]
        if normalize_address(addr)
    }

    df["주소_정규화"] = df["카카오매칭주소"].apply(normalize_address)
    df["공공임대주소일치"] = df["주소_정규화"].isin(public_addresses)

    original_valid_count = len(df)
    public_rental_count = int(df["공공임대주소일치"].sum())

    excluded = df[df["공공임대주소일치"]].copy()
    excluded.to_csv(EXCLUDED_DETAIL_FILE, index=False, encoding="utf-8-sig")

    # 핵심 수정: HL 주거비에서는 공공임대 실거래 제외
    market_df = df[~df["공공임대주소일치"]].copy()

    market_df["거래구분"] = "월세"
    market_df.loc[market_df["월세_만원"] == 0, "거래구분"] = "전세"
    market_df["월환산주거비_만원"] = (
        market_df["월세_만원"]
        + market_df["보증금_만원"] * DEPOSIT_ANNUAL_RATE / 12
    )

    print(f"\n원본 유효 실거래: {original_valid_count:,}건")
    print(f"공공임대 주소 일치 제외: {public_rental_count:,}건")
    print(f"HL 민간임대 분석 사용: {len(market_df):,}건")

    result = []

    for project_gu, project_dong in TARGET_DONGS:
        original_dong = df[
            (df["프로젝트자치구"] == project_gu)
            & (df["프로젝트행정동"] == project_dong)
        ]
        dong_df = market_df[
            (market_df["프로젝트자치구"] == project_gu)
            & (market_df["프로젝트행정동"] == project_dong)
        ]

        jeonse_df = dong_df[dong_df["거래구분"] == "전세"]
        monthly_df = dong_df[dong_df["거래구분"] == "월세"]

        transaction_count = len(dong_df)
        original_count = len(original_dong)
        excluded_count = int(original_dong["공공임대주소일치"].sum())

        source_gu = "광산구" if project_dong == "첨단2동" else project_gu

        output = {
            "자치구": project_gu,
            "행정동": project_dong,
            "공식조회자치구": source_gu,
            "원본유효거래건수": original_count,
            "공공임대제외건수": excluded_count,
            # 기존 하위 스크립트 호환: 이제 '전체거래건수'는 HL에 실제 사용한 민간임대 표본수
            "전체거래건수": transaction_count,
            "전세거래건수": len(jeonse_df),
            "월세거래건수": len(monthly_df),
            "전세보증금_평균값_만원": safe_mean(jeonse_df["보증금_만원"]),
            "월세보증금_평균값_만원": safe_mean(monthly_df["보증금_만원"]),
            "월세_평균값_만원": safe_mean(monthly_df["월세_만원"]),
            "전체임대차보증금_평균값_만원": safe_mean(dong_df["보증금_만원"]),
            "월환산주거비_평균값_만원": safe_mean(dong_df["월환산주거비_만원"]),
            "전용면적_평균값_m2": safe_mean(dong_df["전용면적_m2"]),
            "전세보증금_중앙값_만원": safe_median(jeonse_df["보증금_만원"]),
            "월세보증금_중앙값_만원": safe_median(monthly_df["보증금_만원"]),
            "월세_중앙값_만원": safe_median(monthly_df["월세_만원"]),
            "월환산주거비_중앙값_만원": safe_median(dong_df["월환산주거비_만원"]),
            "아파트거래건수": int((dong_df["housing_type"] == "아파트").sum()),
            "오피스텔거래건수": int((dong_df["housing_type"] == "오피스텔").sum()),
            "연립다세대거래건수": int((dong_df["housing_type"] == "연립다세대").sum()),
            "단독다가구거래건수": int((dong_df["housing_type"] == "단독/다가구").sum()),
            "표본상태": sample_status(transaction_count),
            "주거비산정대상": "민간임대 실거래(공공임대 주소 일치 거래 제외)",
            "면적기준": "전용면적 59.5㎡ 이하",
            "평수기준": "18평 이하",
            "거래유형기준": "전세+월세",
            "행정동매핑기준": "실거래 지번주소→좌표→공식 행정동",
            "공공임대제외기준": "마이홈 공공임대 공급단위 주소와 카카오 매칭주소 일치",
            "분석시작월": ANALYSIS_START,
            "분석종료월": ANALYSIS_END,
            "보증금환산율": DEPOSIT_ANNUAL_RATE,
        }
        result.append(output)

        print(
            f"{project_gu} {project_dong}: "
            f"원본 {original_count} / 공공임대 제외 {excluded_count} / "
            f"민간 {transaction_count} / 월환산 평균 {output['월환산주거비_평균값_만원']}"
        )

    result_df = pd.DataFrame(result)
    if len(result_df) != 25:
        raise ValueError("결과가 25개 동이 아닙니다.")

    result_df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")

    print("\n========================================")
    print("수정된 동별 주거비 저장 완료")
    print("========================================")
    print(OUTPUT_FILE)
    print(f"민간임대 표본 합계: {int(result_df['전체거래건수'].sum()):,}건")
    print(f"공공임대 제외 합계: {int(result_df['공공임대제외건수'].sum()):,}건")

    suwan = result_df[result_df["행정동"] == "수완동"].iloc[0]
    print("\n[수완동 확인]")
    print(f"원본: {int(suwan['원본유효거래건수'])}건")
    print(f"공공임대 제외: {int(suwan['공공임대제외건수'])}건")
    print(f"민간임대 사용: {int(suwan['전체거래건수'])}건")
    print(f"월환산주거비: {suwan['월환산주거비_평균값_만원']}")
    print(f"표본상태: {suwan['표본상태']}")


if __name__ == "__main__":
    main()
