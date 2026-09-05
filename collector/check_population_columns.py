from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent

FILE_PATH = (
    BASE_DIR
    / "data"
    / "processed"
    / "동별_2030인구.csv"
)


df = pd.read_csv(
    FILE_PATH,
    encoding="utf-8-sig"
)


print()
print("=" * 50)
print("동별_2030인구.csv 컬럼 확인")
print("=" * 50)

print()
print("[컬럼 목록]")

for column in df.columns:
    print("-", column)


print()
print("[앞부분 데이터]")

print(
    df.head(5).to_string(
        index=False
    )
)