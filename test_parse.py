import requests
import pandas as pd
import io
from scraper import fetch_ods_link

link, name = fetch_ods_link()
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
}
resp = requests.get(link, headers=HEADERS)
df = pd.read_excel(io.BytesIO(resp.content), engine='odf')
print("Original head:")
print(df.head(10))

print("\nSearching for header:")
# Ensure we drop completely empty rows
df.dropna(how='all', inplace=True)
df.reset_index(drop=True, inplace=True)

header_row_idx = None
for i, row in df.head(20).iterrows():
    row_str = " ".join([str(val).lower() for val in row.values])
    print(f"Row {i}: {row_str}")
    if 'application number' in row_str or 'decision' in row_str or 'date' in row_str or 'irl' in row_str:
        header_row_idx = i
        break

print("Found header at:", header_row_idx)
