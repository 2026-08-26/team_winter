from pathlib import Path
import sys
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
P = BASE_DIR / "data" / "processed"

FINAL_FILE = P / "청년주거환경_정책통합분석_공공시설_공공임대_버스정류소반영.csv"
BASELINE_FILE = P / "청년주거환경_정책통합분석_공공시설_공공임대반영.csv"
HOUSING_FILE = P / "25개동_통합분석.csv"

EXPECTED_REGIONS = {
    "동구 충장동","동구 계림1동","동구 지산2동","동구 학동","동구 지원1동",
    "서구 치평동","서구 풍암동","서구 화정2동","서구 농성1동","서구 금호1동",
    "남구 봉선2동","남구 진월동","남구 방림1동","남구 효덕동","남구 송암동",
    "북구 용봉동","북구 두암2동","북구 운암1동","북구 첨단2동","북구 문흥1동",
    "광산구 첨단1동","광산구 수완동","광산구 신가동","광산구 우산동","광산구 송정1동",
}

EXPECTED_YOUTH_VULNERABLE = {
    "북구 두암2동","남구 방림1동","북구 문흥1동",
    "북구 운암1동","동구 지원1동","광산구 송정1동",
}
EXPECTED_SETTLEMENT_PRIORITY = {
    "북구 운암1동","북구 두암2동","동구 지원1동","북구 문흥1동","광산구 송정1동",
}
EXPECTED_CAUSE_CHECK = {"남구 방림1동"}

EXPECTED_FACILITY_CANDIDATES = {
    "북구 두암2동","북구 문흥1동","북구 운암1동","남구 방림1동",
}
EXPECTED_RENTAL_CANDIDATES = {
    "북구 운암1동","동구 지원1동","광산구 송정1동","남구 방림1동","북구 문흥1동",
}
EXPECTED_BUS_CANDIDATES = {
    "동구 지원1동","남구 방림1동","북구 운암1동","광산구 송정1동","북구 두암2동",
}
EXPECTED_HL_EXCLUDED = {
    "광산구 수완동","남구 송암동","남구 방림1동","북구 두암2동",
}

EXPECTED_POLICY_COUNTS = {
    "일반 관찰": 9,
    "주거환경 관심 검토": 5,
    "주거환경 개선 우선": 3,
    "복합 최우선 검토": 2,
    "청년 유입·정착 지원 우선": 2,
    "HL순위 제외": 2,
    "청년 유입·정착 지원 우선 · HL순위 제외": 1,
    "청년비중 낮음 · 원인 추가점검 · HL순위 제외": 1,
}

errors = []
warnings = []

def b(v):
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() in {"true","1","yes","y"}

def ensure_region(df):
    df = df.copy()
    if "지역" not in df.columns:
        if "자치구" not in df.columns or "행정동" not in df.columns:
            raise ValueError("지역 또는 자치구/행정동 컬럼이 없습니다.")
        df["지역"] = df["자치구"].astype(str).str.strip() + " " + df["행정동"].astype(str).str.strip()
    else:
        df["지역"] = df["지역"].astype(str).str.strip()
    return df

def true_regions(df, col):
    if col not in df.columns:
        errors.append(f"필수 컬럼 누락: {col}")
        return set()
    return set(df.loc[df[col].apply(b), "지역"])

def check_set(name, actual, expected):
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        msg = f"{name} 불일치"
        if missing:
            msg += " / 누락: " + ", ".join(missing)
        if extra:
            msg += " / 추가: " + ", ".join(extra)
        errors.append(msg)

def close(name, actual, expected, tol=0.01):
    if pd.isna(actual) or abs(float(actual) - float(expected)) > tol:
        errors.append(f"{name} 불일치: 실제 {actual} / 기대 {expected}")

def find_col(df, names):
    for c in names:
        if c in df.columns:
            return c
    return None

