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
    "Accept": "*/*",
    "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7"
}

DIGITS = string.digits

def extract_from_maps_data(text):
    rating = 0.0
    reviews = 0

    # 1. Tangkap Array Internal Google Maps: [4.4, 76] atau [4.39999, 76]
    m_arr = re.findall(r'\[\s*([1-5]\.[0-9]+)\s*,\s*([0-9]+)\s*\]', text)
    for r_str, rev_str in m_arr:
        try:
            v = float(r_str)
            if int(v) in (1, 2, 3, 4, 5):
                rating = round(v, 1)
                reviews = int(rev_str)
                return rating, reviews
        except Exception:
            pass

    # 2. Tangkap dari teks visual / aria-label / ratingValue
    m_rat = re.findall(r'([1-5][.,][0-9])\s*(?:★|bintang|stars|dari|out of)', text, re.IGNORECASE)
    m_rat += re.findall(r'aria-label="[^"]*?([1-5][.,][0-9])', text, re.IGNORECASE)
    m_rat += re.findall(r'Rating:\s*([1-5][.,][0-9])', text, re.IGNORECASE)
    m_rat += re.findall(r'"ratingValue"\s*:\s*"?([1-5][.,][0-9])"?', text, re.IGNORECASE)

    for r_str in m_rat:
        try:
            v = float(r_str.replace(',', '.'))
            if int(v) in (1, 2, 3, 4, 5):
                rating = round(v, 1)
                break
        except Exception:
            pass

    m_rev = re.findall(r'([0-9.]+)\s*(?:ulasan|reviews|penilaian)', text, re.IGNORECASE)
    m_rev += re.findall(r'"reviewCount"\s*:\s*"?([0-9.]+)"?', text, re.IGNORECASE)

    for rev_str in m_rev:
        try:
            r_clean = rev_str.replace('.', '')
            if r_clean.isdigit():
                reviews = int(r_clean)
                break
        except Exception:
            pass

    return rating, reviews

def fetch_unit(unit):
    name = unit["namaUnit"]
    
    params_maps = {
        "q": "PLN " + name,
        "tbm": "map",
        "hl": "id",
        "gl": "id"
    }
    
    rating, reviews = 0.0, 0
    
    try:
        res = requests.get("https://www.google.com/search", params=params_maps, headers=HEADERS, timeout=12)
        print("Fetch Maps " + name + " - Status: " + str(res.status_code) + " - Length: " + str(len(res.text)))
        if res.status_code == 200:
            rating, reviews = extract_from_maps_data(res.text)
    except Exception as e:
        print("Error fetching Maps " + name + ": " + str(e))

    # Fallback pencarian web jika rating masih 0
    if rating == 0.0:
        params_web = {
            "q": "PLN " + name + " Google Maps",
            "hl": "id",
            "gl": "id"
        }
        try:
            res_web = requests.get("https://www.google.com/search", params=params_web, headers=HEADERS, timeout=12)
            if res_web.status_code == 200:
                rating, reviews = extract_from_maps_data(res_web.text)
        except Exception as e_web:
            print("Error fetching Web " + name + ": " + str(e_web))

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
