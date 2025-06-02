import streamlit as st
import requests
from bs4 import BeautifulSoup
import re
import time
import pandas as pd
import os

HUNTER_API_KEY = os.getenv("HUNTER_API_KEY")

HEADERS = {"User-Agent": "Mozilla/5.0"}

def is_valid_email(email):
    invalid_keywords = ["noreply", "no-reply", "donotreply", "example", "test"]
    return (
        email
        and email.count("@") == 1
        and not any(k in email.lower() for k in invalid_keywords)
        and not email.lower().endswith(".png")
    )

def extract_emails_from_site(url):
    try:
        res = requests.get(url, headers=HEADERS, timeout=5)
        return set(
            email for email in re.findall(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", res.text)
            if is_valid_email(email)
        )
    except:
        return set()

def hunter_domain_search(domain):
    url = f"https://api.hunter.io/v2/domain-search?domain={domain}&api_key={HUNTER_API_KEY}"
    try:
        res = requests.get(url).json()
        emails = res.get("data", {}).get("emails", [])
        for e in emails:
            if e.get("type") == "personal" and e.get("value"):
                return e["value"]
        if emails:
            return emails[0]["value"]
    except:
        pass
    return ""

def hunter_email_verification(email):
    url = f"https://api.hunter.io/v2/email-verifier?email={email}&api_key={HUNTER_API_KEY}"
    try:
        res = requests.get(url).json()
        result = res.get("data", {})
        return result.get("result") == "deliverable"
    except:
        return False

def get_website_and_email(yelp_page_url):
    try:
        res = requests.get(yelp_page_url, headers=HEADERS, timeout=5)
        soup = BeautifulSoup(res.text, 'html.parser')
        website_tag = soup.find("a", string="Business website")
        if website_tag:
            website = website_tag.get("href")
            emails = extract_emails_from_site(website)
            if emails:
                return website, next(iter(emails))
            domain = website.replace("http://", "").replace("https://", "").split("/")[0]
            email = hunter_domain_search(domain)
            if email and hunter_email_verification(email):
                return website, email
    except:
        pass
    return "", ""

def scrape_yelp(query, location, pages):
    base_url = "https://www.yelp.ca/search"
    leads = []

    for page in range(0, pages * 10, 10):
        st.info(f"Scraping page {page//10 + 1}...")
        params = {"find_desc": query, "find_loc": location, "start": page}
        res = requests.get(base_url, headers=HEADERS, params=params)
        st.write(res.text[:5000])  # DEBUG: Show part of page

        soup = BeautifulSoup(res.text, "html.parser")

        for biz in soup.select("div.container__09f24__21w3G"):
            name_tag = biz.select_one("a.css-19v1rkv")
            if not name_tag:
                continue

            name = name_tag.text.strip()
            link = "https://www.yelp.ca" + name_tag["href"]
            website, email = get_website_and_email(link)

            if email:
                leads.append({
                    "Name": name,
                    "Yelp URL": link,
                    "Website": website,
                    "Email": email
                })

            time.sleep(1.5)

    return leads

# Streamlit App UI
st.title("🔍 B2B Lead Scraper")
st.write("Enter your niche and city to find businesses with verified emails.")

query = st.text_input("Business Type", value="dentists")
location = st.text_input("City", value="Montreal")
pages = st.slider("Pages to Scrape", 1, 5, 2)

if st.button("Start Scraping"):
    with st.spinner("Working..."):
        leads = scrape_yelp(query, location, pages)
        if leads:
            df = pd.DataFrame(leads)
            st.success(f"Found {len(df)} leads.")
            st.dataframe(df)
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download CSV", csv, "leads.csv", "text/csv")
        else:
            st.warning("No leads found.")
