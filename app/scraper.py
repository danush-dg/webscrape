# import re
# import pandas as pd
# import os
# import asyncio
# import sys
# from urllib.parse import urlparse
# from playwright.async_api import async_playwright

# # ✅ Windows fix
# if sys.platform == "win32":
#     asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# BASE_URL = "https://sieportal.siemens.com/en-vn/products-services/detail/{}?tree=CatalogTree"
# OUTPUT_FILE = "data/output/output.xlsx"
# IMAGE_DIR = "data/images"


# # -----------------------------
# # COOKIE HANDLER
# # -----------------------------
# async def handle_cookie(page):
#     try:
#         # Try direct button (fastest)
#         btn = page.get_by_role("button", name=re.compile("accept|agree|allow|ok", re.I))

#         if await btn.count() > 0:
#             await btn.first.click(timeout=2000)
#             print("✅ Cookie accepted")
#             return

#     except:
#         pass

# # -----------------------------
# # IMAGE DOWNLOAD (UPDATED)
# # -----------------------------
# async def download_image(page, part):
#     os.makedirs(IMAGE_DIR, exist_ok=True)

#     try:
#         html = await page.content()

#         # ✅ 1. OG IMAGE (best)
#         img_url = None
#         try:
#             og = page.locator("meta[property='og:image']")
#             if await og.count() > 0:
#                 img_url = await og.first.get_attribute("content")
#         except:
#             pass

#         # ✅ 2. JSON fallback
#         if not img_url:
#             match = re.search(r'"image":"(https://[^"]+)"', html)
#             if match:
#                 img_url = match.group(1)

#         # ✅ 3. last fallback
#         if not img_url:
#             try:
#                 img_url = await page.locator("img").first.get_attribute("src")
#             except:
#                 return ""

#         if not img_url:
#             return ""

#         # Fix relative URL
#         if img_url.startswith("/"):
#             img_url = "https://sieportal.siemens.com" + img_url

#         img_url = img_url.split("?")[0]

#         # Extension
#         ext = os.path.splitext(urlparse(img_url).path)[1]
#         if ext.lower() not in [".jpg", ".jpeg", ".png", ".webp"]:
#             ext = ".jpg"

#         file_path = os.path.join(IMAGE_DIR, f"{part}_image{ext}")

#         # ✅ Download image
#         response = await page.context.request.get(img_url)

#         if response.ok:
#             with open(file_path, "wb") as f:
#                 f.write(await response.body())

#             print(f"🖼️ Saved: {file_path}")

#         # ✅ RETURN URL (IMPORTANT)
#         return img_url

#     except Exception as e:
#         print(f"⚠️ Image error for {part}: {e}")

#     return ""


# # -----------------------------
# # HELPER
# # -----------------------------
# def extract(text, label):
#     pattern = rf"{label}\s+(.*?)\n"
#     match = re.search(pattern, text, re.IGNORECASE)
#     return match.group(1).strip() if match else None


# # -----------------------------
# # SCRAPE ONE PART
# # -----------------------------
# async def scrape_part(page, part):
#     url = BASE_URL.format(part)

#     data = {
#         "Part Number": part,
#         "Article Number": None,
#         "Description": None,
#         "Family": None,
#         "Lifecycle": None,
#         "PLM Date": None,
#         "Image": None,
#         "URL": url,
#         "Status": "Success"
#     }

#     try:
#         await page.goto(url, timeout=60000)

#         await handle_cookie(page)

#         await page.wait_for_timeout(2000)

#         print("🌐 Current URL:", page.url)

#         # ❌ Search page → skip
#         if "search" in page.url:
#             data["Status"] = "No Data"
#             return data

#         try:
#             await page.wait_for_selector("h1.intro-section__content-headline", timeout=5000)
#         except:
#             data["Status"] = "No Data / Timeout"
#             return data

#         await page.mouse.wheel(0, 1500)

#         content = await page.locator("body").text_content() or ""

#         if "no results" in content.lower() or "not found" in content.lower():
#             data["Status"] = "No Data Found"
#             return data

#         # -----------------------------
#         # EXTRACTION
#         # -----------------------------

#         match = re.search(r"Article number\s+([A-Z0-9\-]+)", content)
#         data["Article Number"] = (
#             match.group(1) if match else await page.locator("h1.intro-section__content-headline").first.inner_text()
#         )

#         # ✅ UPDATED IMAGE LOGIC
#         data["Image"] = await download_image(page, part)

#         try:
#             label = page.locator("text=Product Family").first
#             link = label.locator("xpath=following::a[1]")
#             data["Family"] = await link.inner_text()
#         except:
#             pass

#         data["Lifecycle"] = (
#             extract(content, "Product lifecycle")
#             or extract(content, "Life cycle status")
#         )

