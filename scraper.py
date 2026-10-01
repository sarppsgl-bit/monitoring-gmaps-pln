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
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7"
}

VALID_PREFIXES = ("1.", "2.", "3.", "4.", "5.0")

def is_valid_rating(val):
    s_val = str(float(val))
    return s_val.startswith(VALID_PREFIXES)

def parse_html_for_rating(html):
    rating = 0.0
    reviews = 0

    # 1. Menangkap angka desimal presisi Google + jumlah ulasan
    js_matches = re.findall(r'([0-9]\.[0-9]{1,15})\s*,\s*([0-9]{1,5})\b', html)
    for r_str, rev_str in js_matches:
        try:
            val = float(r_str)
            if is_valid_rating(val):
                rev_num = int(rev_str)
                if rev_num != 0:
                    rating = round(val, 1)
                    reviews = rev_num
                    return rating, reviews
        except Exception:
            pass

    # 2. Menangkap dari struktur JSON-LD
    m_json_r = re.search(r'"ratingValue"\s*:\s*"([0-9.,]+)"', html, re.IGNORECASE)
    m_json_c = re.search(r'"reviewCount"\s*:\s*"([0-9.]+)"', html, re.IGNORECASE)
    if m_json_r:
        try:
            val = float(m_json_r.group(1).replace(',', '.'))
            if is_valid_rating(val):
                rating = round(val, 1)
        except Exception:
            pass
    if m_json_c:
        try:
            rev_num = int(m_json_c.group(1).replace('.', ''))
            if rev_num != 0:
                reviews = rev_num
        except Exception:
            pass

    if rating != 0.0 and reviews != 0:
        return rating, reviews

    # 3. Menangkap dari aria-label / teks visual
    if rating == 0.0:
        candidates = re.findall(r'aria-label="[^"]*?\b([0-9][.,][0-9])\b', html, re.IGNORECASE)
        candidates += re.findall(r'\b([0-9][.,][0-9])\b\s*(?:★|bintang|stars|dari|out of)', html, re.IGNORECASE)
        candidates += re.findall(r'(?:Rating|Di-rating)\s*:?\s*\b([0-9][.,][0-9])\b', html, re.IGNORECASE)
        for c in candidates:
            try:
                val = float(str(c).replace(',', '.'))
                if is_valid_rating(val):
                    rating = round(val, 1)
                    break
            except Exception:
                pass

    if reviews == 0:
        rev_candidates = re.findall(r'\b([0-9]{1,5})\s*(?:ulasan|reviews|penilaian)\b', html, re.IGNORECASE)
        rev_candidates += re.findall(r'\\(\s*([0-9]{1,5})\s*\\)', html)
        for rc in rev_candidates:
            try:
                r_clean = str(rc).replace('.', '')
                if r_clean.isdigit():
                    rev_num = int(r_clean)
                    if rev_num != 0:
                        reviews = rev_num
                        break
            except Exception:
                pass

    return rating, reviews

def fetch_unit(unit):
    name = unit["namaUnit"]
    rating, reviews = 0.0, 0
    
    # Percobaan 1: Google Search Standar
    params_std = {
        "q": "PLN " + name,
        "hl": "id",
        "gl": "id"
    }
    try:
        res = requests.get("https://www.google.com/search", params=params_std, headers=HEADERS, timeout=12)
        print("Fetch Std " + name + " - Status: " + str(res.status_code) + " - Length: " + str(len(res.text)))
        if res.status_code == 200:
            rating, reviews = parse_html_for_rating(res.text)
    except Exception as e:
        print("Error Std " + name + ": " + str(e))

    # Percobaan 2: Google Maps Mode (tbm=map) jika rating masih 0
    if rating == 0.0:
        params_map = {
            "q": "PLN " + name,
            "tbm": "map",
            "hl": "id",
            "gl": "id"
        }
        try:
            res_map = requests.get("https://www.google.com/search", params=params_map, headers=HEADERS, timeout=12)
            print("Fetch Map " + name + " - Status: " + str(res_map.status_code) + " - Length: " + str(len(res_map.text)))
            if res_map.status_code == 200:
                rating, reviews = parse_html_for_rating(res_map.text)
        except Exception as e_map:
            print("Error Map " + name + ": " + str(e_map))

    print("RESULT : " + name + " Rating=" + str(rating) + ", Reviews=" + str(reviews))
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
        print("Sending " + str(len(valid_data)) + " records to Sheets...")
        try:
            res = requests.post(WEB_APP_URL, json=valid_data, headers={"Content-Type": "application/json"}, timeout=12)
            print("Sheets Response: " + res.text)
        except Exception as e:
            print("Error posting to Sheets: " + str(e))
    else:
        print("WARNING: No valid ratings found. Post skipped.")

if __name__ == "__main__":
    main()
