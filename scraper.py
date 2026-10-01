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
    "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7"
}

DIGITS = string.digits

def extract_rating(html):
    pattern = f"([{DIGITS}]+(?:[.,][{DIGITS}]+)?)"
    matches = re.findall(pattern + r'\s*(?:★|bintang|stars|dari)', html, re.IGNORECASE)
    matches += re.findall(r'Rating:\s*' + pattern, html, re.IGNORECASE)
    matches += re.findall(r'aria-label="' + pattern, html, re.IGNORECASE)
    for val_str in matches:
        try:
            val = float(val_str.replace(',', '.'))
            if str(int(val)) in "12345":
                return val
        except Exception:
            pass
    return 0.0

def extract_reviews(html):
    pattern = f"([{DIGITS}.]+)"
    matches = re.findall(pattern + r'\s*(?:ulasan|reviews|penilaian)', html, re.IGNORECASE)
    for val_str in matches:
        try:
            rev_clean = val_str.replace('.', '')
            if rev_clean.isdigit():
                return int(rev_clean)
        except Exception:
            pass
    return 0

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
            rating = extract_rating(res.text)
            reviews = extract_reviews(res.text)
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
