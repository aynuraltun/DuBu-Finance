/* =========================================
   DUBU FINANCE — Full Professional Logic
   ========================================= */

let userFavorites = new Set();
let chartInstances = {};

/* ---------- Burger & UI (Giriş/Kayıt Geri Geldi) ---------- */
function initUI() {
    const burgerBtn = document.getElementById('burger-btn');
    const burgerMenu = document.getElementById('burger-menu');
    
    // Burger Menü Tıklama Mekanizması
    if (burgerBtn && burgerMenu) {
        burgerBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            burgerBtn.classList.toggle('open');
            burgerMenu.classList.toggle('open');
        });
        document.addEventListener('click', (e) => {
            if (!burgerMenu.contains(e.target) && !burgerBtn.contains(e.target)) {
                burgerBtn.classList.remove('open');
                burgerMenu.classList.remove('open');
            }
        });
    }

    // Giriş / Kayıt / Kullanıcı Badge Yapısı
    const badge = document.getElementById('user-badge');
    const auth = document.getElementById('burger-auth');
    
    // Varsayılan olarak Giriş Yap linkini göster (Orijinal kodundaki gibi)
    if (badge) {
        badge.innerHTML = '<a href="/login" style="color:var(--color-primary);font-weight:700">Giriş Yap</a>';
    }
    if (auth) {
        auth.innerHTML = '<a href="/login">Giriş Yap</a> / <a href="/register">Kaydol</a>';
    }
}

/* ---------- Market Table (Açılış, En Düşük, En Yüksek Bilgileriyle) ---------- */
async function loadMarketTable() {
    const table = document.getElementById('market-table-home');
    if (!table) return;
    const tbody = table.querySelector('tbody');
    
    // BIST 100 Listesi
    const symbols = ["THYAO", "ASELS", "EREGL", "TUPRS", "SAHOL", "KCHOL", "SISE", "AKBNK", "ISCTR", "GARAN", "YKBNK", "BIMAS", "FROTO", "SASA", "HEKTS"];

    try {
        const res = await fetch('https://scanner.tradingview.com/turkey/scan', {
            method: 'POST',
            body: JSON.stringify({
                "symbols": { "tickers": symbols.map(s => `BIST:${s}`) },
                "columns": ["close", "change", "open", "high", "low"]
            })
        });
        const data = await res.json();
        
        tbody.innerHTML = '';
        data.data.forEach(row => {
            const sym = row.s.split(':')[1];
            const price = row.d[0].toFixed(2);
            const change = row.d[1].toFixed(2);
            const open = row.d[2].toFixed(2);
            const high = row.d[3].toFixed(2);
            const low = row.d[4].toFixed(2);
            
            const cls = change > 0 ? 'val-up' : (change < 0 ? 'val-down' : '');
            const sign = change > 0 ? '+' : '';
            
            const tr = document.createElement('tr');
            tr.style.cursor = 'pointer';
            tr.onclick = (e) => { if(e.target.tagName !== 'BUTTON') window.location.href=`/hisse/${sym}`; };
            
            const isFav = userFavorites.has(sym);
            tr.innerHTML = `
                <td><button class="star-btn ${isFav?'starred':''}" data-symbol="${sym}" onclick="event.stopPropagation();toggleFavorite('${sym}',this)">${isFav?'★':'☆'}</button></td>
                <td class="sym-name"><b>${sym}</b></td>
                <td style="text-align:right"><b>${price} ₺</b></td>
                <td class="${cls}" style="text-align:right">${sign}${change}%</td>
                <td style="text-align:right; font-size:0.85rem; color:#666">${open}</td>
                <td style="text-align:right; font-size:0.85rem; color:#10b981">${high}</td>
                <td style="text-align:right; font-size:0.85rem; color:#ef4444">${low}</td>
            `;
            tbody.appendChild(tr);
        });
    } catch(e) {
        tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;padding:2rem">Veriler yüklenemedi.</td></tr>';
    }
}

/* ---------- Diğer Fonksiyonlar (Orijinal Mantık) ---------- */
function toggleFavorite(symbol, btn) {
    if (userFavorites.has(symbol)) userFavorites.delete(symbol);
    else userFavorites.add(symbol);
    updateAllStars();
}

