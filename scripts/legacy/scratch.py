import yfinance as yf
from tvDatafeed import Interval

def get_yf_data_fallback(symbol, exchange, interval_enum, n_bars, extended_session):
    # Mapping tvDatafeed Interval to yfinance interval
    interval_map = {
        Interval.in_1_minute: "1m",
        Interval.in_5_minute: "5m",
        Interval.in_15_minute: "15m",
        Interval.in_30_minute: "30m",
        Interval.in_45_minute: "60m", # yfinance doesn't have 45m natively
        Interval.in_1_hour: "1h",
        Interval.in_daily: "1d",
        Interval.in_weekly: "1wk",
        Interval.in_monthly: "1mo",
    }
    yf_interval = interval_map.get(interval_enum, "1d")
    
    # Map symbols
    yf_sym = symbol
    if exchange == 'BINANCE' or 'USDT' in symbol or 'USD' in symbol:
        if symbol.endswith('USDT'):
            yf_sym = symbol[:-4] + '-USD'
        elif symbol.endswith('USD'):
            yf_sym = symbol[:-3] + '-USD'
    elif exchange == 'SET':
        yf_sym = f"{symbol}.BK"
    # Basic Yahoo format: APPL is just APPL. 

    print(f"Fallback yfinance: {symbol} -> {yf_sym} ({yf_interval})")
    
    ticker = yf.Ticker(yf_sym)
    # n_bars equivalent: yfinance uses periods, but we can't specify exact bars except by dates or max.
    # We will just fetch a large enough period.
    if yf_interval in ["1m", "5m", "15m", "30m"]:
        period = "60d"
    elif yf_interval == "1h":
        period = "730d"
    else:
        period = "5y"
        
    df = ticker.history(period=period, interval=yf_interval, prepost=extended_session)
    if df.empty:
        return None
        
    # Format to match tvDatafeed
    df = df.rename(columns={
        "Open": "open",
        "High": "high",
        "Low": "low",
        "Close": "close",
        "Volume": "volume"
    })
    # TvDatafeed includes 'symbol' column
    df["symbol"] = f"{exchange}:{symbol}"
    
    # Keep only expected columns
    df = df[["symbol", "open", "high", "low", "close", "volume"]]
    
    # Make index naive timezone to match tvDatafeed behavior
    if df.index.tz is not None:
        df.index = df.index.tz_convert('UTC').tz_localize(None)
    
    df.index.name = "datetime"
    
    # Return last n_bars
    return df.tail(n_bars)

df = get_yf_data_fallback("AAPL", "NASDAQ", Interval.in_daily, 5, False)
print(df)
