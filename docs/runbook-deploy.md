# Runbook — deploy branch `feat/web-ui` + ตั้งค่า env (ทำ **หลังสุด**)

> user สั่ง 24 ต.ค. 2026: ค่า env / config ทุกตัวตั้ง **หลัง** งาน dev เสร็จ แล้วค่อย deploy
> ไฟล์นี้อัปเดตทุกครั้งที่งานเพิ่มค่า env ใหม่ — ดูคอลัมน์ "เพิ่มใน commit"
> **ห้ามใส่ค่าลับลงในไฟล์นี้** — ค่าลับอยู่ใน macOS Keychain (service `z-service`) เท่านั้น

---

## 1. ค่า env ทั้งหมดที่ต้องตั้งใน Coolify

> รายการ**ทุกตัว**ที่ backend อ่าน (ชนิด · ค่าเริ่ม · ขอบเขต · คำอธิบาย) อยู่ใน
> [config-reference.md](config-reference.md) — สร้างจากโค้ดอัตโนมัติ (`backend/venv/bin/python tools/config_reference.py`)
> และมี test กันไม่ให้ตกรุ่น · ตารางข้างล่างคือเฉพาะตัวที่งาน `feat/web-ui` เพิ่ม/เปลี่ยน

| ชื่อ | ค่า | ลับไหม | ได้ค่ามาจากไหน | บังคับ? | เพิ่มใน commit |
|--|--|--|--|--|--|
| `AUTH_SECRET` | สุ่ม 64 byte | 🔒 ลับ | `backend/venv/bin/python tools/manage_keys.py copy --account env:AUTH_SECRET` → paste | **บังคับ** — ไม่มี = server ไม่บูต | `365a796` |
| `ZS_API_KEYS` | JSON list ของ key เครื่อง (มีแค่ hash) | ไม่ลับ | §1.1 | ไม่บังคับ (ไม่ตั้ง = ไม่มี key `zsk_` ใช้ได้) | `4bf2d77` |
| `PULL_KEY` | ค่าเดิม | 🔒 ลับ (และ**รั่วใน git แล้ว**) | มีอยู่แล้วใน Coolify | **คงไว้ก่อน** · ลบในขั้น §4 | เดิม |
| `ZS_MACHINE_RATE_LIMIT` | `300` (ค่าเริ่ม) | ไม่ลับ | — | ไม่ต้องตั้ง เว้นแต่ต้องปรับ | `4bf2d77` |
| `ZS_MACHINE_RATE_WINDOW_S` | `60` (ค่าเริ่ม) | ไม่ลับ | — | ไม่ต้องตั้ง | `4bf2d77` |
| `ZS_AUDIT_RING_SIZE` | `2000` (ค่าเริ่ม) | ไม่ลับ | — | ไม่ต้องตั้ง | `4bf2d77` |
| `ZS_DOCS` | `1` (ค่าเริ่ม = เปิด `/docs` แต่ต้อง login) · `0` = ปิด `/docs` + `/openapi.json` ทั้งหมด | ไม่ลับ | — | ไม่ต้องตั้ง (แนะนำ `0` ใน production) | B6 |
| `ZS_CORS_ORIGINS` | **production: ไม่ตั้ง** (origin เดียวกันอยู่แล้ว) · **local dev เท่านั้น:** `http://localhost:5173,http://localhost:6600` ใน `.env` ในเครื่อง | ไม่ลับ | — | dev เท่านั้น · ห้ามใส่ `*` (บูตไม่ขึ้น) | B5 |
| `FORWARDED_ALLOW_IPS` | ช่วง IP ของ proxy Coolify/Traefik (เช่น network ของ Docker) — uvicorn อ่าน env นี้เอง · ถ้า port 9999 **ไม่ได้** map ออก host ใช้ `*` ได้ (เมื่อเป็น `*` แอปใช้ IP ตัวขวาสุดของ X-Forwarded-For = IP ที่ Traefik เห็น ไคลเอนต์ปลอมเองไม่ได้ · ต้องมี proxy ชั้นเดียว) | ไม่ลับ | ดูใน Coolify ว่า Traefik อยู่ network ไหน | **แนะนำ** — ไม่ตั้ง = rate limit login เห็นทุกคนเป็น IP เดียว (ยังปลอดภัย แต่คนอื่นทำให้เรา login ไม่ได้ 1 นาที) | B9 |
| `ZS_JOB_HEARTBEAT_STALE_S` | `180` (ค่าเริ่ม) — container ใหม่รอ job ของ container เก่าจนเงียบเกินเท่านี้ก่อนรับช่วง | ไม่ลับ | — | ไม่ต้องตั้ง | B12 |
| `ZS_LOGIN_RATE_LIMIT` / `ZS_LOGIN_RATE_WINDOW_S` | `5` / `60` (ค่าเริ่ม: 5 ครั้งต่อนาทีต่อ IP+username) | ไม่ลับ | — | ไม่ต้องตั้ง | B9 |
| `APP_BASE` | `/app/` (ค่าเริ่ม) — path ของ UI ใหม่ ใช้ทั้งตอน build `web/` และตอน backend ตัดสินว่า path ไหนบังคับ CSP | ไม่ลับ | — | ไม่ต้องตั้ง เว้นแต่ย้าย path | B8 |
| `ZS_ALLOW_REGISTER` | **ไม่ตั้ง** (ค่าเริ่ม = ปิดการสมัคร) · `1` = เปิดสมัครได้ครั้งเดียวตอนยังไม่มี user | ไม่ลับ | — | **ห้ามตั้งใน production** · ตั้งชั่วคราวเฉพาะติดตั้งใหม่/ฐานข้อมูลถูกล้าง แล้วลบทันทีหลังสมัคร | S-F3 |
| `ZS_LOGIN_IP_RATE_LIMIT` | `20` (ค่าเริ่ม: ครั้ง login ต่อนาทีต่อ IP รวมทุก username · ใช้หน้าต่างเดียวกับ `ZS_LOGIN_RATE_WINDOW_S`) | ไม่ลับ | — | ไม่ต้องตั้ง | S-F3 |
| `ZS_MAX_BODY_BYTES` | `2097152` (ค่าเริ่ม 2 MiB) — body ใหญ่กว่านี้ตอบ 413 | ไม่ลับ | — | ไม่ต้องตั้ง | S-F7 |
| `ZS_REVOCATION_CACHE_S` | `15` (ค่าเริ่ม) — logout/เปลี่ยนรหัสมีผลกับ container อื่นภายในกี่วินาที | ไม่ลับ | — | ไม่ต้องตั้ง | S-F5 |
| `ZS_STATE_DIR` | Dockerfile ตั้งให้แล้ว = `/app/state` (โฟลเดอร์ของ user `app`: cache token TradingView 0600 + `automate.log` หมุนไฟล์ 5 MB×3) | ไม่ลับ | — | **ห้ามตั้งทับใน Coolify** · local dev ไม่ตั้ง = โฟลเดอร์ `backend/` | S-F9 |

