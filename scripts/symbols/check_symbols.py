import sys
symbols = ["EME", "ETN", "MU", "TLN", "VRT", "NVDA", "CEG", "HWM", "PWR", "VST", "NRG", "AVGO", "MSFT", "META", "OKLO"]

with open("dash/src/symbols.ts", "r") as f:
    content = f.read()
    
missing = []
for sym in symbols:
    if f"symbol: '{sym}'" not in content:
        missing.append(sym)
print("Missing symbols:", missing)
