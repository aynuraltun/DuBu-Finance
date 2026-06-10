import os
import re

templates_dir = 'templates'
files = [f for f in os.listdir(templates_dir) if f.endswith('.html')]

for filename in files:
    filepath = os.path.join(templates_dir, filename)
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if '/fonlar' in content:
        continue
    
    # Add Fonlar after Kıymetli Madenler
    new_content = re.sub(
        r'(<li><a href="/madenler.html">.*?</a></li>)',
        r'\1\n                <li><a href="/fonlar">Fonlar</a></li>',
        content
    )
    
    # Alternative if no <li>
    if new_content == content:
        new_content = re.sub(
            r'(<a href="/madenler.html".*?>.*?</a>)',
            r'\1\n                <a href="/fonlar">Fonlar</a>',
            content
        )

    if new_content != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Updated {filename}")
