# lead_scraper_app.py
import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re
import os

HUNTER_API_KEY = st.secrets.get("HUNTER_API_KEY") or os.getenv("HUNTER_API_KEY")
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36"
}

def fetch_yelp_results(niche, location, pages):
    businesses = []
    for page in range(0, pages * 10, 10):
        url = f"https://www.yelp.com/search"
        params = {"find_desc": niche, "find_loc": location, "start": page}
        res = requests.get(url, headers=HEADERS, params=params)

        if res.status_code != 200:
            st.warning(f"Failed to fetch page {page // 10 + 1}: {res.status_code}")
            continue

        soup = BeautifulSoup(res.text, "html.parser")
        listings = soup.select("div.container__09f24__21w3G")

        for item in listings:
            name_tag = item.select_one("a.css-19v1rkv")
            website_url = None
            if name_tag:
                biz_name = name_tag.text.strip()
                link = name_tag['href']
                biz_page = f"https://www.yelp.com{link}"
                try:
                    biz_res = requests.get(biz_page, headers=HEADERS)
                    if biz_res.status_code == 200:
                        biz_soup = BeautifulSoup(biz_res.text, "html.parser")
                        web_tag = biz_soup.select_one("a[data-testid='biz-details-web-url']")
                        if web_tag:
                            website_url = web_tag.get("href")
                except:
                    pass

                if website_url:
                    businesses.append({"name": biz_name, "website": website_url})

        time.sleep(1)  # rate limit

    return businesses

def find_email(domain):
    if not domain:
        return ""
    domain = domain.replace("http://", "").replace("https://", "").split("/")[0]
    url = f"https://api.hunter.io/v2/domain-search?domain={domain}&api_key={HUNTER_API_KEY}"
    try:
        res = requests.get(url)
        data = res.json()
        emails = data.get("data", {}).get("emails", [])
        if emails:
            return emails[0].get("value", "")
    except:
        return ""
    return ""

def run_scraper():
    st.title("🕵️‍♂️ B2B Lead Scraper")

    niche = st.text_input("Niche (e.g. cleaning, landscaping)", "cleaning")
    location = st.text_input("Location (e.g. Montreal, QC)", "Montreal, QC")
    pages = st.slider("How many Yelp pages to scrape?", 1, 10, 3)

    if st.button("Start Scraping"):
        with st.spinner("Scraping in progress..."):
            results = fetch_yelp_results(niche, location, pages)
            st.success(f"Found {len(results)} businesses with websites.")

            data = []
            for biz in results:
                email = find_email(biz['website'])
                data.append({"Business Name": biz['name'], "Website": biz['website'], "Email": email})
                time.sleep(1.5)

            df = pd.DataFrame(data)
            st.dataframe(df)
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("Download CSV", data=csv, file_name="leads.csv", mime="text/csv")

if __name__ == "__main__":
    run_scraper()
