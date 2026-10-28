"""Earnings scan: EPS/revenue actual-vs-estimate history and the next earnings date per
symbol. Three free-tier providers are tried in a fixed order — Finnhub, then FMP, then
Alpha Vantage — falling through on any error, empty response or missing API key. If all
three fail, the result records which providers were attempted so the UI can say so."""