### 1.1 ค่า `ZS_API_KEYS` ปัจจุบัน (ไม่ลับ — มีแค่ sha256 ของ secret)
```
[{"id": "home", "name": "home mac", "scopes": ["jobs", "read", "watchlist:write"], "sha256": "50a2ee4954339e7a3b3edeccae98f8341a6e18749c584d06af67ef3208200702", "expires": "2027-04-22"}]
```
- key ตัวจริงอยู่ใน Keychain: service `z-service` · account `home` (ออกด้วย `tools/manage_keys.py new` วันที่ 24 ต.ค. 2026 · หมดอายุ 2027-04-22)
- ตรวจค่าก่อนวาง: `echo '<ค่าข้างบน>' | backend/venv/bin/python tools/manage_keys.py check`
- คำนวณ entry ใหม่จาก Keychain (ถ้าหาค่าข้างบนไม่เจอ): `backend/venv/bin/python tools/manage_keys.py show-entry --id home`

### 1.2 ค่าที่จะเพิ่มในงานถัดไป (ยังไม่มีในโค้ด — เติมเมื่อ commit เข้า)
| ชื่อ | ใช้ทำอะไร | งาน |
|--|--|--|

---

## 1.3 หลัง deploy: ของที่เปลี่ยนให้ผู้ใช้เห็น
- **ค่า env ถูกตรวจตอนบูต** (pydantic-settings · `zservice/core/config.py`): ค่าผิดรูป (ตัวเลขเป็นคำ · ติดลบ/0 ในช่องที่ต้อง > 0 · bool ที่ไม่ใช่ `1/0/true/false/yes/no/on/off` · `APP_BASE` ไม่มี `/` หัวท้าย) ⇒ **server ไม่บูต** และ log บอกชื่อตัวแปร · Coolify คงเวอร์ชันเดิมไว้เพราะ healthcheck ไม่ผ่าน (เดิม: ค่าผิดถูกเงียบ ๆ เปลี่ยนเป็นค่าเริ่ม)
- bool เปลี่ยนความหมายเล็กน้อย: `ZS_DOCS` / `ZS_AUTOSTART` เดิม "อะไรก็ได้ที่ไม่ใช่ `0`" = เปิด ⇒ ตอนนี้ `false/no/off` = ปิดด้วย · `ZS_ALLOW_REGISTER` เดิมเปิดเฉพาะ `1` ⇒ ตอนนี้ `true/yes/on` ก็เปิด · `AUTO_FORCE_ALL_TF` เหมือนกัน
- security header ใหม่ทุก response (B8) · legacy ที่ `/` ได้ CSP **บังคับเฉพาะ script** (script จาก origin เดียวกัน + script inline ของหน้า login ด้วย hash ที่คำนวณจากไฟล์จริงตอนบูต) + CSP เต็มแบบ report-only · ถ้าหน้า legacy ขาว/ปุ่มไม่ทำงานหลัง deploy: เปิด console ดู `Refused to execute` แล้วแจ้ง (ย้อนกลับ = revert commit ของ `zservice/security/headers.py`)
- **container รันด้วย user `app` (uid 10001) ไม่ใช่ root แล้ว** · ครั้งแรกหลัง deploy TradingView จะ login ใหม่ 1 ครั้ง (cache token ย้ายไป `/app/state`)
- **ออกจากระบบ = จบ session ที่ server จริง** (token นั้นใช้ไม่ได้อีก) · **เปลี่ยนรหัสผ่าน** ได้ที่หน้า Settings ของ UI ใหม่ (`/app/settings/`) — เปลี่ยนแล้ว session อื่นทุกเครื่องหลุด (legacy ที่เปิดค้างไว้จะเด้งไป login)
- รหัสผ่านเดิมยังใช้ได้ · login สำเร็จครั้งแรกหลัง deploy ระบบอัปเกรด hash เป็น 600,000 รอบให้เอง (login ช้าขึ้น ~0.3 วิ) · รหัสใหม่ต้องยาว ≥ 12 ตัว
- การสมัคร user ใหม่ปิดอยู่ (`ZS_ALLOW_REGISTER`) — หน้า login แสดงฟอร์มสมัครเฉพาะตอนฐานข้อมูลไม่มี user และจะตอบว่าปิดอยู่
- legacy: คำสั่งที่เปลี่ยนข้อมูล (POST/PUT/DELETE) ต้องมี header `Authorization` — legacy ส่งให้อยู่แล้วทุกครั้ง · ถ้าเจอ 403 "state-changing requests need the Authorization header" = localStorage ไม่มี token ⇒ login ใหม่
- `/docs` ต้อง login (B6) · ถ้าเปิดจากเบราว์เซอร์ที่ login แล้วยังใช้ได้
- login แล้วได้ cookie `__Host-zs_session` (HttpOnly) + `__Host-zs_csrf` เพิ่ม (B4) — legacy ยังใช้ token ใน JSON แบบเดิม · UI ใหม่ใช้ cookie · ออกจากระบบ: `POST /api/auth/logout`
- login ผิดเกิน 5 ครั้ง/นาที ตอบ 429 (B9)
- รัน legacy dev ในเครื่อง (`cd dash && npm run dev`) ต้องตั้ง `ZS_CORS_ORIGINS` ใน `.env` ในเครื่องก่อน ไม่งั้นเบราว์เซอร์จะบล็อก cross-origin

