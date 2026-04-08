/* =========================================
   DUBU FINANCE — Logic (Sabit Veri & Vercel Uyumlu)
   ========================================= */

let userFavorites = new Set();
let chartInstances = {};

/* ---------- Başlatıcı (DOM Hazır Olduğunda) ---------- */
document.addEventListener('DOMContentLoaded', () => {
    initUI();
    loadMarketTable();
    loadIpoWidget();
    initNews();
    
    // Ana sayfadaki BIST100 grafiğini başlat
    if (document.getElementById('bistChart')) {
        loadNativeChart('XU100', '6mo', 'bistChart');
    }
});

/* ---------- Menü ve Kullanıcı Arayüzü ---------- */
function initUI() {
    const burgerBtn = document.getElementById('burger-btn');
    const burgerMenu = document.getElementById('burger-menu');
    
    if (burgerBtn && burgerMenu) {
        burgerBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            burgerBtn.classList.toggle('open');
            burgerMenu.classList.toggle('open');
        });
        document.addEventListener('click', (e) => {
            if (!burgerMenu.contains(e.target)) {
                burgerBtn.classList.remove('open');
                burgerMenu.classList.remove('open');
            }
        });
    }

    const badge = document.getElementById('user-badge');
    if (badge) {
        // Vercel'de backend olmadığı için demo kullanıcı gösteriyoruz
        badge.innerHTML = '<span style="color:var(--color-primary);font-weight:700;cursor:default;">👤 Demo Kullanıcı</span>';
    }
}

/* ---------- Piyasa Tablosu (SABİT VERİ) ---------- */
function loadMarketTable() {
    const table = document.getElementById('market-table-home');
    if (!table) return;
    const tbody = table.querySelector('tbody');
    
    const mockData = [
        { s: "THYAO", p: 285.50, c: 1.25 },
        { s: "ASELS", p: 58.30, c: -0.45 },
        { s: "EREGL", p: 45.12, c: 0.85 },
        { s: "TUPRS", p: 165.40, c: 2.10 },
        { s: "SASANI", p: 38.20, c: -1.20 },
        { s: "KCHOL", p: 192.30, c: 0.55 },
        { s: "SISE", p: 48.10, c: -0.10 }
    ];

    tbody.innerHTML = '';
    mockData.forEach(row => {
        const cls = row.c > 0 ? 'val-up' : (row.c < 0 ? 'val-down' : '');
        const sign = row.c > 0 ? '+' : '';
        const tr = document.createElement('tr');
        tr.style.cursor = 'pointer';
        tr.onclick = () => window.location.href = `/bist100.html`;
        
        tr.innerHTML = `
            <td><button class="star-btn">☆</button></td>
            <td class="sym-name">${row.s}</td>
            <td style="text-align:right">${row.p.toFixed(2)} ₺</td>
            <td class="${cls}" style="text-align:right">${sign}${row.c}%</td>`;
        tbody.appendChild(tr);
    });
}

/* ---------- Halka Arzlar (SABİT VERİ) ---------- */
function loadIpoWidget() {
    const ipoContainer = document.getElementById('ipo-list');
    if (!ipoContainer) return;
    
    const mockIpos = [
        { title: "Limak Doğu Anadolu Çimento", date: "Talep Toplanıyor", slug: "limak" },
        { title: "Mogan Enerji", date: "Yakında", slug: "mogan" },
        { title: "Artemis Halı", date: "Onay Bekliyor", slug: "artemis" }
    ];

    ipoContainer.innerHTML = '';
    mockIpos.forEach(item => {
        const div = document.createElement('div');
        div.className = 'ipo-item';
        div.innerHTML = `<span class="ipo-name">${item.title}</span><span class="ipo-tarih">${item.date}</span>`;
        div.onclick = () => window.location.href = `/halkaarz.html`;
        ipoContainer.appendChild(div);
    });
}

/* ---------- Haber Akışı (SABİT VERİ) ---------- */
function initNews() {
    const newsContainer = document.getElementById('news-feed-container');
    const modal = document.getElementById('news-modal');
    if (!newsContainer) return;
    
    const mockNews = [
        { 
            title: "BIST 100 Endeksi 10.000 Puan Sınırında", 
            description: "Türkiye piyasaları pozitif ayrışmaya devam ediyor. Analistler 10.200 seviyesinin kritik direnç olduğunu belirtiyor.", 
            published: "15 dk önce" 
        },
        { 
            title: "Altın Fiyatlarında Ons Etkisi", 
            description: "Küresel piyasalarda ons altının değer kazanmasıyla birlikte gram altın yeni rekor seviyelere yaklaştı.", 
            published: "1 saat önce" 
        }
    ];

    newsContainer.innerHTML = '';
    mockNews.forEach(n => {
        const div = document.createElement('div');
        div.className = 'news-item';
        div.innerHTML = `
            <div class="news-title">${n.title}</div>
            <div class="news-preview">${n.description.substring(0, 70)}...</div>
            <div class="news-date">${n.published}</div>`;
        
        div.addEventListener('click', () => {
            if (document.getElementById('modal-title')) document.getElementById('modal-title').textContent = n.title;
            if (document.getElementById('modal-body')) document.getElementById('modal-body').innerHTML = n.description;
            if (modal) modal.classList.add('active');
        });
        newsContainer.appendChild(div);
    });
    
    const closeBtn = document.getElementById('modal-close');
    if (closeBtn) closeBtn.onclick = () => modal.classList.remove('active');
}

/* ---------- Grafik Motoru (SABİT VERİ) ---------- */
window.loadNativeChart = function(symbol, period, canvasId, color='#0f766e', bgColor='rgba(15, 118, 110, 0.1)') {
    let canvas = document.getElementById(canvasId);
    if(!canvas) return;
    let wrapper = canvas.parentElement;

    // Butonların aktiflik durumunu güncelle
    let intervals = wrapper.querySelector('.chart-intervals');
    if(intervals) {
        intervals.querySelectorAll('button').forEach(b => b.classList.remove('active'));
        let activeBtn = intervals.querySelector(`[data-p="${period}"]`);
        if(activeBtn) activeBtn.classList.add('active');
    }

    // Grafik Verisi
    const data = {
        dates: ['09:00', '11:00', '13:00', '15:00', '17:00', '18:00', 'Kapanış'],
        closes: [10100, 10250, 10180, 10320, 10450, 10380, 10400.50],
        current_price: 10400.50,
        change_pct: 1.25
    };

    // Fiyat ve Yüzde Güncelleme
    const priceEl = wrapper.querySelector('.chart-price');
    if(priceEl) {
        priceEl.innerHTML = `${data.current_price.toLocaleString('tr-TR')} ₺ 
        <span style="color:#10b981; font-weight:900; font-size:1.1rem; padding-left:0.5rem;">+${data.change_pct}%</span>`;
    }

    if (chartInstances[canvasId]) chartInstances[canvasId].destroy();

    const ctx = canvas.getContext('2d');
    chartInstances[canvasId] = new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.dates,
            datasets: [{
                label: symbol,
                data: data.closes,
                borderColor: '#10b981',
                backgroundColor: 'rgba(16, 185, 129, 0.1)',
                borderWidth: 2,
                fill: true,
                pointRadius: 0,
                tension: 0.3
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: { display: true, grid: { display: false } },
                y: { position: 'right', grid: { color: '#f1f5f9' } }
            }
        }
    });
};