def main():
    print()
    print("=" * 72)
    print("광주 25개 동 최종 정책통합 품질검사")
    print("정책방향: 청년이 상대적으로 적은 지역의 유입·정착 지원")
    print("=" * 72)

    for path, name in [
        (FINAL_FILE, "최종 통합"),
        (BASELINE_FILE, "버스 병합 전 통합"),
        (HOUSING_FILE, "주거 통합"),
    ]:
        if not path.exists():
            errors.append(f"{name} 파일 없음: {path}")

    if errors:
        finish()
        return

    final = ensure_region(pd.read_csv(FINAL_FILE, encoding="utf-8-sig"))
    base = ensure_region(pd.read_csv(BASELINE_FILE, encoding="utf-8-sig"))
    housing = ensure_region(pd.read_csv(HOUSING_FILE, encoding="utf-8-sig"))

    print(f"최종 통합 지역 : {len(final)}개")
    print(f"최종 통합 컬럼 : {len(final.columns)}개")

    # 1) 25개 동
    if len(final) != 25:
        errors.append(f"최종 지역 수가 25개가 아님: {len(final)}")
    if final["지역"].duplicated().any():
        errors.append("최종 통합 파일에 중복 지역 존재")
    check_set("25개 행정동", set(final["지역"]), EXPECTED_REGIONS)

    # 2) 새 청년정책 방향
    youth_vuln = true_regions(final, "청년인구_상대취약")
    youth_priority = true_regions(final, "청년유입정착_우선후보")
    cause_check = true_regions(final, "청년인구감소원인_추가점검")

    check_set("청년인구 상대취약 6개", youth_vuln, EXPECTED_YOUTH_VULNERABLE)
    check_set("청년 유입·정착 지원 우선 5개", youth_priority, EXPECTED_SETTLEMENT_PRIORITY)
    check_set("원인 추가점검 1개", cause_check, EXPECTED_CAUSE_CHECK)

    if "광산구 수완동" in youth_vuln:
        errors.append("수완동이 새 청년인구 상대취약 후보에 포함됨")

    for col, expected, tol in [
        ("2030인구수_중앙값", 3709, 0.5),
        ("2030인구비율_중앙값", 23.48, 0.01),
        ("청년공공시설수_중앙값", 2, 0.01),
        ("공공임대_세대수_중앙값", 116, 0.01),
        ("공식정류소수_중앙값", 18, 0.01),
    ]:
        if col not in final.columns:
            errors.append(f"필수 중앙값 컬럼 누락: {col}")
        else:
            close(col, final[col].iloc[0], expected, tol)

    # 3) 새 보조지표 후보
    facility_candidates = true_regions(final, "청년유입정착_공공시설지원후보")
    rental_candidates = true_regions(final, "청년유입정착_공공임대지원후보")
    bus_candidates = true_regions(final, "청년유입정착_교통지원후보")

    check_set("공공시설 지원후보", facility_candidates, EXPECTED_FACILITY_CANDIDATES)
    check_set("공공임대 지원후보", rental_candidates, EXPECTED_RENTAL_CANDIDATES)
    check_set("교통지원 후보", bus_candidates, EXPECTED_BUS_CANDIDATES)

    # 4) 총량
    for col, expected, label in [
        ("청년공공시설수", 57, "청년 공공시설"),
        ("공공임대_세대수", 22855, "공공임대"),
        ("공식정류소수", 570, "공식 버스정류소"),
    ]:
        if col not in final.columns:
            errors.append(f"총량 검증 컬럼 누락: {col}")
        else:
            total = int(pd.to_numeric(final[col], errors="coerce").fillna(0).sum())
            if total != expected:
                errors.append(f"{label} 총합 불일치: {total:,} / 기대 {expected:,}")

    # 5) 버스 노선 제외
    if "버스노선데이터_안전매칭률" in final.columns:
        rates = pd.to_numeric(final["버스노선데이터_안전매칭률"], errors="coerce").dropna()
        if rates.empty:
            errors.append("버스 노선 안전매칭률 값 없음")
        else:
            close("버스 노선 안전매칭률", rates.iloc[0], 0.54, 0.01)
    else:
        errors.append("버스노선데이터_안전매칭률 컬럼 누락")

    if "버스노선_정책분석사용여부" not in final.columns:
        errors.append("버스노선_정책분석사용여부 컬럼 누락")
    elif final["버스노선_정책분석사용여부"].apply(b).any():
        errors.append("신뢰도 낮은 버스 노선 데이터가 정책분석에 사용됨")

    # 6) HL 주거비/표본
    sample_col = find_col(housing, ["주거표본판정", "HL주거표본판정"])
    if sample_col is None:
        errors.append("주거표본판정 컬럼 누락")
    else:
        counts = housing[sample_col].fillna("미분류").value_counts().to_dict()
        expected_counts = {"정상":19, "저표본 주의":2, "표본부족":4}
        for k, v in expected_counts.items():
            if int(counts.get(k, 0)) != v:
                errors.append(f"주거 표본 '{k}' 개수 불일치: {counts.get(k,0)} / 기대 {v}")

    rank_col = find_col(final, ["HL정책순위포함여부", "정책순위포함여부"])
    if rank_col is None:
        errors.append("HL 정책순위 포함 여부 컬럼 누락")
    else:
        excluded = set(final.loc[~final[rank_col].apply(b), "지역"])
        check_set("HL 정책순위 제외 4개", excluded, EXPECTED_HL_EXCLUDED)

    original_col = find_col(housing, ["원본유효거래건수", "원본거래건수"])
    excluded_col = find_col(housing, ["공공임대제외건수"])
    private_col = find_col(housing, ["전체거래건수", "민간임대사용건수", "민간임대_사용건수"])

    for col, expected, label in [
        (original_col, 5315, "원본 유효 주거거래"),
        (excluded_col, 1819, "공공임대 제외 거래"),
        (private_col, 3496, "민간임대 HL 사용 거래"),
    ]:
        if col is None:
            errors.append(f"{label} 검증 컬럼 누락")
        else:
            total = int(pd.to_numeric(housing[col], errors="coerce").fillna(0).sum())
            if total != expected:
                errors.append(f"{label} 합계 불일치: {total:,} / 기대 {expected:,}")

    # 7) 최종 정책유형
    if "최종정책유형" not in final.columns:
        errors.append("최종정책유형 컬럼 누락")
    else:
        counts = final["최종정책유형"].value_counts().to_dict()
        for k, expected in EXPECTED_POLICY_COUNTS.items():
            if int(counts.get(k, 0)) != expected:
                errors.append(f"정책유형 '{k}' 개수 불일치: {counts.get(k,0)} / 기대 {expected}")
        unexpected = set(counts) - set(EXPECTED_POLICY_COUNTS)
        if unexpected:
            errors.append("예상하지 않은 정책유형: " + ", ".join(sorted(unexpected)))

    # 8) 버스 병합 전 HL/정책유형 유지
    for col in ["HL_Score", "최종정책유형"]:
        if col not in base.columns or col not in final.columns:
            errors.append(f"병합 전후 비교 컬럼 누락: {col}")
            continue

        comp = base[["지역", col]].merge(
            final[["지역", col]],
            on="지역",
            suffixes=("_before", "_after"),
            validate="one_to_one"
        )

        if col == "HL_Score":
            a = pd.to_numeric(comp[f"{col}_before"], errors="coerce")
            b_ = pd.to_numeric(comp[f"{col}_after"], errors="coerce")
            if (a - b_).abs().fillna(0).max() > 1e-9:
                errors.append("버스 병합 과정에서 HL_Score가 변경됨")
        else:
            changed = comp[comp[f"{col}_before"] != comp[f"{col}_after"]]
            if not changed.empty:
                errors.append("버스 병합 과정에서 최종정책유형이 변경됨")

    # 9) 보조지표 HL 미반영
    for col in ["공공시설_HL반영여부", "공공임대_HL반영여부", "버스정류소_HL반영여부"]:
        if col not in final.columns:
            errors.append(f"{col} 컬럼 누락")
        elif final[col].apply(b).any():
            errors.append(f"{col}=True 존재 → 보조지표가 HL에 혼입됨")

    # 구형 후보 컬럼이 남아 있으면 경고만
    for col in ["청년수요_우선후보", "청년주거지원_점검후보", "청년교통공급_점검후보"]:
        if col in final.columns:
            warnings.append(
                f"기존 후보 컬럼 '{col}'이 남아 있음. UI/정책판정에서는 새 청년 유입·정착 후보 컬럼만 사용해야 함."
            )

    print()
    print("-" * 72)
    print("최종 검사 요약")
    print("-" * 72)
    print(f"분석 지역 : {len(final)}개")
    print(f"청년인구 상대취약 : {len(youth_vuln)}개")
    print(f"청년 유입·정착 지원 우선 : {len(youth_priority)}개")
    print(f"공공시설 지원후보 : {len(facility_candidates)}개")
    print(f"공공임대 지원후보 : {len(rental_candidates)}개")
    print(f"교통지원 후보 : {len(bus_candidates)}개")

    finish()

