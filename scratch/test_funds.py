import yfinance as yf
tickers = "MAC.IS GMR.IS TTE.IS ST1.IS"
data = yf.download(tickers, period="5d", interval="1d", progress=False)
print("Columns:", data.columns)
if "Close" in data:
    print("Close data:\n", data["Close"].tail())
else:
    print("No Close column")
