import requests
from bs4 import BeautifulSoup

def test_scrape():
    url = "https://halkarz.com/"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    r = requests.get(url, headers=headers, timeout=10)
    print("Status:", r.status_code)
    soup = BeautifulSoup(r.content, 'html.parser')
    
    articles = soup.select('article')
    print("Found articles:", len(articles))
    for idx, art in enumerate(articles[:10]):
        title_el = art.select_one('h3') or art.select_one('.entry-title')
        title = title_el.get_text(strip=True) if title_el else "No Title"
        
        # Check classes and structure
        classes = art.get('class', [])
        
        # Try to find date or status
        date_el = art.select_one('.halka-arz-tarih') or art.select_one('time')
        date_text = date_el.get_text(strip=True) if date_el else "No Date"
        
        # Try to find badges or status texts
        badge_el = art.select_one('.halka-arz-durum') or art.select_one('.badge') or art.select_one('.status')
        badge_text = badge_el.get_text(strip=True) if badge_el else "No Badge"
        
        print(f"[{idx}] {title} | Date: {date_text} | Badge: {badge_text} | Classes: {classes}")
        # Let's print some inner html to see classes or tags
        # print(art.prettify()[:500])
        print("-" * 50)

if __name__ == "__main__":
    test_scrape()