#         match = re.search(r"Since:\s*(\d{2}\.\d{2}\.\d{4})", content)
#         data["PLM Date"] = match.group(1) if match else None

#         match = re.search(r"Device:\s*(.*?)(\n|$)", content)
#         if match:
#             desc = match.group(1)
#             desc = re.sub(r"\s+", " ", desc).strip()
#             desc = desc.replace("|", ";")
#             desc = re.sub(r";+", ";", desc)
#             data["Description"] = desc

#     except Exception as e:
#         data["Status"] = f"Error: {e}"

#     return data


# # -----------------------------
# # MAIN FUNCTION
# # -----------------------------
# async def scrape(csv_path):
#     parts = pd.read_csv(csv_path).iloc[:, 0].dropna().tolist()

#     results = []
#     os.makedirs("data/output", exist_ok=True)

#     async with async_playwright() as p:
#         browser = await p.chromium.launch(headless=False)
#         page = await browser.new_page()

#         await page.goto(BASE_URL.format(parts[0]))
#         await handle_cookie(page)

#         for part in parts:
#             print(f"🔍 Scraping {part}")
#             data = await scrape_part(page, part)
#             results.append(data)

#         await browser.close()

#     pd.DataFrame(results).to_excel(OUTPUT_FILE, index=False)
#     print(f"✅ Done → {OUTPUT_FILE}")


#2
# import re
# import pandas as pd
# import os
# import asyncio
# import sys
# from urllib.parse import urlparse
# from playwright.async_api import async_playwright

# # ✅ Windows fix
# if sys.platform == "win32":
#     asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# BASE_URL = "https://sieportal.siemens.com/en-vn/products-services/detail/{}?tree=CatalogTree"
# OUTPUT_FILE = "data/output/output.xlsx"
# IMAGE_DIR = "data/images"


# # -----------------------------
# # CLEAN TEXT
# # -----------------------------
# def clean_text(text):
#     text = re.sub(r"<.*?>", " ", text)
#     text = re.sub(r"\s+", " ", text)
#     text = text.replace("|", ";")
#     text = re.sub(r";+", ";", text)
#     return text.strip()


# # -----------------------------
# # DESCRIPTION EXTRACTION
# # -----------------------------
# def extract_description(html):
#     match = re.search(
#         r"Product description[:\s]*(.*?)(?:</p>|</div>|\n[A-Z])",
#         html,
#         re.IGNORECASE | re.DOTALL
#     )
#     if match:
#         return clean_text(match.group(1))

#     match = re.search(
#         r"Device:\s*(.*?)(\n|$)",
#         html,
#         re.IGNORECASE
#     )
#     if match:
#         return clean_text(match.group(1))

#     match = re.search(r'"description":"(.*?)"', html)
#     if match:
#         return clean_text(match.group(1))

#     return None


# # -----------------------------
# # COOKIE HANDLER
# # -----------------------------
# async def handle_cookie(page):
#     try:
#         btn = page.get_by_role("button", name=re.compile("accept|agree|allow|ok", re.I))

#         if await btn.count() > 0:
#             await btn.first.click(timeout=2000)
#             print("✅ Cookie accepted")
#             return

#     except:
#         pass


# # -----------------------------
# # IMAGE DOWNLOAD (UPDATED)
# # -----------------------------
# async def download_image(page, part):
#     os.makedirs(IMAGE_DIR, exist_ok=True)

#     try:
#         html = await page.content()

#         img_url = None

#         try:
#             og = page.locator("meta[property='og:image']")
#             if await og.count() > 0:
#                 img_url = await og.first.get_attribute("content")
#         except:
#             pass

#         if not img_url:
#             match = re.search(r'"image":"(https://[^"]+)"', html)
#             if match:
#                 img_url = match.group(1)

#         if not img_url:
#             try:
#                 img_url = await page.locator("img").first.get_attribute("src")
#             except:
#                 return ""

#         if not img_url:
#             return ""

#         if img_url.startswith("/"):
#             img_url = "https://sieportal.siemens.com" + img_url

#         img_url = img_url.split("?")[0]

#         ext = os.path.splitext(urlparse(img_url).path)[1]
#         if ext.lower() not in [".jpg", ".jpeg", ".png", ".webp"]:
#             ext = ".jpg"

#         file_path = os.path.join(IMAGE_DIR, f"{part}_image{ext}")

#         response = await page.context.request.get(img_url)

#         if response.ok:
#             with open(file_path, "wb") as f:
#                 f.write(await response.body())

#             print(f"🖼️ Saved: {file_path}")

#         return img_url

#     except Exception as e:
#         print(f"⚠️ Image error for {part}: {e}")

#     return ""


