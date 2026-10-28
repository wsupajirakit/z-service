"""build_meta.py — run at Docker build time: parse the SYMBOLS array of dash/src/symbols.ts -> symbols.json and write VERSION.json.
usage: python3 build_meta.py <symbols.ts> <package.json> <commit> [<outdir>]"""
import json, re, sys, datetime, os
app_tsx, pkg, commit = sys.argv[1], sys.argv[2], (sys.argv[3] if len(sys.argv) > 3 else "unknown")
out = sys.argv[4] if len(sys.argv) > 4 else os.path.dirname(os.path.abspath(__file__))
src = open(app_tsx, encoding="utf-8").read(); blk = src[src.find("const SYMBOLS"):]; blk = blk[:blk.find("\n];") + 3]
pat = r"symbol:\s*'([^']+)'\s*,\s*name:\s*(?:'((?:[^'\\]|\\.)*)'|\"((?:[^\"\\]|\\.)*)\")\s*,\s*exchange:\s*'([^']+)'"
syms = [{"symbol": s, "name": (n1 or n2).replace("\\'", "'"), "exchange": e} for s, n1, n2, e in re.findall(pat, blk)]
json.dump(syms, open(os.path.join(out, "symbols.json"), "w"), ensure_ascii=False)
ver = json.load(open(pkg)).get("version", "0.0.0")
json.dump({"version": ver, "commit": commit[:12], "build_time": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "symbols": len(syms)}, open(os.path.join(out, "VERSION.json"), "w"))
print(f"[build_meta] symbols={len(syms)} version={ver} commit={commit[:12]}")
