# XAU_AUTOMATE — สเปคระบบข้อมูล/วิเคราะห์ทอง สำหรับ bot เทรด XAUUSD

> เวอร์ชัน 2026-08-04 · โมดูลหลัก: `backend/gold.py` (standalone ไม่แตะ flow หุ้น) · design: `docs/gold-mode-design.md`
> ผู้บริโภคหลักของเอกสารนี้ = **bot เทรดทอง** ที่จะดึงข้อมูล → ส่งให้ AI วิเคราะห์ → ได้คำสั่ง order ไปยิงที่ broker (IC Markets)

---

## 1) ภาพรวม — สองระบบในบ้านเดียว

| ระบบ | เส้นทาง | เหมาะกับ |
|--|--|--|
| **A. Gold Data Export (ใหม่ — แนะนำสำหรับ bot)** | `GET /api/gold/export` + `GET /api/gold/modes` | bot ดึง ZIP (ราคา+อินดิเคเตอร์ทุก TF + ตัวประกอบ + ข่าว + โจทย์วิเคราะห์) แล้วส่งให้ AI ของตัวเอง (Claude/Gemini/GPT) วิเคราะห์ → ได้ order กลับมา |
| B. Gemini Analyzer เดิม (ปุ่มใน dash) | `POST /api/gold/analyze`, `POST /api/gold/automate`, `GET /api/gold/status`, `GET /api/gold/price`, `GET /api/gold/config`, `GET /api/gold/models` | คนกดใช้ใน dash — server วิเคราะห์ด้วย Gemini เอง + แจ้ง Telegram + อัป Drive · bot ใช้ก็ได้แต่ผูกกับ Gemini key ฝั่ง server |

ทั้งสองระบบอยู่หลัง **auth เดียวกัน**: JWT (login) หรือ **`X-Pull-Key`** (สำหรับ bot/สคริปต์)

---

## 2) Auth (สำหรับ bot ใช้ pull key)

```bash
# แบบ header (แนะนำ — ไม่ติด log/query string)
curl -H "X-Pull-Key: <PULL_KEY>" "https://z-service.duckdns.org/api/gold/export?mode=scalp"
# แบบ query param (สำรอง)
curl "https://z-service.duckdns.org/api/gold/export?mode=scalp&pull_key=<PULL_KEY>"
```
- `PULL_KEY` ตั้งใน env ของ server (Coolify) — **ไม่ตั้ง = ปิดช่องทางนี้สนิท**
- ตอบ `401` = key ผิด/ไม่ส่ง · เทียบกันด้วย `hmac.compare_digest` (กัน timing attack)

---

## 3) Endpoint spec (ระบบ A — ตัวหลักของ bot)

### `GET /api/gold/export`
| param | ค่า | default |
|--|--|--|
| `mode` | `scalp` \| `intraday` \| `swing` \| `position` | `swing` |
| `exchange` | `ICMARKETS` \| `OANDA` \| `FOREXCOM` (ใช้กับ XAUUSD เท่านั้น — ตัวประกอบ fix exchange ของตัวเอง) | `ICMARKETS` |

- **ตอบ:** `application/zip` · header `X-Gold-Cache: hit|miss`
- **HTTP codes:** `200` สำเร็จ (แม้ตัวประกอบบางตัวพลาด — ดู `_errors.txt`) · `400` mode/exchange ผิด · `401` auth · `502` = ดึง XAUUSD ไม่ได้เลยทุก TF (ชุดข้อมูลใช้ไม่ได้ ห้ามเทรดรอบนั้น)
- **TTL cache ฝั่ง server ต่อ (mode, exchange):** scalp 60s · intraday 120s · swing 300s · position 900s — ยิงถี่กว่านี้ได้ไฟล์ชุดเดิม (เร็ว ~10ms ไม่เปลืองโควต้า TradingView)
- ดึงพลาดชั่วคราวมี **retry 1 รอบในตัว** แล้ว

### `GET /api/gold/modes`
คืน JSON รายการโหมด/exchange/ไฟล์ที่จะได้ — ให้ bot อ่านเพื่อ discover config แทน hardcode

---

## 4) สเปคโหมด (TF, ตัวประกอบ, เกณฑ์)

| mode | ใช้เทรด | XAUUSD TFs (แท่ง) | ตัวประกอบ (fix exchange) | R:R ขั้นต่ำ | TTL |
|--|--|--|--|--|--|
| `scalp` | ถือ 1–4 ชม. | 5m(500) + 15m(400) | DXY·US10Y·USDJPY @15m | 1.5 | 60s |
| `intraday` | ข้ามชั่วโมง | 15m(400)+30m(350)+1h(400) | DXY·US10Y·VIX·USDJPY·SPY @1h | 1.8 | 120s |
| `swing` | หลายวัน–สัปดาห์ | 1h(400)+4h(360)+1d(300) | DXY@4h+1d · US10Y·VIX·WTI·BTCUSDT·SPY·XAGUSD @1d | 2.0 | 300s |
| `position` | หลายสัปดาห์+ | 1d(300)+1w(200) | DXY·US10Y·XAGUSD @1w · GDX @1d+1w | 2.5 | 900s |

