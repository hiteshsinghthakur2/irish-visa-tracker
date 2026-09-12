import requests
import pandas as pd
import io
from scraper import fetch_ods_link

link, name = fetch_ods_link()
print("Link:", link)
resp = requests.get(link)
df = pd.read_excel(io.BytesIO(resp.content), engine='odf')
print(df.head(30))
