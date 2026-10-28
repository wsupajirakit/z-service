# 🥇 Gold Trading Routes — design (2026-08-03)

เป้าหมาย: ใช้ z-service เป็นแหล่งข้อมูลเทรดทอง XAUUSD (IC Markets) แบบ on-demand — แยกจาก automate rounds ของหุ้นเด็ดขาด (rounds ช้า/หนักเกินสำหรับ TF นาที)

## ความเหมาะสมของระบบปัจจุบัน (ประเมินตรง ๆ)
| โหมด | เหมาะไหม | เหตุผล |
|--|--|--|
| Swing (ถือวัน–สัปดาห์) | ✅ ได้เลย | 1h/4h/1d/1w + CMF/IPI/RVOL machinery ใช้ได้ทันที · XAUUSD มีในระบบแล้ว (OANDA) แค่เพิ่ม ICMARKETS |
| สั้น 1–4 ชม | ✅ ได้ | 15m/30m/1h มีใน INTERVAL_MAP แล้ว — ขาดแค่ route on-demand ที่ดึงสด |
| สั้น 5–30 นาที | ⚠️ ได้ แต่ต้องเพิ่ม 3 ชิ้น | ① interval **5m** (TvDatafeed มี in_5_minute อยู่แล้ว แค่ยังไม่ map) ② **on-demand fetch** สดต่อคำขอ + TTL cache (ห้ามพึ่ง rounds — ข้อมูลเก่า 5 นาทีคือตายสำหรับ TF นี้) ③ session/asof สำหรับตลาด ~23 ชม. (metals ไม่ใช่ RTH หุ้น — path is_us_stock=False มีอยู่แล้ว ใช้ต่อได้) |
| Scalp < 5 นาที | ❌ ไม่เหมาะ | TvDatafeed เป็น snapshot ไม่ใช่ websocket tick — latency วินาทีถึงนาที + ไม่มี bid/ask · อย่าฝืน |

**ข้อจำกัดที่ต้องรู้ (ติดหัวไว้ตอนใช้):**
- Volume ของ CFD (ICMARKETS) = **tick volume** ไม่ใช่ volume จริงของตลาดกลาง → CMF/RVOL เป็น proxy (ยังใช้เทียบ relative ได้ดี แต่อย่าอ่านเป็น "เงินสถาบัน" แบบหุ้น)
- ราคา IC Markets มี spread ฝังใน bid — ต่างจาก OANDA เล็กน้อย: ให้เลือก exchange เดียวคงเส้นคงวา (default ICMARKETS, มี `&exchange=OANDA` เป็น fallback)
- ทองปิดวันละ ~1 ชม. (17:00–18:00 ET) + ปิดสุดสัปดาห์ — is_closed_bar ต้อง flag แท่งที่กำลังวิ่ง

## Route ใหม่
```
GET /api/gold/export?mode=<scalp|intraday|swing|position>[&exchange=ICMARKETS]
```
- คืน **ZIP ของ CSV** (โครงเดียวกับ export_zip เดิม: metadata 5 บรรทัด + OHLCV+indicators) — 1 ไฟล์ต่อ symbol×TF + `gold_news.csv`
- **ดึงสดทุกคำขอ** ผ่าน TvDatafeed + **TTL cache ต่อ mode** กันยิงถี่ (scalp 60s · intraday 120s · swing 300s · position 900s)
- ไม่เขียนทับ history ของหุ้น (key = symbol+exchange+interval — ICMARKETS แยก namespace เองอยู่แล้ว; จะ store หรือ stateless ก็ได้ — แนะนำ stateless เพื่อไม่บวม DB)
- auth: โดน middleware คุ้มครองอัตโนมัติ (JWT หรือ X-Pull-Key) — ไม่ต้องเขียนอะไรเพิ่ม

## โหมด × TF × ตัวประกอบ (หัวใจของ design)
| mode | ใช้เทรดแบบ | XAUUSD TFs (n_bars) | ตัวที่มีผลต่อทอง (TF) | news | TTL |
|--|--|--|--|--|--|
| **scalp** | เข้า-ออกใน 1–4 ชม. อ่านโมเมนตัมนาที | **5m (500 ≈ 1.7 วันเทรด) + 15m (400 ≈ 4 วัน)** | DXY 15m · US10Y 15m · USDJPY 15m (ตัวขับ intervention ตอนนี้) | หัวข้อ macro ล่าสุด 10 ข่าว | 60s |
| **intraday** | ถือข้ามชั่วโมง 1–4 ชม. | **15m (400) + 30m (350) + 1h (400 ≈ 2-3 สัปดาห์)** | DXY 1h · US10Y 1h · VIX 1h · USDJPY 1h · SPY 1h | 15 ข่าว | 120s |
| **swing** | ถือวัน–สัปดาห์ | **1h (400) + 4h (360 ≈ 2 เดือน) + 1d (300 ≈ 14 เดือน)** | DXY 4h+1d · US10Y 1d · VIX 1d · WTI 1d (เงินเฟ้อ) · BTC 1d (คู่แข่ง risk) · SPY 1d · **XAGUSD 1d (คอนเฟิร์มเผ่าโลหะ)** | 25 ข่าว | 300s |
| **position** (เสริม) | 2 สัปดาห์+ | **1d (300) + 1w (200 ≈ 4 ปี)** | DXY 1w · US10Y 1w · XAGUSD 1w · GDX 1d+1w (เหมืองนำ/ตามทอง) | 25 ข่าว | 900s |

เหตุผลเลือกคู่ TF ต่อโหมด: ทุกโหมดมี "TF สั่งการ + TF บริบท" เสมอ (เช่น scalp: เข้าออกที่ 5m แต่ทิศจาก 15m) — สอดคล้องกฎ multi-TF confluence ของ radar

## Implementation checklist (แตะ ~3 จุด, ~80-120 บรรทัด)
1. `INTERVAL_MAP` เพิ่ม `"5m": Interval.in_5_minute` (บรรทัดเดียว)
2. `GOLD_MODES` config dict (symbol, exchange, interval, n_bars ตามตารางบน) + route `/api/gold/export` — reuse `_build_export_csv_bytes`-style builder (ตัด session-US logic ออก ใช้ path non-US ที่มีอยู่)
3. TTL cache dict ต่อ (mode, exchange) กันยิง TV ถี่
4. (dash — ถ้าต้องการ) ปุ่มโหลด 4 โหมดในหน้า "วิเคราะห์เทรดทอง" ที่มีอยู่แล้ว (App.tsx:3745)

## ตัวอย่างใช้จริง
```bash
curl -H "X-Pull-Key: $PULL_KEY" "https://z-service.duckdns.org/api/gold/export?mode=swing" -o gold_swing.zip
curl -H "X-Pull-Key: $PULL_KEY" "https://z-service.duckdns.org/api/gold/export?mode=scalp&exchange=ICMARKETS" -o gold_scalp.zip
```
