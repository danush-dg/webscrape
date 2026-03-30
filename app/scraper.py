
import re
import pandas as pd
import os
import asyncio
import sys
import json
import random
from urllib.parse import urlparse, quote
from playwright.async_api import async_playwright, Page
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_fixed
from app.logger import setup_logger

SEM = asyncio.Semaphore(3)  # reduced to avoid race issues
BATCH_SIZE = 20

SEARCH_URL = "https://sieportal.siemens.com/en-vn/search?scope=catalog&Type=products&SearchTerm={}&CatalogSearchSettings.Limit=20&CatalogSearchSettings.Index=0&SortingOption=Relevance"
DETAIL_BASE_URL = "https://sieportal.siemens.com/en-vn/products-services/detail/{}"

OUTPUT_FILE = "data/output/output.xlsx"
IMAGE_DIR = "data/images"

os.makedirs("data/output", exist_ok=True)
os.makedirs("logs", exist_ok=True)
os.makedirs(IMAGE_DIR, exist_ok=True)

logger = setup_logger()

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# =========================
# UTILITIES
# =========================

def clean_text(text):
    return re.sub(r"\s+", " ", text).strip() if text else None


def normalize_weight(weight):
    if not weight:
        return None
    weight = weight.replace(",", ".")
    match = re.findall(r"\d+\.?\d*", weight)
    return float(match[0]) if match else None


def is_valid_data(data):
    return any([
        data.get("Description"),
        data.get("Lifecycle Status"),
        data.get("Notes")
    ])


async def handle_cookie(page):
    try:
        btn = page.get_by_role("button", name=re.compile("accept|agree|allow|ok|close", re.I))
        if await btn.count() > 0:
            await btn.first.click(timeout=2000)
    except:
        pass

# =========================
# PAGE LOAD
# =========================

async def stable_load(page, url, part_number=None):
    await page.goto(url, timeout=60000, wait_until="domcontentloaded")

    try:
        await page.wait_for_selector("h1", timeout=15000)
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(2000)
    except:
        logger.warning(f"{part_number}: page not stable")

# =========================
# PARSER (HYBRID)
# =========================

def parse_html(html):
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True)

    data = {
        "Description": None,
        "Notes": None,
        "Lifecycle Status": None,
        "Standard Delivery Time": None,
        "Net Weight (kg)": None,
        "Minimum Order Quantity": None,
        "Country of Origin": None
    }

    # META
    meta = soup.select_one("meta[name='description']")
    if meta and meta.get("content"):
        data["Description"] = clean_text(meta.get("content"))

    # DOM fallback
    if not data["Description"]:
        desc = soup.select_one("div.product-description")
        if desc:
            data["Description"] = clean_text(desc.text)

    # REGEX (robust)
    lifecycle_match = re.search(
        r"(?:Life cycle|Lifecycle)\s*(?:status)?[:\s]*(.*?)(?:\||Product|Download|$)",
        text, re.I
    )
    if lifecycle_match:
        data["Lifecycle Status"] = clean_text(lifecycle_match.group(1))

    notes_match = re.search(
        r"Notes[:\s]*(.*?)(?:Product family|Life cycle|$)",
        text, re.I
    )
    if notes_match:
        data["Notes"] = clean_text(notes_match.group(1))

    weight_match = re.search(r"Weight[^\d]*([\d\.,]+)", text, re.I)
    if weight_match:
        data["Net Weight (kg)"] = normalize_weight(weight_match.group(1))

    return data

# =========================
# VARIANT FINDER
# =========================

async def find_variants(page, parent_part):
    variants = set()

    try:
        url = SEARCH_URL.format(quote(parent_part))
        await stable_load(page, url, parent_part)
        await handle_cookie(page)

        html = await page.content()
        soup = BeautifulSoup(html, "html.parser")

        links = soup.find_all("a", href=re.compile(r"/detail/"))

        for link in links:
            match = re.search(r"/detail/([A-Z0-9\-]+)$", link.get("href", ""))
            if match:
                part = match.group(1)
                if part.startswith(parent_part):
                    variants.add(part)

        if not variants:
            variants.add(parent_part)

        return list(set(variants))

    except Exception as e:
        logger.error(f"Variant error: {e}")
        return [parent_part]

