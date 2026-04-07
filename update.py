import os, glob

def update_templates():
    files = glob.glob('templates/*.html') + ['static/styles.css', 'static/script.js']
    for f in files:
        with open(f, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # Sadece Zümrüt Yeşili ve Ivory
        # Eğer Kırmızı varsa Yeşile geri çevir
        content = content.replace("#cf142b", "#013b2c")
        content = content.replace("rgba(207, 20, 43, ", "rgba(1, 59, 44, ")
        
        # Altın (gold) rengi veya diğer vurguları yemyeşil yapalım
        content = content.replace("#d4a574", "#013b2c")
        content = content.replace("rgba(212, 165, 116, ", "rgba(1, 59, 44, ")
        
        # Font ayarlaması
        content = content.replace("Outfit", "Roboto")
        content = content.replace("Inter", "Open Sans")
        
        # Halka arz yazısı değişikliği
        content = content.replace("Veriler halkarz.com üzerinden yükleniyor...", "Yükleniyor...")

        # Menüye Login/Register Entegrasyonu için (Eğer statik kullanılıyorsa dinamiğe çevrilecek)
        if "<!-- Dinamik oturum menüsü script ile renderlanıyor -->" not in content and "<nav class=\"main-menu\">" in content:
             nav_start = content.find("<nav class=\"main-menu\">")
             nav_end = content.find("</nav>", nav_start) + 6
             if nav_start != -1 and nav_end != -1:
                 # Tüm nav menüsünü id="dynamic-nav" ile değiştir
                 content = content[:nav_start] + '<nav class="main-menu" id="dynamic-nav"></nav>' + content[nav_end:]

        with open(f, 'w', encoding='utf-8') as file:
            file.write(content)

update_templates()


# Eğer değişken adın farklıysa (örneğin 'dubu'), onu app'e eşitle:
app = dubu  # 'dubu' yerine kendi Antigravity değişken ismini yaz.
# ... diğer kodların ...

# Vercel'in görmesi gereken ana nesne
app = uygulama_degiskenin_adin 

if __name__ == "__main__":
    # Bu kısım sadece senin bilgisayarında çalışırken devreye girer
    app.run()