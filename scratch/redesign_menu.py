import os
import re

templates_dir = 'templates'
files = [f for f in os.listdir(templates_dir) if f.endswith('.html')]

new_menu_html = """        <nav class="burger-menu" id="burger-menu">
            <div class="menu-grid">
                <div class="menu-category">
                    <h3>📊 Piyasalar</h3>
                    <ul>
                        <li><a href="/bist100.html">BİST 100</a></li>
                        <li><a href="/madenler.html">Madenler</a></li>
                        <li><a href="/fonlar">Yatırım Fonları</a></li>
                        <li><a href="/halkaarz.html">Halka Arzlar</a></li>
                    </ul>
                </div>
                <div class="menu-category">
                    <h3>🛠️ Araçlar</h3>
                    <ul>
                        <li><a href="/zaman-makinesi">Zaman Makinesi</a></li>
                        <li><a href="/karsilastir">Kıyasla & Analiz</a></li>
                    </ul>
                </div>
                <div class="menu-category">
                    <h3>👤 Hesabım</h3>
                    <ul>
                        <li><a href="/portfolio">Portföy Takibi</a></li>
                        <li><a href="/takip">İzleme Listesi</a></li>
                    </ul>
                </div>
            </div>
        </nav>"""

for filename in files:
    filepath = os.path.join(templates_dir, filename)
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 1. Replace the whole nav block
    # Pattern to find <nav ... id="burger-menu"> ... </nav>
    content = re.sub(r'<nav class="burger-menu" id="burger-menu">.*?</nav>', new_menu_html, content, flags=re.DOTALL)
    
    # 2. Update specific page titles and links
    content = content.replace('Simülasyon', 'Zaman Makinesi')
    content = content.replace('/simulasyon', '/zaman-makinesi')
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Updated {filename}")