exchange ตัวประกอบ: DXY/US10Y/VIX=TVC · SPY/GDX=AMEX · WTI=BLACKBULL · BTCUSDT=BINANCE · USDJPY/XAGUSD=OANDA

---

## 5) โครง ZIP + สคีมา CSV (สัญญาข้อมูลที่ bot parse)

```
gold_<mode>.zip
├── gold_formula.csv          # โจทย์วิเคราะห์ + playbook + session map + ข่าว (ดูข้อ 6)
├── xauusd_<tf>.csv           # ต่อ TF ตามโหมด
├── <companion>_<tf>.csv      # เช่น dxy_1d.csv, usdjpy_15m.csv
└── _errors.txt               # มีเฉพาะเมื่อบางตัวดึงพลาด: "EXCH:SYM tf -> เหตุผล" ต่อบรรทัด
```

**ไฟล์ราคา:** 5 บรรทัดแรกขึ้นต้น `#` (metadata) — ข้ามด้วย `comment='#'` แล้วอ่าน CSV ปกติ
```
# gold_mode: swing | symbol: XAUUSD | tf: 1d | exchange: ICMARKETS
# generated_utc: ... | et: ... | bangkok: ...
# last_bar_start: ...
# volume_note: tick volume (proxy)
# session_note: metals ~23h/day ...
```
**คอลัมน์ (คงที่ทุกไฟล์):**
`Symbol, Datetime, Open, High, Low, Close, Volume, EMA_20, EMA_50, EMA_100, EMA_200, RSI, OBV, CMF_50, CMF_20, VWAP_20, ATR_14, RVOL_20, Is_Closed_Bar`

**กฎเหล็กสำหรับ bot:**
- `Is_Closed_Bar=False` (แถวสุดท้ายที่แท่งยังไม่จบ) — **ห้ามใช้ยืนยันสัญญาณ/คำนวณ indicator ตัดสินใจ** ใช้ได้แค่เป็นราคาปัจจุบัน
- `Volume` = tick volume ของ CFD → CMF/OBV/RVOL อ่านเชิงเปรียบเทียบเท่านั้น
- เจอ `_errors.txt` ที่มีตัวประกอบสำคัญของโหมด (เช่น DXY) หาย → ลดขนาดไม้หรือข้ามรอบ

---

## 6) `gold_formula.csv` — สัญญา "โจทย์→คำตอบ" ระหว่าง bot กับ AI

โครง: `Section, Key, Field, Value` · Sections ที่ bot ต้องส่งให้ AI ครบ: `ANALYSIS_REQUEST` (Output 1–8) · `ENTRY_PLAYBOOK` (setup ต่อโหมด — **จุดเข้าต้องอ้าง playbook อย่างน้อย 1 ข้อ ไม่งั้น NO-TRADE**) · `SESSION_MAP` (นาฬิกาไทย+ET) · `READING_GUIDE` · `LATEST_FINANCIAL_NEWS`

**คำตอบที่ AI ต้องคืน (บังคับใน ANALYSIS_REQUEST):** bias ต่อ TF · **order type หนึ่งเดียว: BUY LIMIT / BUY STOP / SELL LIMIT / SELL STOP @ราคา หรือ NO-TRADE พร้อมเหตุผล** · Entry/SL/TP1/TP2 ตัวเลข + R:R ≥ เกณฑ์โหมด · invalidation · ผลตัวประกอบสุทธิ · ข่าว/event ข้างหน้า · ขนาดไม้+confidence 0-10 · สรุปแผน A/B

**แนะนำสำหรับ bot: บังคับ AI ตอบ JSON ท้ายรายงานเสมอ** (แนบ instruction นี้ต่อท้าย prompt ของ bot เอง):
```json
{
  "order_type": "BUY_LIMIT|BUY_STOP|SELL_LIMIT|SELL_STOP|NO_TRADE",
  "entry": 4032.5, "sl": 4021.0, "tp1": 4055.0, "tp2": 4070.0,
  "rr_tp1": 2.0, "confidence": 7, "size": "half|full|quarter",
  "valid_until_utc": "2026-08-04T12:00:00Z",
  "invalidation": "ปิด 1h ต่ำกว่า 4020 หรือ DXY ทะลุ 100.5",
  "playbook_ref": "swing #1", "reason": "หนึ่งบรรทัด"
}
```
→ bot parse JSON นี้ไปตั้ง order ตรง ๆ · `NO_TRADE` = ไม่ทำอะไร + log เหตุผล · `valid_until` หมด = ยกเลิก pending order

