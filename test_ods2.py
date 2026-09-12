import requests
from scraper import fetch_ods_link

link, name = fetch_ods_link()
print("Link:", link)
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
}
resp = requests.get(link, headers=HEADERS)
print("Status:", resp.status_code)
print("Content length:", len(resp.content))
if resp.status_code == 200:
    print(resp.content[:100])
