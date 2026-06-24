import sqlite3
import requests

db_path = "users.db"

def test_database():
    print("--- TESTING DATABASE ---")
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        
        # Check settings
        settings = conn.execute("SELECT * FROM settings").fetchall()
        print("Settings in DB:")
        for s in settings:
            print(f"  {s['key']}: {s['value']}")
            
        # Check IPO count
        count = conn.execute("SELECT COUNT(*) FROM ipo_library").fetchone()[0]
        print(f"Total IPO count in DB: {count}")
        
        # Check drafts vs non-drafts
        rows = conn.execute("SELECT title, date_text, fiyat, slug FROM ipo_library").fetchall()
        print("\nIPOs in DB:")
        for r in rows:
            fiyat = r['fiyat']
            tarih = r['date_text']
            
            # Simple check matching index.py is_draft_ipo logic
            f_clean = (fiyat or "").strip().lower()
            d_clean = (tarih or "").strip().lower()
            invalid_keywords = [
                "bilinmiyor", "açıklanmadı", "belirlenmedi", "belli değil", "belli degil",
                "yok", "belirsiz", "açıklanacak", "bekleniyor", "hazırlanıyor", "hazirlaniyor",
                "yakında", "yakinda", "taslak"
            ]
            is_fiyat_invalid = any(kw in f_clean for kw in invalid_keywords) or not f_clean
            is_date_invalid = any(kw in d_clean for kw in invalid_keywords) or not d_clean
            is_draft = is_fiyat_invalid or is_date_invalid
            
            print(f"  Slug: {r['slug']} | Price: {fiyat} | Date: {tarih} | Draft: {is_draft}")
        
        conn.close()
    except Exception as e:
        print(f"Error testing DB: {e}")

def test_api():
    print("\n--- TESTING API ENDPOINT ---")
    try:
        r = requests.get("http://127.0.0.1:5001/api/halkaarz", timeout=5)
        print(f"Status Code: {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            print(f"API returned {len(data)} IPOs:")
            for item in data[:5]:
                print(f"  Title: {item['title']} | Date: {item['date']} | Price: {item['fiyat']}")
        else:
            print(f"API Error: {r.text}")
    except Exception as e:
        print(f"Error testing API: {e}")

if __name__ == '__main__':
    test_database()
    test_api()
