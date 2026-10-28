"""The server-owned symbol list: build-time symbols.json (parsed from dash/src/App.tsx by
build_meta.py) plus MongoDB watchlist rows that carry an exchange; plus build version info.

Why the server owns it: the legacy dashboard's "Auto All" used the SYMBOLS array baked into
the deployed frontend, so adding symbols needed a rebuild + hard refresh, and the in-memory
job died on every container restart until someone clicked again (fixed 20 Oct 2026).
"""
