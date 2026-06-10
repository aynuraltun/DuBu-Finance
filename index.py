# Trigger auto-reload - Altınkaynak Integration
import feedparser
import requests
from flask import Flask, render_template, jsonify, request, redirect, session, flash
from flask_socketio import SocketIO, emit
import threading
import time
import numpy as np
import scipy.optimize as sco
import re
import yfinance as yf
from bs4 import BeautifulSoup
import sqlite3
import os
from metals_provider import MetalsProvider
from funds_provider import FundsProvider

metals_provider = MetalsProvider()
funds_provider = FundsProvider()

# Uygulama nesnesini Vercel'in beklentisi doğrultusunda 'app' adıyla tanımlıyoruz
app = Flask(__name__)
app.secret_key = 'dubu_finance_ultra_safe_2026'
socketio = SocketIO(app, async_mode='threading', cors_allowed_origins="*")

# ---------- YFINANCE THREAD SAFETY LOCK & WRAPPERS ----------
yf_lock = threading.Lock()

_orig_download = yf.download
_orig_Ticker = yf.Ticker

def safe_yf_download(*args, **kwargs):
    with yf_lock:
        return _orig_download(*args, **kwargs)

def safe_yf_ticker(*args, **kwargs):
    with yf_lock:
        return _orig_Ticker(*args, **kwargs)

# Overwrite yfinance globally to ensure thread-safety
yf.download = safe_yf_download
yf.Ticker = safe_yf_ticker

# ---------- CACHES & LOCKS ----------
cached_metals_data = []
metals_lock = threading.Lock()

cached_news_data = []
news_lock = threading.Lock()

cached_ipo_list = []
ipo_lock = threading.Lock()

translated_descriptions_cache = {}
ipo_details_cache = {}

# ---------- TRANSLATION HELPER ----------
def translate_to_turkish(text):
    if not text:
        return ""
    common_english = {'the', 'is', 'and', 'of', 'in', 'to', 'a', 'with', 'for', 'by', 'on', 'at', 'manufacture', 'military', 'systems', 'operates', 'provides', 'segment', 'segments', 'products', 'services'}
    words = set(re.findall(r'[a-zA-Z]+', text.lower()))
    if not words.intersection(common_english):
        return text
    try:
        url = "https://translate.googleapis.com/translate_a/single"
        params = {
            "client": "gtx",
            "sl": "en",
            "tl": "tr",
            "dt": "t",
            "q": text
        }
        r = requests.get(url, params=params, timeout=3)
        if r.status_code == 200:
            result = r.json()
            translated_parts = [part[0] for part in result[0] if part[0]]
            return "".join(translated_parts)
    except Exception as e:
        print(f"Translation error: {e}")
    return text

def get_translated_description(symbol, english_desc):
    if not english_desc:
        return ""
    if symbol in translated_descriptions_cache:
        return translated_descriptions_cache[symbol]
    translated = translate_to_turkish(english_desc)
    translated_descriptions_cache[symbol] = translated
    return translated

# ---------- BACKGROUND UPDATERS ----------
def background_price_stream():
    import random
    while True:
        time.sleep(0.18)  # 4x faster updates!
        updates = {}
        # BIST Stocks
        for sym in ["THYAO", "ASELS", "GARAN", "AKBNK", "SISE", "EREGL", "SASA", "BIMAS", "KCHOL", "SAHOL", "XU100"]:
            direction = random.choice([1, -1])
            pct_change = random.uniform(0.0001, 0.0005)
            updates[sym] = {"direction": direction, "pct": pct_change}
        # Metals
        for sym in ["GOLD", "SILVER", "PLATINUM", "PALLADIUM", "GRAM", "CEYREK", "YARIM"]:
            direction = random.choice([1, -1])
            pct_change = random.uniform(0.0001, 0.0004)
            updates[sym] = {"direction": direction, "pct": pct_change}
        # Currencies
        for sym in ["USDTRY", "EURTRY", "GBPTRY"]:
            direction = random.choice([1, -1])
            pct_change = random.uniform(0.00005, 0.0002)
            updates[sym] = {"direction": direction, "pct": pct_change}
            
        socketio.emit('price_update', updates)

def background_metals_updater():
    global cached_metals_data
    mp = MetalsProvider()
    while True:
        try:
            data = mp.fetch_data()
            if data:
                with metals_lock:
                    cached_metals_data = data
        except Exception as e:
            print(f"Error in background metals fetch: {e}")
        time.sleep(3.75)

def background_news_updater():
    global cached_news_data
    from textblob import TextBlob
    detailed_suffix = (
        "<br><br><b>Piyasa Analizi ve Gelecek Projeksiyonları:</b><br>"
        "Uzmanlar, piyasadaki mevcut makroekonomik dalgalanmaların ve global merkez bankalarının faiz politikalarının "
        "enstrümanlar üzerindeki baskısını sürdüreceğini öngörüyor. Gerek arz-talep zincirindeki yapısal kırılmalar, gerekse "
        "jeopolitik gerilimlerin yol açtığı risk iştahındaki dalgalanmalar, yatırımcıların kısa vadeli stratejilerini "
        "doğrudan şekillendiriyor.<br><br>"
        "Öte yandan enflasyon beklentilerindeki katılık ve büyüme verilerinde yaşanan sürprizler, para politikası "
        "yapıcılarının adımlarını daha da karmaşık hale getiriyor. Piyasalar, önümüzdeki çeyrekte açıklanacak olan "
        "şirket kârlılık rasyoları ve makro veriler rehberliğinde yön arayışını sürdürecek."
    )
    feeds = [
        'https://www.bloomberght.com/rss/ekonomi',
        'https://www.bloomberght.com/rss',
        'https://tr.investing.com/rss/news_25.rss',
        'https://tr.investing.com/rss/news_28.rss',
        'https://tr.investing.com/rss/news_1.rss'
    ]
    
    financial_keywords = [
        'borsa', 'hisse', 'piyasa', 'endeks', 'faiz', 'merkez bankası', 'enflasyon', 'tcmb', 'fed', 
        'altın', 'dolar', 'euro', 'sterlin', 'şirket', 'temettü', 'bilanço', 'halka arz', 'tahvil', 
        'kap ', 'fon ', 'yatırım', 'emtia', 'petrol', 'sanayi', 'bankacılık', 'bist', 'xu100'
    ]
    
    while True:
        temp_news = []
        for f in feeds:
            try:
                feed = feedparser.parse(requests.get(f, timeout=3).content)
                for e in feed.entries[:15]:
                    title_lower = e.title.lower()
                    summary = e.get('summary', '') or e.get('description', '')
                    summary_lower = summary.lower()
                    
                    # Strictly filter for stock/financial news
                    is_financial = any(kw in title_lower or kw in summary_lower for kw in financial_keywords)
                    if not is_financial:
                        continue
                        
                    try:
                        blob = TextBlob(e.title)
                        polarity = blob.sentiment.polarity
                    except:
                        polarity = 0.0
                    if polarity == 0.0:
                        val = hash(e.title) % 100
                        polarity = (val - 50) / 50.0
                    sentiment_score = int(abs(polarity) * 100)
                    if sentiment_score < 30: sentiment_score += 40
                    if sentiment_score > 99: sentiment_score = 99
                    if polarity > 0.1:
                        sentiment_color = "#10b981"
                        sentiment_text = f"AI Analizi: Pozitif Etki Beklentisi (%{sentiment_score})"
                        icon = "📈"
                    elif polarity < -0.1:
                        sentiment_color = "#ef4444"
                        sentiment_text = f"AI Analizi: Negatif Etki Beklentisi (%{sentiment_score})"
                        icon = "📉"
                    else:
                        sentiment_color = "#64748b"
                        sentiment_text = f"AI Analizi: Nötr Etki Beklentisi (%{sentiment_score})"
                        icon = "📊"
                        
                    full_text = summary[:400] + "..." + detailed_suffix
                    temp_news.append({
                        "title": e.title,
                        "description": full_text,
                        "published": e.get('published', 'Yeni Haber'),
                        "sentiment_text": sentiment_text,
                        "sentiment_color": sentiment_color,
                        "sentiment_icon": icon
                    })
            except Exception as ex:
                print(f"Error reading feed {f}: {ex}")
        if temp_news:
            with news_lock:
                cached_news_data = temp_news[:35]
        time.sleep(15)

def is_draft_ipo(fiyat, date_text):
    f_clean = (fiyat or "").strip().lower()
    d_clean = (date_text or "").strip().lower()
    invalid_keywords = [
        "bilinmiyor", "açıklanmadı", "belirlenmedi", "belli değil", "belli degil",
        "yok", "belirsiz", "açıklanacak", "bekleniyor", "hazırlanıyor", "hazirlaniyor",
        "yakında", "yakinda", "taslak"
    ]
    is_fiyat_invalid = any(kw in f_clean for kw in invalid_keywords) or not f_clean
    is_date_invalid = any(kw in d_clean for kw in invalid_keywords) or not d_clean
    return is_fiyat_invalid or is_date_invalid

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
    except:
        pass
    return ""

def get_ipo_detail_live(slug):
    url = f"https://halkarz.com/{slug}/"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        r = requests.get(url, headers=headers, timeout=5)
        if r.status_code == 200:
            soup = BeautifulSoup(r.content, 'html.parser')
            title_el = soup.select_one('h1.entry-title') or soup.select_one('h1')
            title = title_el.get_text(strip=True) if title_el else slug.replace("-", " ").title() + " A.Ş."
            tarih = "Açıklanmadı"
            fiyat = "Bilinmiyor"
            lot = "Bilinmiyor"
            buyukluk = "Bilinmiyor"
            yontem = "Eşit Dağıtım"
            endeks = "BİST 100 / Yıldız Pazar"
            rows = soup.select('table tr')
            for row in rows:
                tds = row.find_all(['td', 'th'])
                if len(tds) >= 2:
                    k = tds[0].get_text(strip=True)
                    v = tds[1].get_text(strip=True)
                    k_lower = k.lower()
                    if 'tarih' in k_lower:
                        tarih = v
                    elif 'fiyat' in k_lower:
                        fiyat = v
                    elif 'lot' in k_lower or 'pay' in k_lower:
                        lot = v
                    elif 'büyüklük' in k_lower or 'buyukluk' in k_lower:
                        buyukluk = v
                    elif 'yöntem' in k_lower or 'yontem' in k_lower:
                        yontem = v
                    elif 'pazar' in k_lower or 'endeks' in k_lower:
                        endeks = v
            desc_el = soup.select_one('.entry-content p')
            description = desc_el.get_text(strip=True) if desc_el else f"{title} şirketinin halka arz detayları ve talep toplama bilgileri."
            
            web_info = ddg_search(title)
            if web_info:
                description += f"\n\nWeb Arama Özeti: {web_info}"
                
            return {
                "title": title,
                "fiyat": fiyat,
                "tarih": tarih,
                "lot": lot,
                "buyukluk": buyukluk,
                "yontem": yontem,
                "endeks": endeks,
                "description": description
            }
    except Exception as e:
        print(f"Error scraping detail live: {e}")
    
    title = slug.replace("-", " ").title() + " A.Ş."
    return {
        "title": title,
        "fiyat": "Bilinmiyor",
        "tarih": "Açıklanmadı",
        "lot": "Açıklanmadı",
        "buyukluk": "Açıklanmadı",
        "yontem": "Bireysele Eşit",
        "endeks": "BİST / Yıldız Pazar",
        "description": f"{title} şirketinin halka arz talep toplama tarihleri ve detayları yakında açıklanacaktır."
    }

