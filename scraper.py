import re
import json
import urllib.parse
import string
import requests

WEB_APP_URL = "https://script.google.com/macros/s/AKfycbwG0n7k4j9LkdumyKuyCi3s4rxd_XK9Oi_11s8fKp7WOa5L6dDJjWtFWGdPTMdxipmn/exec"

UNITS = [
    {"idUnit": "UP3_SGL", "namaUnit": "UP3 Sigli"},
    {"idUnit": "ULP_SGL", "namaUnit": "ULP Sigli Kota"},
    {"idUnit": "ULP_BRN", "namaUnit": "ULP Beureunuen"},
    {"idUnit": "ULP_MRD", "namaUnit": "ULP Meureudu"}
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
    "Cookie": "SOCS=CAISHAgBEhJnd3NfMjAyMzA4MTAtMF9SQzEaAmVuIAEaBgiAo_CmBg"
}

DIGITS = string.digits

def extract_rating_and_reviews(html):
    rating = 0.0
    reviews = 0

    # 1. TANGKAP DARI JSON-LD SCHEMA GOOGLE
    m_json_rat = re.search(r'"ratingValue"\s*:\s*"?([' + DIGITS + r'\.,]+)"?', html, re.IGNORECASE)
    m_json_rev = re.search(r'"reviewCount"\s*:\s*"?([' + DIGITS + r'\.]+)"?', html, re.IGNORECASE)

    if m_json_rat:
        try:
            v = float(m_json_rat.group(1).replace(',', '.'))
            if str(int(v)) in "12345":
                rating = v
        except Exception:
            pass

    if m_json_rev:
        try:
            r_str = m_json_rev.group(1).replace('.', '')
            if r_str.isdigit():
                reviews = int(r_str)
        except Exception:
            pass

    # 2. FALLBACK PATTERN VISUAL JIKA JSON TIDAK TERSEDIA
    if rating == 0.0:
        pat_num = f"([{DIGITS}]+(?:[.,][{DIGITS}]+)?)"
        matches = re.findall(pat_num + r'\s*(?:★|bintang|stars|dari)', html, re.IGNORECASE)
        matches += re.findall(r'Rating:\s*' + pat_num, html, re.IGNORECASE)
        matches += re.findall(r'aria-label="' + pat_num, html, re.IGNORECASE)
        
        for val_str in matches:
            try:
                v = float(val_str.replace(',', '.'))
                if str(int(v)) in "12345":
                    rating = v
                    break
            except Exception:
                pass

    if reviews == 0:
        pat_rev = f"([{DIGITS}.]+)"
        matches_rev = re.findall(pat_rev + r'\s*(?:ulasan|reviews|penilaian)', html, re.IGNORECASE)
        for r_str in matches_rev:
            try:
                r_clean = r_str.replace('.', '')
                if r_clean.isdigit():
                    reviews = int(r_clean)
                    break
            except Exception:
                pass

    return rating, reviews

def fetch_unit(unit):
    name = unit["namaUnit"]
    params = {
        "q": "PLN " + name,
        "hl": "id",
        "gl": "id"
    }
    rating, reviews = 0.0, 0
    try:
        res = requests.get("https://www.google.com/search", params=params, headers=HEADERS, timeout=12)
        print(f"Fetch {name} - Status: {res.status_code}")
        if res.status_code == 200:
            rating, reviews = extract_rating_and_reviews(res.text)
    except Exception as e:
        print(f"Error fetching {name}: {e}")
        
    print(f"RESULT : {name} Rating={rating}, Reviews={reviews}")
    return {
        "idUnit": unit["idUnit"],
        "namaUnit": name,
        "rating": rating,
        "reviews": reviews
    }

def main():
    print("=== STARTING GMAPS RATING SCRAPER ===")
    results = [fetch_unit(u) for u in UNITS]
    
    valid_data = [r for r in results if r["rating"] != 0.0]
    
    if valid_data:
        print(f"Sending {len(valid_data)} records to Sheets...")
        try:
            res = requests.post(WEB_APP_URL, json=valid_data, headers={"Content-Type": "application/json"}, timeout=12)
            print("Sheets Response:", res.text)
        except Exception as e:
            print("Error posting to Sheets:", e)
    else:
        print("WARNING: No valid ratings found. Post skipped.")

if __name__ == "__main__":
    main()