# # -----------------------------
# # HELPER
# # -----------------------------
# def extract(text, label):
#     pattern = rf"{label}\s+(.*?)\n"
#     match = re.search(pattern, text, re.IGNORECASE)
#     return match.group(1).strip() if match else None


# # -----------------------------
# # SCRAPE ONE PART
# # -----------------------------
# async def scrape_part(page, part):
#     url = BASE_URL.format(part)

#     data = {
#         "Part Number": part,
#         "Article Number": None,
#         "Description": None,
#         "Family": None,
#         "Lifecycle": None,
#         "PLM Date": None,
#         "Image": None,
#         "URL": url,
#         "Status": "Success"
#     }

#     try:
#         await page.goto(url, timeout=60000)

#         await handle_cookie(page)

#         await page.wait_for_timeout(2000)

#         print("🌐 Current URL:", page.url)

#         if "search" in page.url:
#             data["Status"] = "No Data"
#             return data

#         try:
#             await page.wait_for_selector("h1.intro-section__content-headline", timeout=5000)
#         except:
#             data["Status"] = "No Data / Timeout"
#             return data

#         await page.mouse.wheel(0, 1500)

#         content = await page.locator("body").text_content() or ""
#         html = await page.content()

#         if "no results" in content.lower() or "not found" in content.lower():
#             data["Status"] = "No Data Found"
#             return data

#         # -----------------------------
#         # EXTRACTION
#         # -----------------------------

#         match = re.search(r"Article number\s+([A-Z0-9\-]+)", content)
#         data["Article Number"] = (
#             match.group(1) if match else await page.locator("h1.intro-section__content-headline").first.inner_text()
#         )

#         # ✅ ONLY CHANGE HERE
#         desc = extract_description(html) or extract_description(content)
#         if desc:
#             data["Description"] = desc

#         data["Image"] = await download_image(page, part)

#         try:
#             label = page.locator("text=Product Family").first
#             link = label.locator("xpath=following::a[1]")
#             data["Family"] = await link.inner_text()
#         except:
#             pass

#         data["Lifecycle"] = (
#             extract(content, "Product lifecycle")
#             or extract(content, "Life cycle status")
#         )

#         match = re.search(r"Since:\s*(\d{2}\.\d{2}\.\d{4})", content)
#         data["PLM Date"] = match.group(1) if match else None

#     except Exception as e:
#         data["Status"] = f"Error: {e}"

#     return data


# # -----------------------------
# # MAIN FUNCTION
# # -----------------------------
# async def scrape(csv_path):
#     parts = pd.read_csv(csv_path).iloc[:, 0].dropna().tolist()

#     results = []
#     os.makedirs("data/output", exist_ok=True)

#     async with async_playwright() as p:
#         browser = await p.chromium.launch(headless=False)
#         page = await browser.new_page()

#         await page.goto(BASE_URL.format(parts[0]))
#         await handle_cookie(page)

#         for part in parts:
#             print(f"🔍 Scraping {part}")
#             data = await scrape_part(page, part)
#             results.append(data)

#         await browser.close()

#     pd.DataFrame(results).to_excel(OUTPUT_FILE, index=False)
#     print(f"✅ Done → {OUTPUT_FILE}")



import re
import pandas as pd
import os
import asyncio
import sys
import logging
from urllib.parse import urlparse
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_fixed

# Windows fix
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

BASE_URL = "https://mall.industry.siemens.com/mall/en/vn/Catalog/Product/{}"
OUTPUT_FILE = "data/output/output.xlsx"
IMAGE_DIR = "data/images"
LOG_FILE = "logs/scraper.log"

os.makedirs("data/output", exist_ok=True)
os.makedirs("logs", exist_ok=True)
os.makedirs(IMAGE_DIR, exist_ok=True)

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# -----------------------------
# COOKIE HANDLER
# -----------------------------
async def handle_cookie(page):
    for _ in range(3):
        try:
            btn = page.get_by_role("button", name=re.compile("accept|agree|allow|ok", re.I))
            if await btn.count() > 0:
                await btn.first.click(timeout=2000)
                logging.info("Cookie accepted")
                return
        except:
            await page.wait_for_timeout(1000)

# -----------------------------
# CLEAN TEXT
# -----------------------------
def clean_text(text):
    return re.sub(r"\s+", " ", text).strip()