def sync_ipos_to_db():
    try:
        from datetime import datetime
        url = "https://halkarz.com/"
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, headers=headers, timeout=5)
        if r.status_code != 200:
            print(f"Failed to fetch halkaarz.com homepage for sync: {r.status_code}")
            return
            
        soup = BeautifulSoup(r.content, 'html.parser')
        cards = soup.select('article')[:30]
        
        for card in cards:
            title_el = card.select_one('h3') or card.select_one('.entry-title')
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            
            link_el = card.select_one('a')
            if not link_el:
                continue
            href = link_el.get('href', '')
            slug = href.strip('/').split('/')[-1]
            
            date_el = card.select_one('.il-halka-arz-tarihi') or card.select_one('.halka-arz-tarih') or card.select_one('time')
            date_text = date_el.get_text(strip=True) if date_el else "Yakında"
            
            # Check if slug exists in DB and is not a draft
            conn = get_db()
            row = conn.execute("SELECT fiyat, date_text FROM ipo_library WHERE slug = ?", (slug,)).fetchone()
            conn.close()
            
            if row:
                existing_fiyat = row["fiyat"]
                existing_date = row["date_text"]
                if not is_draft_ipo(existing_fiyat, existing_date):
                    # It's already in DB and it's valid, skip detail scraping!
                    continue
            
            # Scrape detail page (it is either missing or was a draft previously)
            print(f"Scraping detail page for new/draft IPO: {slug}")
            detail = get_ipo_detail_live(slug)
            if not detail:
                continue
                
            # Insert or replace in DB
            conn = get_db()
            conn.execute("""
                INSERT OR REPLACE INTO ipo_library 
                (slug, title, date_text, fiyat, lot, buyukluk, yontem, endeks, description, scraped_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                slug,
                detail["title"],
                detail["tarih"],
                detail["fiyat"],
                detail["lot"],
                detail["buyukluk"],
                detail["yontem"],
                detail["endeks"],
                detail["description"],
                datetime.now().isoformat()
            ))
            conn.commit()
            conn.close()
            
            # Polite sleep to avoid rate limiting
            time.sleep(1)
            
    except Exception as e:
        print(f"Error in sync_ipos_to_db: {e}")

def background_ipo_updater():
    global cached_ipo_list
    # Wait a bit on start to let the app initialize and define all names
    time.sleep(5)
    try:
        initial_setup()
    except Exception as e:
        print(f"Error calling initial_setup in thread: {e}")
        
    while True:
        try:
            from datetime import datetime
            today_str = datetime.now().date().isoformat()
            
            # Check last sync date
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM settings WHERE key = 'last_ipo_sync'")
            row = cursor.fetchone()
            last_sync = row[0] if row else None
            
            cursor.execute("SELECT COUNT(*) FROM ipo_library")
            db_count = cursor.fetchone()[0]
            conn.close()
            
            # If not synced today OR database is empty, sync
            if last_sync != today_str or db_count == 0:
                print("Running daily IPO database sync...")
                sync_ipos_to_db()
                
                # Update last sync date
                conn = get_db()
                conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('last_ipo_sync', ?)", (today_str,))
                conn.commit()
                conn.close()
                print("Daily IPO sync complete.")
                
            # Load list from database into cached_ipo_list
            data = get_ipo_list()
            with ipo_lock:
                cached_ipo_list = data
                
        except Exception as e:
            print(f"Error in background_ipo_updater: {e}")
            
        time.sleep(60)

threading.Thread(target=background_price_stream, daemon=True).start()
threading.Thread(target=background_metals_updater, daemon=True).start()
threading.Thread(target=background_news_updater, daemon=True).start()
threading.Thread(target=background_ipo_updater, daemon=True).start()


# ---------- STORAGE (Vercel fix) ----------
DB_FILE = '/tmp/users.db' if os.environ.get('VERCEL') else 'users.db'

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

@app.before_request
def initial_setup():
    conn = get_db()
    conn.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT)")
    conn.execute("CREATE TABLE IF NOT EXISTS favorites (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL, symbol TEXT NOT NULL, UNIQUE(username, symbol))")
    conn.execute("CREATE TABLE IF NOT EXISTS portfolio (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL, symbol TEXT NOT NULL, amount REAL NOT NULL, buy_price REAL NOT NULL)")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ipo_library (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            slug TEXT UNIQUE,
            title TEXT,
            date_text TEXT,
            fiyat TEXT,
            lot TEXT,
            buyukluk TEXT,
            yontem TEXT,
            endeks TEXT,
            description TEXT,
            scraped_at TEXT
        )
    """)
    conn.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT UNIQUE, value TEXT)")
    # Multi-portfolio support
    conn.execute("CREATE TABLE IF NOT EXISTS portfolios (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL, name TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP)")
    # Add portfolio_id column to portfolio table if not exists
    try:
        conn.execute("ALTER TABLE portfolio ADD COLUMN portfolio_id INTEGER DEFAULT NULL")
    except Exception:
        pass  # Column already exists
    # Migrate existing data: assign orphan rows to a default portfolio
    orphan_users = conn.execute("SELECT DISTINCT username FROM portfolio WHERE portfolio_id IS NULL").fetchall()
    for row in orphan_users:
        uname = row['username']
        existing = conn.execute("SELECT id FROM portfolios WHERE username=? AND name=?", (uname, 'Varsayılan Portföy')).fetchone()
        if not existing:
            conn.execute("INSERT INTO portfolios (username, name) VALUES (?,?)", (uname, 'Varsayılan Portföy'))
        pid = conn.execute("SELECT id FROM portfolios WHERE username=? AND name=?", (uname, 'Varsayılan Portföy')).fetchone()['id']
        conn.execute("UPDATE portfolio SET portfolio_id=? WHERE username=? AND portfolio_id IS NULL", (pid, uname))
    conn.commit()
    conn.close()

# ---------- ANTIGRAVITY AI CACHE ----------
antgravity_cache = {}  # {symbol: {data: {...}, ts: timestamp}}

# ---------- HALKARZ.COM SCRAPER ----------
def parse_ipo_date(date_str):
    if not date_str:
        return None
    from datetime import datetime
    import re
    
    date_str = date_str.lower().strip()
    if 'yakında' in date_str:
        return None  # Future
        
    months = {
        'ocak': 1, 'subat': 2, 'şubat': 2, 'mart': 3, 'nisan': 4, 'mayis': 5, 'mayıs': 5,
        'haziran': 6, 'temmuz': 7, 'agustos': 8, 'ağustos': 8, 'eylul': 9, 'eylül': 9,
        'ekim': 10, 'kasim': 11, 'kasım': 11, 'aralik': 12, 'aralık': 12
    }
    
    year_match = re.search(r'20\d{2}', date_str)
    year = int(year_match.group(0)) if year_match else datetime.now().year
    
    found_month = None
    found_month_idx = -1
    for m_name, m_val in months.items():
        if m_name in date_str:
            idx = date_str.rfind(m_name)
            if idx > found_month_idx:
                found_month_idx = idx
                found_month = m_val
                
    if not found_month:
        return None
        
    part_for_days = date_str.replace(str(year), '')
    day_numbers = re.findall(r'\d+', part_for_days)
    if not day_numbers:
        return None
        
    day = int(day_numbers[-1])
    try:
        return datetime(year, found_month, day)
    except:
        return None

def get_ipo_list():
    try:
        from datetime import datetime, timedelta
        conn = get_db()
        rows = conn.execute("SELECT title, date_text, fiyat, slug FROM ipo_library ORDER BY id DESC LIMIT 100").fetchall()
        conn.close()
        
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        cutoff_date = today - timedelta(days=180)
        
        items = []
        for r in rows:
            fiyat = r["fiyat"]
            date_text = r["date_text"]
            parsed_date = parse_ipo_date(date_text)
            if parsed_date and parsed_date < cutoff_date:
                # Skip past IPOs that are older than 180 days
                continue
            items.append({
                "title": r["title"],
                "date": date_text,
                "fiyat": fiyat,
                "slug": r["slug"],
                "_parsed_date": parsed_date
            })
        
        def sort_key(item):
            d = item.get("_parsed_date")
            if d is None:
                return datetime(2100, 1, 1)
            return d
            
        items.sort(key=sort_key, reverse=True)
        
        for item in items:
            item.pop("_parsed_date", None)
            
        return items[:30]
    except Exception as e:
        print(f"Error in get_ipo_list: {e}")
        return []

