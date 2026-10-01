# -*- coding: utf-8 -*-
import sys
import re
import urllib.parse
import json

def main():
    print("=== STARTING GMAPS RATING SCRAPER ===")
    
    web_app_url = "https://script.google.com/macros/s/AKfycbwG0n7k4j9LkdumyKuyCi3s4rxd_XK9Oi_11s8fKp7WOa5L6dDJjWtFWGdPTMdxipmn/exec"
    
    units = [
        {"idUnit": "UP3_SGL", "namaUnit": "UP3 Sigli"},
        {"idUnit": "ULP_SGL", "namaUnit": "ULP Sigli Kota"},
        {"idUnit": "ULP_BRN", "namaUnit": "ULP Beureunuen"},
        {"idUnit": "ULP_MRD", "namaUnit": "ULP Meureudu"}
    ]
    
    try:
        import requests
    except Exception as e:
        print("ERROR: Module requests belum terinstall:", e)
        sys.exit(0)

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
        "Cookie": "SOCS=CAISHAgBEhJnd3NfMjAyMzA4MTAtMF9SQzEaAmVuIAEaBgiAo_CmBg"
    }

    results = []

    for u in units:
        unit_id = u["idUnit"]
        unit_name = u["namaUnit"]
        query = "PLN " + unit_name
        encoded_q = urllib.parse.quote(query)
        target_url = f"https://www.google.com/search?q={encoded_q}&amp;hl=id&amp;gl=id"
        
        rating = 0.0
        reviews = 0
        
        print(f"Mengambil data {unit_name}...")
        
        try:
            resp = requests.get(target_url, headers=headers, timeout=12)
            print(f"Status HTTP {unit_name}: {resp.status_code}")
            
            if resp.status_code == 200:
                html = resp.text
                
                # Extract Rating
                m_rat = re.search(r'([0-9]+[\.,]?[0-9]*)\s*(?:★|bintang|stars|dari|out of)', html, re.IGNORECASE) or \
                        re.search(r'Rating:\s*([0-9]+[\.,]?[0-9]*)', html, re.IGNORECASE) or \
                        re.search(r'aria-label="([0-9]+[\.,]?[0-9]*)', html, re.IGNORECASE)
                        
                if m_rat:
                    try:
                        v = float(m_rat.group(1).replace(',', '.'))
                        if 1.0 &lt;= v &lt;= 5.0:
                            rating = v
                    except Exception as ex_r:
                        print(f"Gagal parse rating: {ex_r}")

                # Extract Reviews
                m_rev = re.search(r'([0-9\.]+)\s*(?:ulasan|reviews|penilaian)', html, re.IGNORECASE) or \
                        re.search(r'\\(([0-9\.]+)\\)\s*(?:ulasan|reviews)?', html, re.IGNORECASE)
                        
                if m_rev:
                    try:
                        rev_str = m_rev.group(1).replace('.', '')
                        if rev_str.isdigit():
                            reviews = int(rev_str)
                    except Exception as ex_rev:
                        print(f"Gagal parse ulasan: {ex_rev}")

        except Exception as err_fetch:
            print(f"Error fetch {unit_name}: {err_fetch}")
            
        print(f"HASIL -&gt; {unit_name}: Rating={rating}, Ulasan={reviews}")
        results.append({
            "idUnit": unit_id,
            "namaUnit": unit_name,
            "rating": rating,
            "reviews": reviews
        })

    print("RINGKASAN SCRAPE:", results)

    valid_list = [r for r in results if r["rating"] &gt; 0]

    if valid_list:
        print(f"Mengirim {len(valid_list)} data valid ke Google Sheets...")
        try:
            p_resp = requests.post(web_app_url, json=valid_list, headers={"Content-Type": "application/json"}, timeout=10)
            print("Respon Google Sheets:", p_resp.text)
        except Exception as err_post:
            print(f"Error kirim ke Google Sheets: {err_post}")
    else:
        print("PERINGATAN: Tidak ada data rating valid (&gt; 0). Pengiriman dilewati.")

if __name__ == "__main__":
    try:
        main()
    except Exception as fatal_err:
        print(f"CRITICAL ERROR: {fatal_err}")
    finally:
        print("Skrip selesai dijalankan.")
        sys.exit(0)
