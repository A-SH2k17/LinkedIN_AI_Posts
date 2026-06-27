import os
import requests
import json
import re

def clean_title(title):
    """
    This function takes a title string and converts it into a filename-friendly format by replacing spaces with
    underscores and removing special characters

    Args:
        title (str): The title string to be cleaned.
    
    Returns:
        str: A cleaned version of the title suitable for use as a filename.
    """
    cleaned_title = title.lower().replace(' ', '_')
    cleaned_title = re.sub(r'[^a-zA-Z0-9_]', '', cleaned_title)
    return cleaned_title


def save_image(article,IMG_URL,pbar=None):
    """
    This function saves an image from a given URL to a specified filename.

    Args:
        article (dict): A dictionary containing article information, including the title.
    """


    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1"
    }

    if not article['image_url']:
        return  # Skip if there's no image URL
    
    image_filename = os.path.join(IMG_URL, f"{article['title']}.jpg")
    response = requests.get(article['image_url'], headers=headers)
    with open(image_filename, 'wb') as f:
        f.write(response.content)


def convert_to_json(articles, output_file='articles.json'):
    """
    This function appends a list of articles into an existing JSON file.

    Args:
        articles (list): A list of dictionaries, each containing the title, link, and image URL of an article.
        output_file (str): The name of the output JSON file.
    """
    if not os.path.exists(output_file) or os.path.getsize(output_file) == 0:
        with open(output_file, 'w') as f:
            json.dump([], f)

    with open(output_file, 'r+') as f:
        existing_data = json.load(f)
    
        if not isinstance(existing_data, list):
            existing_data = [existing_data]
            
        existing_data.extend(articles)
        f.seek(0)
        json.dump(existing_data, f, indent=4)
        f.truncate()
