import requests
from bs4 import BeautifulSoup
import pandas as pd
import io
import time
import re
from urllib.parse import urljoin
from datetime import datetime

TARGET_URL = 'https://www.ireland.ie/en/india/newdelhi/services/visas/processing-times-and-decisions/#visa-decisions'
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
}

def fetch_ods_link(max_retries=3):
    for attempt in range(max_retries):
        try:
            response = requests.get(TARGET_URL, headers=HEADERS, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            target_a = soup.find('a', string=lambda t: t and 'Visa decisions made from' in t)
            
            if not target_a or not target_a.has_attr('href'):
                raise ValueError("Could not find the target link on the page.")
                
            href = target_a['href']
            download_link = urljoin(TARGET_URL, href)
            
            filename = download_link.split('/')[-1]
            if '?' in filename:
                filename = filename.split('?')[0]
                
            return download_link, filename
            
        except (requests.RequestException, ValueError) as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** (attempt + 1))
            else:
                raise Exception(f"Failed to fetch ods link after {max_retries} attempts.")

def parse_ods_file(ods_content, filename):
    try:
        df = pd.read_excel(io.BytesIO(ods_content), engine='odf')
        df.dropna(how='all', inplace=True)
        df.reset_index(drop=True, inplace=True)
        
        header_row_idx = None
        for i, row in df.head(20).iterrows():
            row_str = " ".join([str(val).lower() for val in row.values])
            if 'application number' in row_str and 'decision' in row_str:
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
        
        if not app_num_col or not status_col:
            raise ValueError(f"Could not reliably identify required columns. Found columns: {df.columns.tolist()}")

        parsed_data = []

        # Extract date from filename or use today
        date_match = re.search(r'(\d{4})(\d{2})(\d{2})', filename)
        if date_match:
            fallback_date = f"{date_match.group(1)}-{date_match.group(2)}-{date_match.group(3)}"
        else:
            fallback_date = datetime.now().strftime('%Y-%m-%d')

        for _, row in df.iterrows():
            if pd.isna(row[app_num_col]):
                continue
                
            raw_irl = str(row[app_num_col]).strip().upper()
            
            if raw_irl.startswith("IRL"):
                clean_irl = raw_irl
            else:
                clean_num = ''.join(e for e in raw_irl if e.isalnum())
                clean_irl = f"IRL{clean_num}"
                
            if len(clean_irl) < 5:
                continue
                
            raw_status = str(row[status_col]).strip().title()
            raw_date = str(row[date_col]).strip() if date_col and pd.notna(row[date_col]) else ""
            if not raw_date or raw_date.lower() in ('nan', 'unknown', 'nat'):
                raw_date = fallback_date
            
            parsed_data.append({
                "irl_number": clean_irl,
                "status": raw_status,
                "decision_date": raw_date
            })

        return parsed_data
        
    except Exception as e:
        raise Exception(f"Failed to parse ODS data: {e}")

def run_scraper():
    print("Starting scraper...")
    try:
        download_link, filename = fetch_ods_link()
        print(f"Found link: {download_link}")
        
        response = requests.get(download_link, headers=HEADERS, timeout=30)
        response.raise_for_status()
        
        data = parse_ods_file(response.content, filename)
        print(f"Successfully parsed {len(data)} records from {filename}.")
        
        return {
            "success": True,
            "filename": filename,
            "download_link": download_link,
            "data": data
        }
        
    except Exception as e:
        print(f"Scraper error: {e}")
        return {
            "success": False,
            "error": str(e)
        }
