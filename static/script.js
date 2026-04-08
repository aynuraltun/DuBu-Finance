/* =========================================
   DUBU FINANCE — Logic & API Integration
   (Orijinal Yapı Korundu - Statik Güvenli Mod)
   ========================================= */

let userFavorites = new Set();
let chartInstances = {};

/* ---------- Favori Sistemi (Orijinal Mantık) ---------- */
function updateAllStars() {
    document.querySelectorAll('.star-btn').forEach(btn => {
        const sym = btn.dataset.symbol;
        const fav = userFavorites.has(sym);
        btn.classList.toggle('starred', fav);
        btn.textContent = fav ? '★' : '☆';
    });
}

function showToast(msg) {
    let t = document.getElementById('custom-toast');
    if (!t) {
        t = document.createElement('div');
        t.id = 'custom-toast';
        t.className = 'toast-msg';
        document.body.appendChild(t);
    }
    t.innerHTML = '⚠️ ' + msg;
    t.classList.add('show');
    setTimeout(() => t.classList.remove('show'), 3000);
}

function toggleFavorite(symbol, btn) {
    // Vercel'de database olmadığı için yerel hafızayı kullanıyoruz
    if (userFavorites.has(symbol)) {
        userFavorites.delete(symbol);
    } else {
        userFavorites.add(symbol);
    }
    updateAllStars();
}

/* ---------- Burger & User (Orijinal Tasarım) ---------- */
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

    // Orijinal Badge yapısı
    const badge = document.getElementById('user-badge');
    const auth = document.getElementById('burger-auth');
    if (badge) {
        badge.innerHTML = `
            <div class="user-menu-wrap">
                <span style="font-weight:800; font-family:var(--font-display);">👤 Kullanıcı ▾</span>
                <div class="user-menu-dropdown">
                    <a href="/takip">⭐ Favorilerim</a>
                    <a href="/logout">🚪 Çıkış Yap</a>
                </div>
            </div>`;
    }
}

/* ---------- Market Table (Orijinal Mantık & Canlı Veri) ---------- */
async function loadMarketTable() {
    const table = document.getElementById('market-table-home');
    if (!table) return;
    const tbody = table.querySelector('tbody');
    
    // Tüm BIST100 hisselerini buraya ekleyebilirsin
    const symbols = ["THYAO", "ASELS", "EREGL", "TUPRS", "SAHOL", "KCHOL", "SISE", "AKBNK", "ISCTR", "GARAN", "YKBNK", "BIMAS", "FROTO", "SASA", "HEKTS"];

    try {
        const res = await fetch('https://scanner.tradingview.com/turkey/scan', {
            method: 'POST',
            body: JSON.stringify({
                "symbols": { "tickers": symbols.map(s => `BIST:${s}`) },
                "columns": ["close", "change"]
            })
        });
        const data = await res.json();
        
        tbody.innerHTML = '';
        data.data.forEach(row => {
            const sym = row.s.split(':')[1];
            const price = row.d[0].toFixed(2);
            const change = row.d[1].toFixed(2);
            const cls = change > 0 ? 'val-up' : (change < 0 ? 'val-down' : '');
            const sign = change > 0 ? '+' : '';
            const tr = document.createElement('tr');
            
            // Orijinal yönlendirme mantığı
            tr.onclick = (e) => { if(e.target.tagName !== 'BUTTON') window.location.href=`/hisse/${sym}`; };
            
            const isFav = userFavorites.has(sym);
            tr.innerHTML = `
                <td><button class="star-btn ${isFav?'starred':''}" data-symbol="${sym}" onclick="event.stopPropagation();toggleFavorite('${sym}',this)">${isFav?'★':'☆'}</button></td>
                <td class="sym-name">${sym}</td>
                <td style="text-align:right">${price} ₺</td>
                <td class="${cls}" style="text-align:right">${sign}${change}%</td>`;
            tbody.appendChild(tr);
        });
    } catch(e) {
        tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;padding:2rem">Veri yüklenemedi.</td></tr>';
    }
}

