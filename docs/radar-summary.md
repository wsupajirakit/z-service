# Radar Summary — รอบเรดาร์บนเซิร์ฟเวอร์

หน้า **Radar Summary** (`/#radar_summary`) ให้กด "ประมวลรอบใหม่" แล้วเซิร์ฟเวอร์จะ
สร้างชุด CSV 9 ไฟล์จาก Mongo → รันสูตรเรดาร์ทั้งชุด → **แช่ผลไว้เป็น "รอบ" (round)**
พร้อม stamp เวลา ย้อนดูรอบไหนก็ได้ ทุกที่ทุกเวลา ไม่ต้องมีเครื่องที่มี stock-radar

## กติกาข้อเดียวที่ต้องจำ

`backend/radar_engine/lib.py` คือ **สำเนาแบบไบต์ต่อไบต์** ของ
`stock-radar/.claude/skills/us-stock-fund-manager/scripts/radar_lib.py`
— **ห้ามแก้ในนี้เด็ดขาด** ถ้าสูตรต้นทางเปลี่ยน ให้ sync ทั้งไฟล์:

```bash
cd backend && ./radar_engine/sync_lib.sh          # copy + verify
venv/bin/python test_radar_round.py               # ต้องผ่าน = สูตรสองฝั่งยังตรงกัน
```

`test_radar_round.py` เอา CSV ชุดจริงจาก `~/stock-radar/csv_archive/<stamp>/` มารัน
แล้วเทียบ digest กับ `~/stock-radar/{history,report_archive}/<stamp>/digest.md`
**ทีละบรรทัด** — แก้ lib.py เองเมื่อไหร่ เทสต์แตกทันที (ยกเว้น 2 อย่างที่ต่างโดยตั้งใจ:
บรรทัด mtime ของไฟล์ CSV และ section Portfolio ซึ่งฝั่งเซิร์ฟเวอร์ปิดถาวร)

## ไฟล์

| ไฟล์ | หน้าที่ |
|--|--|
| `backend/radar_engine/lib.py` | สูตรทั้งหมด (สำเนา ห้ามแก้) |
| `backend/radar_engine/adapter.py` | ทุกอย่างที่เป็นของ z-service: สร้าง CSV จาก Mongo, ประกอบ round doc, job-lock, คำเตือนเรื่องนาฬิกาข้อมูล |
| `backend/radar_api.py` | 6 endpoints |
| `backend/store.py` (ท้ายไฟล์) | `radar_round_*` + `history_tf_stats` |
| `backend/main.py` | แตะ 2 บรรทัด: `import radar_api` + `include_router` |
| `Dockerfile` | เพิ่ม `COPY backend/radar_engine/ ./radar_engine/` — `COPY backend/*.py` กินแค่ไฟล์ชั้นบนสุด ถ้าลืมบรรทัดนี้ **ทั้งเซอร์วิส boot ไม่ขึ้น** (main.py import radar_api ตอนโหลดโมดูล) |
| `dash/src/RadarView.tsx` | หน้าเว็บทั้งหน้า |
| `dash/src/App.tsx` | เพิ่มแท็บ `radar_summary` อย่างเดียว |

## API

| endpoint | ทำอะไร |
|--|--|
| `POST /api/radar_round/run` | `{timeframes?: ["1w","1d","4h","1h"], list_name?}` → 200 เริ่มแล้ว / 400 TF ผิด / 409 มีรอบวิ่งอยู่ |
| `GET /api/radar_round/status` | phase + message ของรอบที่กำลังวิ่ง (poll ทุก 2 วิ) |
| `GET /api/radar_round/tf_status` | แต่ละ TF มีกี่ symbol + บันทึกลง DB เมื่อไหร่ (เช็คก่อนกด) |
| `GET /api/radar_round/list?limit=` | รอบทั้งหมด ใหม่สุดก่อน (เฉพาะ metadata) |
| `GET /api/radar_round/{stamp}` | รอบเต็ม: `digest_md` + `full` (= full.json ของ stock-radar) + `packs` |
| `DELETE /api/radar_round/{stamp}` | ลบรอบ |

auth: ใช้ middleware เดิมของ `/api/*` (JWT หรือ `X-Pull-Key`) — ไม่มีคีย์ใหม่

## สิ่งที่ออกแบบไว้แล้วอย่าไปรื้อ

