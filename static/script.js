/* =========================================
   DUBU FINANCE — Logic (Sabit Veri Modu)
   ========================================= */

let userFavorites = new Set();

// Favoriler, Kullanıcı ve Haberler için boş fonksiyonlar (Hata vermemesi için)
async function loadFavorites() { }
function initUI() { 
    const badge = document.getElementById('user-badge');
    if (badge) badge.innerHTML = '<span style="color:var(--color-primary);font-weight:700">Demo Modu</span>';
}
function loadIpoWidget() {
    const ipoContainer = document.getElementById('ipo-list');
    if (ipoContainer) ipoContainer.innerHTML = '<p style="color:#999;padding:1rem">Arz takvimi yakında güncellenecek.</p>';
}
function initNews() {
    const newsContainer = document.getElementById('news-feed-container');
    if (newsContainer) newsContainer.innerHTML = '<p style="color:#999;padding:1.5rem">Güncel haber bulunmuyor.</p>';
}

/* ---------- Market Table (SABİT VERİ) ---------- */
function loadMarketTable() {
    const table = document.getElementById('market-table-home');
    if (!table) return;
    const tbody = table.querySelector('tbody');
    
    // API yerine buradaki veriler görünecek
    const mockData = [
        { s: "THYAO", p: 285.50, c: 1.25 },
        { s: "ASELS", p: 58.30, c: -0.45 },
        { s: "EREGL", p: 45.12, c: 0.85 },
        { s: "TUPRS", p: 165.40, c: 2.10 },
        { s: "SASANI", p: 38.20, c: -1.20 }
    ];

    tbody.innerHTML = '';
    mockData.forEach(row => {
        const cls = row.c > 0 ? 'val-up' : (row.c < 0 ? 'val-down' : '');
        const sign = row.c > 0 ? '+' : '';
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><button class="star-btn">☆</button></td>
            <td class="sym-name">${row.s}</td>
            <td style="text-align:right">${row.p.toFixed(2)} ₺</td>
            <td class="${cls}" style="text-align:right">${sign}${row.c}%</td>`;
        tbody.appendChild(tr);
    });
}

/* ---------- Native Chart (SABİT VERİ) ---------- */
let chartInstances = {};

window.loadNativeChart = function(symbol, period, canvasId, color='#0f766e', bgColor='rgba(15, 118, 110, 0.1)') {
    let canvas = document.getElementById(canvasId);
    if(!canvas) return;
    let wrapper = canvas.parentElement;

    // Aktif buton görseli
    let intervals = wrapper.querySelector('.chart-intervals');
    if(intervals) {
        intervals.querySelectorAll('button').forEach(b => b.classList.remove('active'));
        let activeBtn = intervals.querySelector(`[data-p="${period}"]`);
        if(activeBtn) activeBtn.classList.add('active');
    }

    // Grafik için sabit veri
    const data = {
        dates: ['09:00', '11:00', '13:00', '15:00', '17:00', '18:00', 'Kapanış'],
        closes: [9800, 9950, 9750, 10100, 10250, 10300, 10400.50],
        current_price: 10400.50,
        change_pct: 1.25
    };

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
                x: { display: true },
                y: { position: 'right', grid: { color: '#f1f5f9' } }
            }
        }
    });
};

/* ---------- Başlatıcı ---------- */
document.addEventListener('DOMContentLoaded', () => {
    initUI();
    loadMarketTable();
    loadIpoWidget();
    initNews();
    // İlk grafiği yükle
    loadNativeChart('XU100', '6mo', 'bistChart');
});