## 2. ก่อนเริ่ม (ตรวจในเครื่อง)

```bash
cd "$ZSERVICE_REPO"   # โฟลเดอร์ที่ clone z-service ไว้
git switch feat/web-ui && git pull
# venv = Python 3.12 + เวอร์ชันเดียวกับ image ทุกตัว (สร้างครั้งเดียว/เมื่อ lock เปลี่ยน)
#   uv venv --python 3.12 --seed backend/venv
#   backend/venv/bin/pip install --require-hashes -r backend/requirements.lock -r backend/requirements-dev.lock
#   backend/venv/bin/pip install --no-deps -r backend/requirements-git.txt
cd backend && MONGO_URI= venv/bin/python -m pytest        # ต้องผ่านทั้งหมด (warning = fail)
cd .. && backend/venv/bin/ruff check .                     # All checks passed
cd web && nice -n 15 npm ci && nice -n 15 npm run verify   # เขียวทุกด่าน
```
- ตรวจใน Coolify: port 9999 **ไม่ได้** map ออก host (ต้องเข้าผ่าน Traefik เท่านั้น) — จำเป็นสำหรับ B9

---

## 3. ลำดับ deploy (ทำตามลำดับ ห้ามสลับ)

| ขั้น | ทำ | ตรวจว่าผ่าน | ย้อนกลับ |
|--|--|--|--|
| 1 | Coolify → env: ตั้ง `AUTH_SECRET` (paste จาก clipboard แล้ว copy อย่างอื่นทับ) | ค่ามีใน Coolify | — |
| 2 | Coolify → env: ตั้ง `ZS_API_KEYS` = §1.1 | ค่ามีใน Coolify | ลบ env |
| 3 | merge `feat/web-ui` → `main` แล้ว push (**user สั่งเท่านั้น**) → Coolify build + deploy | badge เวอร์ชันบนหน้าเว็บเปลี่ยน · `curl -s https://z-service.duckdns.org/api/healthz` = `{"status":"ok"}` | revert merge commit แล้ว push |
| 4 | login หน้าเว็บใหม่ 1 ครั้ง (secret เปลี่ยน ⇒ session เดิมหลุดทุกคน) | legacy ที่ `/` ใช้ได้ 9 แท็บ | — |
| 5 | ทดสอบ key ใหม่จากเครื่องบ้าน: `source tools/zsvc_curl.sh && zsvc_curl -m 15 "$ZS_BASE_URL/api/automate/status"` | ได้ JSON สถานะ (ไม่ใช่ 401) | — |
| 6 | ทดสอบสคริปต์เดิมยังใช้ PULL_KEY ได้: `.claude/skills/us-stock-fund-manager/scripts/load_all.sh` (stock-radar) · PULL_KEY ตอนนี้ใช้ได้เฉพาะอ่าน + สั่ง job (รวม `POST /api/stock_radar/scan`) + gold job + แก้ watchlist (§8.2c F15) · ทั้ง header `X-Pull-Key` และ `?pull_key=` · path เดิมทุกตัวที่สคริปต์ stock-radar เรียก (test `test_scopes.py` / `test_machine_auth.py` ล็อกไว้) | โหลด csv สำเร็จ · `/api/admin/key_audit` ไม่มี `legacy-pull-key` สถานะ 403 (ถ้ามี = สคริปต์เรียก route นอกขอบเขต ⇒ แจ้ง) | ใส่ scope เพิ่มใน `LEGACY_SCOPES` |
| 7 | ย้ายสคริปต์บ้านไปใช้ `tools/zsvc_client.py` / `tools/zsvc_curl.sh` (งานแยก · ทำหลังขั้น 3 เท่านั้น) | รันผ่านทุกตัว | git revert ฝั่งสคริปต์ |
| 8 | เปิด `/api/admin/key_audit` (login แล้ว) ทิ้งไว้ ≥ 1 วันทำการ | `summary.callers` ไม่มี `legacy-pull-key` | — |
| 9 | ลบ env `PULL_KEY` ใน Coolify → redeploy | สคริปต์บ้านยังผ่าน · key เก่าที่รั่วใน git ใช้ไม่ได้แล้ว | ใส่ `PULL_KEY` คืน |
| 10 | ลบ literal key เก่าออกจาก `scripts/symbols/add_symbols_0811.py` · `docs/ops/ADD_SYMBOLS.md` (z-service) · `cmd.md` (stock-radar) | `git grep` ไม่เจอ | — |

