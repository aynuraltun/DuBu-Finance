import requests
from bs4 import BeautifulSoup

url = "https://halkarz.com/"
headers = {'User-Agent': 'Mozilla/5.0'}
r = requests.get(url, headers=headers, timeout=10)
soup = BeautifulSoup(r.content, 'html.parser')
cards = soup.select('article')[:5]

for card in cards:
    print(card.get_text(separator=' | ', strip=True))
    print("-----")
