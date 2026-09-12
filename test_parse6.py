import requests
import pandas as pd
import io
from scraper import fetch_ods_link

link, name = fetch_ods_link()
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
}
resp = requests.get(link, headers=HEADERS)
df = pd.read_excel(io.BytesIO(resp.content), engine='odf')
df.dropna(how='all', inplace=True)
df.reset_index(drop=True, inplace=True)

for i, row in df.head(15).iterrows():
    row_str = " | ".join([str(val).lower() for val in row.values])
    print(f"Row {i}: {row_str}")