# =========================
# IMAGE
# =========================

async def extract_image(page, part_number):
    try:
        await page.wait_for_selector("img", timeout=10000)

        # Strategy 1: og:image
        og = page.locator("meta[property='og:image']")
        if await og.count() > 0:
            url = await og.first.get_attribute("content")
            if url:
                return url

        # Strategy 2: main product image (IMPORTANT)
        product_img = page.locator("img[src*='product'], img[src*='catalog']")
        if await product_img.count() > 0:
            src = await product_img.first.get_attribute("src")
            if src:
                return src

        # Strategy 3: fallback (first valid large image)
        imgs = page.locator("img")
        count = await imgs.count()

        for i in range(count):
            src = await imgs.nth(i).get_attribute("src")
            if src and "logo" not in src.lower() and len(src) > 50:
                return src

    except Exception as e:
        logger.warning(f"{part_number}: Image error {e}")

    return None
# =========================
# SCRAPER
# =========================

async def scrape_product(page, part_number, parent_part=None):
    data = {
        "Parent Part": parent_part or part_number,
        "Part Number": part_number,
        "Article Number": None,
        "Description": None,
        "Notes": None,
        "Lifecycle Status": None,
        "Net Weight (kg)": None,
        "Image": None,
        "Status": "Success"
    }

    url = DETAIL_BASE_URL.format(part_number)

    try:
        await stable_load(page, url, part_number)
        await handle_cookie(page)

        html = await page.content()

        if "captcha" in html.lower() or "access denied" in html.lower():
            data["Status"] = "Blocked"
            return data

        if len(html) < 1000:
            data["Status"] = "Empty Page"
            return data

        parsed = parse_html(html)

        # 🔁 retry if missing
        if not is_valid_data(parsed):
            logger.warning(f"{part_number}: retry due to missing data")
            await page.reload()
            await page.wait_for_timeout(3000)
            html = await page.content()
            parsed = parse_html(html)

        data.update(parsed)

        # Article number
        headings = page.locator("h1")
        if await headings.count() > 0:
            data["Article Number"] = (await headings.first.inner_text()).strip()

        # Image
        data["Image"] = await extract_image(page, part_number)

        if not is_valid_data(parsed):
            data["Status"] = "Partial Data"

        logger.info(json.dumps({"event": "scraped", "part": part_number}))

    except asyncio.TimeoutError:
        data["Status"] = "Timeout"
    except Exception as e:
        data["Status"] = f"Error: {str(e)[:50]}"
        logger.exception(e)

    return data


async def scrape_product_parallel(browser, part, parent):
    async with SEM:
        page = await browser.new_page()
        try:
            return await scrape_product(page, part, parent)
        finally:
            await page.close()

# =========================
# MAIN
# =========================

async def scrape(csv_path):
    parts = pd.read_csv(csv_path).iloc[:, 0].dropna().tolist()

    results = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)

        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        )

        page = await context.new_page()

        for parent in parts:
            variants = await find_variants(page, parent)

            for i in range(0, len(variants), BATCH_SIZE):
                batch = variants[i:i+BATCH_SIZE]

                tasks = [scrape_product_parallel(browser, v, parent) for v in batch]
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)

                for r in batch_results:
                    if isinstance(r, dict):
                        results.append(r)

        await browser.close()

    if results:
        df = pd.DataFrame(results)
        try:
            df.to_excel(OUTPUT_FILE, index=False)
        except PermissionError:
            logger.error("Close Excel file and retry")


if __name__ == "__main__":
    asyncio.run(scrape("data/input/products.csv"))