/* ---------- News Feed (Orijinal Modal Yapısı) ---------- */
function initNews() {
    const newsContainer = document.getElementById('news-feed-container');
    const modal = document.getElementById('news-modal');
    if (!newsContainer) return;
    
    const news = [
        {title: "BIST 100 Rekor Seviyede", description: "Endeks güne yükselişle başladı...", published: "10 dk önce"},
        {title: "Dolar/TL'de Yatay Seyir", description: "Piyasalar Merkez Bankası kararını bekliyor...", published: "1 sa önce"},
        {title: "Halka Arzlarda Yeni Dönem", description: "SPK'dan yeni düzenleme sinyalleri...", published: "2 sa önce"},
        {title: "Altın Fiyatları Hareketli", description: "Ons altın küresel risklerle primli...", published: "3 sa önce"},
        {title: "Otomotiv Verileri Açıklandı", description: "Mart ayında satışlar beklentiyi aştı...", published: "4 sa önce"},
        {title: "Enerji Yatırımları Artıyor", description: "Yenilenebilir enerjiye dev teşvik...", published: "5 sa önce"},
        {title: "Teknoloji Hisseleri Revaçta", description: "Yazılım şirketlerinde alımlar güçlendi...", published: "6 sa önce"}
    ];

    newsContainer.innerHTML = '';
    news.forEach(n => {
        const div = document.createElement('div');
        div.className = 'news-item';
        div.innerHTML = `<div class="news-title">${n.title}</div><div class="news-preview">${n.description}...</div><div class="news-date">${n.published}</div>`;
        div.addEventListener('click', () => {
            document.getElementById('modal-title').textContent = n.title;
            document.getElementById('modal-date').textContent = n.published;
            document.getElementById('modal-body').innerHTML = n.description;
            if (modal) modal.classList.add('active');
        });
        newsContainer.appendChild(div);
    });
    
    const closeBtn = document.getElementById('modal-close');
    if (closeBtn) closeBtn.onclick = () => modal.classList.remove('active');
}

/* ---------- Native Chart Tools (Orijinal Fonksiyon) ---------- */
window.loadNativeChart = async function(symbol, period, canvasId, color='#0f766e', bgColor='rgba(15, 118, 110, 0.1)') {
    let canvas = document.getElementById(canvasId);
    if(!canvas) return;
    let wrapper = canvas.parentElement;

    try {
        const ticker = symbol === 'XU100' ? 'BIST:XU100' : `BIST:${symbol}`;
        const response = await fetch('https://scanner.tradingview.com/turkey/scan', {
            method: 'POST',
            body: JSON.stringify({ "symbols": { "tickers": [ticker] }, "columns": ["close", "change"] })
        });
        const res = await response.json();
        const price = res.data[0].d[0];
        const change = res.data[0].d[1];

        const priceEl = wrapper.querySelector('.chart-price');
        if(priceEl) {
            priceEl.innerHTML = `${price.toLocaleString('tr-TR')} ₺ <span style="color:${change>=0?'#10b981':'#ef4444'}; font-weight:900;">${change>=0?'+':''}${change.toFixed(2)}%</span>`;
        }

        if (chartInstances[canvasId]) chartInstances[canvasId].destroy();
        const ctx = canvas.getContext('2d');
        chartInstances[canvasId] = new Chart(ctx, {
            type: 'line',
            data: {
                labels: ['9:00', '12:00', '15:00', '18:00'],
                datasets: [{
                    data: [price*0.99, price*0.98, price*1.01, price],
                    borderColor: change>=0?'#10b981':'#ef4444',
                    backgroundColor: change>=0?'rgba(16, 185, 129, 0.1)':'rgba(239, 68, 68, 0.1)',
                    fill: true, pointRadius: 0, tension: 0.3
                }]
            },
            options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } } }
        });
    } catch(e) {}
}

/* ---------- Halka Arz Widget (Orijinal Tasarım) ---------- */
function loadIpoWidget() {
    const ipoContainer = document.getElementById('ipo-list');
    if (!ipoContainer) return;
    
    const data = [
        {title: "Limak Doğu Anadolu Çimento", date: "22-23 Şubat", slug: "limak-cimento"},
        {title: "Mogan Enerji", date: "28-29 Şubat", slug: "mogan-enerji"}
    ];

    ipoContainer.innerHTML = '';
    data.forEach(item => {
        const div = document.createElement('div');
        div.className = 'ipo-item';
        div.style.cursor = 'pointer';
        div.onclick = () => window.location.href = `/halkaarz/${item.slug}`;
        div.innerHTML = `<span class="ipo-name">${item.title}</span><span class="ipo-tarih">${item.date}</span>`;
        ipoContainer.appendChild(div);
    });
}

/* ---------- DOMContentLoaded ---------- */
document.addEventListener('DOMContentLoaded', () => {
    initUI();
    loadMarketTable();
    loadIpoWidget();
    initNews();
    if(document.getElementById('bistChart')) loadNativeChart('XU100', '1d', 'bistChart');
});
