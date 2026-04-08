# 📊 DuBu Finance - Proje Yapı Rehberi

Bu dosya, projenin güncel dosya ağacını ve her bir bileşenin görevini açıklar.

## 📂 Dosya Listesi ve Görevleri

### 🖥️ Backend / Sunucu
*   **`index.py`**: Uygulamanın ana dosyası. Veri çekme (scraping), API uç noktaları ve sayfa yönlendirmeleri burada yapılır. Sunucu **5001** portunda çalışır.
*   **`users.db`**: Kullanıcı kayıtlarını ve favori listelerini tutan SQLite veritabanı.

### 🎨 Tasarım ve Görsellik (`static/`)
*   **`static/styles.css`**: Uygulamanın tüm görsel tasarımı, renk paleti ve animasyonları bu dosyada tanımlıdır.

### 📄 Kullanıcı Arayüzü (`templates/`)
*   **`templates/index.html`**: Terminal ana sayfası (Dashboard).
*   **`templates/altin.html`**: Altın, Gümüş ve diğer kıymetli madenlerin takip edildiği sayfa.
*   **`templates/bist100.html`**: Borsa İstanbul canlı verileri ve hisse listesi.
*   **`templates/takip.html`**: Kullanıcının kendi izleme listesini gördüğü sayfa.
*   **`templates/hisse.html`**: Detaylı hisse senedi analizi ve grafik sayfası.
*   **`templates/login.html` / `register.html`**: Kullanıcı giriş ve kayıt formları.

## 🚀 Çalıştırma Notları
Uygulamayı başlatmak için terminale `python3 index.py` yazmanız yeterlidir. Ardından tarayıcınızdan `http://127.0.0.1:5001` adresine giderek projeyi canlı olarak görebilirsiniz.
