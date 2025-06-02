"""
UCSD Majors Scraper (Selenium + BeautifulSoup)
------------------------------------------------
This script crawls the UC San Diego Admissions majors directory and retrieves
all undergraduate majors, following each link and extracting a short overview.

Output: `ucsd_majors.md` – a Markdown catalog with one section per major.

### Quick start
```bash
python -m venv .venv && source .venv/bin/activate
pip install selenium webdriver-manager beautifulsoup4 tqdm
python ucsd_majors_scraper.py --headless
```

> **Tip**: If the site structure changes, adjust the CSS selectors in
> `get_major_links()` and `scrape_major_page()`.
"""

import argparse
import os
import re
import textwrap
import time
from pathlib import Path

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from tqdm import tqdm

BASE_URL = "https://admissions.ucsd.edu/why/majors/index.html#tab-1"
OUTPUT_FILE = "ucsd_majors.md"


def get_driver(headless: bool = True) -> webdriver.Chrome:
    """Spin up a Chrome WebDriver (auto‑downloads chromedriver)."""
    chrome_opts = Options()
    if headless:
        chrome_opts.add_argument("--headless=new")
    chrome_opts.add_argument("--disable-gpu")
    chrome_opts.add_argument("--no-sandbox")
    chrome_opts.add_argument("--disable-dev-shm-usage")
    return webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=chrome_opts,
    )


def get_major_links(driver: webdriver.Chrome) -> dict[str, str]:
    """Return {url: visible_text} for every major link on every tab."""
    driver.get(BASE_URL)
    wait = WebDriverWait(driver, 20)

    # Ensure the first tab-pane is loaded
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.tab-content")))

    major_links: dict[str, str] = {}

    # UCSD majors are split across eight tabs – click through each
    tab_buttons = driver.find_elements(By.CSS_SELECTOR, "ul.nav-tabs li a")

    for tab_btn in tab_buttons:
        driver.execute_script("arguments[0].click();", tab_btn)
        time.sleep(1)  # allow JS to populate the pane

        active_pane = driver.find_element(By.CSS_SELECTOR, "div.tab-pane.active")
        anchors = active_pane.find_elements(By.TAG_NAME, "a")

        for a in anchors:
            href = a.get_attribute("href")
            text = a.text.strip()
            if href and text and href.startswith("https://admissions.ucsd.edu"):
                major_links[href] = text

    return major_links


def scrape_major_page(driver: webdriver.Chrome, url: str) -> dict:
    """Go to `url` and extract title, first few paragraphs, and degree types."""
    driver.get(url)
    wait = WebDriverWait(driver, 20)
    wait.until(EC.presence_of_element_located((By.TAG_NAME, "h1")))

    soup = BeautifulSoup(driver.page_source, "html.parser")

    title_tag = soup.find("h1")
    title = title_tag.get_text(strip=True) if title_tag else "(missing title)"

    # Grab up to 3 non‑empty <p> elements beneath the hero section as description
    description_chunks: list[str] = []
    for p in soup.select("main p"):
        txt = p.get_text(" ", strip=True)
        if txt:
            description_chunks.append(txt)
        if len(description_chunks) >= 3:
            break
    description = "\n".join(description_chunks)

    # Naïve degree detection (BA, BS, etc.)
    degree_types = sorted(set(re.findall(r"\b[BM]\.?[SA]\.?(?:\sHons\.)?\b", soup.get_text())))

    return {
        "title": title,
        "url": url,
        "description": description,
        "degrees": degree_types,
    }


def write_markdown(records: list[dict]):
    """Write scraped records into `OUTPUT_FILE` in nicely formatted Markdown."""
    with Path(OUTPUT_FILE).open("w", encoding="utf‑8") as md:
        md.write(f"# UC San Diego Undergraduate Majors\n\n")
        md.write(f"_Scraped on {time.strftime('%Y‑%m‑%d %H:%M:%S')}._\n\n")

        for rec in records:
            md.write(f"## {rec['title']}\n")
            md.write(f"**URL:** {rec['url']}\n\n")
            if rec["degrees"]:
                md.write(f"**Degree(s) Offered:** {', '.join(rec['degrees'])}\n\n")
            if rec["description"]:
                md.write(textwrap.fill(rec["description"], 100))
                md.write("\n\n")
            md.write("---\n\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="UCSD majors scraper")
    parser.add_argument("--headless", action="store_true", help="Run Chrome in headless mode (default)")
    args = parser.parse_args()

    driver = get_driver(headless=args.headless or True)
    try:
        print("Gathering major links …")
        links = get_major_links(driver)

        records = []
        for url in tqdm(links.keys(), desc="Scraping majors"):
            records.append(scrape_major_page(driver, url))

        write_markdown(records)
        print(f"\nDone! {len(records)} majors written to {OUTPUT_FILE} -> {os.path.abspath(OUTPUT_FILE)}")
    finally:
        driver.quit()