function updateAllStars() {
    document.querySelectorAll('.star-btn').forEach(btn => {
        const sym = btn.dataset.symbol;
        const fav = userFavorites.has(sym);
        btn.classList.toggle('starred', fav);
        btn.textContent = fav ? '★' : '☆';
    });
}

function initNews() {
    const newsContainer = document.getElementById('news-feed-container');
    if (!newsContainer) return;
    const news = [
        {title: "BIST 100 Rekor Kırdı", desc: "Havacılık ve bankacılık hisseleri öncülüğünde yükseliş sürüyor.", date: "10 dk önce"},
        {title: "Merkez Bankası Rezervleri", desc: "Swap hariç net rezervlerde iyileşme devam ediyor.", date: "1 sa önce"},
        {title: "Teknoloji Hisselerinde Hareket", desc: "Nasdaq etkisiyşe yerli teknoloji hisseleri primli.", date: "2 sa önce"},
        {title: "Altın Fiyatları", desc: "Ons altın jeopolitik risklerle 2300 dolar üzerinde.", date: "3 sa önce"},
        {title: "Otomotiv İhracat Rakamları", desc: "Mart ayında otomotiv sektörü ihracat lideri oldu.", date: "4 sa önce"},
        {title: "Halka Arz Takvimi", desc: "Bu hafta iki yeni şirketin talep toplaması başlıyor.", date: "5 sa önce"},
        {title: "Enerji Sektörü Analizi", desc: "Yenilenebilir enerji şirketleri yatırımcı markajında.", date: "6 sa önce"}
    ];
    newsContainer.innerHTML = news.map(n => `
        <div class="news-item">
            <div class="news-title">${n.title}</div>
            <div class="news-preview">${n.desc}</div>
            <div class="news-date">${n.date}</div>
        </div>
    `).join('');
}

function loadIpoWidget() {
    const ipoContainer = document.getElementById('ipo-list');
    if (!ipoContainer) return;
    const data = [
        {title: "Limak Doğu Anadolu Çimento", date: "22-23 Şubat", slug: "limak"},
        {title: "Mogan Enerji", date: "28-29 Şubat", slug: "mogan"},
        {title: "Artemis Halı", date: "Onay Bekliyor", slug: "artemis"}
    ];
    ipoContainer.innerHTML = data.map(item => `
        <div class="ipo-item" onclick="window.location.href='/halkaarz/${item.slug}'">
            <span class="ipo-name">${item.title}</span>
            <span class="ipo-tarih">${item.date}</span>
        </div>
    `).join('');
}

window.loadNativeChart = async function(symbol, period, canvasId) {
    let canvas = document.getElementById(canvasId);
    if(!canvas) return;
    try {
        const ticker = symbol === 'XU100' ? 'BIST:XU100' : `BIST:${symbol}`;
        const res = await fetch('https://scanner.tradingview.com/turkey/scan', {
            method: 'POST',
            body: JSON.stringify({ "symbols": { "tickers": [ticker] }, "columns": ["close", "change"] })
        });
        const data = await res.json();
        const price = data.data[0].d[0];
        const change = data.data[0].d[1];
        
        const priceEl = canvas.parentElement.querySelector('.chart-price');
        if(priceEl) {
            priceEl.innerHTML = `${price.toFixed(2)} ₺ <span style="color:${change>=0?'#10b981':'#ef4444'}">${change>=0?'+':''}${change.toFixed(2)}%</span>`;
        }
        
        if (chartInstances[canvasId]) chartInstances[canvasId].destroy();
        chartInstances[canvasId] = new Chart(canvas.getContext('2d'), {
            type: 'line',
            data: {
                labels: ['9:00', '12:00', '15:00', '18:00'],
                datasets: [{
                    data: [price*0.99, price*1.01, price*0.98, price],
                    borderColor: '#10b981', fill: true, backgroundColor: 'rgba(16, 185, 129, 0.1)', pointRadius: 0
                }]
            },
            options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } } }
        });
    } catch(e) {}
};

/* ---------- Başlatıcı ---------- */
document.addEventListener('DOMContentLoaded', () => {
    initUI();
    loadMarketTable();
    loadIpoWidget();
    initNews();
    if(document.getElementById('bistChart')) loadNativeChart('XU100', '1d', 'bistChart');
});
