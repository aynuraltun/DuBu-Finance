import feedparser
import requests
from flask import Flask, render_template, jsonify, request, redirect, session, flash
import re
import yfinance as yf
from bs4 import BeautifulSoup
import sqlite3
import os

app = Flask(__name__)
app.secret_key = 'dubu_finance_ipo_master_2026'

# ---------- STORAGE (Vercel fix) ----------
DB_FILE = '/tmp/users.db' if os.environ.get('VERCEL') else 'users.db'

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

# Veritabanını uygulama ayağa kalktıktan sonra, ilk istekte başlatıyoruz
# Bu sayede Vercel sunucusu başlatılırken (import aşamasında) çökmez.
@app.before_request
def initial_setup():
    if not os.path.exists(DB_FILE):
        conn = get_db()
        conn.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS favorites (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL, symbol TEXT NOT NULL, UNIQUE(username, symbol))")
        conn.commit()
        conn.close()

# ---------- HALKARZ.COM SCRAPER ----------
def get_ipo_list():
    try:
        url = "https://halkarz.com/"
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(r.content, 'html.parser')
        items = []
        cards = soup.select('article')[:10]
        for card in cards:
            title_el = card.select_one('h3') or card.select_one('.entry-title')
            if not title_el: continue
            title = title_el.get_text(strip=True)
            slug = title.lower().replace(" ","-").replace(".","").replace("aş","").strip()
            date_el = card.select_one('.halka-arz-tarih') or card.select_one('time')
            items.append({
                "title": title, "date": date_el.get_text(strip=True) if date_el else "Yakında", "slug": slug
            })
        return items
    except:
        return [{"title": "Gündem Teknoloji A.Ş.", "date": "10-12 Nisan", "slug": "gundem-tek"}]

@app.route('/api/halkaarz')
def api_halkaarz(): return jsonify(get_ipo_list())

@app.route('/halkaarz/<slug>')
def halkaarz_detay(slug):
    ipo_data = {
        "title": slug.replace("-"," ").title() + " A.Ş.", "fiyat": "₺ 21,10", "tarih": "01 - 03 Nisan",
        "lot": "176.000.000 Lot", "buyukluk": "₺ 3.713.600.000", "yontem": "Bireysele Eşit",
        "endeks": "BİST 100 / Yıldız Pazar", "description": "Teknoloji sektöründe yatırımların güçlendirilmesi hedefli halka arz."
    }
    return render_template('halkaarz_detay.html', ipo=ipo_data)

# ---------- ROUTES ----------
@app.route('/')
def index(): return render_template('index.html')
@app.route('/bist100.html')
def bist100(): return render_template('bist100.html')
@app.route('/takip')
def takip(): return render_template('takip.html')
@app.route('/madenler.html')
def madenler(): return render_template('madenler.html')
@app.route('/halkaarz.html')
def halkaarz_page(): return render_template('halkaarz.html')

@app.route('/api/news')
def get_news():
    feeds = ['https://www.bloomberght.com/rss/ekonomi','https://tr.investing.com/rss/news_25.rss']
    news = []
    for f in feeds:
        try:
            feed = feedparser.parse(requests.get(f, timeout=5).content)
            for e in feed.entries[:8]:
                news.append({"title":e.title,"description":e.summary[:300],"published":e.get('published','Haber'),"link":e.link})
        except: pass
    return jsonify(news)

@app.route('/api/user')
def get_user(): return jsonify({"user": session.get('user')})

@app.route('/api/favorites', methods=['GET'])
def get_favorites():
    u = session.get('user')
    if not u: return jsonify({"favorites": []})
    conn = get_db(); rows = conn.execute("SELECT symbol FROM favorites WHERE username=?", (u,)).fetchall(); conn.close()
    return jsonify({"favorites": [r['symbol'] for r in rows]})

@app.route('/api/favorites/<symbol>', methods=['POST', 'DELETE'])
def toggle_fav(symbol):
    u = session.get('user')
    if not u: return jsonify({"error":"Giriş yapın"}), 401
    conn = get_db()
    if request.method == 'POST': conn.execute("INSERT OR IGNORE INTO favorites (username, symbol) VALUES (?,?)",(u,symbol))
    else: conn.execute("DELETE FROM favorites WHERE username=? AND symbol=?",(u,symbol))
    conn.commit(); conn.close()
    return jsonify({"status":"ok"})

# Bu kısım Vercel tarafından kullanılmaz ancak local test için kalabilir
if __name__ == '__main__':
    app.run()
