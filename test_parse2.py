import requests
import pandas as pd
import io

url = "https://www.ireland.ie/5111/20260908_NDVO_Visa_Decisions.ods"
HEADERS = {'User-Agent': 'Mozilla/5.0'}
resp = requests.get(url, headers=HEADERS)
with open("test.ods", "wb") as f:
    f.write(resp.content)

df = pd.read_excel("test.ods", engine="odf")
print(df.head(5))
print(df.columns)
