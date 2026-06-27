
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
from utils import clean_title
from tqdm import tqdm

def scrape_ft_page(page):
    """
    This function scrapes a single page of the Financial Times Technology section and returns a list of articles
    with their titles, links, and image URLs.

    Args:
        page (int): The page number to scrape from the Financial Times Technology section.

    Returns:
        list: A list of dictionaries, each containing the title, link, and image URL of an article.
    """
    articles_data = []
    
    try:
        res = requests.get(f'https://www.ft.com/technology?page={page}')
        soup = BeautifulSoup(res.content, 'html.parser')
        
        section_part = soup.select_one('ul[data-stream-list=""]')
        news_article_list = section_part.select('li.o-teaser-collection__item')

        for article in news_article_list:
            title_element = article.select_one('a.js-teaser-heading-link')
            title = title_element.get_text(strip=True) if title_element else None
            if not title:
                continue  # Skip articles without a title

            cleaned_title = clean_title(title)

            link = title_element['href'] 
            
            image_element = article.select_one('img.o-teaser__image')
            image_url = image_element["data-src"] 

            summary_element = article.select_one('p.o-teaser__standfirst')
            summary = summary_element.get_text(strip=True) if summary_element else None
            
            articles_data.append({
                'title': cleaned_title,
                'link': link,
                'image_url': image_url,
                'summary': summary
            })
    except Exception as e:
        print(f"An error occurred while scraping page {page}: {e}")

    return articles_data


def scrape_ft_technology_articles(pages_to_scrape=1):
    """
    This function scrapes the Financial Times Technology section and returns a 
    list of articles
    with their titles, links, and image URLs.

    Args:
        pages_to_scrape (int): The number of pages to scrape from the Financial Times Technology section.

    Returns:
        list: A list of dictionaries, each containing the title, link, and image URL of
        an article.
    """
    articles_data = []
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(scrape_ft_page, page) for page in range(1, pages_to_scrape + 1)]
        for f in tqdm(futures, desc="Scraping pages"):
            try:
                articles_data.extend(f.result())
            except Exception as e:
                print(f"Error scraping a page: {e}")
    return articles_data