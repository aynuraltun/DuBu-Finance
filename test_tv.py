import requests
import json

def test():
    url = "https://scanner.tradingview.com/turkey/scan"
    payload = {
        "columns": ["name", "close", "change", "volume"],
        "sort": {"sortBy": "volume", "sortOrder": "desc"},
        "range": [0, 5]
    }
    r = requests.post(url, json=payload)
    print(r.text)

test()
