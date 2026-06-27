from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth
from bs4 import BeautifulSoup
from tqdm import tqdm
from utils import clean_title
import random
import time
import os


ARTICLES_PER_CATEGORY = 200

URLS_TO_SCRAPE = [
    #"https://www.cnbc.com/technology/",
    #"https://www.cnbc.com/finance/",
    #"https://www.cnbc.com/business/",
    #"https://www.cnbc.com/economy/",
    #"https://www.cnbc.com/markets/",
    "https://www.cnbc.com/investing/",
]


# -------------------------------
# Human-like helper functions
# -------------------------------

def random_sleep(min_s=2, max_s=5):
    time.sleep(random.uniform(min_s, max_s))


def human_scroll(page):
    scroll_distance = random.randint(200, 700)
    page.mouse.wheel(0, scroll_distance)
    random_sleep(0.5, 2)


def random_mouse_move(page):
    x = random.randint(100, 1200)
    y = random.randint(100, 800)
    page.mouse.move(x, y)
    random_sleep(0.2, 1)


# -------------------------------
# Extract articles
# -------------------------------

def extract_articles(html, target_count):
    soup = BeautifulSoup(html, "html.parser")

    articles = []

    for card in soup.find_all("div", attrs={"data-test": "Card"}):

        title_tag = card.find("a", class_="Card-title")
        if not title_tag:
            continue

        link = title_tag.get("href")

        if link.startswith("/"):
            link = "https://www.cnbc.com" + link

        raw_title = title_tag.get_text(strip=True)

        img = card.find("img")

        articles.append({
            "title": clean_title(raw_title),
            "link": link,
            "image_url": img.get("src") if img else None
        })

        if len(articles) >= target_count:
            break

    return articles


# -------------------------------
# Main scraper
# -------------------------------

def scrape_category(url, target_count):

    profile_dir = "./browser_profile"

    with Stealth().use_sync(sync_playwright()) as p:

        # persistent context = real browser profile
        context = p.chromium.launch_persistent_context(
            user_data_dir=profile_dir,

            headless=False,   # test with false first

            viewport={
                "width": 1366,
                "height": 768
            },

            locale="en-US",

            timezone_id="Africa/Cairo",

            args=[
                "--disable-blink-features=AutomationControlled",
            ]
        )

        page = context.new_page()

        print("Opening homepage...")

        # optional warmup
        page.goto("https://www.google.com")
        random_sleep(3, 6)

        random_mouse_move(page)

        print("Opening CNBC...")

        page.goto(
            url,
            wait_until="networkidle",
            timeout=60000
        )

        random_sleep(4, 7)

        # check block page
        html = page.content().lower()

        if "access denied" in html:
            print("CNBC blocked request.")
            context.close()
            return []

        try:
            # remove cookie popup
            page.evaluate("""
                document.getElementById(
                    'onetrust-consent-sdk'
                )?.remove();
            """)
        except:
            pass

        all_cards = page.locator(
            "div[data-test='Card']"
        )

        clicks = 0
        max_clicks = 50
        previous_count = all_cards.count()

        with tqdm(
            total=target_count,
            desc="Scraping CNBC"
        ) as pbar:

            while previous_count < target_count:

                load_more = page.locator(
                    "button:has-text('Load More')"
                ).first

                if not load_more.is_visible():
                    print("No more button.")
                    break

                # act like user
                random_mouse_move(page)

                load_more.scroll_into_view_if_needed()

                human_scroll(page)

                random_sleep(2, 5)

                try:
                    load_more.hover()

                    random_sleep(0.5, 1.5)

                    # REAL click
                    load_more.click(delay=120)

                except Exception as e:
                    print("Click failed:", e)
                    break

                # wait longer
                random_sleep(8, 15)

                new_count = all_cards.count()

                if new_count == previous_count:
                    print("No new cards loaded.")
                    break

                added = new_count - previous_count

                pbar.update(added)

                previous_count = new_count

                clicks += 1

                if clicks > max_clicks:
                    break

        final_html = page.content()

        context.close()

        return extract_articles(
            final_html,
            target_count
        )


# -------------------------------
# Run
# -------------------------------

if __name__ == "__main__":

    for url in URLS_TO_SCRAPE:

        print("\nScraping:", url)

        articles = scrape_category(
            url,
            ARTICLES_PER_CATEGORY
        )

        print(f"Found {len(articles)} articles")

        for a in articles[:5]:
            print(a)