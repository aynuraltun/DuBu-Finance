/* =========================================
   DUBU FINANCE — Full Professional Logic
   ========================================= */

// Apply theme immediately to prevent flashing
if (localStorage.getItem('theme') === 'dark') {
    document.body.classList.add('dark-theme');
}

let userFavorites = new Set();
let chartInstances = {};

/* ---------- Burger & UI ---------- */
function initUI() {
    console.log("initUI started");
    const burgerBtn = document.getElementById('burger-btn');
    const burgerMenu = document.getElementById('burger-menu');
    
    if (burgerBtn && burgerMenu) {
        console.log("Burger elements found");
        burgerBtn.onclick = (e) => {
            console.log("Burger clicked");
            e.stopPropagation();
            burgerBtn.classList.toggle('open');
            burgerMenu.classList.toggle('open');
        };

        document.addEventListener('click', (e) => {
            if (!burgerMenu.contains(e.target) && !burgerBtn.contains(e.target)) {
                burgerBtn.classList.remove('open');
                burgerMenu.classList.remove('open');
            }
        });
    } else {
        console.error("Burger elements not found:", {burgerBtn, burgerMenu});
    }

    // Inject Theme Toggle Switch inside the burger menu if not exists
    if (burgerMenu && !document.getElementById('theme-toggle-container')) {
        const switchDiv = document.createElement('div');
        switchDiv.id = 'theme-toggle-container';
        switchDiv.className = 'theme-switch-container';
        switchDiv.innerHTML = `
            <span style="color:var(--color-primary); font-weight:700; display:flex; align-items:center; gap:0.5rem;">🌓 Karanlık Tema</span>
            <label class="switch">
                <input type="checkbox" id="theme-toggle-checkbox">
                <span class="slider round"></span>
            </label>
        `;
        burgerMenu.appendChild(switchDiv);

        const checkbox = document.getElementById('theme-toggle-checkbox');
        const isDark = document.body.classList.contains('dark-theme');
        checkbox.checked = isDark;

        checkbox.onchange = () => {
            const currentlyDark = document.body.classList.toggle('dark-theme');
            localStorage.setItem('theme', currentlyDark ? 'dark' : 'light');
        };
    }

    // Giriş / Kayıt / Kullanıcı Badge Yapısı (Hesabım Dropdown Menüsü ile)
    fetch('/api/user')
        .then(r => r.json())
        .then(data => {
            const badge = document.getElementById('user-badge');
            const auth = document.getElementById('burger-auth');
            if (data.user) {
                if (badge) {
                    badge.innerHTML = `
                        <div class="user-menu-wrap">
                            <span style="color:var(--color-primary);font-weight:700">👤 Hesabım (${data.user}) ▼</span>
                            <div class="user-menu-dropdown">
                                <a href="/portfolio">📈 Akıllı Varlık Yönetimi</a>
                                <a href="/takip">⭐ İzleme Listesi</a>
                                <a href="/logout">🚪 Çıkış Yap</a>
                            </div>
                        </div>
                    `;
                }
                if (auth) auth.innerHTML = `<a href="/logout">Oturumu Kapat (${data.user})</a>`;
            } else {
                if (badge) badge.innerHTML = '<a href="/login" style="color:var(--color-primary);font-weight:700">Giriş Yap</a>';
                if (auth) auth.innerHTML = '<a href="/login">Giriş Yap</a> / <a href="/register">Kaydol</a>';
            }
        });

    // Favorileri yükle
    fetch('/api/favorites').then(r => r.json()).then(data => {
        if (data.favorites) {
            userFavorites = new Set(data.favorites);
            updateAllStars();
        }
    });
}

