import requests
from bs4 import BeautifulSoup
import sys

url = "https://www.sdxd.edu.cn/detail/202512121125523yri14xwaz2ch4soy4.html"
try:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    r = requests.get(url, headers=headers, timeout=10)
    r.encoding = r.apparent_encoding
    soup = BeautifulSoup(r.text, 'html.parser')
    
    # Find content container
    selectors = [
        {'class_': 'article-2'},
        {'id': 'vsb_content'},
        {'class_': 'v_news_content'},
        {'class_': 'content-box'},
        {'class_': 'bodytext'}
    ]
    
    content_div = None
    for selector in selectors:
        found = soup.find('div', **selector)
        if found:
            content_div = found
            print(f"Found container with selector: {selector}")
            break
            
    if content_div:
        imgs = content_div.find_all('img')
        print(f"Found {len(imgs)} images.")
        for img in imgs:
            print(f"Image src: {img.get('src')}")
    else:
        print("Content container not found.")

except Exception as e:
    print(e)
