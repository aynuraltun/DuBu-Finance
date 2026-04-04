from app import app

# Vercel'in beklentisi doğrultusunda uygulama nesnesini dışa aktarıyoruz
handler = app
app = app
