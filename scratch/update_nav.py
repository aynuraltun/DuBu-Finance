import os
import re

templates_dir = 'templates'
files = [f for f in os.listdir(templates_dir) if f.endswith('.html')]

for filename in files:
    filepath = os.path.join(templates_dir, filename)
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check if simulation link already exists
    if '/simulasyon' in content:
        print(f"Skipping {filename}, link already exists.")
        continue
    
    # Standard link pattern
    new_content = re.sub(
        r'(<li><a href="/portfolio">.*?</a></li>)',
        r'\1\n                <li><a href="/simulasyon">Simülasyon</a></li>',
        content
    )
    
    # Alternative link pattern (some files might not have <li>)
    if new_content == content:
        new_content = re.sub(
            r'(<a href="/portfolio".*?>.*?</a>)',
            r'\1\n                <a href="/simulasyon">Simülasyon</a>',
            content
        )

    if new_content != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Updated {filename}")
    else:
        print(f"Could not update {filename}")
