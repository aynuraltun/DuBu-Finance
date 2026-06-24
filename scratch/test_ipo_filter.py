import sqlite3
import requests

db_path = "users.db"

def insert_test_data():
    print("Inserting test data...")
    conn = sqlite3.connect(db_path)
    
    # We will use slugs starting with "test-filter-"
    test_ipos = [
        ("test-filter-recent", "Test IPO 2 Days Ago", "7 Haziran 2026", "10,00 TL"),
        ("test-filter-future", "Test IPO Future", "15 Haziran 2026", "20,00 TL"),
        ("test-filter-old", "Test IPO 8 Days Ago", "1 Haziran 2026", "30,00 TL")
    ]
    
    for slug, title, date_text, fiyat in test_ipos:
        conn.execute("""
            INSERT OR REPLACE INTO ipo_library 
            (slug, title, date_text, fiyat, lot, buyukluk, yontem, endeks, description, scraped_at)
            VALUES (?, ?, ?, ?, '10M Lot', '100M TL', 'Eşit', 'Yıldız', 'Test description', '2026-06-09')
        """, (slug, title, date_text, fiyat))
        
    conn.commit()
    conn.close()

def query_api():
    print("\nQuerying /api/halkaarz...")
    try:
        r = requests.get("http://127.0.0.1:5001/api/halkaarz", timeout=5)
        print(f"Status Code: {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            print(f"API returned {len(data)} IPOs:")
            for item in data:
                if "test-filter" in item["slug"]:
                    print(f"  Title: {item['title']} | Date: {item['date']} | Price: {item['fiyat']} | Slug: {item['slug']}")
        else:
            print(f"API Error: {r.text}")
    except Exception as e:
        print(f"Error: {e}")

def cleanup():
    print("\nCleaning up test data...")
    conn = sqlite3.connect(db_path)
    conn.execute("DELETE FROM ipo_library WHERE slug LIKE 'test-filter-%'")
    conn.commit()
    conn.close()

if __name__ == '__main__':
    try:
        insert_test_data()
        query_api()
    finally:
        cleanup()
