import sys
sys.path.append('/Users/aynuraltun/Desktop/dubu haziran')
import sqlite3
import index

db_path = "users.db"

def force_sync():
    print("Clearing last sync date in database to force a live sync...")
    conn = sqlite3.connect(db_path)
    conn.execute("DELETE FROM settings WHERE key = 'last_ipo_sync'")
    conn.commit()
    conn.close()
    
    print("Calling sync_ipos_to_db() to scrape halkaarz.com...")
    index.sync_ipos_to_db()
    
    print("\nReading data from ipo_library table after sync:")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT title, date_text, fiyat, slug FROM ipo_library").fetchall()
    
    non_draft_count = 0
    draft_count = 0
    for r in rows:
        is_draft = index.is_draft_ipo(r["fiyat"], r["date_text"])
        if is_draft:
            draft_count += 1
        else:
            non_draft_count += 1
        print(f"  Slug: {r['slug']} | Title: {r['title']} | Date: {r['date_text']} | Price: {r['fiyat']} | Draft: {is_draft}")
        
    print(f"\nSummary:")
    print(f"  Total records: {len(rows)}")
    print(f"  Valid IPOs: {non_draft_count}")
    print(f"  Draft IPOs (filtered out): {draft_count}")
    
    conn.close()

if __name__ == '__main__':
    force_sync()
