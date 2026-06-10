import yfinance as yf
tickers = ["GC=F", "USDTRY=X"]
data = yf.download(tickers, period="5d", interval="1d", progress=False)
print("Columns:", data.columns)
print("Close Data:\n", data['Close'].tail())