def finish():
    print()
    print("=" * 72)
    print("최종 통합 품질검사 결과")
    print("=" * 72)

    if errors:
        print()
        print("[검사 실패]")
        for msg in errors:
            print("X", msg)

        if warnings:
            print()
            print("[경고]")
            for msg in warnings:
                print("!", msg)

        print()
        print(f"총 오류 : {len(errors)}개")
        print("최종 정책통합 품질검사 : FAIL")
        sys.exit(1)

    print()
    print("모든 핵심 검사 통과")
    print("25개 행정동 누락·중복 없음")
    print("새 정책방향 '청년인구 상대취약 → 유입·정착 지원' 정상 반영")
    print("청년인구 상대취약 6개 / 유입·정착 지원 우선 5개 정상")
    print("공공시설·공공임대·교통 보조지표가 새 방향으로 정상 반영")
    print("주거비는 공공임대 실거래를 제외한 민간임대 기준 유지")
    print("주거 표본 정상 19 / 저표본 2 / 표본부족 4 유지")
    print("청년 공공시설 57개 / 공공임대 22,855세대 / 공식 정류소 570개 유지")
    print("버스 노선 데이터 0.54% 매칭률로 정책분석 제외 유지")
    print("공공시설·공공임대·버스 보조지표는 HL-Score 미반영")

    if warnings:
        print()
        print("[경고]")
        for msg in warnings:
            print("!", msg)
    else:
        print("추가 경고사항도 없습니다.")

    print()
    print("최종 정책통합 품질검사 : PASS")

if __name__ == "__main__":
    main()
