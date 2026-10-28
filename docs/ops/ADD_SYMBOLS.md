# 📌 คู่มือเพิ่ม Symbol เข้า z-service (ฉบับสมบูรณ์ ไม่ตกหล่น)

> **💡 กฎเหล็กที่ต้องเข้าใจก่อนทำ:**
> 1. **Symbol ต้องเพิ่ม 2 ที่เสมอ:**
>    * **Frontend (`dash/src/symbols.ts`):** ปุ่มทุกปุ่มบนหน้าเว็บ (**Automate All / All Symbols / Export**) อ่านรายชื่อหุ้นจาก array `SYMBOLS` ที่ฮาร์ดโค้ดไว้ในไฟล์นี้เท่านั้น
>    * **Database (MongoDB Watchlist):** ใช้สำหรับจัดกลุ่ม watchlist / filter / export ตาม list
> 2. **Auto Job ล็อก Symbol List ใน Memory ตอนกด Start:**
>    * ถึงแม้จะแก้โค้ดและ Deploy แล้ว แต่ถ้า Job เก่ายังวิ่งอยู่ ตัวเลขจะยังเป็นจำนวนเดิม **ต้องกด "หยุด Auto Run" แล้วกด "Automate All" ใหม่ทุกครั้ง**

---

## 🚀 ขั้นตอนการเพิ่ม Symbol (ทำตามลำดับ 1 - 4)

### ขั้นตอนที่ 1: เพิ่มใน Frontend (`dash/src/symbols.ts`)

เปิดไฟล์ `dash/src/symbols.ts` แล้วเลื่อนไปที่ array `export const SYMBOLS = [...]` (ประมาณบรรทัด 40–320)  
เพิ่มข้อมูลหุ้นตัวใหม่ต่อท้าย array ตามรูปแบบ:

```ts
{ symbol: 'DLO', name: 'dLocal Limited', exchange: 'NASDAQ' },
{ symbol: 'ECG', name: 'Everus Construction Group, Inc.', exchange: 'NYSE' },
```

> **ข้อควรระวัง:** `exchange` ต้องใส่ให้ตรงกับ TradingView (เช่น `NASDAQ`, `NYSE`, `AMEX`, `BINANCE`, `TVC`)

---

### ขั้นตอนที่ 2: เพิ่มเข้า Database (MongoDB Watchlist)

สร้างหรือใช้สคริปต์ Python ยิงเข้า API โดยมี `PULL_KEY` (`viigdjjbduugdg4glieig5vljg`) เสมอ  
*(ใช้ Standard Library `urllib.request` ไม่ต้องลง `pip install pymongo` หรือ dependency ใดๆ)*

**ตัวอย่างสคริปต์ (`add_symbols.py`):**
```python
import urllib.request
import json
import ssl

API_URL = "https://z-service.duckdns.org/api/watchlist"
PULL_KEY = "viigdjjbduugdg4glieig5vljg"
LIST_NAME = "HG-0811-top"  # เปลี่ยนชื่อกลุ่มตามต้องการ

SYMBOLS = [
    {"symbol": "DLO", "name": "dLocal Limited"},
    {"symbol": "GLBE", "name": "Global-e Online Ltd."},
    # ใส่ symbol ที่ต้องการเพิ่มตรงนี้
]

def main():
    target_url = f"{API_URL}?pull_key={PULL_KEY}"
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    headers = {
        "Content-Type": "application/json",
        "X-Pull-Key": PULL_KEY,
        "User-Agent": "Mozilla/5.0"
    }

    for item in SYMBOLS:
        payload = {"symbol": item["symbol"], "name": item["name"], "list_name": LIST_NAME}
        req = urllib.request.Request(target_url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
                print(f"✅ [OK] Added {item['symbol']}")
        except Exception as e:
            print(f"❌ [FAIL] {item['symbol']}: {e}")

if __name__ == "__main__":
    main()
```

**รันสคริปต์ใน Terminal** (จากราก repo · เก็บไฟล์ไว้ใน `scripts/symbols/` ตั้งชื่อ `add_symbols_<ชุด>_<MMDD>.py`):
```bash
python3 scripts/symbols/add_symbols_<ชุด>_<MMDD>.py
```

---

### ขั้นตอนที่ 3: Commit & Push ขึ้น Git เพื่อให้ Coolify Deploy

```bash
git add .
git commit -m "add new symbols to symbols.ts and watchlist"
git push
```
*รอระบบ Coolify ทำการ Build & Deploy ขึ้น Server ให้เสร็จสมบูรณ์*

---

### ขั้นตอนที่ 4: เคลียร์ Job เก่า และสั่งรันรอบใหม่บน Dashboard (จุดตายที่พบบ่อยสุด ⚠️)

1. เปิดหน้าเว็บ Dashboard (`https://z-service.duckdns.org` หรือ URL ภายใน)
2. กด **`Cmd + Shift + R`** (Hard Refresh) เพื่อล้างแคช JS ตัวเก่า
3. **กดปุ่มสีแดง `"หยุด Auto Run"`** เพื่อยกเลิก Job เก่าที่ค้างตัวเลขเดิมใน Memory
4. **กดปุ่มสีม่วง `"Automate All"`** ใหม่อีกครั้ง
5. 👉 **ตัวเลขความคืบหน้าจะอัปเดตเป็นยอดรวมใหม่ทันที (เช่น `1 / 300`)**

---

## 🛠️ สรุปปัญหาที่พบบ่อยและวิธีแก้ (Troubleshooting)

| ปัญหา / Error | สาเหตุ | วิธีแก้ |
|---|---|---|
| **ตัวเลขยังเป็นยอดเดิม (เช่น 280 เท่าเดิม)** | 1. Auto Job เก่ายังวิ่งอยู่ (ล็อก list ใน memory)<br>2. ยังไม่ได้แก้ `App.tsx`<br>3. เบราว์เซอร์แคช JS เก่า | 1. กด **"หยุด Auto Run"**<br>2. กด **Cmd + Shift + R**<br>3. กด **"Automate All"** ใหม่ |
| **HTTP Error 401: Unauthorized** | ยิง API Watchlist โดยไม่ได้ส่ง `PULL_KEY` | ใส่ Header `X-Pull-Key: viigdjjbduugdg4glieig5vljg` หรือเติม `?pull_key=...` ท้าย URL |
| **`ModuleNotFoundError: No module named 'pymongo'`** | Python ในเครื่องไม่มี driver pymongo | ใช้สคริปต์ที่เรียกผ่าน API ด้วย `urllib.request` (Standard Library) แทนการต่อ DB ตรง |
| **Fetch ข้อมูลค้างนานผิดปกติ (~35 วิ/ตัว)** | ใส่ `exchange` ผิด ทำให้หาแท่งเทียนไม่เจอ | ตรวจสอบชื่อ Exchange บน TradingView ให้ถูกต้อง (เช่น `NASDAQ`, `NYSE`, `AMEX`) |
