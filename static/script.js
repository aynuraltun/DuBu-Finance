/* =========================================
   DUBU FINANCE — Logic & API Integration
   ========================================= */

let userFavorites = new Set();

async function loadFavorites() {
    try {
        const res = await fetch('/api/favorites');
        const data = await res.json();
        if (data.favorites) {
            userFavorites = new Set(data.favorites);
            updateAllStars();
        }
    } catch(e) {}
}

function updateAllStars() {
    document.querySelectorAll('.star-btn').forEach(btn => {
        const sym = btn.dataset.symbol;
        const fav = userFavorites.has(sym);
        btn.classList.toggle('starred', fav);
        btn.textContent = fav ? '★' : '☆';
    });
}

/* ---------- Custom Toast Bildirimi ---------- */
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

async function toggleFavorite(symbol, btn) {
    const isFav = userFavorites.has(symbol);
    try {
        const res = await fetch(`/api/favorites/${symbol}`, { method: isFav ? 'DELETE' : 'POST' });
        const data = await res.json();
        if (data.error) return showToast('Lütfen favorilere eklemek için giriş yapın.');
        if (isFav) userFavorites.delete(symbol);
        else userFavorites.add(symbol);
        updateAllStars();
    } catch(e) {}
}

/* ---------- Burger & User ---------- */
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

    fetch('/api/user').then(r => r.json()).then(u => {
        const badge = document.getElementById('user-badge');
        const auth = document.getElementById('burger-auth');
        if (badge) {
            if (u.user) {
                badge.innerHTML = `
                    <div class="user-menu-wrap">
                        <span style="font-weight:800; font-family:var(--font-display);">👤 ${u.user} ▾</span>
                        <div class="user-menu-dropdown">
                            <a href="/takip">⭐ Favorilerim</a>
                            <a href="/logout">🚪 Çıkış Yap</a>
                        </div>
                    </div>`;
            } else {
                badge.innerHTML = '<a href="/login" style="color:var(--color-primary);font-weight:700">Giriş Yap</a>';
            }
        }
        if (auth) auth.innerHTML = u.user ? `<a href="/logout">Çıkış Yap (${u.user})</a>` : '<a href="/login">Giriş Yap</a> / <a href="/register">Kaydol</a>';
    });
}

/* ---------- Halka Arz Widget (Canlı) ---------- */
function loadIpoWidget() {
    const ipoContainer = document.getElementById('ipo-list');
    if (!ipoContainer) return;
    
    fetch('/api/halkaarz').then(r => r.json()).then(data => {
        ipoContainer.innerHTML = '';
        if (!data || !data.length) {
            ipoContainer.innerHTML = '<p style="color:#999;padding:1rem">Henüz güncel halka arz bulunmuyor.</p>';
            return;
        }
        data.forEach(item => {
            const div = document.createElement('div');
            div.className = 'ipo-item';
            div.style.cursor = 'pointer';
            div.onclick = () => window.location.href = `/halkaarz/${item.slug}`;
            div.innerHTML = `<span class="ipo-name">${item.title}</span><span class="ipo-tarih">${item.date}</span>`;
            ipoContainer.appendChild(div);
        });
    });
}

/* ---------- Market Table ---------- */
function loadMarketTable() {
    const table = document.getElementById('market-table-home');
    if (!table) return;
    const tbody = table.querySelector('tbody');
    
    fetch('/api/screener').then(r => r.json()).then(res => {
        tbody.innerHTML = '';
        if (!res.data || !res.data.length) {
            tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;padding:2rem">Veri yüklenemedi.</td></tr>';
            return;
        }
        res.data.slice(0, 15).forEach(row => {
            const sym = row.s.split(':')[1];
            const price = row.d[1].toFixed(2);
            const change = row.d[2].toFixed(2);
            const cls = change > 0 ? 'val-up' : (change < 0 ? 'val-down' : '');
            const sign = change > 0 ? '+' : '';
            const tr = document.createElement('tr');
            tr.onclick = (e) => { if(e.target.tagName !== 'BUTTON') window.location.href=`/hisse/${sym}`; };
            const isFav = userFavorites.has(sym);
            tr.innerHTML = `
                <td><button class="star-btn ${isFav?'starred':''}" data-symbol="${sym}" onclick="event.stopPropagation();toggleFavorite('${sym}',this)">${isFav?'★':'☆'}</button></td>
                <td class="sym-name">${sym}</td>
                <td style="text-align:right">${price} ₺</td>
                <td class="${cls}" style="text-align:right">${sign}${change}%</td>`;
            tbody.appendChild(tr);
        });
    });
}

/* ---------- News Feed ---------- */
function initNews() {
    const newsContainer = document.getElementById('news-feed-container');
    const modal = document.getElementById('news-modal');
    if (!newsContainer) return;
    
    fetch('/api/news').then(r => r.json()).then(news => {
        newsContainer.innerHTML = '';
        news.forEach(n => {
            const div = document.createElement('div');
            div.className = 'news-item';
            div.innerHTML = `<div class="news-title">${n.title}</div><div class="news-preview">${n.description}...</div><div class="news-date">${n.published}</div>`;
            div.addEventListener('click', () => {
                const titleEl = document.getElementById('modal-title');
                if (titleEl) titleEl.textContent = n.title;
                const dateEl = document.getElementById('modal-date');
                if (dateEl) dateEl.textContent = n.published;
                const bodyEl = document.getElementById('modal-body');
                if (bodyEl) {
                    bodyEl.innerHTML = `${n.description} Detaylı analiz ve tam metin için haberi kaynağından görüntüleyebilirsiniz.`;
                }
                const linkEl = document.getElementById('modal-link');
                if (linkEl) {
                    linkEl.href = n.link;
                } else if (bodyEl) {
                    bodyEl.innerHTML += `<div style="margin-top:2rem;text-align:center;"><a href="${n.link}" target="_blank" style="display:inline-block; padding:1rem 2rem; background:var(--color-primary); color:#fff; text-decoration:none; border-radius:8px; font-weight:700;">Haberin Tamamını Oku</a></div>`;
                }
                if (modal) modal.classList.add('active');
            });
            newsContainer.appendChild(div);
        });
    });
    
    const closeBtn = document.getElementById('modal-close');
    if (closeBtn) closeBtn.onclick = () => modal.classList.remove('active');
}

/* ---------- DOMContentLoaded ---------- */
document.addEventListener('DOMContentLoaded', () => {
    initUI();
    loadFavorites();
    loadMarketTable();
    loadIpoWidget();
    initNews();
});
