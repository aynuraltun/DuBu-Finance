import requests
import json
import pandas as pd

url = "https://www.tefas.gov.tr/api/historical/price"
payload = {"fund":"MAC","startDate":"2023-01-01","endDate":"2023-05-01"}
headers = {'Content-Type': 'application/json'}
try:
    r = requests.post(url, json=payload, headers=headers, timeout=5)
    print(r.status_code)
    print(r.text[:200])
except Exception as e:
    print(e)
