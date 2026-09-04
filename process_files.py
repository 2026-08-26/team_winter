import pandas as pd
import glob

# 1. 실거래가 CSV 파일만 선택 (좌표 파일 및 기존 결과 파일 제외)
csv_files = glob.glob("*.csv")
target_files = [
    f for f in csv_files 
    if "raw_gwangju" not in f and "coords" not in f
]

print(f"대상 실거래가 CSV 파일 목록: {len(target_files)}개")

merged_dfs = []

for file in target_files:
    try:
        try:
            df = pd.read_csv(file, encoding="cp949", skiprows=15)
        except:
            df = pd.read_csv(file, encoding="utf-8-sig", skiprows=15)
            
        if not df.empty and len(df.columns) > 1:
            if "단독다가구" in file:
                df['주택유형'] = "단독다가구"
            elif "오피스텔" in file:
                df['주택유형'] = "오피스텔"
            elif "연립다세대" in file:
                df['주택유형'] = "연립다세대"
            elif "아파트" in file:
                df['주택유형'] = "아파트"
            else:
                df['주택유형'] = "기타"
                
            merged_dfs.append(df)
            print(f" -> [{file}] 로드 성공 ({len(df)}건)")
    except Exception as e:
        print(f" -> [{file}] 읽기 실패: {e}")

if merged_dfs:
    full_df = pd.concat(merged_dfs, ignore_index=True)

    # 2. 광주광역시 5개 구 필터링
    sigungu_cols = [c for c in full_df.columns if '시군구' in c or 'SGG' in c]
    if sigungu_cols:
        col = sigungu_cols[0]
        gwangju_df = full_df[full_df[col].astype(str).str.contains("광주|동구|서구|남구|북구|광산구")].copy()
    else:
        gwangju_df = full_df

    # 3. 전용면적 40㎡ 이하 필터링
    area_cols = [c for c in full_df.columns if '면적' in c or 'area' in c.lower()]
    if area_cols:
        col = area_cols[0]
        gwangju_df[col] = pd.to_numeric(gwangju_df[col].astype(str).str.replace(',', ''), errors='coerce')
        oneroom_df = gwangju_df[gwangju_df[col] <= 40.0].copy()
    else:
        oneroom_df = gwangju_df

    # 4. 최종 저장
    output_filename = "raw_gwangju_oneroom_rent.csv"
    oneroom_df.to_csv(output_filename, index=False, encoding="utf-8-sig")
    
    print("\n==========================================")
    print(f"최종 정제 완료! 파일 저장: {output_filename}")
    print(f"순수 광주 원룸/투룸(40㎡ 이하) 데이터: {len(oneroom_df)}건")
    print("==========================================")