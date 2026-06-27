import os
import json
import requests
import re
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm
from playwright_stealth import Stealth
import random

# We need 2000 total. We will try to pull up to 200 per category to be safe.
TOTAL_TARGET = 2000
ARTICLES_PER_CATEGORY = 200
IMAGE_DIR = "cnbc_scraped_images"

# The master list of CNBC categories
URLS_TO_SCRAPE = [
    "https://www.cnbc.com/finance/",
    "https://www.cnbc.com/technology/",
    "https://www.cnbc.com/business/",
    "https://www.cnbc.com/economy/",
    "https://www.cnbc.com/markets/",
    "https://www.cnbc.com/investing/",
    "https://www.cnbc.com/wealth/",
    "https://www.cnbc.com/real-estate/",
    "https://www.cnbc.com/retail/",
    "https://www.cnbc.com/autos/",
    "https://www.cnbc.com/media/",
    "https://www.cnbc.com/health-and-science/",
    "https://www.cnbc.com/energy/",
    "https://www.cnbc.com/climate/",
    "https://www.cnbc.com/personal-finance/"
]


def clean_title(title):
    cleaned_title = title.lower().replace(' ', '_')
    cleaned_title = re.sub(r'[^a-zA-Z0-9_]', '', cleaned_title)
    return cleaned_title


def extract_articles(html, target_count):
    soup = BeautifulSoup(html, "html.parser")

    # The header title changes based on the category (e.g., "More In Tech", "More In Wealth")
    # So we just look for a header that starts with "More In"
    more_heading = None
    for header in soup.find_all("div", class_="ModuleHeader-container"):
        if "More In " in header.get_text():
            more_heading = header
            break

    if not more_heading:
        print("Could not find the 'More In...' section on this page.")
        return []

    articles = []
    
    main_column = more_heading.find_parent("div", class_="Layout-layoutMain") 
    search_area = main_column if main_column else more_heading.parent.parent

    for card in search_area.find_all_next("div", attrs={"data-test": "Card"}):
        title_tag = card.find("a", class_="Card-title")
        if not title_tag:
            continue

        link = title_tag.get("href")
        if link.startswith("/"):
            link = "https://www.cnbc.com" + link

        raw_title = title_tag.get_text(strip=True)
        img_tag = card.find("img", class_="Card-mediaContainerInner")
        
        articles.append({
            "title": raw_title,
            "clean_title": clean_title(raw_title),
            "link": link,
            "image_url": img_tag.get("src") if img_tag else None,
        })

        # We stop extracting if we hit the limit for this specific category
        if len(articles) >= target_count:
            return articles

    return articles


def scrape_category(url, target_count):
    """Scrapes a single category page with stealth and humanized behavior."""
    
    # NEW SYNTAX: Wrap sync_playwright() with Stealth().use_sync()
    # This automatically applies stealth evasions to all browsers, contexts, and pages.
    with Stealth().use_sync(sync_playwright()) as p:
        browser = p.chromium.launch(
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars"
            ]
        )
        
        # Build a highly realistic context
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            locale="en-US",
            timezone_id="America/New_York",
            extra_http_headers={
                "Accept-Language": "en-US,en;q=0.9",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                "Sec-Ch-Ua": "\"Not_A Brand\";v=\"8\", \"Chromium\";v=\"120\", \"Google Chrome\";v=\"120\"",
                "Sec-Ch-Ua-Mobile": "?0",
                "Sec-Ch-Ua-Platform": "\"Windows\"",
                "Upgrade-Insecure-Requests": "1"
            }
        )
        
        page = context.new_page()
        
        # Add a random initial delay before even going to the site
        page.wait_for_timeout(random.randint(1000, 3000))
        page.goto(url, wait_until="domcontentloaded")

        try:
            page.evaluate("document.getElementById('onetrust-consent-sdk')?.remove();")
            page.evaluate("document.querySelector('.onetrust-pc-dark-filter')?.remove();")
        except Exception:
            pass

        all_cards_locator = page.locator("div[data-test='Card']")
        load_more_btn = page.locator("button:has-text('Load More')").first

        max_clicks = 50
        clicks = 0
        stalled_attempts = 0
        
        previous_total_cards = all_cards_locator.count()

        with tqdm(total=target_count, desc=f"Loading {url.split('/')[-2].title()}") as pbar:
            cards_added = 0 
            
            while cards_added < target_count and clicks < max_clicks:
                if not load_more_btn.is_visible():
                    break

                load_more_btn.scroll_into_view_if_needed()
                
                # Human-like scrolling
                scroll_amount = random.randint(300, 700)
                page.mouse.wheel(0, scroll_amount) 
                
                # Randomize the pre-click pause
                page.wait_for_timeout(random.randint(400, 1200))
                
                load_more_btn.evaluate("node => node.click()")
                
                # Randomize the post-click pause (Jitter: 2.0s to 4.5s)
                page.wait_for_timeout(random.randint(2000, 4500)) 
                clicks += 1
                
                current_total_cards = all_cards_locator.count()
                new_batch_size = current_total_cards - previous_total_cards

                if new_batch_size > 0:
                    cards_added += new_batch_size
                    pbar.update(min(new_batch_size, target_count - pbar.n))
                    
                    stalled_attempts = 0
                    previous_total_cards = current_total_cards
                else:
                    stalled_attempts += 1
                    if stalled_attempts >= 3:
                        break

        final_html = page.content()
        browser.close()

        return extract_articles(final_html, target_count)

def save_image(article):
    if not article.get('image_url'):
        return
    
    image_filename = os.path.join(IMAGE_DIR, f"{article['clean_title']}.jpg")
    try:
        response = requests.get(article['image_url'], timeout=10)
        if response.status_code == 200:
            with open(image_filename, 'wb') as f:
                f.write(response.content)
    except Exception:
        pass


def convert_to_json(articles, output_file='articles.json'):
    with open(output_file, 'w') as f:
        json.dump(articles, f, indent=4)


if __name__ == "__main__":
    os.makedirs(IMAGE_DIR, exist_ok=True)
    
    master_articles = []
    global_seen_links = set()

    print(f"Goal: {TOTAL_TARGET} unique articles.")
    
    # 1. Loop through all the categories
    for url in URLS_TO_SCRAPE:
        if len(master_articles) >= TOTAL_TARGET:
            break
            
        print(f"\n--- Starting: {url} ---")
        category_data = scrape_category(url, ARTICLES_PER_CATEGORY)
        
        # Cross-reference with our global set to prevent duplicates across categories
        new_unique_count = 0
        for article in category_data:
            if article["link"] not in global_seen_links:
                global_seen_links.add(article["link"])
                master_articles.append(article)
                new_unique_count += 1
                
                # Stop immediately if we hit exactly 2000
                if len(master_articles) >= TOTAL_TARGET:
                    break
                    
        print(f"Found {new_unique_count} new unique articles. Total is now {len(master_articles)}.")

    print(f"\nScraping complete! Final count: {len(master_articles)} articles.")

    # # 2. Download Images
    # if master_articles:
    #     with ThreadPoolExecutor(max_workers=20) as executor:
    #         list(tqdm(
    #             executor.map(save_image, master_articles), 
    #             total=len(master_articles), 
    #             desc="Downloading all images"
    #         ))

    #     # 3. Save JSON
    #     json_path = 'cnbc_articles_2000.json'
    #     convert_to_json(master_articles, output_file=json_path)
    #     print(f"\nProcess complete! Data saved to {json_path} and images saved to {IMAGE_DIR}/")