- **stamp = `<asofET %Y%m%d%H%M>_<fingerprint8>`** เหมือนฝั่ง stock-radar เป๊ะ →
  อ้างอิงข้ามระบบได้ทันที และ **fingerprint = hash เนื้อไฟล์ CSV** ⇒ กดซ้ำบนข้อมูลเดิม
  = คืนรอบเดิม ไม่สร้างซ้ำ (เช็คก่อนรันสูตร เสียแค่ query เดียว) ด้วยเหตุนี้จึง
  **ไม่มี** ปุ่ม force — ข้อมูลเดิมยังไงก็ได้ stamp เดิม
- **PARTIAL**: เลือกไม่ครบ 4 TF → `partial: true` + `warnings[]` บอกตรงๆ ว่าเสียอะไร
  (ไม่มี 1W = Kill-Switch ชั้นสัปดาห์ตรวจไม่ได้ ฯลฯ) หน้าเว็บติด badge ส้มทุกที่ที่รอบโผล่
- **นาฬิกาข้อมูล 3 ชั้น** ทุกอย่างเก็บดิบเป็น ISO + offset แปลงตอน render เท่านั้น:
  `fetched_at` = เวลาที่ z-service เขียนชุด TF นั้นลง DB (จบรอบ fetch) ·
  `bar_asof` = แท่งใหม่สุดในไฟล์ (อาจยังไม่ปิด) · `asof_et` = as-of ของทั้งรอบ
  เตือนอัตโนมัติเมื่อ TF ในรอบเดียวกันห่างกัน ≥6 ชม. หรือข้อมูลเก่ากว่าเวลาประมวล ≥18 ชม.
  (หน้าเว็บคิดความเก่าสดจากนาฬิกาปัจจุบันด้วย เพราะรอบที่ถูก reuse จะไม่ถูกคำนวณใหม่)
- **portfolio ปิดถาวร** (`port_path=None`) — ตำแหน่งจริงไม่ขึ้นเซิร์ฟเวอร์
- **payload เก็บเป็น JSON string** (`full_json` / `packs_json`) แบบเดียวกับ `history.result_json`
  → ticker ที่มีจุด (เช่น `BRK.B`) เป็น key ไม่ได้มีปัญหากับ BSON
- **เก็บ 30 รอบล่าสุด** (`RADAR_KEEP_ROUNDS`) รอบละ ~0.4–0.7MB, prune อัตโนมัติหลังบันทึก
  และ**บอกในข้อความผลลัพธ์ว่าลบรอบไหนไป** — ไม่ลบประวัติของผู้ใช้แบบเงียบๆ
- **เรียง/prune ด้วย `id` ไม่ใช่ `created_at`** — `created_at` เป็นสตริง ISO ที่ offset
  เปลี่ยนตาม setting timezone ของผู้ใช้ ถ้าเรียงด้วยสตริงแล้วมีการสลับ timezone
  ลำดับจะเพี้ยนจนกระทั่ง prune ลบรอบที่เพิ่งสร้างทิ้ง
- **`history_tf_stats` ต้องเลือกแถวแบบเดียวกับ export (max `id` ไม่ใช่ max `timestamp`)**
  — หนึ่ง symbol มีได้หลายแถวต่อ interval (คนละค่า extended_session) ถ้าเลือกคนละเกณฑ์
  หน้าเว็บจะโชว์ความสดของแถวที่รอบจริงไม่ได้ใช้
- **`packs`** = ตารางเชิงกลที่หน้าเว็บใช้ (near_pivot / spring / ez / conviction)
  ผลิตจากฟังก์ชันใน lib ล้วน — ไม่มีการคำนวณสูตรซ้ำใน adapter หรือใน React

## ข้อจำกัด (เขียนไว้ท้ายหน้าเว็บด้วย)

ตัวเลข ~100% แต่การตัดสินใจ ~0% — หน้านี้ไม่ตีความข่าว ไม่เช็คปฏิทินงบ ไม่รู้พอร์ตจริง
ไม่มีชั้น verify/no-bias audit ใช้เป็นจอเครื่องมือได้ **ห้ามใช้ตัดสินใจเข้าไม้เดี่ยวๆ**

## ยังไม่ได้ทำ (Phase ถัดไป ตามแผน)

- hook ท้าย `run_auto_job`: automate ครบ 4 TF → ประมวลรอบใหม่เองอัตโนมัติ
- `GET /api/radar_round/diff?a=&b=` เทียบสองรอบ (stage flips / kill Δ / CMF พลิก)
  — `lib.compare_snapshots` ทำงานบนไฟล์ ต้องเขียนตัวเทียบจาก `full` สองก้อนแทน
- passed-pivots registry (BT-18) · แจ้ง Telegram เมื่อมีรอบใหม่ · เลือก watchlist บนหน้าเว็บ
  (API รับ `list_name` แล้ว แต่ UI ยังรันทุก symbol)
