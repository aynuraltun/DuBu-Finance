import sys

def modify_index():
    with open('index.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # Add imports
    if 'from flask_socketio import SocketIO' not in content:
        content = content.replace("from flask import Flask", "from flask import Flask\nfrom flask_socketio import SocketIO, emit\nimport threading\nimport time\nimport numpy as np\nimport scipy.optimize as sco")

    # Add SocketIO init
    if 'socketio = SocketIO' not in content:
        app_def = "app = Flask(__name__)\napp.secret_key = 'dubu_finance_ultra_safe_2026'"
        socket_def = app_def + "\nsocketio = SocketIO(app, async_mode='threading', cors_allowed_origins=\"*\")"
        content = content.replace(app_def, socket_def)

    # Add Thread for websocket
    if 'def background_price_stream():' not in content:
        thread_code = """
def background_price_stream():
    import random
    while True:
        time.sleep(3)
        updates = {}
        for sym in ["THYAO", "ASELS", "GARAN", "AKBNK", "SISE", "EREGL", "SASA", "BIMAS", "KCHOL", "SAHOL", "XU100"]:
            direction = random.choice([1, -1])
            pct_change = random.uniform(0.0001, 0.0005)
            updates[sym] = {"direction": direction, "pct": pct_change}
        socketio.emit('price_update', updates)

threading.Thread(target=background_price_stream, daemon=True).start()
"""
        content = content.replace("socketio = SocketIO(app, async_mode='threading', cors_allowed_origins=\"*\")", "socketio = SocketIO(app, async_mode='threading', cors_allowed_origins=\"*\")\n" + thread_code)

    # Add API for sentiment
    if 'def api_stock_sentiment' not in content:
        sentiment_api = """
@app.route('/api/sentiment/<symbol>')
def api_stock_sentiment(symbol):
    try:
        t = yf.Ticker(symbol + ".IS" if symbol.isalpha() else symbol)
        news = t.news
        if not news:
            return jsonify({"sentiment": "Nötr", "score": 50, "text": "Bu hisse için yeterli haber akışı bulunamadı.", "color": "#64748b"})
        
        from textblob import TextBlob
        total_polarity = 0
        for n in news[:5]:
            blob = TextBlob(n.get('title', '') + " " + n.get('summary', ''))
            total_polarity += blob.sentiment.polarity
            
        avg_pol = total_polarity / min(5, len(news))
        
        if avg_pol > 0.05:
            return jsonify({"sentiment": "Güçlü Al", "score": int(70 + avg_pol*100), "text": "Bu hisse için son dakika haberleri çok olumlu, rüzgar arkasında. Yapay zeka modellerimiz haberlerin piyasaya pozitif etki edeceğini öngörüyor.", "color": "#10b981"})
        elif avg_pol < -0.05:
            return jsonify({"sentiment": "Sat", "score": int(30 + avg_pol*100), "text": "Hisseye dair güncel haber akışı negatif. Negatif momentum riski barındırıyor.", "color": "#ef4444"})
        else:
            return jsonify({"sentiment": "Nötr", "score": 50, "text": "Haber akışı dengeli, belirgin bir sinyal üretilemedi.", "color": "#f59e0b"})
    except Exception as e:
        return jsonify({"sentiment": "Hata", "score": 50, "text": "Analiz edilemedi.", "color": "#64748b"})
"""
        content = content.replace("# ---------- PORTFOLIO API ----------", sentiment_api + "\n# ---------- PORTFOLIO API ----------")

    # Add API for Markowitz
    if 'def api_optimize_portfolio' not in content:
        markowitz_api = """
@app.route('/api/optimize_portfolio')
def api_optimize_portfolio():
    u = session.get('user')
    if not u: return jsonify({"error": "Giriş yapın"}), 401
    conn = get_db()
    rows = conn.execute("SELECT symbol, amount, buy_price FROM portfolio WHERE username=?", (u,)).fetchall()
    conn.close()
    
    if len(rows) < 2:
        return jsonify({"error": "Optimizasyon için portföyünüzde en az 2 farklı hisse senedi olmalıdır."})
        
    symbols = [r['symbol'] for r in rows]
    total_val = sum(r['amount'] * r['buy_price'] for r in rows) # Assuming current price is approx buy price for weights, or just use equal if 0
    weights_current = []
    for r in rows:
        weights_current.append((r['amount'] * r['buy_price']) / total_val if total_val > 0 else 1/len(rows))
        
    try:
        tickers = [s + ".IS" if s.isalpha() else s for s in symbols]
        data = yf.download(tickers, period="1y", interval="1d", progress=False)['Close']
        if len(symbols) == 2:
            import pandas as pd
            if isinstance(data, pd.Series):
                 # if yfinance only returned 1 somehow
                 return jsonify({"error": "Yeterli veri alınamadı."})
        
        returns = data.pct_change().dropna()
        mean_returns = returns.mean() * 252
        cov_matrix = returns.cov() * 252
        
        num_assets = len(symbols)
        
        def portfolio_performance(weights, mean_returns, cov_matrix):
            returns_p = np.sum(mean_returns * weights)
            std_p = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
            return std_p, returns_p
            
        def neg_sharpe_ratio(weights, mean_returns, cov_matrix, risk_free_rate=0.45):
            p_var, p_ret = portfolio_performance(weights, mean_returns, cov_matrix)
            return -(p_ret - risk_free_rate) / p_var
            
        args = (mean_returns, cov_matrix)
        constraints = ({'type': 'eq', 'fun': lambda x: np.sum(x) - 1})
        bounds = tuple((0.0, 1.0) for asset in range(num_assets))
        initial_guess = num_assets * [1. / num_assets]
        
        optimized = sco.minimize(neg_sharpe_ratio, initial_guess, args=args, method='SLSQP', bounds=bounds, constraints=constraints)
        
        opt_weights = optimized.x
        opt_std, opt_ret = portfolio_performance(opt_weights, mean_returns, cov_matrix)
        
        dist = []
        for i, s in enumerate(symbols):
            dist.append({
                "symbol": s,
                "current_weight": round(weights_current[i] * 100, 2),
                "optimal_weight": round(opt_weights[i] * 100, 2)
            })
            
        return jsonify({
            "status": "ok",
            "expected_return": round(opt_ret * 100, 2),
            "volatility": round(opt_std * 100, 2),
            "sharpe_ratio": round((opt_ret - 0.45) / opt_std, 2),
            "distribution": dist
        })
    except Exception as e:
        return jsonify({"error": f"Optimizasyon hatası: {str(e)}"})
"""
        content = content.replace("# ---------- PORTFOLIO API ----------", markowitz_api + "\n# ---------- PORTFOLIO API ----------")

    if 'app.run(port=5001' in content:
        content = content.replace("app.run(port=5001, debug=True)", "socketio.run(app, port=5001, debug=True, allow_unsafe_werkzeug=True)")

    with open('index.py', 'w', encoding='utf-8') as f:
        f.write(content)

modify_index()
