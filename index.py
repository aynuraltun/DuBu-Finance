import feedparser
import requests
from flask import Flask, render_template, jsonify, request, redirect, session, flash
import re
import yfinance as yf
from bs4 import BeautifulSoup
import sqlite3
import os

# Uygulama nesnesini Vercel'in beklentisi doğrultusunda 'app' adıyla tanımlıyoruz
app = Flask(__name__)
app.secret_key = 'dubu_finance_ultra_safe_2026'

# ---------- STORAGE (Vercel fix) ----------
DB_FILE = '/tmp/users.db' if os.environ.get('VERCEL') else 'users.db'

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

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
        "endeks": "BİST 100 / Yıldız Pazar", "description": "Teknoloji sektöründe teknolojik altyapının modernize edilmesi amacıyla halka arz edilen şirketin detaylı teknik verileri."
    }
    return render_template('halkaarz_detay.html', ipo=ipo_data)

# ---------- SCREENER API ----------
@app.route('/api/screener')
def api_screener():
    try:
        url = "https://scanner.tradingview.com/turkey/scan"
        payload = {"columns":["name","close","change","volume"],"sort":{"sortBy":"volume","sortOrder":"desc"},"range":[0,100],"filter":[{"left":"exchange","operation":"equal","right":"BIST"}]}
        r = requests.post(url, json=payload, timeout=3)
        if r.status_code == 200:
            return jsonify(r.json())
    except: pass
    
    # Fast fallback
    SYMBOLS = ["THYAO","ASELS","GARAN","AKBNK","SISE","EREGL","SASA","BIMAS","KCHOL","SAHOL"]
    fallback = []
    for s in SYMBOLS:
        fallback.append({"s": "BIST:"+s, "d": [s, 0, 0, 0, s]})
    return jsonify({"data": fallback})

@app.route('/api/metals')
def api_metals():
    return jsonify([
        {"symbol": "GOLD", "name": "Ons Altın", "price": 2345.10, "change": 1.25},
        {"symbol": "SILVER", "name": "Gümüş", "price": 27.60, "change": 2.10},
        {"symbol": "GRAM", "name": "Gram Altın", "price": 2435.50, "change": 1.15},
        {"symbol": "CEYREK", "name": "Çeyrek Altın", "price": 4065.00, "change": 1.20},
        {"symbol": "PLATINUM", "name": "Platin", "price": 940.50, "change": -0.40},
        {"symbol": "PALLADIUM", "name": "Paladyum", "price": 1050.00, "change": 0.85}
    ])

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

@app.route('/hisse/<symbol>')
def hisse_detay(symbol):
    # Dummy technical details for fast rendering
    details = {
        "symbol": symbol.upper(),
        "price": "145.50 ₺",
        "change": "+2.5%",
        "open": "142.00 ₺",
        "high": "146.20 ₺",
        "low": "141.50 ₺",
        "volume": "15,400,000",
        "market_cap": "85.2 Milyar ₺",
        "desc": f"{symbol.upper()} A.Ş., Türkiye pazarında faaliyet gösteren öncü şirketlerden biridir. Geniş hizmet ağı ve yenilikçi teknoloji yatırımlarıyla sektöründe lider konumdadır."
    }
    return render_template('hisse.html', data=details)

@app.route('/api/news')
def get_news():
    feeds = ['https://www.bloomberght.com/rss/ekonomi','https://tr.investing.com/rss/news_25.rss']
    news = []
    for f in feeds:
        try:
            feed = feedparser.parse(requests.get(f, timeout=2).content) # Hızlı timeout
            for e in feed.entries[:6]:
                news.append({"title":e.title,"description":e.summary[:300],"published":e.get('published','Haber'),"link":e.link})
        except: pass
        
    if not news:
        news = [
            {"title": "Borsa İstanbul'da Rekor Kapanış", "description": "BİST 100 endeksi, teknoloji ve bankacılık hisselerinin öncülüğünde tüm zamanların en yüksek kapanışını gerçekleştirdi. Yatırımcıların yoğun ilgisi gözlendi.", "published": "2 Saat Önce", "link": "/"},
            {"title": "Altın Fiyatlarında Yükseliş Eğilimi Sürüyor", "description": "Küresel piyasalardaki belirsizlikler ve merkez bankalarının faiz kararları sonrasında yatırımcılar güvenli liman altına yönelmeye devam ediyor.", "published": "4 Saat Önce", "link": "/"},
            {"title": "Gümüş Endüstriyel Talebi Artıyor", "description": "Güneş enerjisi panelleri ve elektrikli araç üretimindeki ivme, gümüşe yönelik endüstriyel talebi tarihi zirvesine taşıdı.", "published": "5 Saat Önce", "link": "/"}
        ]
    return jsonify(news)

@app.route('/api/favorites_data')
def api_favorites_data():
    u = session.get('user')
    if not u: return jsonify([])
    conn = get_db(); rows = conn.execute("SELECT symbol FROM favorites WHERE username=?", (u,)).fetchall(); conn.close()
    fav_symbols = [r['symbol'] for r in rows]
    
    # Çok hızlı yüklenmesi için fallback kullanıyoruz (Yfinance timeout beklemez)
    data = []
    for s in fav_symbols:
        data.append({"symbol": s, "price": "GÜNCEL ₺", "change": "+1.00%"})
    return jsonify(data)


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

# ---------- AUTH ROUTES ----------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db()
        user = conn.execute("SELECT id FROM users WHERE username=? AND password=?", (username, password)).fetchone()
        conn.close()
        if user:
            session['user'] = username
            return redirect('/')
        flash("Geçersiz kullanıcı adı veya şifre!")
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db()
        try:
            conn.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
            conn.commit()
            flash("Kayıt başarılı! Lütfen giriş yapın.")
            return redirect('/login')
        except sqlite3.IntegrityError:
            flash("Bu kullanıcı adı zaten alınmış!")
        finally:
            conn.close()
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/')

# Vercel tarafından handler olarak tanınması için 'app' nesnesini export ediyoruz
handler = app

if __name__ == '__main__':
    app.run(port=5001, debug=True)