# -----------------------------
# BEAUTIFULSOUP PARSER
# -----------------------------
def parse_html(html):
    soup = BeautifulSoup(html, "html.parser")

    data = {
        "Description": None,
        "Notes": None,
        "Lifecycle Status": None
    }

    # -----------------------------
    # DESCRIPTION
    # -----------------------------
    meta = soup.select_one("meta[name='description']")
    if meta and meta.get("content"):
        data["Description"] = clean_text(meta.get("content"))

    # -----------------------------
    # FULL TEXT (for fallback parsing)
    # -----------------------------
    text = soup.get_text(" ", strip=True)

    # -----------------------------
    # NOTES (clean extraction)
    # -----------------------------
    notes_match = re.search(
        r"Notes[:\s]*(.*?)(?:Product family|Life cycle|$)",
        text,
        re.I
    )
    if notes_match:
        data["Notes"] = clean_text(notes_match.group(1))

    # -----------------------------
    # LIFECYCLE STATUS (IMPORTANT)
    # -----------------------------
    lifecycle_match = re.search(
        r"Life cycle status[:\s]*(.*?)(?:\||Product|$)",
        text,
        re.I
    )
    if lifecycle_match:
        data["Lifecycle Status"] = clean_text(lifecycle_match.group(1))

    return data

# -----------------------------
# IMAGE DOWNLOAD
# -----------------------------
async def download_image(page, part):
    try:
        html = await page.content()

        match = re.search(r'"image":"(https://[^"]+)"', html)
        if not match:
            return ""

        img_url = match.group(1).split("?")[0]

        ext = os.path.splitext(urlparse(img_url).path)[1] or ".jpg"
        file_path = os.path.join(IMAGE_DIR, f"{part}_image{ext}")

        response = await page.context.request.get(img_url)
        if response.ok:
            with open(file_path, "wb") as f:
                f.write(await response.body())

        return img_url

    except Exception as e:
        logging.error(f"Image error {part}: {e}")
        return ""

# -----------------------------
# RETRY LOAD
# -----------------------------
@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
async def load_page(page, url):
    await page.goto(url, timeout=60000)
    await page.wait_for_timeout(3000)

# -----------------------------
# PRODUCT LINKS
# -----------------------------
async def get_product_links(page):
    return [page.url]

# -----------------------------
# SCRAPE SINGLE
# -----------------------------
async def scrape_single(page, url, part):
    data = {
        "Part Number": part,
        "Article Number": None,
        "Description": None,
        "Notes": None,
        "Notes": None,
        "Lifecycle Status": None,
        "Image": None,
        "URL": url,
        "Status": "Success"
    }

    try:
        await load_page(page, url)
        await handle_cookie(page)

        # Redirect check
        if "search" in page.url.lower():
            data["URL"] = page.url
            data["Status"] = "Redirected to Search"
            return data

        await page.wait_for_selector("h1", timeout=10000)

        html = await page.content()

        # Description & Notes
        parsed = parse_html(html)
        data["Description"] = parsed["Description"]
        data["Notes"] = parsed["Notes"]
        data["Lifecycle Status"] = parsed["Lifecycle Status"]

        # Article Number
        headings = page.locator("h1")
        count = await headings.count()

        for i in range(count):
            text = (await headings.nth(i).inner_text()).strip()
            if re.match(r"[A-Z0-9\-]{6,}", text):
                data["Article Number"] = text
                break

        # Image
        try:
            img_url = None

            og = page.locator("meta[property='og:image']")
            if await og.count() > 0:
                img_url = await og.first.get_attribute("content")

            if not img_url:
                img = page.locator("img")
                if await img.count() > 0:
                    img_url = await img.first.get_attribute("src")

            if img_url:
                if img_url.startswith("/"):
                    img_url = "https://mall.industry.siemens.com" + img_url

                img_url = img_url.split("?")[0]

                ext = os.path.splitext(urlparse(img_url).path)[1] or ".jpg"
                file_path = os.path.join(IMAGE_DIR, f"{part}_image{ext}")

                response = await page.context.request.get(img_url)
                if response.ok:
                    with open(file_path, "wb") as f:
                        f.write(await response.body())

                data["Image"] = img_url

        except Exception as e:
            logging.error(f"Image error {part}: {e}")

        # Final validation
        if not data["Article Number"]:
            data["Description"] = None
            data["Notes"] = None
            data["Notes"] = None
            data["Lifecycle Status"] = None
            data["Image"] = None
            data["Status"] = "No Article Number"

    except Exception as e:
        logging.error(f"Error {part}: {e}")
        data["Status"] = "Error"

    return data

# -----------------------------
# MAIN
# -----------------------------
async def scrape(csv_path):
    parts = pd.read_csv(csv_path).iloc[:, 0].dropna().tolist()
    results = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        for part in parts:
            try:
                url = BASE_URL.format(part)
                logging.info(f"Scraping {part}")

                links = [url]

                for link in links:
                    data = await scrape_single(page, link, part)
                    results.append(data)

            except Exception as e:
                logging.error(f"Failed {part}: {e}")

        await browser.close()

    pd.DataFrame(results).to_excel(OUTPUT_FILE, index=False)
    logging.info("Scraping completed")
    print(f"✅ Done → {OUTPUT_FILE}")
