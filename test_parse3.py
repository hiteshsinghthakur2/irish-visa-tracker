import requests
import pandas as pd
import io
from scraper import fetch_ods_link

link, name = fetch_ods_link()
HEADERS = {
    'User-Agent': 'Mozilla/5.0'
}
resp = requests.get(link, headers=HEADERS)
df = pd.read_excel(io.BytesIO(resp.content), engine='odf')
df.dropna(how='all', inplace=True)
df.reset_index(drop=True, inplace=True)

header_row_idx = None
for i, row in df.head(20).iterrows():
    row_str = " ".join([str(val).lower() for val in row.values])
    print(f"Row {i}: {row_str}")
    if ('application' in row_str or 'irl' in row_str) and ('decision' in row_str or 'status' in row_str):
        header_row_idx = i
        break

print("Found header at:", header_row_idx)
if header_row_idx is not None:
    df.columns = df.iloc[header_row_idx]
    df = df.iloc[header_row_idx + 1:]
    df.reset_index(drop=True, inplace=True)

df.columns = [str(col).strip().lower() for col in df.columns]
print("Columns:", df.columns.tolist())

app_num_col = next((c for c in df.columns if 'application' in c or 'number' in c or 'irl' in c), None)
status_col = next((c for c in df.columns if 'decision' in c or 'status' in c), None)
date_col = next((c for c in df.columns if 'date' in c), None)

print("Identified cols:", app_num_col, status_col, date_col)
