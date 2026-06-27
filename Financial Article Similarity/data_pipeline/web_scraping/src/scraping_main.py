import requests
import os
import json
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm
import re
from ft_scrping import scrape_ft_technology_articles
from cnbc_scraping import scrape_category,URLS_TO_SCRAPE,ARTICLES_PER_CATEGORY
from utils import save_image, convert_to_json
from dotenv import load_dotenv


if __name__ == "__main__":

    load_dotenv()  

    root_path = os.getenv("fin_article_root_path")
    CNBC_IMAGE_DIR = os.path.join(root_path, 'data_pipline/web_scraping/storage/raw/CNBC/cnbc_scraped_images')
    FT_IMAGE_DIR = os.path.join(root_path, 'data_pipline/web_scraping/storage//ft_scraped_images')

    ft_articles_json = os.path.join(root_path, 'data_pipline/web_scraping/storage/raw/financial_times/financial_times.json')
    cnbc_articles_json = os.path.join(root_path, 'data_pipline/web_scraping/storage/raw//CNBC/cnbc_articles_2000.json')

    os.makedirs(CNBC_IMAGE_DIR, exist_ok=True)
    os.makedirs(FT_IMAGE_DIR, exist_ok=True)

    TOTAL_TARGET = 2000
    print(cnbc_articles_json)
    print(CNBC_IMAGE_DIR)
    print("Starting the scraping process...")
    # #scraping the articles from the Financial Times Technology section
    # articles = scrape_ft_technology_articles(pages_to_scrape=80)
    
    # with tqdm(total=len(articles), desc="Downloading images") as pbar:
    #     with ThreadPoolExecutor(max_workers=20) as executor:
    #         list(tqdm(executor.map(lambda art: save_image(art, FT_IMAGE_DIR), articles), total=len(articles), desc="Downloading images"))


    # convert_to_json(articles, output_file='Financial Article Similarity/financial_times.json')

    ## Scraping CNBC articles
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

        if len((master_articles)) != 200:
            break
        # 2. Download Images
        if master_articles:
            with ThreadPoolExecutor(max_workers=20) as executor:
                # Wrap save_image in a lambda to pass the static directory argument
                list(tqdm(
                    executor.map(lambda art: save_image(art, CNBC_IMAGE_DIR), master_articles), 
                    total=len(master_articles), 
                    desc="Downloading all images"
                ))

            # 3. Save JSON
            json_path = 'cnbc_articles_2000.json'
            convert_to_json(master_articles, output_file=json_path)
            print(f"\nProcess complete! Data saved to {json_path} and images saved to {CNBC_IMAGE_DIR}/")