/* ---------- Market Table ---------- */
async function loadMarketTable() {
    const table = document.getElementById('market-table-home');
    if (!table) return;
    const tbody = table.querySelector('tbody');
    
    try {
        const res = await fetch('/api/screener');
        const data = await res.json();
        
        tbody.innerHTML = '';
        if (!data.data || !data.data.length) {
            tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;padding:2rem">Veri yüklenemedi.</td></tr>';
            return;
        }

        data.data.slice(0, 15).forEach(row => {
            const sym = row.s.split(':')[1];
            const price = row.d[1].toFixed(2);
            const change = row.d[2].toFixed(2);
            
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
            `;
            tbody.appendChild(tr);
        });
    } catch(e) {
        tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;padding:2rem">Hata oluştu.</td></tr>';
    }
}

async function toggleFavorite(symbol, btn) {
    const isFav = userFavorites.has(symbol);
    const method = isFav ? 'DELETE' : 'POST';
    
    const resp = await fetch(`/api/favorites/${symbol}`, { method });
    if (resp.ok) {
        if (isFav) userFavorites.delete(symbol);
        else userFavorites.add(symbol);
        updateAllStars();
    } else {
        alert("Lütfen önce giriş yapın.");
        window.location.href = "/login";
    }
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
    const modal = document.getElementById('news-modal');
    if (!newsContainer) return;
    
    fetch('/api/news').then(r => r.json()).then(news => {
        newsContainer.innerHTML = '';
        news.forEach(n => {
            const div = document.createElement('div');
            div.className = 'news-item';
            
            const sentimentHtml = n.sentiment_text ? `
                <div style="font-size: 0.85rem; font-weight: 700; color: ${n.sentiment_color}; margin-top: 0.3rem; margin-bottom: 0.5rem; display:flex; align-items:center; gap:0.4rem;">
                    ${n.sentiment_icon} <span style="opacity:0.9">${n.sentiment_text}</span>
                </div>` : '';

            div.innerHTML = `
                <div class="news-title">${n.title}</div>
                ${sentimentHtml}
                <div class="news-date" style="margin-top:0.5rem;">${n.published}</div>
            `;
            
            div.addEventListener('click', () => {
                document.getElementById('modal-title').textContent = n.title;
                document.getElementById('modal-body').innerHTML = n.description;
                if (modal) modal.classList.add('active');
            });
            newsContainer.appendChild(div);
        });
    });
    
    const closeBtn = document.getElementById('modal-close');
    if (closeBtn) {
        closeBtn.onclick = () => {
            if (modal) modal.classList.remove('active');
        };
    }
}

function loadIpoWidget() {
    const ipoContainer = document.getElementById('ipo-list');
    if (!ipoContainer) return;
    fetch('/api/halkaarz').then(r => r.json()).then(data => {
        if (!data || data.length === 0) {
            ipoContainer.innerHTML = '<p style="color:#999;padding:1rem 0;font-size:0.9rem;text-align:center;">Aktif halka arz bulunmuyor.</p>';
            return;
        }
        ipoContainer.innerHTML = data.map(item => `
            <div class="ipo-item" onclick="window.location.href='/halkaarz/${item.slug}'" style="display:flex; justify-content:space-between; align-items:center; padding: 0.8rem 1rem;">
                <div>
                    <span class="ipo-name" style="font-weight:700; color:var(--color-primary); font-size:0.88rem; display:block; margin-bottom: 0.2rem;">${item.title}</span>
                    <span class="ipo-tarih" style="font-size:0.75rem; color:#64748b;">📅 ${item.date}</span>
                </div>
                <div style="text-align:right;">
                    <span style="font-weight:700; font-family:var(--font-data); font-size:0.78rem; background:rgba(245,158,11,0.1); color:#d97706; padding:0.2rem 0.5rem; border-radius:4px; border:1px solid rgba(245,158,11,0.2); white-space: nowrap;">${item.fiyat}</span>
                </div>
            </div>
        `).join('');
    });
}

window.loadNativeChart = async function(symbol, period, canvasId, color='#10b981', bgColor='rgba(16, 185, 129, 0.1)', isMetal=false) {
    let canvas = document.getElementById(canvasId);
    if(!canvas) return;
    try {
        const parentContainer = canvas.closest('.card') || canvas.parentElement.parentElement;
        const intervalsContainer = parentContainer.querySelector('.chart-intervals');
        if (intervalsContainer) {
            intervalsContainer.querySelectorAll('button').forEach(btn => {
                const btnPeriod = btn.dataset.p || (btn.getAttribute('onclick') ? btn.getAttribute('onclick').match(/'([^']+)'/)[1] : null);
                btn.classList.toggle('active', btnPeriod === period);
            });
        }

        const res = await fetch(`/api/chart/${symbol}?period=${period}`);
        const data = await res.json();
        
        if (data.error) return;

        const priceEl = parentContainer.querySelector('.chart-price');
        if(priceEl) {
            const suffix = '₺';
            priceEl.innerHTML = `${data.current_price.toLocaleString('tr-TR')} ${suffix} <span style="color:${data.change_pct>=0?'#10b981':'#ef4444'}">${data.change_pct>=0?'+':''}${data.change_pct}%</span>`;
        }
        
        if (chartInstances[canvasId]) chartInstances[canvasId].destroy();
        chartInstances[canvasId] = new Chart(canvas.getContext('2d'), {
            type: 'line',
            data: {
                labels: data.dates,
                datasets: [{
                    data: data.closes,
                    borderColor: color, 
                    fill: true, 
                    backgroundColor: bgColor, 
                    pointRadius: 0,
                    borderWidth: 2,
                    tension: 0.3
                }]
            },
            options: { 
                responsive: true, 
                maintainAspectRatio: false, 
                plugins: { 
                    legend: { display: false },
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                        callbacks: {
                            label: function(ctx) { return ctx.parsed.y + ' ₺'; }
                        }
                    }
                },
                interaction: { mode: 'index', intersect: false },
                scales: {
                    x: { display: true, grid: { display: false }, ticks: { maxRotation: 0, autoSkip: true, maxTicksLimit: 6, color: '#888' } },
                    y: { display: true, position: 'right', grid: { color: 'rgba(200,200,200,0.1)' }, ticks: { color: '#888' } }
                }
            }
        });
        
        const periodStats = parentContainer.querySelector('.period-stats') || parentContainer.querySelector('#pnl-badge') || document.getElementById('pnl-badge');
        if(periodStats) {
            if (symbol === 'XU100') {
                periodStats.innerHTML = "";
                periodStats.style.display = "none";
            } else {
                periodStats.style.display = ""; // Reset display
                const firstPrice = data.closes[0] || 1;
                const currPrice = data.current_price;
                const absDiff = currPrice - firstPrice;
                const sign = absDiff >= 0 ? '+' : '';
                const colorClass = absDiff >= 0 ? '#10b981' : '#ef4444';
                const bgClass = absDiff >= 0 ? 'rgba(16,185,129,0.1)' : 'rgba(239,68,68,0.1)';
                const labelText = absDiff >= 0 ? 'KAR' : 'ZARAR';
                periodStats.innerHTML = `<span style="color:${colorClass}; font-weight:900; background: ${bgClass}; padding: 0.4rem 0.8rem; border-radius: 8px; border: 1px solid ${colorClass}50;">Dönem Getirisi: ${sign}${absDiff.toLocaleString('tr-TR', {minimumFractionDigits:2, maximumFractionDigits:2})} ₺ (${sign}${data.change_pct.toFixed(2)}%) - ${labelText}</span>`;
            }
        }
    } catch(e) {}
};

async function loadHomeMetals() {
    const container = document.getElementById('metals-mini-list');
    const usdCard = document.getElementById('curr-usdtry');
    const eurCard = document.getElementById('curr-eurtry');
    const gbpCard = document.getElementById('curr-gbptry');
    if(!container && !usdCard) return;
    try {
        const resp = await fetch('/api/metals');
        const data = await resp.json();
        
        if (container) {
            container.innerHTML = '';
            data.slice(0, 4).forEach(m => {
                const isUp = m.change >= 0;
                const changeClass = isUp ? 'val-up' : 'val-down';
                const changeIcon = isUp ? '▲' : '▼';
                
                let priceHtml = `<div style="font-weight:700; font-family:var(--font-data); font-size:0.95rem;">${m.price.toLocaleString('tr-TR')} ${m.unit}</div>`;
                if (m.has_bid_ask) {
                    priceHtml = `
                        <div style="font-size:0.78rem; color:var(--color-text); opacity:0.8; font-weight:700; line-height:1.2;">A: ${m.alis.toLocaleString('tr-TR')} ${m.unit}</div>
                        <div style="font-weight:900; font-family:var(--font-data); font-size:0.88rem; color:var(--color-text); line-height:1.2; margin-top:0.1rem;">S: ${m.satis.toLocaleString('tr-TR')} ${m.unit}</div>
                    `;
                }
                
                container.innerHTML += `
                    <div class="ipo-item" style="display:flex; justify-content:space-between; align-items:center; padding: 0.8rem 1rem;">
                        <div>
                            <div style="font-weight:700; color:var(--color-primary); font-size:0.88rem;">${m.name}</div>
                            <div style="font-size:0.75rem; color:var(--color-muted); font-weight:700;">${m.symbol}</div>
                        </div>
                        <div style="text-align:right;">
                            ${priceHtml}
                            <div class="${changeClass}" style="font-size:0.75rem; font-weight:800; margin-top:0.2rem;">${changeIcon} ${m.change.toFixed(2)}%</div>
                        </div>
                    </div>
                `;
            });
        }
        
        if (usdCard || eurCard || gbpCard) {
            data.forEach(item => {
                let card = null;
                let valId = '';
                let pctId = '';
                if (item.symbol === 'USDTRY') { card = usdCard; valId = 'usd-val'; pctId = 'usd-pct'; }
                else if (item.symbol === 'EURTRY') { card = eurCard; valId = 'eur-val'; pctId = 'eur-pct'; }
                else if (item.symbol === 'GBPTRY') { card = gbpCard; valId = 'gbp-val'; pctId = 'gbp-pct'; }
                
                if (card) {
                    const valEl = document.getElementById(valId);
                    const pctEl = document.getElementById(pctId);
                    if (valEl) valEl.textContent = `${item.price.toFixed(4)} ₺`;
                    if (pctEl) {
                        const isUp = item.change >= 0;
                        pctEl.className = `curr-pct ${isUp ? 'val-up' : 'val-down'}`;
                        pctEl.textContent = `${isUp ? '▲' : '▼'} ${item.change.toFixed(2)}%`;
                    }
                }
            });
        }
    } catch(e) {
        if (container) container.innerHTML = '<p style="color:#ef4444;padding:1rem 0">Yüklenemedi.</p>';
    }
}

async function loadHomeFunds() {
    const container = document.getElementById('funds-mini-list');
    if(!container) return;
    try {
        const resp = await fetch('/api/funds');
        const data = await resp.json();
        container.innerHTML = '';
        const popular = ["MAC", "AFT", "TCD", "YZG"];
        const filtered = data.filter(f => popular.includes(f.symbol));
        (filtered.length ? filtered : data.slice(0, 4)).forEach(f => {
            const isUp = f.change >= 0;
            const changeClass = isUp ? 'val-up' : 'val-down';
            const changeIcon = isUp ? '▲' : '▼';
            container.innerHTML += `
                <div class="ipo-item" style="display:flex; justify-content:space-between; align-items:center; padding: 0.8rem 1rem;">
                    <div>
                        <div style="font-weight:700; color:var(--color-primary); font-size:0.88rem;">${f.symbol}</div>
                        <div style="font-size:0.72rem; color:#64748b; text-overflow:ellipsis; overflow:hidden; white-space:nowrap; max-width:150px;">${f.name}</div>
                    </div>
                    <div style="text-align:right;">
                        <div style="font-weight:700; font-family:var(--font-data); font-size:0.95rem;">${f.price.toLocaleString('tr-TR')} ₺</div>
                        <div class="${changeClass}" style="font-size:0.78rem; font-weight:700;">${changeIcon} ${f.change.toFixed(2)}%</div>
                    </div>
                </div>
            `;
        });
    } catch(e) {
        container.innerHTML = '<p style="color:#ef4444;padding:1rem 0">Yüklenemedi.</p>';
    }
}

document.addEventListener('DOMContentLoaded', () => {
    initUI();
    loadMarketTable();
    loadIpoWidget();
    initNews();
    loadHomeMetals();
    setInterval(loadHomeMetals, 185);
    loadHomeFunds();
    if(document.getElementById('bistChart')) loadNativeChart('XU100', '6mo', 'bistChart', '#0f766e', 'rgba(15, 118, 110, 0.1)');

    const socketScript = document.createElement('script');
    socketScript.src = "https://cdn.socket.io/4.5.4/socket.io.min.js";
    document.head.appendChild(socketScript);
    socketScript.onload = () => {
        if(typeof io !== 'undefined') {
             const socket = io();
             socket.on('price_update', (data) => {
                 Object.keys(data).forEach(sym => {
                     // Canlı döviz kartlarını güncelle
                     const card = document.getElementById(`curr-${sym.toLowerCase()}`);
                     if (card) {
                         const update = data[sym];
                         const valId = sym.substring(0, 3).toLowerCase() + '-val';
                         const valEl = document.getElementById(valId);
                         if (valEl) {
                             let currentVal = parseFloat(valEl.textContent.replace(' ₺', ''));
                             if (!isNaN(currentVal)) {
                                 let multiplier = 1 + (update.direction * update.pct);
                                 let newVal = currentVal * multiplier;
                                 valEl.textContent = `${newVal.toFixed(4)} ₺`;
                             }
                         }
                     }
                 });
             });
        }
    };
});

window.loadMonteCarloChart = async function(symbol, canvasId) {
    let canvas = document.getElementById(canvasId);
    if(!canvas) return;
    try {
        const parentContainer = canvas.closest('.card') || canvas.parentElement.parentElement;
        const intervalsContainer = parentContainer.querySelector('.chart-intervals');
        if (intervalsContainer) {
            intervalsContainer.querySelectorAll('button').forEach(btn => {
                const btnPeriod = btn.dataset.p || (btn.getAttribute('onclick') ? btn.getAttribute('onclick').match(/'([^']+)'/)[1] : null);
                btn.classList.toggle('active', btnPeriod === 'montecarlo');
            });
        }

        // Display loading state on the canvas
        const ctx = canvas.getContext('2d');
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        
        // Hide standard pnl badge or update it
        const periodStats = parentContainer.querySelector('.period-stats') || parentContainer.querySelector('#pnl-badge') || document.getElementById('pnl-badge');
        if(periodStats) {
            periodStats.innerHTML = `<span style="color:#0f766e; font-weight:900; background: rgba(15,118,110,0.1); padding: 0.4rem 0.8rem; border-radius: 8px; border: 1px solid rgba(15,118,110,0.3); font-size:0.85rem;">🔮 AI Beklenti Yapay Zeka Simülasyonu Hazırlanıyor...</span>`;
        }

        const res = await fetch(`/api/montecarlo/${symbol}`);
        const data = await res.json();
        
        if (data.error) {
            if(periodStats) periodStats.innerHTML = `<span style="color:#ef4444; font-size:0.85rem;">Hata: ${data.error}</span>`;
            return;
        }

        // Show stats badge
        if(periodStats) {
            periodStats.innerHTML = `
                <div style="display:flex; flex-wrap:wrap; gap: 0.5rem; font-size: 0.85rem;">
                    <span style="color:#0f766e; font-weight:900; background: rgba(15,118,110,0.06); padding: 0.4rem 0.8rem; border-radius: 8px; border: 1px solid rgba(15,118,110,0.2);">
                        🔮 Beklenen Ortalama: ${data.expected_final.toLocaleString('tr-TR')} ₺
                    </span>
                    <span style="color:#10b981; font-weight:900; background: rgba(16,185,129,0.06); padding: 0.4rem 0.8rem; border-radius: 8px; border: 1px solid rgba(16,185,129,0.2);">
                        🚀 İyimser Durum (%80 Olasılık): ${data.bullish.toLocaleString('tr-TR')} ₺
                    </span>
                    <span style="color:#ef4444; font-weight:900; background: rgba(239,68,68,0.06); padding: 0.4rem 0.8rem; border-radius: 8px; border: 1px solid rgba(239,68,68,0.2);">
                        📉 Kötümser Durum (%20 Olasılık): ${data.bearish.toLocaleString('tr-TR')} ₺
                    </span>
                </div>
            `;
        }

        // Combine history dates and future dates for X-axis labels
        const allDates = [...data.history_dates, ...data.future_dates];
        const datasets = [];

        // 1. Add simulated paths (thin semi-transparent lines)
        data.paths.forEach((path, index) => {
            const pathData = new Array(data.history_closes.length - 1).fill(null);
            pathData.push(...path);

            datasets.push({
                data: pathData,
                borderColor: index % 2 === 0 ? 'rgba(15, 118, 110, 0.15)' : 'rgba(217, 119, 6, 0.15)', // Alternating turquoise and orange
                borderWidth: 1,
                pointRadius: 0,
                fill: false,
                tension: 0.3
            });
        });

        // 2. Add history data (thick solid turquoise line)
        const histData = [...data.history_closes];
        const padArray = new Array(data.future_dates.length).fill(null);
        histData.push(...padArray);

        datasets.push({
            label: 'Tarihsel Fiyat (Son 30 Gün)',
            data: histData,
            borderColor: '#0f766e',
            borderWidth: 4,
            pointRadius: 0,
            fill: false,
            tension: 0.1
        });

        // 3. Add expected final trajectory (thick dotted line connecting last price to expected final)
        const expectedData = new Array(data.history_closes.length - 1).fill(null);
        const lastPrice = data.last_price;
        const steps = data.future_dates.length;
        expectedData.push(lastPrice);
        for(let i = 1; i <= steps; i++) {
            const val = lastPrice + ((data.expected_final - lastPrice) / steps) * i;
            expectedData.push(val);
        }

        datasets.push({
            label: 'Beklenen Ortalama Rota',
            data: expectedData,
            borderColor: '#d97706', // Golden secondary color
            borderWidth: 3,
            borderDash: [6, 6],
            pointRadius: 0,
            fill: false,
            tension: 0.2
        });

        if (chartInstances[canvasId]) chartInstances[canvasId].destroy();
        chartInstances[canvasId] = new Chart(canvas.getContext('2d'), {
            type: 'line',
            data: {
                labels: allDates,
                datasets: datasets
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: true,
                        labels: {
                            filter: function(item) {
                                return item.text === 'Tarihsel Fiyat (Son 30 Gün)' || item.text === 'Beklenen Ortalama Rota';
                            },
                            font: { weight: 'bold' }
                        }
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                        callbacks: {
                            label: function(ctx) {
                                if (ctx.dataset.label) {
                                    return ctx.dataset.label + ': ' + ctx.parsed.y.toLocaleString('tr-TR') + ' ₺';
                                }
                                return null;
                            }
                        }
                    }
                },
                interaction: { mode: 'index', intersect: false },
                scales: {
                    x: { display: true, grid: { display: false }, ticks: { maxRotation: 0, autoSkip: true, maxTicksLimit: 8, color: '#888' } },
                    y: { display: true, position: 'right', grid: { color: 'rgba(200,200,200,0.1)' }, ticks: { color: '#888' } }
                }
            }
        });

    } catch(e) {
        console.error(e);
    }
};

window.initLiveDepthSimulation = function(basePrice) {
    const depthAsks = document.getElementById('depth-asks');
    const depthBids = document.getElementById('depth-bids');
    const depthTrades = document.getElementById('depth-trades');
    const depthSpread = document.getElementById('depth-spread');
    if(!depthAsks || !depthBids || !depthTrades) return;

    let currentPrice = basePrice;
    
    const generateRows = (isAsk) => {
        let rows = [];
        let priceOffset = 0.05;
        for(let i=0; i<5; i++) {
            const price = isAsk ? (currentPrice + priceOffset) : (currentPrice - priceOffset);
            const size = Math.floor(Math.random() * 1800) + 100;
            const pct = Math.min(100, Math.floor((size / 2000) * 100));
            rows.push({ price, size, pct });
            priceOffset += 0.05;
        }
        return rows;
    };

    const renderBook = (asks, bids) => {
        depthAsks.innerHTML = asks.map(row => `
            <div style="position:relative; display:flex; justify-content:space-between; padding:0.2rem 0.4rem; font-size:0.75rem; font-family:monospace; font-weight:700;">
                <div style="position:absolute; right:0; top:0; height:100%; width:${row.pct}%; background:rgba(239,68,68,0.08); z-index:1;"></div>
                <span style="color:#ef4444; z-index:2;">${row.price.toFixed(2)}</span>
                <span style="color:var(--color-primary); z-index:2; font-size:0.7rem; font-weight:600; opacity:0.8;">${row.size}</span>
            </div>
        `).join('');

        depthBids.innerHTML = bids.map(row => `
            <div style="position:relative; display:flex; justify-content:space-between; padding:0.2rem 0.4rem; font-size:0.75rem; font-family:monospace; font-weight:700;">
                <div style="position:absolute; right:0; top:0; height:100%; width:${row.pct}%; background:rgba(16,185,129,0.08); z-index:1;"></div>
                <span style="color:#10b981; z-index:2;">${row.price.toFixed(2)}</span>
                <span style="color:var(--color-primary); z-index:2; font-size:0.7rem; font-weight:600; opacity:0.8;">${row.size}</span>
            </div>
        `).join('');

        const spread = asks[0].price - bids[0].price;
        depthSpread.innerText = `Makas (Spread): ${spread.toFixed(2)} ₺`;
    };

    let asks = generateRows(true);
    let bids = generateRows(false);
    renderBook(asks, bids);

    const intervalId = setInterval(() => {
        if (!document.getElementById('depth-asks')) {
            clearInterval(intervalId);
            return;
        }

        const change = (Math.random() - 0.5) * 0.1;
        currentPrice += change;
        if(currentPrice < basePrice * 0.95) currentPrice = basePrice * 0.95;
        if(currentPrice > basePrice * 1.05) currentPrice = basePrice * 1.05;

        asks = generateRows(true);
        bids = generateRows(false);
        renderBook(asks, bids);

        const now = new Date();
        const timeStr = now.toTimeString().split(' ')[0];
        const isUp = change >= 0;
        const tradePrice = isUp ? asks[0].price : bids[0].price;
        const tradeSize = Math.floor(Math.random() * 500) + 10;
        
        const tickDiv = document.createElement('div');
        tickDiv.style.display = 'flex';
        tickDiv.style.justifyContent = 'space-between';
        tickDiv.style.padding = '0.2rem 0.4rem';
        tickDiv.style.borderRadius = '4px';
        tickDiv.style.transition = 'background-color 0.3s';
        tickDiv.style.backgroundColor = isUp ? 'rgba(16,185,129,0.15)' : 'rgba(239,68,68,0.15)';
        
        tickDiv.innerHTML = `
            <span style="color:var(--color-muted);">${timeStr}</span>
            <span style="color:${isUp ? '#10b981' : '#ef4444'}; font-weight:800;">${tradePrice.toFixed(2)}</span>
            <span style="font-weight:700;">${tradeSize}</span>
        `;

        depthTrades.insertBefore(tickDiv, depthTrades.firstChild);
        if(depthTrades.children.length > 7) {
            depthTrades.removeChild(depthTrades.lastChild);
        }

        setTimeout(() => {
            tickDiv.style.backgroundColor = 'transparent';
        }, 300);

    }, 1200);
};
