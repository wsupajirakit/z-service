from tvDatafeed import TvDatafeed

tv = TvDatafeed()

symbols_str = """FIX, VRT, PWR, EME, IESC, BWXT, CW, LEU, VICI, AGO, IRM, T, TOL, SKWD, OTTR, HBM, MLI, KGS, TLN, JEF, FN, POWL, NVT, STRL, AAON, CRS, WST, WHD, MWA, AROC, SBAC, ITRN, NWPX, WLDN, CECO, USLM, EXP, USFD, IDCC, NGS, PLMR, GEV, ETN, AGX, ATEX, UTI, UFPT, UMH, GHM, FLS"""

unique_symbols = sorted(list(set([s.strip() for s in symbols_str.split(',')])))

results = []
for sym in unique_symbols:
    try:
        res = tv.search_symbol(sym)
        found = False
        if res:
            for item in res:
                if item.get('symbol') == sym and item.get('exchange') in ['NASDAQ', 'NYSE', 'AMEX']:
                    desc = item.get('description', '').replace("'", "\\'")
                    exc = item.get('exchange')
                    results.append(f"{{ symbol: '{sym}', name: '{desc}', exchange: '{exc}' }}")
                    found = True
                    break
        if not found:
            results.append(f"{{ symbol: '{sym}', name: '{sym}', exchange: 'NYSE' }}")
    except Exception as e:
        results.append(f"{{ symbol: '{sym}', name: '{sym}', exchange: 'NYSE' }}")

print(",\n".join(results))
