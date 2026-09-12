import requests
import pandas as pd
import io

url = "https://www.ireland.ie/5111/20260908_NDVO_Visa_Decisions.ods"
HEADERS = {'User-Agent': 'Mozilla/5.0'}
resp = requests.get(url, headers=HEADERS)
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
for _, row in df.head(5).iterrows():
    val = row[app_num_col]
    print(f"Raw IRL: {val}, matches: {bool(pd.notna(val) and irl_pattern.match(str(val).strip().upper()))}")