**Semantics ของ order type (จาก READING_GUIDE):** BUY LIMIT = ตั้งซื้อต่ำกว่าราคาปัจจุบัน (รอย่อ) · BUY STOP = เหนือราคา (รอทะลุ) · SELL LIMIT = เหนือราคา (รอเด้ง) · SELL STOP = ต่ำกว่าราคา (รอหลุด)

---

## 7) Loop แนะนำสำหรับ bot ต่อโหมด

| mode | จังหวะดึง | หน้าต่างทำงาน (จาก SESSION_MAP) | วินัยบังคับ |
|--|--|--|--|
| scalp | ทุกแท่ง 5m ปิด (+5-10s) — TTL 60s รองรับ | London open 14:00-16:00 ไทย · overlap 19:00-23:00 ไทย · **นอกหน้าต่าง = พัก** | NO-TRADE ±30 นาทีรอบ 19:30 ไทย (ข่าว US) · SL หลบเลขกลม $50/$100 |
| intraday | ทุกแท่ง 15m/30m ปิด | รอบวงจร เอเชียสร้างกรอบ → London break → NY | FOMC วัน: ห้ามเปิดก่อน 01:00 ไทย · เช็คทิศ DXY/US10Y ก่อนไล่ |
| swing | ทุกแท่ง 1h หรือ 2-4 ครั้ง/วัน | ตลอด session | SL ใต้ swing ของ pullback เสมอ · เช็ค real-yield/DXY overlay |
| position | วันละ 1-2 ครั้ง (หลังปิด 1d) | — | ทยอยไม้ · ทบทวนเมื่อ Fed cycle เปลี่ยน |

**Risk guard ฝั่ง bot (นอกเหนือจากคำตอบ AI):** จำกัดไม้ค้างพร้อมกัน ≤2-3 · daily stop (เช่น −2R/วัน หยุดเทรด) · ตรวจ spread จริงก่อนยิง (dead zone 04:00-05:00 ไทย spread ถ่าง) · ห้ามยิงถ้า `_errors.txt` มี XAUUSD TF สั่งการหาย (ระบบตอบ 502 ให้อยู่แล้วเป็นชั้นแรก)

---

## 8) การปรับแต่ง (ทุกอย่างอยู่ที่ `backend/gold.py` — แก้แล้ว push, Coolify deploy เอง)

| อยากปรับ | แก้ตรงไหน |
|--|--|
| เพิ่ม/ลด TF, จำนวนแท่ง, ตัวประกอบของโหมด | dict `GOLD_MODES[mode]["sets"]` — tuple `(SYMBOL, tf, n_bars)` |
| เพิ่มโหมดใหม่ | เพิ่ม key ใหม่ใน `GOLD_MODES` (ttl/news/rr_min/horizon/tf_roles/sl_guide/playbook/sets) — route/modes-endpoint เห็นเองอัตโนมัติ |
| แก้สูตร/playbook/เกณฑ์ R:R | `GOLD_MODES[mode]["playbook"]` (list ข้อความ) · `rr_min` · `sl_guide` |
| เพิ่ม broker/exchange ของ XAUUSD | list `_XAU_EXCHANGES` (whitelist) |
| เปลี่ยน exchange ตัวประกอบ | dict `_COMP_EXCH` |
| เพิ่ม TF ใหม่ (เช่น 1m — ไม่แนะนำ) | dict `_INTERVALS` |
| แหล่งข่าว | list `_NEWS_FEEDS` |
| ความถี่ cache | `GOLD_MODES[mode]["ttl"]` |
| บัญชี TradingView (เพิ่มสิทธิ์ข้อมูล) | env `TV_USERNAME`/`TV_PASSWORD` (ไม่ตั้ง = anonymous ก็ใช้ได้) |
| คีย์ bot | env `PULL_KEY` (เปลี่ยนแล้ว restart — แจก key ใหม่ให้ bot) |

**สิ่งที่ระบบนี้ไม่ทำ (by design):** ไม่ยิง order เอง (bot เป็นคนยิง) · ไม่เก็บ history ลง Mongo · ไม่แตะ automate rounds ของหุ้น

---

## 9) Troubleshooting เร็ว
- `401` → เช็ค `X-Pull-Key` ตรงกับ env server
- `400` → mode/exchange สะกดผิด (ดู `/api/gold/modes`)
- `502` → TradingView ดึง XAUUSD ไม่ได้ทั้งหมด (มี retry ให้แล้ว) — รอ 1-2 นาทีแล้วยิงใหม่ · ถ้าค้างนาน เช็ค TV_USERNAME/token ฝั่ง server
- ไฟล์ตัวประกอบหาย → ดู `_errors.txt` (bot ควร log และลดขนาดไม้)
- ได้ไฟล์ชุดเดิมซ้ำ → ปกติ (TTL cache — ดู header `X-Gold-Cache`)
