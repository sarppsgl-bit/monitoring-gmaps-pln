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

def extract_gmaps_data(html):
    rating = 0.0
    reviews = 0

    # 1. Ekstrak dari Google Maps JS Data Block (Format: [4.4, 76] atau [4.3999996, 76])
    matches = re.findall(r'\[\s*([34]\.[0-9]{1,15}|5\.0)\s*,\s*([1-9][0-9]{0,4})\s*\]', html)
    for r_str, rev_str in matches:
        try:
            val = float(r_str)
            rev_num = int(rev_str)
            if 3.0 &lt;= val &lt;= 5.0 and rev_num &gt;= 5:
                rating = round(val, 1)
                reviews = rev_num
                return rating, reviews
        except Exception:
            pass

    # 2. Ekstrak dari Google Search Knowledge Panel (aria-label)
    aria_m = re.findall(r'aria-label="[^"]*?([34]\.[0-9]|5\.0)\s*(?:bintang|stars|dari|out of)[^"]*?([0-9.]+)\s*(?:ulasan|reviews)', html, re.IGNORECASE)
    for r_str, rev_str in aria_m:
        try:
            val = float(r_str.replace(',', '.'))
            rev_num = int(rev_str.replace('.', ''))
            if 3.0 &lt;= val &lt;= 5.0:
                rating = round(val, 1)
                reviews = rev_num
                return rating, reviews
        except Exception:
            pass

    # 3. Ekstrak dari Schema JSON-LD (ratingValue &amp; reviewCount)
    m_rat = re.search(r'"ratingValue"\s*:\s*"?([34]\.[0-9]|5\.0)"?', html, re.IGNORECASE)
    m_rev = re.search(r'"reviewCount"\s*:\s*"?([0-9.]+)"?', html, re.IGNORECASE)
    if m_rat and m_rev:
        try:
            val = float(m_rat.group(1).replace(',', '.'))
            rev_num = int(m_rev.group(1).replace('.', ''))
            if 3.0 &lt;= val &lt;= 5.0:
                rating = round(val, 1)
                reviews = rev_num
                return rating, reviews
        except Exception:
            pass

    return rating, reviews

def fetch_unit(unit):
    name = unit["namaUnit"]
    rating, reviews = 0.0, 0
    
    # Percobaan 1: Tembak Google Maps Search URL
    gmaps_url = "https://www.google.com/maps/search/" + urllib.parse.quote("PLN " + name)
    try:
        res = requests.get(gmaps_url, headers=HEADERS, timeout=12)
        print("Fetch GMaps " + name + " - Status: " + str(res.status_code) + " - Length: " + str(len(res.text)))
        if res.status_code == 200:
            rating, reviews = extract_gmaps_data(res.text)
    except Exception as e:
        print("Error GMaps " + name + ": " + str(e))

    # Percobaan 2: Fallback ke Google Search Biasa jika Maps kosong
    if rating == 0.0:
        search_url = "https://www.google.com/search?q=" + urllib.parse.quote("PLN " + name + " Google Maps") + "&amp;hl=id&amp;gl=id"
        try:
            res_search = requests.get(search_url, headers=HEADERS, timeout=12)
            print("Fetch Search " + name + " - Status: " + str(res_search.status_code) + " - Length: " + str(len(res_search.text)))
            if res_search.status_code == 200:
                rating, reviews = extract_gmaps_data(res_search.text)
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
