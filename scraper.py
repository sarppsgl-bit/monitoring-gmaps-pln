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

DIGITS = string.digits

def extract_rating_and_reviews(html):
    candidates = []

    # 1. Strategy 1: Google Maps JS Data Payload
    # Matches float between 1.0 and 5.9 (e.g. 4.399999618530273 or 4.6) followed by review count
    gmaps_matches = re.findall(r'(?:\[|,)\s*([1-5]\.\d{1,15})\s*,\s*([' + DIGITS + r']{1,5})\s*(?:\]|,)', html)
    for m in gmaps_matches:
        if isinstance(m, tuple) and len(m) == 2:
            r_str, rev_str = m
            try:
                val = float(r_str)
                rev_num = int(rev_str)
                if int(val) in (1, 2, 3, 4, 5) and rev_num not in (0, 1, 2, 3, 4, 9):
                    candidates.append((round(val, 1), rev_num))
            except Exception:
                pass

    # 2. Strategy 2: aria-label in Google Search Knowledge Panel
    aria_matches = re.findall(r'aria-label="([0-9.,]+)\s*(?:bintang|stars|dari|out of)[^"]*?([' + DIGITS + r'\.]+)\s*(?:ulasan|reviews)', html, re.IGNORECASE)
    for m in aria_matches:
        if isinstance(m, tuple) and len(m) == 2:
            r_str, rev_str = m
            try:
                val = float(r_str.replace(',', '.'))
                rev_num = int(rev_str.replace('.', ''))
                if int(val) in (1, 2, 3, 4, 5) and rev_num not in (0, 1, 2, 3, 4, 9):
                    candidates.append((round(val, 1), rev_num))
            except Exception:
                pass

    # 3. Strategy 3: Schema JSON-LD
    m_rat = re.search(r'"ratingValue"\s*:\s*"?([0-9.,]+)"?', html, re.IGNORECASE)
    m_rev = re.search(r'"reviewCount"\s*:\s*"?([' + DIGITS + r']+)"?', html, re.IGNORECASE)
    if m_rat and m_rev:
        try:
            val = float(m_rat.group(1).replace(',', '.'))
            rev_num = int(m_rev.group(1).replace('.', ''))
            if int(val) in (1, 2, 3, 4, 5) and rev_num not in (0, 1, 2, 3, 4, 9):
                candidates.append((round(val, 1), rev_num))
        except Exception:
            pass

    if candidates:
        # Sort candidates by review count descending so real place entity (highest reviews) wins
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[0]

    return 0.0, 0

def fetch_unit(unit):
    name = unit["namaUnit"]
    rating, reviews = 0.0, 0
    amp = chr(38)
    
    # Percobaan 1: Google Maps Search URL
    gmaps_url = "https://www.google.com/maps/search/" + urllib.parse.quote("PLN " + name)
    try:
        res_gmaps = requests.get(gmaps_url, headers=HEADERS, timeout=12)
        print("Fetch GMaps " + name + " - Status: " + str(res_gmaps.status_code) + " - Length: " + str(len(res_gmaps.text)))
        if res_gmaps.status_code == 200:
            rating, reviews = extract_rating_and_reviews(res_gmaps.text)
    except Exception as e_gmaps:
        print("Error GMaps " + name + ": " + str(e_gmaps))

    # Percobaan 2: Google Search Standar jika Maps masih 0
    if rating == 0.0:
        search_url = "https://www.google.com/search?q=" + urllib.parse.quote("PLN " + name) + amp + "hl=id" + amp + "gl=id"
        try:
            res_search = requests.get(search_url, headers=HEADERS, timeout=12)
            print("Fetch Search " + name + " - Status: " + str(res_search.status_code) + " - Length: " + str(len(res_search.text)))
            if res_search.status_code == 200:
                rating, reviews = extract_rating_and_reviews(res_search.text)
        except Exception as e_search:
            print("Error Search " + name + ": " + str(e_search))

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