---

## 3.1 build image ครั้งแรกหลัง merge (สิ่งที่เปลี่ยนใน Dockerfile)
- **ก่อนกด deploy:** เปิด env ใน Coolify เทียบกับ [config-reference.md](config-reference.md) — ทุกค่าต้องอยู่ในขอบเขต/รูปแบบที่ตารางบอก (โดยเฉพาะ bool และตัวเลข) ไม่งั้นบูตไม่ขึ้น (§1.3)
- dependency ใหม่ `pydantic-settings==2.16.0` (ใน `requirements.lock` แล้ว · OSV 0)
- stage ใหม่ `web` (node 24 · pin digest) รัน `npm ci --ignore-scripts` + `npm run verify` — ไม่ผ่าน = image ไม่ถูกสร้าง = Coolify รันเวอร์ชันเดิมต่อ (ไม่ล่ม)
- Python ติดตั้งจาก `requirements.lock` แบบ `--require-hashes` + tvdatafeed pin commit
- `HEALTHCHECK` ที่ `/api/healthz` (start-period 90 วิ) ⇒ Coolify ทำ rolling update ได้ · job auto ไม่ซ้อนเพราะ heartbeat
- uvicorn `--no-server-header`
- ถ้า build นานกว่าปกติ: stage `web` + test ใช้เวลาเพิ่ม ~1–2 นาที
- runtime image ไม่มี `git` แล้ว (ลงแล้วถอนใน layer เดียวกับ pip) · `USER app` · `compileall` ตอน build
- ตรวจหลัง deploy: log ของ container ต้องไม่มี `PermissionError` / `automate.log not writable` · ถ้ามี = มีโค้ดเขียนไฟล์นอก `/app/state` หรือ `/tmp` ⇒ แจ้ง (ย้อนกลับชั่วคราว: ลบบรรทัด `USER app` แล้ว build ใหม่)
- dependency: `python3 tools/osv_audit.py` ต้องได้ 0 advisories ก่อน merge (ตรวจทั้ง `requirements.lock` ของ image และ `requirements-dev.lock` ของเครื่องมือ test/lint · ตอนนี้ 0 · lock ใช้ `--exclude-newer` 7 วัน)

