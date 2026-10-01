import sys
import re
import urllib.parse
import json
import string

WEB_APP_URL = "https://script.google.com/macros/s/AKfycbwG0n7k4j9LkdumyKuyCi3s4rxd_XK9Oi_11s8fKp7WOa5L6dDJjWtFWGdPTMdxipmn/exec"

UNITS = [
    {"idUnit": "UP3_SGL", "namaUnit": "UP3 Sigli"},
    {"idUnit": "ULP_SGL", "namaUnit": "ULP Sigli Kota"},
    {"idUnit": "ULP_BRN", "namaUnit": "ULP Beureunuen"},
    {"idUnit": "ULP_MRD", "namaUnit": "ULP Meureudu"}
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
    "Cookie": "SOCS=CAISHAgBEhJnd3NfMjAyMzA4MTAtMF9SQzEaAmVuIAEaBgiAo_CmBg"
}

# Gunakan string.digits agar bebas dari kesalahan formatting regex
d_str = string.digits
pat_rating = f"([{d_str}]+(?:[.,][{d_str}]+)?)"
pat_reviews = f"([{d_str}.]+)"

def extract_data(html_text):
    rating = 0.0
    reviews = 0

    m1 = re.search(pat_rating + r'\s*(?:★|bintang|stars|dari|out of)', html_text, re.IGNORECASE)
    m2 = re.search(r'Rating:\s*' + pat_rating, html_text, re.IGNORECASE)
    m3 = re.search(r'aria-label="' + pat_rating, html_text, re.IGNORECASE)

    for m in [m1, m2, m3]:
        if m:
            try:
                v = float(m.group(1).replace(',', '.'))
                if 1.0 &lt;= v &lt;= 5.0:
                    rating = v
                    break
            except Exception:
                pass

    r1 = re.search(pat_reviews + r'\s*(?:ulasan|reviews|penilaian)', html_text, re.IGNORECASE)
    r2 = re.search(r'\\(' + pat_reviews + r'\\)', html_text, re.IGNORECASE)

    for r in [r1, r2]:
        if r:
            try:
                rev_s = r.group(1).replace('.', '')
                if rev_s.isdigit():
                    reviews = int(rev_s)
                    break
            except Exception:
                pass

    return rating, reviews

def run():
    print("=== STARTING GMAPS RATING SCRAPER ===")
    
    try:
        import requests
    except Exception as e:
        print("Error importing requests:", e)
        sys.exit(0)

    results = []

    for u in UNITS:
        u_id = u["idUnit"]
        u_name = u["namaUnit"]
        q = "PLN " + u_name
        encoded_q = urllib.parse.quote(q)
        target_url = f"https://www.google.com/search?q={encoded_q}&amp;hl=id&amp;gl=id"

        rating = 0.0
        reviews = 0

        print(f"Fetching data for {u_name}...")

        try:
            resp = requests.get(target_url, headers=HEADERS, timeout=12)
            print(f"HTTP Status {u_name}: {resp.status_code}")
            if resp.status_code == 200:
                rating, reviews = extract_data(resp.text)
        except Exception as err:
            print(f"Fetch error for {u_name}: {err}")

        print(f"RESULT -&gt; {u_name}: Rating = {rating}, Reviews = {reviews}")
        results.append({
            "idUnit": u_id,
            "namaUnit": u_name,
            "rating": rating,
            "reviews": reviews
        })

    print("SCRAPE SUMMARY:", results)

    valid_results = [r for r in results if r["rating"] &gt; 0]

    if valid_results:
        print(f"Sending {len(valid_results)} valid records to Google Sheets...")
        try:
            post_resp = requests.post(WEB_APP_URL, json=valid_results, headers={"Content-Type": "application/json"}, timeout=12)
            print("Google Sheets Response:", post_resp.text)
        except Exception as post_err:
            print("Error sending to Google Sheets:", post_err)
    else:
        print("WARNING: No valid ratings (&gt; 0) found. Post skipped.")

if __name__ == "__main__":
    try:
        run()
    except Exception as main_err:
        print("Main execution error:", main_err)
    finally:
        print("Script execution completed successfully.")
        sys.exit(0)