def get_ipo_detail(slug):
    # Check DB first
    try:
        conn = get_db()
        row = conn.execute("SELECT * FROM ipo_library WHERE slug = ?", (slug,)).fetchone()
        conn.close()
        if row:
            return {
                "title": row["title"],
                "fiyat": row["fiyat"],
                "tarih": row["date_text"],
                "lot": row["lot"],
                "buyukluk": row["buyukluk"],
                "yontem": row["yontem"],
                "endeks": row["endeks"],
                "description": row["description"]
            }
    except Exception as e:
        print(f"Error checking DB for details: {e}")
        
    # If not found, scrape it live and write to DB
    detail = get_ipo_detail_live(slug)
    if detail:
        from datetime import datetime
        try:
            conn = get_db()
            conn.execute("""
                INSERT OR REPLACE INTO ipo_library 
                (slug, title, date_text, fiyat, lot, buyukluk, yontem, endeks, description, scraped_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                slug,
                detail["title"],
                detail["tarih"],
                detail["fiyat"],
                detail["lot"],
                detail["buyukluk"],
                detail["yontem"],
                detail["endeks"],
                detail["description"],
                datetime.now().isoformat()
            ))
            conn.commit()
            conn.close()
        except Exception as db_err:
            print(f"Error saving detail to DB: {db_err}")
    return detail

@app.route('/api/halkaarz')
def api_halkaarz():
    global cached_ipo_list
    with ipo_lock:
        if cached_ipo_list:
            return jsonify(cached_ipo_list)
    # If cache is empty, load from DB directly
    try:
        data = get_ipo_list()
        if data:
            with ipo_lock:
                cached_ipo_list = data
            return jsonify(data)
    except Exception as e:
        print(f"Error serving api_halkaarz direct query: {e}")
    return jsonify([])

@app.route('/halkaarz/<slug>')
def halkaarz_detay(slug):
    ipo_data = get_ipo_detail(slug)
    return render_template('halkaarz_detay.html', ipo=ipo_data)

# ---------- SCREENER API ----------
@app.route('/api/screener')
def api_screener():
    try:
        url = "https://scanner.tradingview.com/turkey/scan"
        payload = {
            "columns":["description","close","change","volume"],
            "sort":{"sortBy":"volume","sortOrder":"desc"},
            "range":[0,100],
            "filter":[{"left":"exchange","operation":"equal","right":"BIST"}]
        }
        r = requests.post(url, json=payload, timeout=3)
        if r.status_code == 200:
            return jsonify(r.json())
    except: pass
    
    # Fast fallback
    SYMBOLS = ["THYAO","ASELS","GARAN","AKBNK","SISE","EREGL","SASA","BIMAS","KCHOL","SAHOL"]
    fallback = []
    for s in SYMBOLS:
        # fallback: Name, price, change, volume
        fallback.append({"s": "BIST:"+s, "d": [s + " A.S.", 0, 0, 0]})
    return jsonify({"data": fallback})

@app.route('/api/metals')
def api_metals():
    with metals_lock:
        if cached_metals_data:
            return jsonify(cached_metals_data)
    mp = MetalsProvider()
    return jsonify(mp.fetch_data())

# ---------- ROUTES ----------
@app.route('/')
def index(): return render_template('index.html')
@app.route('/bist100.html')
def bist100(): return render_template('bist100.html')

@app.route('/fonlar')
def fonlar():
    return render_template('fonlar.html')

@app.route('/fon/<symbol>')
def fon_detay(symbol):
    raw_data = funds_provider.get_fund_detail(symbol)
    if not raw_data:
        return redirect('/fonlar')
    
    price = raw_data["price"]
    change = raw_data["change"]
    prev_close = price / (1 + change/100) if change != -100 else price
    
    data = {
        "symbol": raw_data["symbol"],
        "name": raw_data["name"],
        "price": f"{price:,.2f} ₺",
        "change": f"{'+' if change >= 0 else ''}{change:.2f}%",
        "open": f"{price * 0.993:,.2f} ₺",
        "high": f"{price * 1.011:,.2f} ₺",
        "low": f"{price * 0.987:,.2f} ₺",
        "prev_close": f"{prev_close:,.2f} ₺",
        "volume": f"{int(price * 1250):,}",
        "market_cap": "TEFAS Portföyü",
        "pe": "-",
        "allocation": raw_data["allocation"],
        "change_val": float(change)
    }
    return render_template('fon_detay.html', data=data)

@app.route('/api/funds')
def api_funds():
    data = funds_provider.get_funds_list()
    return jsonify(data)

@app.route('/api/funds/<symbol>')
def api_fund_detail(symbol):
    data = funds_provider.get_fund_detail(symbol)
    return jsonify(data)
@app.route('/takip')
def takip(): return render_template('takip.html')
@app.route('/madenler.html')
def madenler(): return render_template('madenler.html')
@app.route('/halkaarz.html')
def halkaarz_page(): return render_template('halkaarz.html')

@app.route('/hisse/<symbol>')
def hisse_detay(symbol):
    sym = symbol.upper()
    try:
        t = yf.Ticker(sym + ".IS")
        info = t.info
        name = info.get('longName', sym + ' A.Ş.')
        price = info.get('currentPrice') or info.get('regularMarketPrice') or 0
        prev = info.get('previousClose') or info.get('regularMarketPreviousClose') or 1
        change = ((price - prev) / prev) * 100 if prev else 0
        
        details = {
            "symbol": sym,
            "name": name,
            "price": f"{price:,.2f} ₺",
            "change": f"{'+' if change >= 0 else ''}{change:.2f}%",
            "open": f"{info.get('open', 0):,.2f} ₺",
            "high": f"{info.get('dayHigh', 0):,.2f} ₺",
            "low": f"{info.get('dayLow', 0):,.2f} ₺",
            "prev_close": f"{prev:,.2f} ₺",
            "volume": f"{info.get('volume', 0):,}",
            "market_cap": f"{info.get('marketCap', 0) / 1e9:.1f} Milyar ₺",
            "pe": f"{info.get('trailingPE', 0):.2f}" if info.get('trailingPE') else "-",
            "desc": get_translated_description(sym, info.get('longBusinessSummary', f"{name}, Türkiye pazarında faaliyet gösteren öncü şirketlerden biridir.")),
            "change_val": float(change)
        }
    except:
        details = {
            "symbol": sym, "name": sym + " A.Ş.", "price": "Giriş Yapılmadı", "change": "0.00%",
            "open": "-", "high": "-", "low": "-", "prev_close": "-", "volume": "-", "market_cap": "-", "pe": "-",
            "desc": "Şirket bilgisi şu an yüklenemiyor.", "change_val": 0.0
        }
    return render_template('hisse.html', data=details)

@app.route('/api/news')
def get_news():
    with news_lock:
        if cached_news_data:
            return jsonify(cached_news_data)
    # Fast Fallback
    detailed_suffix = "<br><br><b>Piyasa Analizi ve Gelecek Projeksiyonları:</b>..."
    news = [
        {"title": "Borsa İstanbul'da Rekor Kapanış ve Yeni Hedefler", "description": "BİST 100 endeksi tüm zamanların en yüksek kapanışını gerçekleştirdi..." + detailed_suffix, "published": "2 Saat Önce", "sentiment_text": "Bu haber piyasayı %85 ihtimalle olumlu etkileyebilir.", "sentiment_color": "#10b981", "sentiment_icon": "⚡"},
        {"title": "Altın Fiyatlarında Yükseliş Eğilimi Sürüyor", "description": "Küresel piyasalardaki belirsizlikler ve merkez bankalarının faiz kararları sonrasında..." + detailed_suffix, "published": "4 Saat Önce", "sentiment_text": "Bu haber piyasayı %72 ihtimalle olumlu etkileyebilir.", "sentiment_color": "#10b981", "sentiment_icon": "⚡"},
        {"title": "Gümüş Endüstriyel Talebi Artıyor", "description": "Güneş enerjisi panelleri ve elektrikli araç üretimindeki ivme, gümüşe yönelik talebi..." + detailed_suffix, "published": "5 Saat Önce", "sentiment_text": "Bu haberin piyasa etkisi %40 ihtimalle yatay kalacaktır.", "sentiment_color": "#64748b", "sentiment_icon": "⚖️"}
    ]
    return jsonify(news)

@app.route('/api/favorites_data')
def api_favorites_data():
    u = session.get('user')
    if not u: return jsonify([])
    conn = get_db(); rows = conn.execute("SELECT symbol FROM favorites WHERE username=?", (u,)).fetchall(); conn.close()
    fav_symbols = [r['symbol'] for r in rows]
    
    data = []
    for s in fav_symbols:
        try:
            ticker = s + ".IS" if ".IS" not in s else s
            t = yf.Ticker(ticker)
            info = t.info
            price = info.get('currentPrice') or info.get('regularMarketPrice') or 0
            prev = info.get('previousClose') or 1
            change = ((price - prev) / prev) * 100
            data.append({"symbol": s, "price": f"{price:,.2f} ₺", "change": f"{change:+.2f}%"})
        except:
            data.append({"symbol": s, "price": "Hata", "change": "0.00%"})
    return jsonify(data)


@app.route('/api/sentiment/<symbol>')
def api_stock_sentiment(symbol):
    import json as _json
    try:
        # Check Antigravity cache (1 hour TTL)
        cache_key = symbol.upper()
        if cache_key in antgravity_cache:
            cached = antgravity_cache[cache_key]
            if time.time() - cached['ts'] < 3600:
                return jsonify(cached['data'])
        
        ticker_sym = symbol + ".IS" if symbol.isalpha() else symbol
        t = yf.Ticker(ticker_sym)
        info = t.info or {}
        
        # Gather financial ratios for Antigravity prompt
        pe_ratio = info.get('trailingPE', info.get('forwardPE', 'N/A'))
        pb_ratio = info.get('priceToBook', 'N/A')
        current_ratio = info.get('currentRatio', 'N/A')
        debt_equity = info.get('debtToEquity', 'N/A')
        revenue_growth = info.get('revenueGrowth', 'N/A')
        earnings_growth = info.get('earningsGrowth', 'N/A')
        profit_margins = info.get('profitMargins', 'N/A')
        sector = info.get('sector', 'N/A')
        industry = info.get('industry', 'N/A')
        market_cap = info.get('marketCap', 'N/A')
        beta = info.get('beta', 'N/A')
        dividend_yield = info.get('dividendYield', 'N/A')
        roe = info.get('returnOnEquity', 'N/A')
        roa = info.get('returnOnAssets', 'N/A')
        free_cashflow = info.get('freeCashflow', 'N/A')
        
        # Momentum data: 52w high/low, 50/200 MA
        fifty_day_avg = info.get('fiftyDayAverage', 'N/A')
        two_hundred_day_avg = info.get('twoHundredDayAverage', 'N/A')
        fifty_two_week_high = info.get('fiftyTwoWeekHigh', 'N/A')
        fifty_two_week_low = info.get('fiftyTwoWeekLow', 'N/A')
        current_price = info.get('currentPrice', info.get('regularMarketPrice', 'N/A'))
        
        ratios_text = f"""Hisse: {symbol}
Sektör: {sector} | Endüstri: {industry}
Piyasa Değeri: {market_cap}
F/K Oranı: {pe_ratio}
PD/DD Oranı: {pb_ratio}
Cari Oran: {current_ratio}
Borç/Özsermaye: {debt_equity}
Gelir Büyümesi (YoY): {revenue_growth}
Kar Büyümesi (YoY): {earnings_growth}
Kar Marjı: {profit_margins}
Beta: {beta}
Temettü Verimi: {dividend_yield}
Özsermaye Karlılığı (ROE): {roe}
Aktif Karlılığı (ROA): {roa}
Serbest Nakit Akışı: {free_cashflow}
Güncel Fiyat: {current_price}
50 Günlük Ortalama: {fifty_day_avg}
200 Günlük Ortalama: {two_hundred_day_avg}
52 Hafta Yüksek: {fifty_two_week_high}
52 Hafta Düşük: {fifty_two_week_low}"""
        
        # Antigravity Prompt
        antigravity_prompt = f"""Sen Dubu Finance uygulamasının "Antigravity" isimli finansal analiz motorusun. Görevin, sana ham verileri ve rasyoları verilen bir hisseyi 5 ana eksende (Yönetim Güveni, Momentum, Büyüme, Borçluluk, Sektör Rüzgarı) 1 ile 10 arasında puanlamaktır.

### KRİTİK KURAL: "ORTALAMA BİASINI" YOK ET
Analiz ettiğin şirketlerin radar grafiklerinde "mükemmel dengeli beşgenler" çıkması finansal gerçekliğe aykırıdır. Bir şirketin büyümesi çok agresifse genellikle borçluluğu kötüdür; momentumu zirvedeyse çarpanları şişmiştir. Güvenli oynamayı bırak, uç değerleri (1-3 ve 8-10 arası) kullanmaktan çekinme. Puanları dağıtırken cimri veya aşırı korumacı olma. Finansal rasyolar ortalamaysa 5 ver, ancak ortalamadan sapan en ufak emarede puanı sert bir şekilde uçlara doğru kaydır.

### EKSEN PUANLAMA METRİKLERİ VE ÖLÇEKLERİ
Her eksende 10 puan "Şirket için EN OLUMLU durum", 1 puan ise "Şirket için EN OLUMSUZ durum" anlamına gelir.

1. Yönetim Güveni (1-10):
- 10: Kurumsal yönetim ilkelerine tam uyum, şeffaf KAP bildirimleri, geri alım programları, profesyonel CEO/Yönetim, yüksek temettü/özsermaye karlılığı vizyonu.
- 1: Aile içi taht kavgaları, manipülasyon şüpheleri, şeffaf olmayan ilişkili taraf işlemleri, yatırımcıyı sürekli mağdur eden bedelli sermaye artırımları.

2. Momentum (1-10):
- 10: Fiyat tüm hareketli ortalamaların (20, 50, 200 HO) üzerinde, RSI aşırı alım bölgesine yakın ama güçlü, işlem hacmi rekor kırıyor, para girişi zirvede.
- 1: Fiyat sürekli dip tazeliyor, 200 günlük ortalamanın çok altında, ölüm kesişmesi (death cross) gerçekleşmiş, hacimsiz ve sürekli para çıkışı var.

3. Büyüme (1-10):
- 10: Satışlar, FAVÖK ve Net Kar yıllık (YoY) ve çeyreklik (QoQ) bazda enflasyonun ve sektör medyanının çok üzerinde (örn: >%50 reel büyüme).
- 1: Kar sürekli eriyor, satış hacmi (adet bazında) düşüyor, şirket küçülme ve pazar payı kaybetme trendinde.

4. Borçluluk Finansal Sağlık (1-10):
*Not: 10 borcun olmaması/çok rahat ödenmesi, 1 ise borç batağı demektir.*
- 10: Net Borç / FAVÖK negatif veya sıfıra yakın, Cari Oran > 2.0, kaldıraç oranı çok düşük, finansman giderleri net karı baskılamıyor.
- 1: Net Borç / FAVÖK > 4.0, Cari Oran < 1.0, yüksek faiz ortamında şirketin tüm karı finansman giderine (faize) gidiyor, borç döndürme krizi var.

5. Sektör Rüzgarı (1-10):
- 10: Makroekonomik ve küresel konjonktür bu sektörü destekliyor (örn: yapay zeka çılgınlığında teknoloji, teşvik alan enerji, ihracat atağındaki sanayi).
- 1: Sektör resesyonda, regülasyon baskısı altında, marjlar daralıyor veya modası geçmiş/doyuma ulaşmış bir pazar (Dying Industry).

### ANALİZ METODOLOJİSİ
1. Sana verilen şirketin rasyolarını kendi içinde değil, SEKTÖR MEDYANI ve BİST ORTALAMALARI ile kıyasla.
2. Eğer bir eksende veri yetersizse veya tam olarak ortalamaysa 5 puan ver. Ama şirket sektöründen iyiye gidiyorsa direkt 8'e, kötüye gidiyorsa direkt 2'ye yuvarla. Çekinme.
3. Çıktıyı sadece ve sadece aşağıdaki JSON formatında ver, ekstra hiçbir metin veya açıklama ekleme.

### VERİLER:
{ratios_text}

Çıktı formatı (SADECE JSON):
{{"yonetim_guveni": X, "momentum": X, "buyume": X, "borcluluk": X, "sektor_ruzgari": X}}"""
        
        # Try Gemini API
        gemini_api_key = os.environ.get('GEMINI_API_KEY', '')
        radar_data = [5, 5, 5, 5, 5]  # Default fallback
        used_antigravity = False
        
        if gemini_api_key:
            try:
                gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={gemini_api_key}"
                gemini_payload = {
                    "contents": [{"parts": [{"text": antigravity_prompt}]}],
                    "generationConfig": {"temperature": 0.3, "maxOutputTokens": 200}
                }
                gemini_resp = requests.post(gemini_url, json=gemini_payload, timeout=15)
                if gemini_resp.status_code == 200:
                    gemini_data = gemini_resp.json()
                    raw_text = gemini_data['candidates'][0]['content']['parts'][0]['text'].strip()
                    # Clean markdown code blocks if present
                    raw_text = raw_text.replace('```json', '').replace('```', '').strip()
                    parsed = _json.loads(raw_text)
                    radar_data = [
                        max(1, min(10, int(parsed.get('yonetim_guveni', 5)))),
                        max(1, min(10, int(parsed.get('momentum', 5)))),
                        max(1, min(10, int(parsed.get('buyume', 5)))),
                        max(1, min(10, int(parsed.get('borcluluk', 5)))),
                        max(1, min(10, int(parsed.get('sektor_ruzgari', 5))))
                    ]
                    used_antigravity = True
            except Exception as ex:
                print(f"Antigravity Gemini error for {symbol}: {ex}")
        
        # If Gemini not available, use heuristic fallback based on real financial data
        if not used_antigravity:
            def safe_float(val, default=0):
                if val in ('N/A', None, ''): return default
                try: return float(val)
                except: return default
                
            try:
                # Momentum heuristic
                cp = safe_float(current_price)
                ma50 = safe_float(fifty_day_avg, cp)
                ma200 = safe_float(two_hundred_day_avg, cp)
                w52h = safe_float(fifty_two_week_high, cp)
                w52l = safe_float(fifty_two_week_low, cp)
                
                momentum = 5
                if cp > 0 and ma50 > 0 and ma200 > 0:
                    if cp > ma50 and cp > ma200: momentum = 8
                    elif cp > ma50: momentum = 7
                    elif cp < ma200: momentum = 3
                    elif cp < ma50 and cp < ma200: momentum = 2
                    # Position within 52w range
                    if w52h > w52l:
                        pos = (cp - w52l) / (w52h - w52l)
                        if pos > 0.85: momentum = min(10, momentum + 1)
                        elif pos < 0.2: momentum = max(1, momentum - 2)
                
                # Growth heuristic
                growth = 5
                rg = safe_float(revenue_growth)
                eg = safe_float(earnings_growth)
                avg_g = (rg + eg) / 2
                if avg_g > 0.5: growth = 9
                elif avg_g > 0.2: growth = 8
                elif avg_g > 0.1: growth = 7
                elif avg_g > 0: growth = 6
                elif avg_g > -0.1: growth = 4
                elif avg_g > -0.3: growth = 3
                else: growth = 2
                
                # Debt heuristic
                debt = 5
                cr = safe_float(current_ratio)
                de = safe_float(debt_equity)
                if cr > 0:
                    if cr > 2.5 and de < 50: debt = 9
                    elif cr > 2.0: debt = 8
                    elif cr > 1.5: debt = 7
                    elif cr > 1.0: debt = 5
                    elif cr > 0.7: debt = 3
                    else: debt = 2
                    if de > 200: debt = max(1, debt - 3)
                    elif de > 100: debt = max(1, debt - 1)
                
                # Management heuristic
                mgmt = 5
                r_roe = safe_float(roe)
                dy = safe_float(dividend_yield)
                if r_roe > 0.3: mgmt = 9
                elif r_roe > 0.2: mgmt = 8
                elif r_roe > 0.1: mgmt = 6
                elif r_roe > 0: mgmt = 5
                else: mgmt = 3
                if dy > 0.05: mgmt = min(10, mgmt + 1)
                
                # Sector wind
                sector_scores = {
                    'Technology': 8, 'Financial Services': 6, 'Energy': 7,
                    'Industrials': 6, 'Basic Materials': 5, 'Consumer Defensive': 7,
                    'Consumer Cyclical': 5, 'Healthcare': 7, 'Real Estate': 4,
                    'Utilities': 5, 'Communication Services': 6
                }
                sector_wind = sector_scores.get(sector, 5)
                
                radar_data = [mgmt, momentum, growth, debt, sector_wind]
            except Exception as e:
                print(f"Heuristic error for {symbol}: {e}")
                radar_data = [5, 5, 5, 5, 5]
        
        # Calculate overall score and sentiment
        avg_score = sum(radar_data) / len(radar_data)
        score = max(1, min(10, round(avg_score)))
        
        if score >= 8:
            sentiment_label = "Güçlü Boğa Sinyali"
            color = "#10b981"
            text = f"Antigravity motoru {symbol} hissesini güçlü bir alım fırsatı olarak değerlendiriyor. Temel rasyolar, momentum ve sektörel rüzgar uyumlu şekilde pozitif sinyal üretiyor."
        elif score >= 6:
            sentiment_label = "Boğa Sinyali"
            color = "#10b981"
            text = f"Antigravity analizi {symbol} için temkinli iyimser. Büyüme ve momentum göstergeleri olumlu, ancak bazı eksenlerde dikkatli olunmalı."
        elif score >= 4:
            sentiment_label = "Nötr / Dengeli Görünüm"
            color = "#f59e0b"
            text = f"Antigravity motoru {symbol} için nötr sinyal üretiyor. Güçlü ve zayıf yönler birbirini dengeliyor, piyasa yön arayışında."
        elif score >= 3:
            sentiment_label = "Ayı Sinyali"
            color = "#ef4444"
            text = f"Antigravity analizi {symbol} için negatif sinyal veriyor. Temel göstergeler ve/veya momentum baskı altında."
        else:
            sentiment_label = "Güçlü Ayı Sinyali"
            color = "#ef4444"
            text = f"Antigravity motoru {symbol} için ciddi risk uyarısı veriyor. Birden fazla eksende kritik zayıflık tespit edildi."
        
        result = {
            "sentiment": sentiment_label,
            "score": score,
            "text": text,
            "color": color,
            "radar_data": radar_data,
            "radar_labels": ["Yönetim Güveni", "Momentum", "Büyüme", "Borçluluk", "Sektör Rüzgarı"],
            "engine": "Antigravity" if used_antigravity else "Heuristic"
        }
        
        # Cache result
        antgravity_cache[cache_key] = {'data': result, 'ts': time.time()}
        
        return jsonify(result)
    except Exception as e:
        print(f"Sentiment API error for {symbol}: {e}")
        return jsonify({
            "sentiment": "Nötr / Dengeli Görünüm",
            "score": 5,
            "text": "Antigravity analiz motoru verilere erişemedi. Varsayılan nötr değerler gösteriliyor.",
            "color": "#f59e0b",
            "radar_data": [5, 5, 5, 5, 5],
            "radar_labels": ["Yönetim Güveni", "Momentum", "Büyüme", "Borçluluk", "Sektör Rüzgarı"],
            "engine": "Fallback"
        })


def get_historical_prices_for_portfolio(symbols, period="1y"):
    import pandas as pd
    import numpy as np
    import datetime
    import hashlib
    import random
    
    # Establish a master index using XU100.IS
    master_hist = yf.download("XU100.IS", period=period, interval="1d", progress=False)
    if master_hist.empty:
        # Fallback if yfinance fails
        master_hist = yf.download("USDTRY=X", period=period, interval="1d", progress=False)
    
    if master_hist.empty:
        raise ValueError("Ortak takvim verisi alınamadı.")
        
    master_index = master_hist.index
    
    df_prices = pd.DataFrame(index=master_index)
    
    for sym in symbols:
        sym_upper = sym.upper()
        is_metal = sym_upper in ['GOLD', 'SILVER', 'PLATINUM', 'PALLADIUM', 'GRAM', 'CEYREK', 'YARIM']
        is_fund = sym_upper in funds_provider.funds.keys()
        
        if sym_upper in ['TRY', 'NAKIT']:
            df_prices[sym_upper] = 1.00
        elif is_fund:
            # Generate deterministic walk aligned with master_index
            base_val = int(hashlib.md5(sym_upper.encode()).hexdigest(), 16) % 900 + 100
            random.seed(sym_upper)
            walk = base_val
            closes = []
            for _ in range(len(master_index)):
                walk *= (1 + random.gauss(0.0008, 0.015))  # slight positive drift
                closes.append(round(walk, 2))
            df_prices[sym_upper] = closes
            
        elif is_metal:
            # Fetch metal ticker and USDTRY
            if sym_upper == 'SILVER': ticker = 'SI=F'
            elif sym_upper == 'PLATINUM': ticker = 'PL=F'
            elif sym_upper == 'PALLADIUM': ticker = 'PA=F'
            else: ticker = 'GC=F'  # GOLD, GRAM, CEYREK, YARIM
            
            m_hist = yf.download(ticker, period=period, interval="1d", progress=False)
            usd_hist = yf.download("USDTRY=X", period=period, interval="1d", progress=False)
            
            # Reindex to master index
            m_series = m_hist['Close']
            if isinstance(m_series, pd.DataFrame): m_series = m_series.iloc[:, 0]
            m_series = m_series.reindex(master_index, method='ffill').bfill()
            
            u_series = usd_hist['Close']
            if isinstance(u_series, pd.DataFrame): u_series = u_series.iloc[:, 0]
            u_series = u_series.reindex(master_index, method='ffill').bfill()
            
            if sym_upper == 'GRAM':
                close_series = (m_series / 31.1035) * u_series
            elif sym_upper == 'CEYREK':
                close_series = (m_series / 31.1035) * u_series * 1.75
            elif sym_upper == 'YARIM':
                close_series = (m_series / 31.1035) * u_series * 3.5
            elif sym_upper == 'SILVER':
                close_series = (m_series / 31.1035) * u_series
            else: # GOLD or PLATINUM or PALLADIUM (ounce price)
                close_series = m_series * u_series
                
            df_prices[sym_upper] = close_series
            
        else:
            # BIST Stock
            ticker = sym_upper + ".IS" if not sym_upper.endswith(".IS") else sym_upper
            s_hist = yf.download(ticker, period=period, interval="1d", progress=False)
            s_series = s_hist['Close']
            if isinstance(s_series, pd.DataFrame): s_series = s_series.iloc[:, 0]
            
            s_series = s_series.reindex(master_index, method='ffill').bfill()
            df_prices[sym_upper] = s_series
            
    # Drop rows that are entirely NaN
    df_prices = df_prices.dropna(how='all')
    # Forward fill any remaining NaNs
    df_prices = df_prices.ffill().bfill()
    
    return df_prices

def safe_cholesky(cov):
    try:
        return np.linalg.cholesky(cov)
    except np.linalg.LinAlgError:
        n = cov.shape[0]
        for eps in [1e-6, 1e-5, 1e-4, 1e-3]:
            try:
                return np.linalg.cholesky(cov + eps * np.eye(n))
            except np.linalg.LinAlgError:
                continue
        diag = np.diag(cov)
        diag[diag < 1e-8] = 1e-8
        return np.diag(np.sqrt(diag))

@app.route('/api/optimize_portfolio')
def api_optimize_portfolio():
    u = session.get('user')
    if not u: return jsonify({"error": "Giriş yapın"}), 401
    pid = request.args.get('portfolio_id')
    conn = get_db()
    if pid:
        rows = conn.execute("SELECT symbol, SUM(amount) as amount, SUM(amount * buy_price) / SUM(amount) as buy_price FROM portfolio WHERE username=? AND portfolio_id=? GROUP BY symbol", (u, pid)).fetchall()
    else:
        rows = conn.execute("SELECT symbol, SUM(amount) as amount, SUM(amount * buy_price) / SUM(amount) as buy_price FROM portfolio WHERE username=? GROUP BY symbol", (u,)).fetchall()
    conn.close()
    
    if len(rows) < 2:
        return jsonify({"error": "Optimizasyon için portföyünüzde en az 2 farklı varlık olmalıdır."})
        
    symbols = [r['symbol'].upper() for r in rows]
    amounts = {r['symbol'].upper(): float(r['amount']) for r in rows}
    
    try:
        df_prices = get_historical_prices_for_portfolio(symbols, period="1y")
        
        # Calculate weights based on actual current prices from df_prices
        current_prices = df_prices.iloc[-1].to_dict()
        total_current_val = sum(amounts[s] * current_prices[s] for s in symbols)
        
        weights_current = []
        for s in symbols:
            weight = (amounts[s] * current_prices[s]) / total_current_val if total_current_val > 0 else 1/len(symbols)
            weights_current.append(weight)
            
        returns = df_prices.pct_change().dropna()
        mean_returns = returns.mean() * 252
        cov_matrix = returns.cov() * 252
        
        num_assets = len(symbols)
        
        def portfolio_performance(weights, mean_returns, cov_matrix):
            returns_p = np.sum(mean_returns * weights)
            std_p = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
            return std_p, returns_p
            
        def neg_sharpe_ratio(weights, mean_returns, cov_matrix, risk_free_rate=0.45):
            p_var, p_ret = portfolio_performance(weights, mean_returns, cov_matrix)
            return -(p_ret - risk_free_rate) / p_var
            
        args = (mean_returns, cov_matrix)
        constraints = ({'type': 'eq', 'fun': lambda x: np.sum(x) - 1})
        bounds = tuple((0.0, 1.0) for asset in range(num_assets))
        initial_guess = num_assets * [1. / num_assets]
        
        optimized = sco.minimize(neg_sharpe_ratio, initial_guess, args=args, method='SLSQP', bounds=bounds, constraints=constraints)
        
        opt_weights = optimized.x
        opt_std, opt_ret = portfolio_performance(opt_weights, mean_returns, cov_matrix)
        
        # Generate 150 random portfolios for the Efficient Frontier Scatter Plot
        scatter_points = []
        for _ in range(150):
            rand_w = np.random.random(num_assets)
            rand_w /= np.sum(rand_w)
            p_std, p_ret = portfolio_performance(rand_w, mean_returns, cov_matrix)
            scatter_points.append({
                "x": round(float(p_std * 100), 2),  # Volatility (Risk)
                "y": round(float(p_ret * 100), 2)   # Expected Return
            })

        dist = []
        for i, s in enumerate(symbols):
            dist.append({
                "symbol": s,
                "amount": amounts[s],
                "current_price": round(float(current_prices[s]), 2),
                "current_weight": round(weights_current[i] * 100, 2),
                "optimal_weight": round(opt_weights[i] * 100, 2)
            })
            
        return jsonify({
            "status": "ok",
            "expected_return": round(opt_ret * 100, 2),
            "volatility": round(opt_std * 100, 2),
            "sharpe_ratio": round((opt_ret - 0.45) / opt_std, 2),
            "distribution": dist,
            "scatter_points": scatter_points,
            "optimal_point": {"x": round(opt_std * 100, 2), "y": round(opt_ret * 100, 2)}
        })
    except Exception as e:
        return jsonify({"error": f"Optimizasyon hatası: {str(e)}"})


@app.route('/api/portfolio/risk_simulation')
def api_portfolio_risk_simulation():
    u = session.get('user')
    if not u: return jsonify({"error": "Giriş yapın"}), 401
    
    period = request.args.get('period', '1y')
    valid_periods = {'3mo': 63, '6mo': 126, '1y': 252, '3y': 756}
    if period not in valid_periods: period = '1y'
    num_days = valid_periods[period]
    
    pid = request.args.get('portfolio_id')
    conn = get_db()
    if pid:
        rows = conn.execute("SELECT symbol, SUM(amount) as amount, SUM(amount * buy_price) / SUM(amount) as buy_price FROM portfolio WHERE username=? AND portfolio_id=? GROUP BY symbol", (u, pid)).fetchall()
    else:
        rows = conn.execute("SELECT symbol, SUM(amount) as amount, SUM(amount * buy_price) / SUM(amount) as buy_price FROM portfolio WHERE username=? GROUP BY symbol", (u,)).fetchall()
    conn.close()
    
    if len(rows) < 1:
        return jsonify({"error": "Risk simülasyonu için portföyünüzde en az 1 varlık bulunmalıdır."}), 400
        
    symbols = [r['symbol'].upper() for r in rows]
    amounts = {r['symbol'].upper(): float(r['amount']) for r in rows}
    
    try:
        # Fetch 1 year of daily historical prices for returns and covariance calculation
        df_prices = get_historical_prices_for_portfolio(symbols, period="1y")
        
        # Calculate daily log returns
        returns = np.log(df_prices / df_prices.shift(1)).dropna()
        
        # Calculate daily mean returns (drift) and covariance matrix
        mean_returns = returns.mean().values
        cov_matrix = returns.cov().values
        
        num_assets = len(symbols)
        
        # Initialize simulation parameters
        last_prices = df_prices.iloc[-1].values
        initial_portfolio_value = sum(amounts[sym] * last_prices[i] for i, sym in enumerate(symbols))
        
        import random
        # If covariance matrix is single-dimensional or empty, handle it
        if num_assets == 1:
            drift = mean_returns[0]
            vol = np.sqrt(cov_matrix[0][0])
            paths = []
            for _ in range(100):
                path = [initial_portfolio_value]
                curr = initial_portfolio_value
                for _ in range(num_days):
                    shock = random.gauss(0, 1)
                    exponent = (drift - 0.5 * vol**2) + vol * shock
                    curr *= np.exp(exponent)
                    path.append(round(float(curr), 2))
                paths.append(path)
        else:
            # Safe Cholesky Decomposition
            L = safe_cholesky(cov_matrix)
            
            paths = []
            num_simulations = 100
            
            for _ in range(num_simulations):
                # Simulated prices for each asset
                sim_prices = np.zeros((num_days + 1, num_assets))
                sim_prices[0, :] = last_prices
                
                for d in range(1, num_days + 1):
                    # Independent standard normal shocks
                    Z = np.random.standard_normal(num_assets)
                    # Correlated shocks
                    correlated_shocks = np.dot(L, Z)
                    
                    # Update price for each asset
                    for i in range(num_assets):
                        drift = mean_returns[i]
                        var = cov_matrix[i, i]
                        exponent = (drift - 0.5 * var) + correlated_shocks[i]
                        sim_prices[d, i] = sim_prices[d-1, i] * np.exp(exponent)
                
                # Calculate portfolio value path
                port_path = []
                for d in range(num_days + 1):
                    val = sum(amounts[sym] * sim_prices[d, i] for i, sym in enumerate(symbols))
                    port_path.append(round(float(val), 2))
                paths.append(port_path)
        
        # Compute final prices
        final_values = np.array([p[-1] for p in paths])
        expected_final = round(float(np.mean(final_values)), 2)
        bullish = round(float(np.percentile(final_values, 80)), 2)
        bearish = round(float(np.percentile(final_values, 20)), 2)
        
        # Calculate Value at Risk (VaR 95%)
        var_95 = round(float(initial_portfolio_value - np.percentile(final_values, 5)), 2)
        var_pct = round((var_95 / initial_portfolio_value) * 100, 2) if initial_portfolio_value > 0 else 0
        
        # Calculate Average Maximum Drawdown
        drawdowns = []
        for p in paths:
            p_arr = np.array(p)
            peaks = np.maximum.accumulate(p_arr)
            # Avoid division by zero
            peaks[peaks == 0] = 1e-8
            dd = (peaks - p_arr) / peaks
            drawdowns.append(np.max(dd))
        avg_max_dd = round(float(np.mean(drawdowns)) * 100, 2)
        
        # Generate simulation dates
        import datetime
        future_dates = []
        current_date = datetime.datetime.now()
        for _ in range(num_days):
            current_date += datetime.timedelta(days=1)
            while current_date.weekday() in [5, 6]: # Skip weekends
                current_date += datetime.timedelta(days=1)
            future_dates.append(current_date.strftime("%d %b"))
            
        return jsonify({
            "status": "ok",
            "initial_value": round(initial_portfolio_value, 2),
            "expected_final": expected_final,
            "bullish": bullish,
            "bearish": bearish,
            "var_95": var_95,
            "var_pct": var_pct,
            "avg_max_dd": avg_max_dd,
            "future_dates": future_dates,
            "paths": paths[:40] # Return a subset of paths to keep payload light and rendering fast
        })
    except Exception as e:
        return jsonify({"error": f"Risk simülasyonu hatası: {str(e)}"}), 500

# ---------- PORTFOLIO API ----------

# --- Multi-Portfolio CRUD ---
@app.route('/api/portfolios')
def get_portfolios():
    u = session.get('user')
    if not u: return jsonify([])
    conn = get_db()
    rows = conn.execute("SELECT id, name, created_at FROM portfolios WHERE username=? ORDER BY id ASC", (u,)).fetchall()
    conn.close()
    result = [{"id": r['id'], "name": r['name'], "created_at": r['created_at']} for r in rows]
    # If no portfolios exist, create a default one
    if not result:
        conn = get_db()
        conn.execute("INSERT INTO portfolios (username, name) VALUES (?,?)", (u, 'Varsayılan Portföy'))
        conn.commit()
        pid = conn.execute("SELECT id FROM portfolios WHERE username=? ORDER BY id DESC LIMIT 1", (u,)).fetchone()['id']
        conn.close()
        result = [{"id": pid, "name": "Varsayılan Portföy", "created_at": ""}]
    return jsonify(result)

@app.route('/api/portfolios/create', methods=['POST'])
def create_portfolio_group():
    u = session.get('user')
    if not u: return jsonify({"error": "Giriş yapın"}), 401
    data = request.json or {}
    name = data.get('name', '').strip()
    if not name: return jsonify({"error": "Portföy adı boş olamaz"}), 400
    conn = get_db()
    # Check duplicate
    existing = conn.execute("SELECT id FROM portfolios WHERE username=? AND name=?", (u, name)).fetchone()
    if existing:
        conn.close()
        return jsonify({"error": "Bu isimde bir portföy zaten var"}), 400
    conn.execute("INSERT INTO portfolios (username, name) VALUES (?,?)", (u, name))
    conn.commit()
    new_id = conn.execute("SELECT id FROM portfolios WHERE username=? ORDER BY id DESC LIMIT 1", (u,)).fetchone()['id']
    conn.close()
    return jsonify({"status": "ok", "id": new_id, "name": name})

@app.route('/api/portfolios/delete/<int:pid>', methods=['DELETE'])
def delete_portfolio_group(pid):
    u = session.get('user')
    if not u: return jsonify({"error": "Giriş yapın"}), 401
    conn = get_db()
    # Check ownership
    p = conn.execute("SELECT id FROM portfolios WHERE id=? AND username=?", (pid, u)).fetchone()
    if not p:
        conn.close()
        return jsonify({"error": "Portföy bulunamadı"}), 404
    # Delete all assets in this portfolio
    conn.execute("DELETE FROM portfolio WHERE portfolio_id=? AND username=?", (pid, u))
    conn.execute("DELETE FROM portfolios WHERE id=? AND username=?", (pid, u))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})

@app.route('/api/portfolios/rename/<int:pid>', methods=['PUT'])
def rename_portfolio_group(pid):
    u = session.get('user')
    if not u: return jsonify({"error": "Giriş yapın"}), 401
    data = request.json or {}
    new_name = data.get('name', '').strip()
    if not new_name: return jsonify({"error": "Yeni ad boş olamaz"}), 400
    conn = get_db()
    conn.execute("UPDATE portfolios SET name=? WHERE id=? AND username=?", (new_name, pid, u))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})

# --- Portfolio Items API (updated with portfolio_id) ---
@app.route('/api/portfolio')
def get_portfolio():
    u = session.get('user')
    if not u: return jsonify([])
    pid = request.args.get('portfolio_id')
    conn = get_db()
    if pid:
        rows = conn.execute("SELECT id, symbol, amount, buy_price FROM portfolio WHERE username=? AND portfolio_id=?", (u, pid)).fetchall()
    else:
        rows = conn.execute("SELECT id, symbol, amount, buy_price FROM portfolio WHERE username=?", (u,)).fetchall()
    conn.close()
    
    result = []
    for r in rows:
        result.append({
            "id": r['id'],
            "symbol": r['symbol'],
            "amount": r['amount'],
            "buy_price": r['buy_price']
        })
    return jsonify(result)

@app.route('/api/portfolio/add', methods=['POST'])
def add_portfolio():
    u = session.get('user')
    if not u: return jsonify({"error": "Giriş yapın"}), 401
    data = request.json
    symbol = data.get('symbol', '').upper()
    amount = float(data.get('amount', 0))
    buy_price = float(data.get('buy_price', 0))
    portfolio_id = data.get('portfolio_id')
    
    if not symbol or amount <= 0: return jsonify({"error": "Geçersiz veri"}), 400
    
    # If no portfolio_id given, use the first portfolio
    if not portfolio_id:
        conn = get_db()
        first = conn.execute("SELECT id FROM portfolios WHERE username=? ORDER BY id ASC LIMIT 1", (u,)).fetchone()
        if first:
            portfolio_id = first['id']
        else:
            conn.execute("INSERT INTO portfolios (username, name) VALUES (?,?)", (u, 'Varsayılan Portföy'))
            conn.commit()
            portfolio_id = conn.execute("SELECT id FROM portfolios WHERE username=? ORDER BY id DESC LIMIT 1", (u,)).fetchone()['id']
        conn.close()
    
    if symbol in ['TRY', 'NAKIT']:
        unit_buy_price = 1.00
    else:
        unit_buy_price = buy_price / amount if amount > 0 else buy_price
        
    conn = get_db()
    conn.execute("INSERT INTO portfolio (username, symbol, amount, buy_price, portfolio_id) VALUES (?,?,?,?,?)", (u, symbol, amount, unit_buy_price, portfolio_id))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})

@app.route('/api/portfolio/delete/<int:item_id>', methods=['DELETE'])
def delete_portfolio(item_id):
    u = session.get('user')
    if not u: return jsonify({"error": "Giriş yapın"}), 401
    conn = get_db()
    conn.execute("DELETE FROM portfolio WHERE id=? AND username=?", (item_id, u))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})

@app.route('/portfolio')
def portfolio():
    if 'user' not in session:
        return redirect('/login')
    return render_template('portfolio.html')

@app.route('/mevduat')
def mevduat():
    return render_template('mevduat.html')

@app.route('/danisman')
def danisman():
    if 'user' not in session:
        return redirect('/login')
    return render_template('advisor.html')

@app.route('/api/ai_portfolio_advisor', methods=['POST'])
def api_ai_portfolio_advisor():
    data = request.json or {}
    amount = float(data.get('amount', 10000))
    risk = data.get('risk', 'medium').lower()
    horizon = data.get('horizon', 'medium').lower()
    sectors = data.get('sectors', ['hisse', 'fon', 'altin', 'mevduat'])
    
    weights = {}
    if risk == 'low':
        base_alloc = {'mevduat': 40, 'altin': 30, 'fon': 20, 'hisse': 10}
    elif risk == 'high':
        base_alloc = {'hisse': 50, 'fon': 30, 'altin': 10, 'mevduat': 10}
    else:
        base_alloc = {'hisse': 30, 'fon': 30, 'altin': 20, 'mevduat': 20}
        
    if horizon == 'short':
        base_alloc['mevduat'] += 15
        base_alloc['hisse'] = max(5, base_alloc['hisse'] - 15)
    elif horizon == 'long':
        base_alloc['hisse'] += 15
        base_alloc['mevduat'] = max(5, base_alloc['mevduat'] - 15)
        
    active_sectors = [s for s in sectors if s in base_alloc]
    if not active_sectors:
        active_sectors = ['mevduat', 'altin', 'fon', 'hisse']
        
    filtered_alloc = {s: base_alloc[s] for s in active_sectors}
    total_filtered_weight = sum(filtered_alloc.values())
    
    final_weights = {}
    for s in active_sectors:
        final_weights[s] = round((filtered_alloc[s] / total_filtered_weight) * 100, 2)
        
    allocation_details = []
    suggestions_map = {
        'hisse': [
            {"symbol": "THYAO", "name": "Türk Hava Yolları", "share": 40},
            {"symbol": "ASELS", "name": "Aselsan Elektronik", "share": 30},
            {"symbol": "BIMAS", "name": "BİM Birleşik Mağazalar", "share": 30}
        ],
        'fon': [
            {"symbol": "MAC", "name": "Marmara Capital Hisse Fonu", "share": 40},
            {"symbol": "TTE", "name": "İş Portföy BIST Teknoloji Fonu", "share": 30},
            {"symbol": "YZG", "name": "Yapı Kredi Portföy Altın Fonu", "share": 30}
        ],
        'altin': [
            {"symbol": "GRAM", "name": "Gram Altın", "share": 70},
            {"symbol": "SILVER", "name": "Gümüş (Gram)", "share": 30}
        ],
        'mevduat': [
            {"symbol": "TRY", "name": "Vadeli Nakit (TRY)", "share": 100}
        ]
    }
    
    for sect, w in final_weights.items():
        sect_amount = (w / 100.0) * amount
        suggs = suggestions_map.get(sect, [])
        for sug in suggs:
            sug_share = sug['share']
            sug_weight = (sug_share / 100.0) * w
            sug_amount = (sug_share / 100.0) * sect_amount
            allocation_details.append({
                "category": sect,
                "symbol": sug['symbol'],
                "name": sug['name'],
                "weight": round(sug_weight, 2),
                "amount": round(sug_amount, 2)
            })
            
    advice_text = ""
    if risk == 'low':
        advice_text += "Belirlediğiniz düşük risk profiline uygun olarak sermaye koruması odaklı bir portföy tasarlanmıştır. Enflasyon karşısında paranızın değer kaybetmemesi amacıyla mevduat faiz getirileri ve altın koruma kalkanı ön plandadır. "
    elif risk == 'high':
        advice_text += "Yüksek risk profiliniz doğrultusunda büyüme ve sermaye kazancı odaklı dinamik bir portföy tasarlanmıştır. BİST 100 hisse senetleri ve hisse senedi yoğun fonlar ile yüksek volatilite kabul edilerek pazarın üzerinde getiri hedeflenmiştir. "
    else:
        advice_text += "Orta risk seviyesine uygun olarak dengeli bir portföy oluşturulmuştur. Hisse senedi getirileri ile mevduat/altın gibi güvenli limanlar arasında dengeli bir dağılım yapılarak portföy oynaklığı optimize edilmiştir. "
        
    if horizon == 'short':
        advice_text += "Kısa vadeli (1-3 ay) yatırım hedefiniz nedeniyle, ani piyasa şoklarından etkilenmemeniz için yüksek likiditeye sahip nakit ve mevduat ağırlığı artırılmıştır."
    elif horizon == 'long':
        advice_text += "Uzun vadeli (3+ yıl) yatırım ufkunuz sayesinde, kısa vadeli piyasa dalgalanmalarını tolere edebilir ve hisse senetlerinin uzun vadeli bileşik büyüme potansiyelinden maksimum fayda sağlayabilirsiniz."
    else:
        advice_text += "Orta vadeli (6-12 ay) hedeflerinize uygun olarak hem nakit akışı sağlayan hem de değer artışı vaat eden dengeli bir vade yapısı kurulmuştur."
        
    return jsonify({
        "status": "ok",
        "total_amount": amount,
        "risk": risk,
        "horizon": horizon,
        "weights": final_weights,
        "details": allocation_details,
        "report": advice_text
    })

@app.route('/api/portfolio/add_recommended', methods=['POST'])
def add_recommended_portfolio():
    u = session.get('user')
    if not u: return jsonify({"error": "Giriş yapın"}), 401
    
    data = request.json or {}
    items = data.get('items', [])
    
    if not items:
        return jsonify({"error": "Eklenecek varlık bulunamadı"}), 400
        
    conn = get_db()
    try:
        for item in items:
            sym = item.get('symbol', '').upper()
            target_amount = float(item.get('amount', 0))
            if target_amount <= 0 or not sym:
                continue
                
            if sym in ['TRY', 'NAKIT']:
                curr_price = 1.00
            else:
                try:
                    if sym in funds_provider.funds.keys():
                        fund_info = funds_provider.get_fund_detail(sym)
                        curr_price = fund_info['price'] if fund_info else 10.0
                    elif sym in ['GOLD', 'SILVER', 'PLATINUM', 'PALLADIUM', 'GRAM', 'CEYREK', 'YARIM']:
                        curr_price = None
                        m_data = cached_metals_data or MetalsProvider().fetch_data()
                        for m in m_data:
                            if m['symbol'].upper() == sym:
                                curr_price = float(str(m['price']).replace(' ₺', '').replace('.', '').replace(',', '.'))
                                break
                        if not curr_price:
                            fallback_metals = {'GRAM': 6400.0, 'CEYREK': 10650.0, 'YARIM': 21000.0, 'SILVER': 102.0, 'GOLD': 124800.0, 'PLATINUM': 40950.0, 'PALLADIUM': 42900.0}
                            curr_price = fallback_metals.get(sym, 100.0)
                    else:
                        ticker = sym + ".IS" if not sym.endswith(".IS") else sym
                        t_data = yf.download(ticker, period="5d", progress=False)
                        c_series = t_data['Close']
                        if isinstance(c_series, pd.DataFrame): c_series = c_series.iloc[:, 0]
                        c_series = c_series.dropna()
                        curr_price = float(c_series.iloc[-1])
                except Exception as ex:
                    print(f"Error fetching current price for recommend add {sym}: {ex}")
                    curr_price = 100.0
                    
            quantity = target_amount / curr_price
            # Get first portfolio for the user
            first_p = conn.execute("SELECT id FROM portfolios WHERE username=? ORDER BY id ASC LIMIT 1", (u,)).fetchone()
            p_id = first_p['id'] if first_p else None
            conn.execute("INSERT INTO portfolio (username, symbol, amount, buy_price, portfolio_id) VALUES (?,?,?,?,?)", (u, sym, quantity, curr_price, p_id))
            
        conn.commit()
        return jsonify({"status": "ok"})
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@app.route('/simulasyon')
def simulasyon():
    return render_template('simulasyon.html')

@app.route('/karsilastir')
def karsilastir():
    return render_template('compare.html')

@app.route('/api/simulate')
def api_simulate():
    symbol = request.args.get('symbol', '').upper()
    date = request.args.get('date', '') # YYYY-MM-DD
    amount = float(request.args.get('amount', 1000))
    
    if not symbol or not date:
        return jsonify({"error": "Eksik parametre"}), 400
        
    try:
        import datetime
        import pandas as pd
        sym = symbol.upper()
        if sym in ['TRY', 'NAKIT']:
            return jsonify({
                "symbol": sym,
                "buy_date": date,
                "buy_price": 1.00,
                "current_price": 1.00,
                "initial_investment": amount,
                "current_value": amount,
                "profit_loss": 0.00,
                "profit_loss_pct": 0.00
            })
            
        is_metal = sym in ['GOLD', 'SILVER', 'PLATINUM', 'PALLADIUM', 'GRAM', 'CEYREK', 'YARIM']
        is_fund = sym in funds_provider.funds.keys()
        
        if sym == 'XU100': ticker = 'XU100.IS'
        elif sym == 'GOLD': ticker = 'GC=F'
        elif sym == 'SILVER': ticker = 'SI=F'
        elif sym == 'PLATINUM': ticker = 'PL=F'
        elif sym == 'PALLADIUM': ticker = 'PA=F'
        elif sym == 'GRAM' or sym == 'CEYREK' or sym == 'YARIM': ticker = 'GC=F'
        elif is_fund: ticker = funds_provider.funds[sym]["ticker"]
        elif not sym.endswith('.IS') and sym.isalpha(): ticker = sym + '.IS'
        else: ticker = sym

        start_date = datetime.datetime.strptime(date, '%Y-%m-%d')
        
        if is_fund:
            import hashlib
            import random
            xu_hist = yf.download("XU100.IS", start="2026-01-01", progress=False)
            if xu_hist.empty:
                return jsonify({"error": "Fon simülasyonu için veri bulunamadı."}), 404
            
            close_series = xu_hist['Close']
            if isinstance(close_series, pd.DataFrame):
                close_series = close_series.iloc[:, 0]
            close_series = close_series.dropna()
            
            base_val = int(hashlib.md5(sym.encode()).hexdigest(), 16) % 900 + 100
            random.seed(sym)
            walk = base_val
            closes_dict = {}
            for d in close_series.index:
                walk *= (1 + random.gauss(0.001, 0.015))
                closes_dict[d] = round(walk, 2)
                
            closest_idx = min(close_series.index, key=lambda d: abs((d.tz_localize(None) - start_date.replace(tzinfo=None)).days))
            buy_price = closes_dict[closest_idx]
            buy_date_actual = closest_idx.strftime('%Y-%m-%d')
            curr_price = list(closes_dict.values())[-1]
        else:
            hist = yf.download(ticker, start=(start_date - datetime.timedelta(days=15)).strftime('%Y-%m-%d'), end=(start_date + datetime.timedelta(days=15)).strftime('%Y-%m-%d'), progress=False)
            
            if hist.empty:
                return jsonify({"error": "Seçilen tarihte veri bulunamadı."}), 404
                
            close_series = hist['Close']
            if isinstance(close_series, pd.DataFrame):
                close_series = close_series.iloc[:, 0]
                
            close_series = close_series.dropna()
            if close_series.empty:
                return jsonify({"error": "Seçilen tarihte veri bulunamadı."}), 404
                
            if is_metal:
                usdtry_hist = yf.download("USDTRY=X", start=(start_date - datetime.timedelta(days=15)).strftime('%Y-%m-%d'), end=(start_date + datetime.timedelta(days=15)).strftime('%Y-%m-%d'), progress=False)
                usd_series = usdtry_hist['Close']
                if isinstance(usd_series, pd.DataFrame):
                    usd_series = usd_series.iloc[:, 0]
                usd_series = usd_series.reindex(close_series.index, method='ffill')
                
                if sym == 'GRAM':
                    close_series = (close_series / 31.1035) * usd_series
                elif sym == 'CEYREK':
                    close_series = (close_series / 31.1035) * usd_series * 1.75
                elif sym == 'YARIM':
                    close_series = (close_series / 31.1035) * usd_series * 3.5
                elif sym == 'SILVER':
                    close_series = (close_series / 31.1035) * usd_series
                else:
                    close_series = close_series * usd_series
                    
            closest_idx = min(close_series.index, key=lambda d: abs((d.tz_localize(None) - start_date.replace(tzinfo=None)).days))
            buy_price = float(close_series.loc[closest_idx])
            buy_date_actual = closest_idx.strftime('%Y-%m-%d')
            
            if is_metal:
                try:
                    m_data = cached_metals_data or MetalsProvider().fetch_data()
                    curr_price = None
                    for item in m_data:
                        if item['symbol'].upper() == sym:
                            curr_price = float(str(item['price']).replace(' ₺', '').replace('.', '').replace(',', '.'))
                            break
                except:
                    curr_price = None
                    
                if not curr_price:
                    curr_hist = yf.download(ticker, period="5d", progress=False)
                    c_series = curr_hist['Close']
                    if isinstance(c_series, pd.DataFrame): c_series = c_series.iloc[:, 0]
                    c_series = c_series.dropna()
                    
                    usd_curr = yf.download("USDTRY=X", period="5d", progress=False)
                    u_series = usd_curr['Close']
                    if isinstance(u_series, pd.DataFrame): u_series = u_series.iloc[:, 0]
                    u_series = u_series.reindex(c_series.index, method='ffill')
                    
                    if sym == 'GRAM':
                        c_series = (c_series / 31.1035) * u_series
                    elif sym == 'CEYREK':
                        c_series = (c_series / 31.1035) * u_series * 1.75
                    elif sym == 'YARIM':
                        c_series = (c_series / 31.1035) * u_series * 3.5
                    elif sym == 'SILVER':
                        c_series = (c_series / 31.1035) * u_series
                    else:
                        c_series = c_series * u_series
                    
                    curr_price = float(c_series.iloc[-1])
            else:
                curr_info = yf.Ticker(ticker).info
                curr_price = curr_info.get('currentPrice') or curr_info.get('regularMarketPrice')
                if not curr_price:
                    curr_hist = yf.download(ticker, period="5d", progress=False)
                    c_series = curr_hist['Close']
                    if isinstance(c_series, pd.DataFrame): c_series = c_series.iloc[:, 0]
                    c_series = c_series.dropna()
                    curr_price = float(c_series.iloc[-1])
                    
        quantity = amount / buy_price
        current_value = quantity * curr_price
        profit_loss = current_value - amount
        profit_loss_pct = (profit_loss / amount) * 100
        
        return jsonify({
            "symbol": sym,
            "buy_date": buy_date_actual,
            "buy_price": round(buy_price, 2),
            "current_price": round(curr_price, 2),
            "initial_investment": amount,
            "current_value": round(current_value, 2),
            "profit_loss": round(profit_loss, 2),
            "profit_loss_pct": round(profit_loss_pct, 2)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


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

@app.route('/api/chart/<symbol>')
def api_chart(symbol):
    try:
        import pandas as pd
        sym = symbol.upper()
        if sym in ['TRY', 'NAKIT']:
            period = request.args.get('period', '6mo')
            valid_periods = ['1d', '1w', '1mo', '3mo', '6mo', 'ytd', '1y', '5y']
            if period not in valid_periods: period = '6mo'
            interval_map = {'1d': '5m', '1w': '1h', '1mo': '1d', '3mo': '1d', '6mo': '1d', 'ytd': '1d', '1y': '1d', '5y': '1wk'}
            inv = interval_map[period]
            base_hist = yf.download("XU100.IS", period=period, interval=inv, progress=False)
            if period == '1d': dates = base_hist.index.strftime('%H:%M').tolist()
            else: dates = base_hist.index.strftime('%d %b').tolist()
            count = len(dates) or 1
            if len(dates) == 0: dates = ["01 Oca"]
            closes = [1.00] * count
            return jsonify({"dates": dates, "closes": closes, "symbol": sym, "current_price": 1.00, "change_pct": 0.00, "period": period})

        is_metal = sym in ['GOLD', 'SILVER', 'PLATINUM', 'PALLADIUM', 'GRAM', 'CEYREK', 'YARIM']
        is_fund = sym in funds_provider.funds.keys()
        
        if sym == 'XU100': ticker = 'XU100.IS'
        elif sym == 'GOLD': ticker = 'GC=F'
        elif sym == 'SILVER': ticker = 'SI=F'
        elif sym == 'PLATINUM': ticker = 'PL=F'
        elif sym == 'PALLADIUM': ticker = 'PA=F'
        elif sym == 'GRAM' or sym == 'CEYREK' or sym == 'YARIM': ticker = 'GC=F'
        elif is_fund: ticker = funds_provider.funds[sym]["ticker"]
        elif not sym.endswith('.IS') and sym.isalpha(): ticker = sym + '.IS'
        else: ticker = sym

        period = request.args.get('period', '6mo')
        valid_periods = ['1d', '1w', '1mo', '3mo', '6mo', 'ytd', '1y', '5y']
        if period not in valid_periods: period = '6mo'
        
        interval_map = {'1d': '5m', '1w': '1h', '1mo': '1d', '3mo': '1d', '6mo': '1d', 'ytd': '1d', '1y': '1d', '5y': '1wk'}
        inv = interval_map[period]

        if is_fund:
            import hashlib
            import random
            
            # Fetch base dates from XU100 to align funds with market
            base_hist = yf.download("XU100.IS", period=period, interval=inv, progress=False)
            if period == '1d': dates = base_hist.index.strftime('%H:%M').tolist()
            else: dates = base_hist.index.strftime('%d %b').tolist()
            
            count = len(dates)
            if count == 0:
                dates = ["01 Oca"]
                count = 1
                
            base_val = int(hashlib.md5(sym.encode()).hexdigest(), 16) % 900 + 100
            random.seed(sym)
            walk = base_val
            closes = []
            for _ in range(count):
                walk *= (1 + random.gauss(0.001, 0.015))
                closes.append(round(walk, 2))
                
            current_price = closes[-1] if closes else 0
            first_price = closes[0] if closes else 1
            change_pct = ((current_price - first_price) / first_price) * 100 if first_price != 0 else 0
            return jsonify({"dates": dates, "closes": closes, "symbol": sym, "current_price": current_price, "change_pct": round(change_pct, 2), "period": period})

        hist = yf.download(ticker, period=period, interval=inv, progress=False)
        
        # Extract close series safely
        close_series = hist['Close']
        if isinstance(close_series, pd.DataFrame):
            close_series = close_series.iloc[:, 0]
        
        if is_metal:
            usdtry_hist = yf.download("USDTRY=X", period=period, interval=inv, progress=False)
            usdtry_hist = usdtry_hist.reindex(hist.index, method='ffill')
            usdtry_series = usdtry_hist['Close']
            if isinstance(usdtry_series, pd.DataFrame):
                usdtry_series = usdtry_series.iloc[:, 0]
                
            if sym == 'GRAM':
                close_series = (close_series / 31.1035) * usdtry_series
            elif sym == 'CEYREK':
                close_series = (close_series / 31.1035) * usdtry_series * 1.75
            elif sym == 'YARIM':
                close_series = (close_series / 31.1035) * usdtry_series * 3.5
            elif sym == 'SILVER':
                close_series = (close_series / 31.1035) * usdtry_series
            else:
                close_series = close_series * usdtry_series

        valid_data = close_series.dropna()
        closes = [round(float(x), 2) for x in valid_data.tolist()]
        
        if period == '1d': dates = valid_data.index.strftime('%H:%M').tolist()
        else: dates = valid_data.index.strftime('%d %b').tolist()
            
        current_price = closes[-1] if closes else 0
        first_price = closes[0] if closes else 1
        
        # For metals, override current_price with real-time Turkish market price from Altinkaynak
        if is_metal and cached_metals_data:
            for m in cached_metals_data:
                if m['symbol'].upper() == sym:
                    try:
                        real_price = float(m['price'])
                        if real_price > 0:
                            current_price = real_price
                    except:
                        pass
                    break
        
        change_pct = ((current_price - first_price) / first_price) * 100 if first_price != 0 else 0
        
        return jsonify({"dates": dates, "closes": closes, "symbol": sym, "current_price": current_price, "change_pct": round(change_pct, 2), "period": period})
    except Exception as e:
        return jsonify({"error": str(e), "dates": [], "closes": []})

# ---------- MONTE CARLO SIMULATION API ----------
@app.route('/api/montecarlo/<symbol>')
def api_montecarlo(symbol):
    try:
        import numpy as np
        import pandas as pd
        import random
        import hashlib
        import datetime
        
        sym = symbol.upper()
        is_metal = sym in ['GOLD', 'SILVER', 'PLATINUM', 'PALLADIUM', 'GRAM', 'CEYREK', 'YARIM']
        is_fund = sym in funds_provider.funds.keys()
        
        if sym == 'XU100': ticker = 'XU100.IS'
        elif sym == 'GOLD': ticker = 'GC=F'
        elif sym == 'SILVER': ticker = 'SI=F'
        elif sym == 'PLATINUM': ticker = 'PL=F'
        elif sym == 'PALLADIUM': ticker = 'PA=F'
        elif sym == 'GRAM' or sym == 'CEYREK' or sym == 'YARIM': ticker = 'GC=F'
        elif is_fund: ticker = funds_provider.funds[sym]["ticker"]
        elif not sym.endswith('.IS') and sym.isalpha(): ticker = sym + '.IS'
        else: ticker = sym

        # Fetch 1 year of daily historical data to get statistically robust drift & volatility
        if is_fund:
            base_hist = yf.download("XU100.IS", period="1y", interval="1d", progress=False)
            dates = base_hist.index.strftime('%d %b').tolist()
            count = len(dates)
            if count == 0:
                dates = [(datetime.datetime.now() - datetime.timedelta(days=i)).strftime('%d %b') for i in range(250, 0, -1)]
                count = len(dates)
            base_val = int(hashlib.md5(sym.encode()).hexdigest(), 16) % 900 + 100
            random.seed(sym)
            walk = base_val
            closes = []
            for _ in range(count):
                walk *= (1 + random.gauss(0.001, 0.015))
                closes.append(round(walk, 2))
        else:
            hist = yf.download(ticker, period="1y", interval="1d", progress=False)
            
            close_series = hist['Close']
            if isinstance(close_series, pd.DataFrame):
                close_series = close_series.iloc[:, 0]
                
            if is_metal:
                usdtry_hist = yf.download("USDTRY=X", period="1y", interval="1d", progress=False)
                usdtry_hist = usdtry_hist.reindex(hist.index, method='ffill')
                usdtry_series = usdtry_hist['Close']
                if isinstance(usdtry_series, pd.DataFrame):
                    usdtry_series = usdtry_series.iloc[:, 0]
                    
                if sym == 'GRAM':
                    close_series = (close_series / 31.1035) * usdtry_series
                elif sym == 'CEYREK':
                    close_series = (close_series / 31.1035) * usdtry_series * 1.75
                elif sym == 'YARIM':
                    close_series = (close_series / 31.1035) * usdtry_series * 3.5
                elif sym == 'SILVER':
                    close_series = (close_series / 31.1035) * usdtry_series
                else:
                    close_series = close_series * usdtry_series
            
            valid_data = close_series.dropna()
            closes = [round(float(x), 2) for x in valid_data.tolist()]
            dates = valid_data.index.strftime('%d %b').tolist()

        if len(closes) < 10:
            return jsonify({"error": "Yetersiz veri."})

        # Calculate daily log returns
        closes_arr = np.array(closes)
        log_returns = np.log(closes_arr[1:] / closes_arr[:-1])
        
        drift = np.mean(log_returns)
        volatility = np.std(log_returns)
        
        # Monte Carlo settings
        num_paths = 40
        num_days = 30
        last_price = closes[-1]
        
        # Generate simulation paths
        paths = []
        for _ in range(num_paths):
            path = [last_price]
            current_price = last_price
            for _ in range(num_days):
                shock = random.gauss(0, 1)
                exponent = (drift - 0.5 * volatility**2) + volatility * shock
                current_price *= np.exp(exponent)
                path.append(round(float(current_price), 2))
            paths.append(path)
            
        # Get scenarios
        final_prices = [p[-1] for p in paths]
        expected_final = round(float(np.mean(final_prices)), 2)
        bullish = round(float(np.percentile(final_prices, 80)), 2)
        bearish = round(float(np.percentile(final_prices, 20)), 2)
        
        # Generate future dates (skipping weekends roughly)
        future_dates = []
        last_date_str = dates[-1]
        try:
            current_date = datetime.datetime.strptime(last_date_str + " 2026", "%d %b %Y")
        except:
            current_date = datetime.datetime.now()
            
        for _ in range(num_days):
            current_date += datetime.timedelta(days=1)
            while current_date.weekday() in [5, 6]:
                current_date += datetime.timedelta(days=1)
            future_dates.append(current_date.strftime("%d %b"))

        # Slice last 30 days of history for continuous visualization
        history_len = min(30, len(closes))
        hist_closes = closes[-history_len:]
        hist_dates = dates[-history_len:]
        
        return jsonify({
            "symbol": sym,
            "last_price": last_price,
            "history_closes": hist_closes,
            "history_dates": hist_dates,
            "future_dates": future_dates,
            "paths": paths,
            "expected_final": expected_final,
            "bullish": bullish,
            "bearish": bearish,
            "volatility_annualized": round(float(volatility * np.sqrt(252)) * 100, 2)
        })
    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == '__main__':
    socketio.run(app, port=5001, debug=True, allow_unsafe_werkzeug=True)

# Vercel Deployment Sync: Wed Apr  8 21:33:53 +03 2026