## 3.2 pre-push hook (เลือกเปิดเอง)
- `git config core.hooksPath .githooks` — ก่อน push จะรัน ruff + pytest + web verify + audit + build legacy + ตรวจไม่มี key ใน commit
- ข้ามครั้งเดียว: `git push --no-verify`

## 4. หมุน key / secret (ใช้ภายหลัง)

- **key เครื่อง:** `tools/manage_keys.py new --id home2 ...` → เพิ่ม entry ใหม่ต่อท้าย `ZS_API_KEYS` (คง `home` ไว้) → deploy → เปลี่ยน `ZS_KEY_ACCOUNT=home2` ที่เครื่องบ้าน → ลบ entry `home` → deploy
- **`AUTH_SECRET`:** `tools/manage_keys.py secret --name AUTH_SECRET --force` → `copy` → วางใน Coolify → deploy (ทุก session หลุด)
- **เพิกถอนฉุกเฉิน:** ลบ entry ออกจาก `ZS_API_KEYS` → redeploy

---

## 5. บันทึกการทำจริง (เติมเมื่อทำ)

| วันที่ | ขั้น | ใครทำ | ผล |
|--|--|--|--|
| 24 ต.ค. 2026 | ออก `AUTH_SECRET` + key `home` ลง Keychain | Claude | ✅ ยังไม่ตั้งใน Coolify (user สั่งให้ทำหลังสุด) |
| 26 ต.ค. 2026 | ตรวจก่อน deploy ในเครื่อง (`8b7fb06`) | Claude | ✅ pytest ทั้งหมด + กลุ่มเลือกรัน (Mongo ในเครื่อง 11 · parity 9 · TradingView จริง 2) · ruff · web verify 87 test · OSV 0 · npm audit 0 (web + dash) · build dash · **build image จริง** (uid 10001 `app` · ไม่มี git · healthcheck healthy · log ไม่มี PermissionError) · **stock-radar `load_all.sh -force` เทียบ production ปัจจุบัน vs image ใหม่ (ข้อมูลชุดเดียวกัน):** CSV แท่งราคา 8 ไฟล์ byte ตรงกันทุกไฟล์ ยกเว้นหัวไฟล์ใหม่ 2 บรรทัด (`# bars_expected` · `# short_history` — radar_lib อ่านได้) · formula ต่างแค่แถวเอกสาร short_history + ข่าวสด · ผล compute (digest/full.json/health/horizon/port_gate/rebound/jump/rocket/pre_ignition) ตรงกันหมด ยกเว้น fingerprint · อายุข้อมูล · ข่าว · PULL_KEY เดิมใช้ได้ · key `zsk_` ได้ไฟล์เดียวกัน · ไม่มี key/ key ผิด = 401 |

## Inbound events (set last, after the senders exist)

- `ZS_EVENT_SENDERS` — JSON list of allowed senders with their signing secret (`whsec_…`)
  and/or public key (`whpk_…`); see `docs/inbound-events.md`. Empty = every inbound event
  is refused (404), which is the safe default until a sender is configured.
- Optional: `ZS_EVENT_TOLERANCE_SECONDS` (300), `ZS_EVENT_MAX_BYTES` (262144),
  `ZS_EVENT_KEEP_DAYS` (30).
- Indexes are created at start-up (`inbound_events`: unique sender + webhook id, TTL).

