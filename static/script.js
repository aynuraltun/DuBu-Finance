/* =========================================
   DUBU FINANCE — Canlı BIST 100 Entegrasyonu
   ========================================= */

let chartInstances = {};

/* ---------- Başlatıcı ---------- */
document.addEventListener('DOMContentLoaded', () => {
    initUI();
    loadMarketTable(); // BIST 100 listesini yükle
    loadIpoWidget();
    initNews();
    
    if (document.getElementById('bistChart')) {
        loadNativeChart('XU100', '1d', 'bistChart');
    }
});

/* ---------- Menü ve UI ---------- */
function initUI() {
    const burgerBtn = document.getElementById('burger-btn');
    const burgerMenu = document.getElementById('burger-menu');
    if (burgerBtn && burgerMenu) {
        burgerBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            burgerBtn.classList.toggle('open');
            burgerMenu.classList.toggle('open');
        });
    }
}

/* ---------- Canlı BIST 100 Tablosu ---------- */
async function loadMarketTable() {
    const table = document.getElementById('market-table-home');
    if (!table) return;
    const tbody = table.querySelector('tbody');

    // BIST 100'ün en önemli hisseleri (Listenin tamamını buraya ekleyebilirsin)
    const bistHisseler = [
        "THYAO", "ASELS", "EREGL", "TUPRS", "SAHOL", "KCHOL", "SISE", "AKBNK", "ISCTR", "GARAN",
        "YKBNK", "BIMAS", "FROTO", "TOASO", "ARCLK", "PETKM", "SASA", "HEKTS", "PGSUS", "EKGYO",
        "ENKAI", "KARDM", "BORSANEWS", "ASTOR", "KONTR", "SMRTG", "ALARK", "GUBRF", "ODAS", "KOZAL"
    ];

    try {
        // Ücretsiz TradingView tarama API'sini kullanarak güncel verileri çekiyoruz
        const response = await fetch('https://scanner.tradingview.com/turkey/scan', {
            method: 'POST',
            body: JSON.stringify({
                "symbols": { "tickers": bistHisseler.map(s => `BIST:${s}`) },
                "columns": ["close", "change", "change_abs"]
            })
        });
        const res = await response.json();
        
        tbody.innerHTML = '';
        res.data.forEach(row => {
            const sym = row.s.split(':')[1];
            const price = row.d[0].toFixed(2);
            const change = row.d[1].toFixed(2);
            const cls = change > 0 ? 'val-up' : (change < 0 ? 'val-down' : '');
            const sign = change > 0 ? '+' : '';

            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td><button class="star-btn">☆</button></td>
                <td class="sym-name">${sym}</td>
                <td style="text-align:right">${price} ₺</td>
                <td class="${cls}" style="text-align:right">${sign}${change}%</td>`;
            tbody.appendChild(tr);
        });
    } catch (e) {
        console.error("Veri çekilemedi:", e);
        tbody.innerHTML = '<tr><td colspan="4" style="text-align:center">Veriler şu an güncellenemiyor.</td></tr>';
    }
}

/* ---------- Canlı Grafik Motoru (TradingView Kaynaklı) ---------- */
window.loadNativeChart = async function(symbol, period, canvasId) {
    let canvas = document.getElementById(canvasId);
    if(!canvas) return;
    const wrapper = canvas.parentElement;
    const priceEl = wrapper.querySelector('.chart-price');

    try {
        // Güncel endeks verisini çek
        const ticker = symbol === 'XU100' ? 'BIST:XU100' : `BIST:${symbol}`;
        const response = await fetch('https://scanner.tradingview.com/turkey/scan', {
            method: 'POST',
            body: JSON.stringify({ "symbols": { "tickers": [ticker] }, "columns": ["close", "change"] })
        });
        const res = await response.json();
        const livePrice = res.data[0].d[0];
        const liveChange = res.data[0].d[1];

        if(priceEl) {
            const color = liveChange >= 0 ? '#10b981' : '#ef4444';
            priceEl.innerHTML = `${livePrice.toLocaleString('tr-TR')} ₺ 
            <span style="color:${color}; font-weight:900; font-size:1.1rem; padding-left:0.5rem;">
                ${liveChange >= 0 ? '+' : ''}${liveChange.toFixed(2)}%
            </span>`;
        }

        // Grafik Çizimi (SABİT VERİ + CANLI FİYAT)
        if (chartInstances[canvasId]) chartInstances[canvasId].destroy();
        const ctx = canvas.getContext('2d');
        chartInstances[canvasId] = new Chart(ctx, {
            type: 'line',
            data: {
                labels: ['09:00', '11:00', '13:00', '15:00', '17:00', 'Şu an'],
                datasets: [{
                    data: [10100, 10250, 10180, 10320, 10450, livePrice],
                    borderColor: liveChange >= 0 ? '#10b981' : '#ef4444',
                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                    fill: true, tension: 0.3, pointRadius: 0
                }]
            },
            options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } } }
        });
    } catch(e) { console.error("Grafik verisi alınamadı"); }
};

/* ---------- Haberler ve Halka Arzlar (Statik - Çünkü API Gerektirir) ---------- */
function loadIpoWidget() {
    const container = document.getElementById('ipo-list');
    if (!container) return;
    container.innerHTML = `
        <div class="ipo-item"><span>Limak Doğu Anadolu</span><span class="ipo-tarih">Talep Toplanıyor</span></div>
        <div class="ipo-item"><span>Mogan Enerji</span><span class="ipo-tarih">Yakında</span></div>`;
}

function initNews() {
    const container = document.getElementById('news-feed-container');
    if (!container) return;
    container.innerHTML = `
        <div class="news-item"><div class="news-title">BIST 100 Rekora Koşuyor</div><div class="news-date">Canlı</div></div>
        <div class="news-item"><div class="news-title">FED Faiz Kararı Bekleniyor</div><div class="news-date">1 sa önce</div></div>`;
}
