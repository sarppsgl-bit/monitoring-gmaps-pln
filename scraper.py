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
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
    "Cookie": "SOCS=CAISHAgBEhJnd3NfMjAyMzA4MTAtMF9SQzEaAmVuIAEaBgiAo_CmBg"
}

DIGITS = string.digits

def extract_rating_and_reviews(html):
    rating = 0.0
    reviews = 0

    # 1. CARI RATING DESIMAL (1.0 - 5.0)
    pat_digit = f"([{DIGITS}]+(?:[.,][{DIGITS}]+)?)"
    
    # Pola 1: Angka di dekat kata kunci bintang/rating/stars
    candidates = re.findall(pat_digit + r'\s*(?:★|bintang|stars|dari|out of)', html, re.IGNORECASE)
    candidates += re.findall(r'(?:rating|di-rating|rated)\s*:?\s*' + pat_digit, html, re.IGNORECASE)
    candidates += re.findall(r'aria-label="[^"]*?' + pat_digit + r'\s*(?:bintang|stars|dari|out of)', html, re.IGNORECASE)
    candidates += re.findall(r'aria-label="' + pat_digit, html, re.IGNORECASE)
    candidates += re.findall(r'"ratingValue"\s*:\s*"?(' + pat_digit + r')"?', html, re.IGNORECASE)

    for c in candidates:
        if isinstance(c, tuple):
            c = c[0]
        try:
            v = float(str(c).replace(',', '.'))
            if str(int(v)) in "12345":
                rating = v
                break
        except Exception:
            pass

    # 2. CARI JUMLAH ULASAN
    pat_rev = f"([{DIGITS}.]+)"
    rev_candidates = re.findall(pat_rev + r'\s*(?:ulasan|reviews|penilaian)', html, re.IGNORECASE)
    rev_candidates += re.findall(r'\\(' + pat_rev + r'\\)', html, re.IGNORECASE)
    rev_candidates += re.findall(r'"reviewCount"\s*:\s*"?(' + pat_rev + r')"?', html, re.IGNORECASE)

    for r_str in rev_candidates:
        if isinstance(r_str, tuple):
            r_str = r_str[0]
        try:
            r_clean = str(r_str).replace('.', '')
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
