import requests
from bs4 import BeautifulSoup
import json

def test_ipo():
    url = "https://halkarz.com/"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.0.0 Safari/537.36'}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, 'html.parser')
        
        arzs = []
        # Usually halkarz.com has articles or divs with specific classes. Let's just find recent articles.
        for ul in soup.find_all('ul', class_='slider-list'):
            for li in ul.find_all('li'):
                title_tag = li.find('h3')
                if title_tag:
                    arzs.append({"title": title_tag.text.strip(), "link": title_tag.find('a')['href'] if title_tag.find('a') else ''})
                    
        # Let's try finding all hrefs to companies
        if not arzs:
            for div in soup.find_all('h1') + soup.find_all('h2') + soup.find_all('h3'):
                if getattr(div, 'text', '') and "A.Ş." in div.text:
                    arzs.append({"title": div.text.strip()})

        print("IPOS:", arzs[:5])
    except Exception as e:
        print("Error:", e)

test_ipo()
