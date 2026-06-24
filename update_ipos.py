import sqlite3
import requests
from bs4 import BeautifulSoup
import time

def ddg_search(query):
    try:
        url = "https://html.duckduckgo.com/html/"
        headers = {'User-Agent': 'Mozilla/5.0'}
        data = {'q': query + ' ne iş yapar şirket'}
        r = requests.post(url, headers=headers, data=data, timeout=5)
        soup = BeautifulSoup(r.text, 'html.parser')
        res = soup.find('a', class_='result__snippet')
        if res:
            return res.text.strip()
    except Exception as e:
        print("Error:", e)
        pass
    return ""

conn = sqlite3.connect('users.db')
cursor = conn.cursor()
cursor.execute("SELECT id, title, description FROM ipo_library WHERE description NOT LIKE '%Web Arama Özeti%'")
rows = cursor.fetchall()
for row in rows:
    id, title, desc = row
    web_info = ddg_search(title)
    if web_info:
        new_desc = desc + "\n\nWeb Arama Özeti: " + web_info
        conn.execute("UPDATE ipo_library SET description = ? WHERE id = ?", (new_desc, id))
        print(f"Updated {title}")
    time.sleep(0.5)
conn.commit()
conn.close()
