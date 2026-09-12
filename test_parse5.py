import requests
import pandas as pd
import io
from scraper import fetch_ods_link

link, name = fetch_ods_link()
print("Link:", link)
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
}
resp = requests.get(link, headers=HEADERS)
df = pd.read_excel(io.BytesIO(resp.content), engine='odf')
df.dropna(how='all', inplace=True)
df.reset_index(drop=True, inplace=True)

header_row_idx = None
for i, row in df.head(20).iterrows():
    row_str = " ".join([str(val).lower() for val in row.values])
    if ('application' in row_str or 'irl' in row_str) and ('decision' in row_str or 'status' in row_str):
        header_row_idx = i
        break

if header_row_idx is not None:
    df.columns = df.iloc[header_row_idx]
    df = df.iloc[header_row_idx + 1:]
    df.reset_index(drop=True, inplace=True)

df.columns = [str(col).strip().lower() for col in df.columns]

app_num_col = next((c for c in df.columns if 'application' in c or 'number' in c or 'irl' in c), None)
status_col = next((c for c in df.columns if 'decision' in c or 'status' in c), None)
date_col = next((c for c in df.columns if 'date' in c), None)

print(df.head(10))
print(f"Columns selected: App={app_num_col}, Status={status_col}, Date={date_col}")

import re
irl_pattern = re.compile(r'^IRL\w+', re.IGNORECASE)
count = 0
for _, row in df.iterrows():
    val = row[app_num_col]
    if pd.notna(val) and irl_pattern.match(str(val).strip().upper()):
        count += 1
print(f"Total matching IRLs: {count}")

