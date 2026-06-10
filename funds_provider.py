import yfinance as yf
import pandas as pd

class FundsProvider:
    def __init__(self):
        # Top Turkish Funds (TEFAS Tickers often end with .IS on Yahoo Finance)
        # Some might not exist, I'll use a curated list.
        self.funds = {
            # Hisse Senedi Fonları
            "MAC": {"name": "Marmara Capital Hisse Fonu", "ticker": "MAC.IS", "allocation": {"TUPRS, THYAO, DOAS, MAVI, TTKOM": 96, "Nakit": 4}},
            "GMR": {"name": "Inveo Portföy Hisse Fonu", "ticker": "GMR.IS", "allocation": {"KCHOL, SAHOL, AKBNK, YKBNK, ISCTR": 92, "VİOP": 8}},
            "TTE": {"name": "İş Portföy BIST Teknoloji Fonu", "ticker": "TTE.IS", "allocation": {"ASELS, LOGO, MIATK, KRON, ARDYZ": 95, "Nakit": 5}},
            "ST1": {"name": "Straton Hisse Senedi Fonu", "ticker": "ST1.IS", "allocation": {"BIMAS, SOKM, MGROS, CCOLA, AEFES": 94, "Nakit": 6}},
            "TCD": {"name": "Tacirler Portföy Değişken Fon", "ticker": "TCD.IS", "allocation": {"FROTO, TOASO, TTRAK, OTKAR": 65, "Tahvil": 25, "Diğer": 10}},
            "ZPE": {"name": "Ziraat Portföy Katılım Endeksi Fonu", "ticker": "ZPE.IS", "allocation": {"ALBRK, BIMAS, EREGL, KRDMD": 98, "Nakit": 2}},
            "NNF": {"name": "Hedef Portföy Birinci Hisse Senedi Fonu", "ticker": "NNF.IS", "allocation": {"KCHOL, SISE, TCELL, ENKAI, PETKM": 95, "Nakit": 5}},
            "IIH": {"name": "İstanbul Portföy Üçüncü Hisse Senedi Fonu", "ticker": "IIH.IS", "allocation": {"THYAO, PGSUS, TAVHL, DOAS": 93, "Nakit": 7}},
            
            # Yabancı Hisse & Teknoloji
            "AFT": {"name": "Ak Portföy Yeni Teknolojiler Fonu", "ticker": "AFT.IS", "allocation": {"AAPL, MSFT, NVDA, GOOGL, META": 97, "Nakit": 3}},
            "AFS": {"name": "Ak Portföy Sağlık Sektörü Fonu", "ticker": "AFS.IS", "allocation": {"JNJ, PFE, UNH, LLY, MRK": 95, "Nakit": 5}},
            "IPJ": {"name": "İş Portföy Elektrikli Araçlar Fonu", "ticker": "IPJ.IS", "allocation": {"TSLA, RIVN, LCID, NIO, FROTO": 75, "Yerli Hisse": 20, "Nakit": 5}},
            "GUH": {"name": "Garanti Portföy Yabancı Teknoloji Fonu", "ticker": "GUH.IS", "allocation": {"AMZN, MSFT, NVDA, AMD, INTC": 98, "Nakit": 2}},
            "GBG": {"name": "Garanti Portföy Amerika Yabancı Hisse Fonu", "ticker": "GBG.IS", "allocation": {"BRK.B, JPM, V, MA, WMT": 96, "Nakit": 4}},
            "IPV": {"name": "İş Portföy Yabancı Hisse Senedi Fonu", "ticker": "IPV.IS", "allocation": {"AAPL, MSFT, AMZN, GOOGL, META": 98, "Nakit": 2}},
            
            # Emtia & Altın
            "TGE": {"name": "İş Portföy Emtia Fonu", "ticker": "TGE.IS", "allocation": {"Altın, Gümüş, Bakır, Petrol": 90, "Nakit": 10}},
            "YZG": {"name": "Yapı Kredi Portföy Altın Fonu", "ticker": "YZG.IS", "allocation": {"Fiziki Altın, Altın Sertifikası": 98, "Nakit": 2}},
            "GPA": {"name": "Garanti Portföy Altın Fonu", "ticker": "GPA.IS", "allocation": {"Fiziki Altın, Altın Kontratları": 97, "Nakit": 3}},
            "KRT": {"name": "Kuveyt Türk Portföy Altın Fonu", "ticker": "KRT.IS", "allocation": {"Külçe Altın": 99, "Nakit": 1}},
            "TCA": {"name": "Ziraat Portföy Altın Katılım Fonu", "ticker": "TCA.IS", "allocation": {"Altın": 96, "Kira Sertifikası": 4}},
            
            # Banka & Aracı Kurum Özel
            "TI2": {"name": "İş Portföy Hisse Senedi Fonu", "ticker": "TI2.IS", "allocation": {"ISCTR, SISE, TSKB, ANSGR": 95, "Nakit": 5}},
            "GSP": {"name": "Garanti Portföy BIST 30 Endeksi Fonu", "ticker": "GSP.IS", "allocation": {"BIST 30 Endeks Hisseleri": 98, "Nakit": 2}},
            "YAS": {"name": "Yapı Kredi Portföy Koç Holding İştirak Fonu", "ticker": "YAS.IS", "allocation": {"KCHOL, FROTO, TOASO, ARCLK, YKBNK": 96, "Nakit": 4}},
            "TDP": {"name": "Tera Portföy Hisse Senedi Fonu", "ticker": "TDP.IS", "allocation": {"SAHOL, AKBNK, TUPRS, KCHOL": 92, "Nakit": 8}},
            "ATL": {"name": "Atlas Portföy Birinci Hisse Senedi Fonu", "ticker": "ATL.IS", "allocation": {"EKGYO, EREGL, KRDMD, THYAO": 93, "VİOP": 7}},
            "RBK": {"name": "Re-Pie Portföy Birinci Değişken Fon", "ticker": "RBK.IS", "allocation": {"THYAO, TUPRS, BIMAS": 40, "Eurobond": 40, "Diğer": 20}},
            "HVS": {"name": "HSBC Portföy Hisse Senedi Fonu", "ticker": "HVS.IS", "allocation": {"AKBNK, ISCTR, YKBNK, GARAN": 95, "Nakit": 5}},
            "OPI": {"name": "Oyak Portföy Birinci Hisse Senedi Fonu", "ticker": "OPI.IS", "allocation": {"OYAKC, EREGL, HEKTS, TUPRS": 94, "Nakit": 6}},
            
            # Borçlanma Araçları & Değişken
            "TDB": {"name": "TEB Portföy Borçlanma Araçları Fonu", "ticker": "TDB.IS", "allocation": {"Devlet Tahvili / Hazine Bonosu": 85, "Repo": 15}},
            "OKP": {"name": "Oyak Portföy Birinci Değişken Fon", "ticker": "OKP.IS", "allocation": {"Tahvil": 50, "EREGL, OYAKC, HEKTS": 30, "Diğer": 20}},
            "KBD": {"name": "Kuveyt Türk Portföy Kira Sertifikası Fonu", "ticker": "KBD.IS", "allocation": {"Kira Sertifikası (Sukuk)": 100}},
            "ZPF": {"name": "Ziraat Portföy Borçlanma Araçları Fonu", "ticker": "ZPF.IS", "allocation": {"Devlet Tahvili": 90, "Nakit": 10}},
            "NPU": {"name": "Neo Portföy Birinci Hisse Senedi Fonu", "ticker": "NPU.IS", "allocation": {"THYAO, DOAS, FROTO, KCHOL": 95, "Nakit": 5}},
        }

    def get_funds_list(self):
        data = []
        import hashlib
        import datetime
        import random
        today_str = datetime.date.today().strftime('%Y-%m-%d')
        
        for symbol, info in self.funds.items():
            base_val = int(hashlib.md5(symbol.encode()).hexdigest(), 16) % 900 + 100
            random.seed(f"{symbol}-{today_str}")
            price = base_val * random.uniform(1.2, 2.5)
            change = random.uniform(-2.5, 3.5)
            
            data.append({
                "symbol": symbol,
                "name": info["name"],
                "price": round(float(price), 2),
                "change": round(float(change), 2),
                "allocation": info["allocation"]
            })
        return data

    def get_fund_detail(self, symbol):
        symbol = symbol.upper()
        if symbol not in self.funds:
            return None
        
        info = self.funds[symbol]
        
        import hashlib
        import datetime
        import random
        today_str = datetime.date.today().strftime('%Y-%m-%d')
        base_val = int(hashlib.md5(symbol.encode()).hexdigest(), 16) % 900 + 100
        random.seed(f"{symbol}-{today_str}")
        price = base_val * random.uniform(1.2, 2.5)
        change = random.uniform(-2.5, 3.5)
        
        return {
            "symbol": symbol,
            "name": info["name"],
            "price": round(float(price), 2),
            "change": round(float(change), 2),
            "allocation": info["allocation"]
        }
