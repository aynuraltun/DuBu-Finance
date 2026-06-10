import glob
import re

def fix_duplicated_sim():
    # Fix in all HTML files
    files = glob.glob('templates/*.html')
    for f_path in files:
        with open(f_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # We look for:
        # <h3>👤 Hesabım</h3>
        # <ul>
        #     <li><a href="/portfolio">Portföy Takibi</a></li>
        #     <li><a href="/simulasyon">Simülasyon</a></li> (remove this)
        #     <li><a href="/takip">İzleme Listesi</a></li>
        # </ul>
        
        # Regex to find <h3>👤 Hesabım</h3> and its <ul> contents
        pattern = r'(<h3>👤 Hesabım</h3>\s*<ul>\s*<li><a href="/portfolio">Portföy Takibi</a></li>\s*)<li><a href="/simulasyon">Simülasyon</a></li>\s*'
        if re.search(pattern, content):
            new_content = re.sub(pattern, r'\1', content)
            with open(f_path, 'w', encoding='utf-8') as f_out:
                f_out.write(new_content)
            print(f"Fixed navigation duplication in {f_path}")

fix_duplicated_sim()
