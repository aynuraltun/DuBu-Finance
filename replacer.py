import os, glob

def replace_in_files():
    files = glob.glob('templates/*.html') + ['static/styles.css', 'static/script.js']
    for f in files:
        with open(f, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # Text replacements
        content = content.replace("Zümrüt Finans", "Dubu Finance")
        content = content.replace("Zümrüt", "Dubu")
        
        # Color replacements
        content = content.replace("#013b2c", "#cf142b")
        content = content.replace("rgba(1, 59, 44, ", "rgba(207, 20, 43, ")
        
        with open(f, 'w', encoding='utf-8') as file:
            file.write(content)

replace_in_files()
