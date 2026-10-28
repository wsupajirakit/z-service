# z-service web — แผนยกเครื่อง UI + ปิดหนี้ความปลอดภัย backend

> **สถานะ:** แผนล็อกแล้ว (ส 24 ต.ค. 2026) · branch `feat/web-ui` · ยังไม่ deploy อะไร
> **ชื่อ:** UI ใหม่ = `web/` (ไม่เรียกตัวเองว่า v2 · user สั่ง 24 ต.ค.) · ระหว่างสร้างเสิร์ฟที่ `/app/` (ค่าจาก env `APP_BASE`) · cutover แล้วอยู่ที่ `/` และ legacy ย้ายไป `/legacy/`
> **runbook:** ค่า env ทุกตัวตั้งหลังสุด — ลำดับ/ค่า/วิธีตรวจ/ย้อนกลับอยู่ที่ `docs/runbook-deploy.md` (user สั่ง 24 ต.ค.)
> **กติกาใหญ่:** ระบบปัจจุบันทั้งหมด = **legacy** — เก็บไว้ ใช้ได้ต่อ และย้อนกลับได้ทุกขั้น
> ทุกเวอร์ชัน / ช่องโหว่ / ขนาด / พฤติกรรมในไฟล์นี้ **ดึงหรือวัดจริงวันที่ 24 ต.ค. 2026** (npm registry · PyPI · GitHub Advisory DB · nodejs.org · เอกสาร Coolify/OWASP/React/TanStack/Next · ซอร์ส Starlette/uvicorn ในเครื่อง · curl ไปเซิร์ฟเวอร์จริง) — แหล่งอยู่ §18
> จุดที่ยังต้องทดสอบก่อนใช้ ติดป้าย **[ยืนยันใน Phase 0]** — ห้ามเขียนโค้ดตามจุดนั้นก่อนได้ผลจริง

---

## 0. สรุปหน้าเดียว + การตัดสินที่ล็อกแล้ว

| # | เรื่อง | ตัดสิน | เหตุผลสั้น (หลักฐานใน §) |
|--|--|--|--|
| 1 | framework | **Vite 8 + React 19.3 SPA + TanStack Router + TanStack Query** | production ไม่มี Node = ตัดทั้งตระกูล RCE ของ Next/RSC · react.dev แนะนำชุดนี้สำหรับ SPA (§3) |
| 2 | URL ของ UI ใหม่ | **`/app/` แบบ path routing** + ไฟล์ route shell ต่อ route · ค่าที่เปลี่ยนตามข้อมูลอยู่ใน search params | ไม่ต้องแก้ backend เพื่อ SPA fallback (§5) |
| 3 | ชุด component | **หน้าตาแบบ shadcn/ui เขียนเองใน repo (`src/components/ui`) บน element มาตรฐาน** — Dialog/AlertDialog บน `<dialog>` · Toast · Menu · Tabs · Switch · DataTable · ไม่ใช้ radix | native API ทำได้ครบ (กฎ dependency ใหม่ §4.3) · ไม่เพิ่ม bundle |
| 4 | TypeScript | **6.0.x** · ย้าย 7.x เมื่อพ้น cooldown และ typescript-eslint ประกาศรองรับ | 7.0.2 ออก 24 ต.ค. 2026 (วันนี้) |
| 5 | CI | **Coolify (ที่ใช้อยู่)** — ด่านตรวจอยู่ใน Docker build · + git pre-push hook ในเครื่อง · ไม่ใช้ GitHub Actions | เอกสาร Coolify: build พัง = เวอร์ชันเดิมรันต่อ (§11) |
| 6 | หนี้ backend | **แก้ทุกข้อ B1–B13** เรียงตามความเสี่ยง · เครื่องที่บ้านต้องสั่งงานได้ตลอดทุกขั้น (§8, §9) | |
| 7 | `npm audit fix` ใน legacy | **ทำ** — commit ความปลอดภัยล้วน (lockfile เท่านั้น ไม่แตะโค้ด) + build + เปิดทุกแท็บเช็ค | axios 1.17.0 ที่มีช่องโหว่ถูก bundle ไปถึงผู้ใช้จริง |
| 8 | ธีม | **มืด (ค่าเริ่ม) / สว่าง** ปุ่ม sun/moon บนหัว · จำใน cookie `zs_theme` · สีหลัก emerald บน zinc (ต่างจาก indigo ของ MindGrid) | user สั่ง |
| 9 | ภาษา | **ไทย · English · Italiano ครบทุก label** · ภาษาไหนขาด key = build fail | user สั่ง (§7) |
| 10 | legacy | หน้าเว็บเดิม `dash/` **ไม่ย้ายโฟลเดอร์** (สคริปต์ 30+ ตัวอ่าน `dash/src/App.tsx`) · หลัง cutover เสิร์ฟที่ `/legacy/` · กลไก `PULL_KEY` เดิมใช้ต่อได้ช่วงย้าย แล้วค่อยปิด | §6, §9 |

**ห้ามเกิดระหว่างทำ:** v1/legacy ใช้ไม่ได้ · สคริปต์ stock-radar (`load_all.sh` · `fill_short_hist.py` · `fetch_new_symbols.py` · `start_auto_all.py` · `add_symbols_*.py`) สั่งงานไม่ได้ · auto job หยุดเงียบ

---

## 1. สภาพปัจจุบัน (วัดจริง)

| เรื่อง | ค่าที่วัด |
|--|--|
| ขนาดโค้ด | `dash/src/App.tsx` 5,764 บรรทัด / 288 KB · `RadarView.tsx` 1,634 บรรทัด |
| hard code | `SYMBOLS` ~830 แถวใน App.tsx · `EXCHANGES` · `TIMEZONE_OPTIONS` · `EARNING_SCAN_PROVIDER_LABELS` · `TAB_IDS` · literal `/api/...` ~45 จุด |
| state | `useState` 146 · `setInterval` 13 · `localStorage` 12 จุด · ไม่มี cache กลาง |
| bundle | JS ก้อนเดียว **700,920 B (196,409 B gzip)** · CSS 11.7 KB gzip · ไม่มี code-split |
| HTML ดิบ | `dangerouslySetInnerHTML` 3 จุด ผ่าน regex markdown ทำเอง |
| lockfile legacy | `npm audit`: **11 ช่องโหว่ (high 10)** · axios 1.17.0 อยู่ใน bundle (advisory 12 ตัว แก้ใน 1.20.0) · ไม่อัปเดตตั้งแต่ 3 ก.ค. |
| deploy | Dockerfile เดียว: `node:22-slim` build → `python:3.12-slim` + uvicorn port 9999 · ไม่มี `HEALTHCHECK` · ไม่มี CI |
| เซิร์ฟเวอร์จริง | TLS ถูกต้อง (Let's Encrypt YR2 · หมด 24 พ.ย. 2026 · ต่ออัตโนมัติ) · header `server: uvicorn` · **ไม่มี security header เลย** · `/docs` และ `/openapi.json` ตอบ **200 โดยไม่ต้อง login** |
| repo | z-service และ stock-radar เป็น private (GitHub API ตอบ 404) |
| API contract | Pydantic request model 17 ตัว · `response_model` = 0 |

---

## 2. ข้อกำหนด → วิธีวัดว่าผ่าน

| ข้อกำหนด | วัดผ่านด้วย |
|--|--|
| รันที่เดิม | image เดียว · service Coolify เดิม · `/app/` เปิดได้หลัง login · legacy ที่ `/` ทำงาน |
| ไม่กระทบ script หลังบ้าน | สคริปต์ทุกตัวใน §6 รันผลเดิมทุกขั้น (ขั้นที่เปลี่ยนวิธียืนยันตัวตนมีช่วงรับทั้งแบบเก่าและใหม่) |
| เก็บของเดิมเป็น legacy | `git diff dash/src` = ว่างตลอด Phase 0–5 (ยกเว้น lockfile ข้อ 7) |
| เร็ว | งบ bundle §10 บังคับใน Docker build |
| ปลอดภัย + เวอร์ชันล่าสุด | §8 ครบ · `npm audit` = 0 · ทุก dep pin exact + hash (Python) |
| scalable · ไม่สร้างหนี้ · ขยายได้ | กฎ lint §12.2 · เพิ่มแท็บไม่แก้ไฟล์กลาง |
| ห้าม hard code | grep ใน build: ห้าม literal `/api/` นอก `src/shared/api/` · ห้าม ticker ในโค้ด · ห้ามข้อความ UI นอกไฟล์ภาษา (lint) |
| เครื่องที่บ้านสั่งงานตรงได้ ปลอดภัย | §9 — key แยกต่อเครื่อง · ขอบเขตสิทธิ์ · header เท่านั้น · TLS ตรวจจริง · หมุน key ได้ · มี log |
| 3 ภาษา + 2 ธีม | build fail ถ้า key ภาษาไม่ครบ 3 · Playwright ถ่ายภาพทุกหน้า × 3 ภาษา × 2 ธีม |

---

## 3. เลือก framework — เทียบจากหลักฐาน

บริบทตัดสิน: อยู่หลัง login ทั้งหมด · ผู้ใช้คนเดียว · ไม่ต้อง SEO · ข้อมูลมาจาก FastAPI · image เดิมมีแค่ Python เป็น process

| ตัวเลือก | หลักฐาน | ผล |
|--|--|--|
| Next.js 16.4.3 (server) | ต้องเพิ่ม Node process/service · GitHub Advisory: **RCE critical 4 ตัว 8 ก.ย.–22 ต.ค. 2026** (Image Optimization AVIF/SVG · `next/og` · `use cache`) + SSRF high + cache poisoning · RSC มี DoS/RCE ต่อเนื่อง CVE-2025-55182 (ธ.ค. 2025) → CVE-2026-44907 (ก.ค. 2026) | ❌ |
| Next.js `output: 'export'` | เอกสาร Next: ไม่รองรับ cookies · headers · redirects · rewrites · proxy · Server Actions · Image Optimization · dynamic route ที่ไม่มี `generateStaticParams` ⇒ เหลือ SPA ที่ toolchain หนักกว่า · asset อยู่ `/_next/` | ❌ |
| TanStack Start 1.169 | server function XSS critical CVE-2026-102989 (15 ต.ค. 2026) · เราไม่ใช้ server function | ❌ |
| React Router 8.5 framework (SPA) | advisory มิ.ย.–ก.ค. 2026 กระจุกที่ SSR/RSC · search params type-safe น้อยกว่า | 🟡 สำรอง |
| **Vite 8 + React 19 + TanStack Router/Query** | react.dev: SPA ใช้ Vite + (React Router หรือ TanStack Router) + TanStack Query · ข้อเตือนของ react.dev คือต้องทำ SSR/SSG/RSC เอง ซึ่งงานนี้ไม่ต้องใช้ · TanStack Router: file-based · `autoCodeSplitting` · search params ผ่าน schema แล้ว type-safe · `staticData` ต่อ route | ✅ |

ทบทวนเมื่อ: ต้องมีหน้า public ที่ต้อง SEO/SSR จริง — โครง feature-folder (§12) ย้ายไป framework อื่นได้โดยไม่ต้องเขียน feature ใหม่

---

## 4. Stack + เวอร์ชัน

### 4.1 Frontend (npm registry 24 ต.ค. 2026)

| ชั้น | แพ็กเกจ | latest | นโยบาย |
|--|--|--|--|
| build runtime | Node.js | 24.22.1 LTS (maintenance ตั้งแต่ 20 ต.ค. · EOL 30 เม.ย. 2028) · 26.x เป็น LTS **28 ต.ค. 2026** | เริ่ม `node:24-slim` pin digest → ย้าย 26 หลังเป็น LTS + cooldown · Node ใช้แค่ตอน build |
| npm | มากับ Node 24.22.1 | 11.19.1 | รองรับ `min-release-age` · `allowScripts` · `allow-git` |
| UI | react · react-dom | 19.3.1 | ไม่ใช้ RSC/Server Functions |
| build | vite · @vitejs/plugin-react | 8.3.5 · 6.1.2 | ต้อง ≥ 8.3.3 (CVE-2026-112945/6/7) |
| router | @tanstack/react-router · @tanstack/router-plugin | 1.170.46 · 1.168.48 | เวอร์ชันที่โดน malware CVE-2026-45321 (11 พ.ค. 2026) ห้ามเข้า lockfile — ตรวจใน build |
| data | @tanstack/react-query | 5.104.5 | |
| ตาราง | ไม่ใช้ library — `DataTable` ของ repo (ค้นหา · เรียง · แบ่งหน้า) + logic ล้วนใน `utils/table.ts` | | ทุกตารางแบ่งหน้า (แถวใน DOM ≤ 100) จึงไม่ต้อง virtualize · ถอด react-table/react-virtual แล้ว |
| schema | zod | 4.6.7 | ≥ 4.6.6 (GHSA-mrhx-c7xc-m3w5) · เบราว์เซอร์ใช้ `zod/mini` (งบ bundle) |
| HTTP | native `fetch` + openapi-fetch 0.17.0 · openapi-typescript 7.13.0 (dev) | | **ไม่ใช้ axios** |
| style | tailwindcss · @tailwindcss/vite | 4.3.3 | token สีใน CSS variables (§7.2) |
| component | เขียนเองตามแบบ shadcn/ui (ไม่ใช้ CLI · ไม่ใช้ radix) | | §ตัดสินข้อ 3 |
| i18n | @inlang/paraglide-js | 2.29.1 (advisory 0) | §7.1 · **[ยืนยันใน Phase 0]** · สำรอง @lingui 6.10.1 (advisory 0) |
| icon · chart | path จาก Lucide (ISC) ใน `icons.tsx` (ไม่ใช้ runtime lucide-react) · lightweight-charts 5.2.1 | | chart lazy load |
| markdown | markdown-to-jsx 9.10.3 (`disableParsingRawHTML: true` ใน wrapper เดียว) | ✅ เลือกใน Phase 0 | แทน `dangerouslySetInnerHTML` |
| ภาษา | typescript | 6.0.x (7.0.2 รอ) | |
| lint · test | eslint 10.13 + typescript-eslint + react-hooks · vitest 5.0.5 · @playwright/test 1.64.1 · msw 3.0.3 | | |

### 4.2 Backend (PyPI 24 ต.ค. 2026)

| แพ็กเกจ | ตอนนี้ | latest | นโยบาย |
|--|--|--|--|
| fastapi | ไม่ pin | 0.162.0 | pin + hash |
| starlette | ไม่ pin (ในเครื่อง 1.3.1) | 1.10.0 (ต้อง Python ≥ 3.11 · image 3.12 ✅) | pin + hash · อ่าน changelog ก่อนขยับ |
| uvicorn | ไม่ pin | 0.54.0 | pin + hash · `--no-server-header` · `--proxy-headers` + `FORWARDED_ALLOW_IPS` |
| tvdatafeed | git HEAD (ตอนนี้ `e6f6aaa7de43`) | — | pin commit SHA |
| ตัว lock | — | uv 0.13.5 (`uv pip compile --generate-hashes`) | `pip install --require-hashes -r requirements.lock` |
| rate limit | — | slowapi 0.1.10 (ออก มิ.ย. 2026) | **ไม่ใช้** — container เดียว ⇒ ตัวจำกัดในหน่วยความจำ ~40 บรรทัด ทดสอบได้ ไม่เพิ่ม dep |

### 4.3 นโยบาย supply chain (ทั้งสองฝั่ง)
- pin exact + lockfile · Docker ใช้ `npm ci` / `pip install --require-hashes` เท่านั้น
- `web/.npmrc`: `min-release-age=7` · `allow-git=none` · `ignore-scripts=true` · `save-exact=true` · `engine-strict=true`
  - เหตุผล: malware TanStack ถูกปล่อย 84 เวอร์ชันใน **6 นาที** และทำงานตอน install — cooldown + ห้าม install script ตัดได้ทั้งสองทาง
  - patch ความปลอดภัยที่ใหม่กว่า 7 วัน → `min-release-age-exclude` ทีละตัว พร้อมเหตุผลใน commit
- dependency ใหม่ต้องผ่าน: native API ทำไม่ได้ · audit สะอาด · ดู provenance · ขนาดอยู่ในงบ
- อัปเดตรวมเดือนละครั้ง + ทันทีเมื่อ advisory โดนเรา

---

## 5. Deploy: legacy + UI ใหม่ ใน service เดิม

```
                 Coolify (service เดิม · โดเมนเดิม · port 9999)
                                   │
                         FastAPI (backend/)
   ┌───────────┬──────────┬────────────────────────┬───────────────────────────┐
 /api/*      /login     /  = legacy UI             /app/ = UI ใหม่
 (เดิม +     (เดิม)     static/index.html          static/app/index.html
  §8 §9)                + /assets/ (dash/ เดิม)     + /app/assets/ (web/ · base จาก env `APP_BASE` (ค่าเริ่ม '/app/'))
                         หลัง cutover → /legacy/     หลัง cutover → /
```

- **ไม่ต้องแก้ backend เพื่อเสิร์ฟ UI ใหม่:** `StaticFiles(directory="static", html=True)` ที่ mount `/` เสิร์ฟ `static/app/index.html` และ `/app/assets/*` ให้เอง (ตรวจซอร์ส Starlette: path ที่เป็นโฟลเดอร์มี `index.html` → redirect เติม `/` แล้วเสิร์ฟ · หาไม่เจอ → `404.html` ที่ราก)
- **deep link / F5 กลางหน้า:**
  1. หลัง `vite build` สคริปต์ `scripts/emit-route-shells.ts` อ่าน route tree ที่ router-plugin generate แล้ว copy `index.html` เป็น `dist/<route>/index.html` ทุก route — รายชื่อมาจาก route tree ไม่ได้พิมพ์เอง
  2. router ตั้ง trailing slash ให้ตรงกับ redirect ของ Starlette **[ยืนยันชื่อ option ใน Phase 0]**
  3. ค่าที่เปลี่ยนตามข้อมูล (stamp · symbol · list) อยู่ใน search params
  - ทางสำรอง: hash history
- **auth ช่วงคู่ขนาน:** login เดิม → backend ตั้ง cookie HttpOnly (§8 B4) ให้ด้วย ⇒ UI ใหม่ ใช้ cookie นั้น · legacy ใช้ Bearer จาก localStorage แบบเดิม · ทุกโค้ดที่แตะ session ของ UI ใหม่ อยู่ใน `src/shared/auth/session.ts`
- **Dockerfile (เพิ่มเท่านั้น):**
```dockerfile
FROM node:24-slim@sha256:<pin> AS frontend_web
WORKDIR /app/web
COPY web/package.json web/package-lock.json web/.npmrc ./
RUN npm ci --ignore-scripts
COPY web/ ./
RUN npm run verify   # typecheck + lint + unit + i18n-complete + no-hardcode + build + route-shells + budget + lockfile-guard
# ... stage python เดิม ...
COPY --from=frontend    /app/dash/dist    ./static      # legacy (เดิม)
COPY --from=frontend_web /app/web/dist ./static/app   # เพิ่ม
```
- `.dockerignore` เพิ่ม `web/dist/`
- **rollback UI ใหม่** = ลบบรรทัด `COPY --from=frontend_web`
- **ความเสี่ยงต่อ legacy:** UI ใหม่ build พัง ⇒ image ใหม่ไม่เกิด ⇒ Coolify รันเวอร์ชันเดิมต่อ (เอกสาร Coolify) — legacy ไม่ล่ม แต่การแก้ legacy (เช่น เพิ่มหุ้นใน App.tsx) จะ deploy ไม่ได้จนกว่า UI ใหม่ build ผ่าน ⇒ pre-push hook รัน `verify` ทั้งสองฝั่งก่อน push เสมอ

---

## 6. Legacy — สิ่งที่ห้ามพัง

| ผู้ใช้ | ใช้อะไร | แผนกระทบ |
|--|--|--|
| `backend/build_meta.py` (Dockerfile) | อ่าน `dash/src/App.tsx` บล็อก `const SYMBOLS … \n];` · `dash/package.json` | ไม่แตะ |
| `start_auto_all.py` · `backend/test_failed.py` · `check_symbols.py` · `fix_tickers_1019.py` · `resolve_new_symbols.py` · `add_symbols_*.py` 21 ไฟล์ | อ่าน/แก้ `SYMBOLS` · ยิง API ด้วย pull key | path ไฟล์ไม่แตะ · วิธีส่ง key ย้ายตาม §9 (มีช่วงรับทั้งสองแบบ) |
| stock-radar `bottleneck-playbook/scripts/screen.py` · `zsvc_add/webull_check.py` · `tv_verify*.py` | อ่าน App.tsx | ไม่แตะ |
| stock-radar `load_all.sh` · `fetch_csv.sh` · `fill_short_hist.py` · `fetch_new_symbols.py` · `wait_zsvc_*.py` | `/api/export_zip` `/api/automate/status` `/api/history` `/api/automate` `/api/auto/*` `/api/watchlist` | ย้ายวิธีส่ง key ตาม §9 · endpoint ไม่เปลี่ยน |
| คู่มือ `ADD_SYMBOLS.md` · `dev.md` · `cmd.md` · memory | ขั้นตอน + **มี key จริงอยู่ในไฟล์** | ลบ key ออก + อัปเดตขั้นตอน (§9.5) |

ย้ายรายชื่อหุ้นออกจาก App.tsx = Phase L2 (§14) ทำครั้งเดียวทุกแถวในตาราง

---

## 7. ภาษา + ธีม

### 7.1 i18n ไทย · English · Italiano
- **ไลบรารี: Paraglide JS 2** — คอมไพล์ข้อความเป็นฟังก์ชันตอน build ⇒ type-safe (key ผิด = compile error) · ไม่ parse ตอนรัน · advisory 0 · **(ผล Phase 0: ทั้ง 3 ภาษาอยู่ใน bundle เดียว ~2.4 KB gzip ที่ 17 key — ยอมรับ; plugin ต้องมาจาก npm ไม่ใช่ CDN)**
  - **[ยืนยันใน Phase 0]**: สลับภาษาโดยไม่ reload · ใช้กับ Vite 8 · ขนาดจริงต่อภาษา · ถ้าไม่ผ่าน → Lingui 6
- ไฟล์: `web/messages/{th,en,it}.json` = **แหล่งเดียวของข้อความ UI** · lint ห้ามข้อความ UI ใน JSX (ยกเว้นข้อมูลจาก API)
- **ด่าน build:** key ต้องครบทั้ง 3 ภาษา · placeholder (`{count}` ฯลฯ) ต้องตรงกันทุกภาษา · ขาด = build fail
- ตัวเลข / เงิน / วันที่ / เวลา: `Intl.NumberFormat` · `Intl.DateTimeFormat` ตาม locale ที่เลือก · timezone ที่แสดงมาจาก `GET /api/settings/timezone` (ค่าที่ user ตั้ง) ไม่ใช่ locale
- พหูพจน์ใช้กลไกของไลบรารี ไม่ต่อสตริงเอง
- ศัพท์ตลาด (ticker · EMA · RSI · CMF · ATR · R:R) ไม่แปล · อภิธานศัพท์ 3 ภาษาอยู่ในไฟล์ภาษา
- เลือกภาษาจากปุ่มบนหัว (EN/TH/IT) · จำใน cookie `zs_locale` เท่านั้น (`Path=/` · `SameSite=Strict` · `Secure` เมื่อ https · 1 ปี · strategy ของ Paraglide) · ไม่มี cookie = English (base locale)
- ข้อความจาก API (ผล AI · ข่าว · log) แสดงตามต้นฉบับ ไม่แปล
- คำแปลอิตาลีและอังกฤษ: ผมร่างครบทุก key · user ตรวจรอบเดียวใน Phase 5

- **สถานะ 25 ต.ค. (ตรวจซ้ำหลัง user ทักว่าแปลไม่ครบ):** รอบก่อนผมตรวจแค่ว่า key ครบ 3 ภาษา ไม่ได้ไล่ทุกข้อความที่ผู้ใช้เห็นจริง และ lint ห้ามข้อความใน JSX ที่เขียนไว้ข้างบน**ไม่ได้ทำ** — แก้แล้วทั้งหมด:
  - หน้า login ของ UI ใหม่เอง (`/app/login/` · 3 ภาษา · ธีม) แทนการเด้งไปหน้า login legacy ภาษาไทย · session ใช้ cookie ล้วน ไม่ยืม token legacy (`0cfe7d7`)
  - ข้อความที่ server ส่งมาแสดง (สถานะ/คำเตือนรอบเรดาร์ · ผลทดสอบ TradingView · history · gold stop · หมายเหตุ earning · error ของ job · ค่า status/mode/phase) → `code` + `params` แปลจาก `msg_*` / `enum_*` · `zservice/core/messages.py` `coded()` · test ฝั่ง backend ตรวจทุก code กับไฟล์ภาษา (`4a3ba99`)
  - ESLint fail เมื่อมีข้อความ UI ใน JSX หรือ attribute ที่ผู้ใช้เห็น (`4a3ba99`)
  - พหูพจน์ en/it ผ่าน `Intl.PluralRules` (variant ของ inlang message format) · ไทยไม่มีพหูพจน์ · ชื่อแท็บ = ชื่อหน้าตามภาษา (`b322108`)
  - ยังเป็นภาษาต้นฉบับโดยตั้งใจ: ผล AI (prompt ทองถามเป็นไทย) · ข่าว · log ระบบ (อังกฤษตามกฎ 17.1) · รายงาน digest จาก `lib.py` (สำเนา stock-radar แก้ไม่ได้) · ข้อความ Telegram
  - legacy (`dash/`) แยกไว้ไม่แตะตามที่ user สั่ง

### 7.2 ธีม มืด / สว่าง / ตามระบบ
- สีทั้งหมดเป็น CSS variables ชุดเดียว ชื่อตาม shadcn/ui (`--background` `--foreground` `--card` `--primary` `--muted` `--accent` `--destructive` `--border` `--ring` `--sidebar-*` + `--up` `--down` `--warning`) · Tailwind 4 อ่านผ่าน `@theme` · component ห้ามใช้ค่าสีตรง (lint)
- โหมด: `dark` (ค่าเริ่ม) · `light` · จำใน cookie `zs_theme` เท่านั้น (ค่าเดียวกับ `zs_locale`) · ไม่มีการบันทึกที่ server
- กันจอกะพริบ: `public/theme-init.js` ไฟล์เล็กโหลดแบบ sync ใน `<head>` (ผ่าน CSP `script-src 'self'` · ไม่ต้องมี inline script)
- กราฟ lightweight-charts รับสีจาก token เดียวกัน · เปลี่ยนธีม = `applyOptions` ไม่สร้างกราฟใหม่
- contrast ผ่าน WCAG AA ทั้งสองธีม (ตรวจอัตโนมัติจาก token) · สีขึ้น/ลงไม่ใช่เขียว/แดงล้วน (มีสัญลักษณ์ ▲▼ คู่)

---

## 8. ความปลอดภัย — แก้ทุกข้อ

### 8.1 Frontend UI ใหม่ (ทำใน web เอง)

| # | มาตรการ |
|--|--|
| F1 | supply chain §4.3 · build ตรวจ lockfile: ไม่มี git dep · ไม่มีเวอร์ชันในรายการ malware ที่รู้ |
| F2 | production ไม่มี Node — UI ใหม่ เป็นไฟล์ static ล้วน |
| F3 | CSP ผ่าน `<meta>`: `default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; font-src 'self'; object-src 'none'; base-uri 'none'; form-action 'self'` **[ทดสอบกับ chart + Tailwind ใน Phase 0]** (header จริงจาก backend ตาม B8) |
| F4 | ห้าม `dangerouslySetInnerHTML` / `innerHTML` (lint error) · markdown → React element · กราฟล้างด้วย `chart.remove()` |
| F5 | ทุก response ผ่าน zod · search params ผ่าน `validateSearch` |
| F6 | UI ใหม่ ไม่แตะ token เลย (cookie HttpOnly ตาม B4) · ไม่ log ข้อมูล session · ไม่มี key เครื่องในเบราว์เซอร์ |
| F7 | ไม่ deploy source map · ไม่มี secret ใน `VITE_*` |
| F8 | คำขอที่เปลี่ยนข้อมูลส่ง header `X-ZS-CSRF` (ค่าจาก cookie CSRF ตาม B4) · ปุ่มลบ/หยุด job ต้องยืนยัน 2 ชั้น |

### 8.2 Backend — หนี้ที่เจอ + วิธีแก้ (ตรวจจริงทุกข้อ)

| # | เจออะไร | หลักฐาน | วิธีแก้ | ผลต่อ legacy / เครื่องที่บ้าน |
|--|--|--|--|--|
| **B0** 🔴 | **pull key ตัวจริงอยู่ใน git** — z-service `add_symbols_0811.py` + `ADD_SYMBOLS.md` (ตั้งแต่ commit `33b8e9f` 11 ส.ค. 2026) · stock-radar `cmd.md` · สคริปต์หลายตัว regex อ่าน key จากไฟล์นั้น | `git grep` ทั้งสอง repo | ① ออก key ใหม่ (§9) ② ใส่ key ใหม่ใน Keychain เครื่องบ้าน ③ เปลี่ยน env ใน Coolify ④ ลบ literal ออกจากทุกไฟล์ + สคริปต์อ่านจาก helper (§9.4) ⑤ key เก่าใช้ไม่ได้ทันทีที่ ③ เสร็จ ⇒ ไม่ต้องเขียนประวัติ git ใหม่ (repo private · key เก่าตายแล้ว) | ทำพร้อมกันในหน้าต่างเดียว · ทดสอบ `load_all.sh` ทันที |
| **B1** 🔴 | **pull key เปิดทุก method** — comment บอก "read-only" แต่โค้ดผ่านทุกคำขอรวม POST/PUT/DELETE | `main.py` middleware `require_auth` | แทนด้วย key มีขอบเขตสิทธิ์ (§9.2) · default deny | สิทธิ์ที่สคริปต์ใช้จริงยังได้ครบ |
| **B2** 🔴 | สคริปต์ **ปิดการตรวจ TLS** (`curl -sk` · `CERT_NONE` · `check_hostname=False`) ทั้งที่ใบรับรองถูกต้อง | grep + `curl` ตรวจจริง `ssl_verify_result=0` | เปิดตรวจทุกตัว (ลบ `-k`/`CERT_NONE`) ผ่าน helper เดียว | ไม่กระทบ (cert ถูกต้อง) |
| **B3** 🟠 | key ส่งผ่าน **query string** (`?pull_key=`) ด้วย | `fill_short_hist.py` · `add_symbols_core_1023.py` · `fix_tickers_1019.py` | OWASP REST: *"API keys should not appear in the URL"* ⇒ server ไม่รับจาก query (หลังสคริปต์ย้ายครบ) | helper ส่ง header อย่างเดียว |
| **B4** 🟠 | JWT ใน `localStorage` + cookie ที่ JS ตั้ง (ไม่ HttpOnly/Secure) | `dash/src/auth.ts` | login ตั้ง cookie `__Host-zs_session` (`HttpOnly; Secure; SameSite=Strict; Path=/`) + cookie CSRF `__Host-zs_csrf` (อ่านได้ · HMAC ผูก session ตาม OWASP signed double-submit) · คำขอเปลี่ยนข้อมูลที่มาด้วย cookie ต้องมี header `X-ZS-CSRF` ตรง + `Sec-Fetch-Site` ไม่ใช่ `cross-site` + `Origin` ตรงโดเมน · `POST /api/auth/logout` ล้าง cookie · Bearer เดิมยังรับ (legacy · ไม่โดน CSRF เพราะเบราว์เซอร์ไม่แนบเอง) | legacy ใช้ได้เหมือนเดิม · UI ใหม่ ใช้ cookie |
| **B5** 🟠 | `CORSMiddleware(allow_origins=["*"], allow_credentials=True)` — Starlette 1.3.1 บรรทัด 167–168 **สะท้อน Origin ใดก็ได้** | ซอร์สในเครื่อง | origin เดียวกันอยู่แล้ว ⇒ production ไม่เปิด CORS · dev อ่านรายชื่อ origin จาก env `ZS_CORS_ORIGINS` (ค่าเริ่มว่าง) | สคริปต์ไม่ใช้ CORS (ไม่ใช่เบราว์เซอร์) |
| **B6** 🟠 | `/docs` · `/openapi.json` เปิดสาธารณะ | curl จริงได้ 200 | เอาออกจาก public · เปิดเฉพาะเมื่อ login หรือ key scope `admin` · env `ZS_DOCS=0` ปิดทั้งหมดได้ | UI ใหม่ generate type จาก openapi ด้วย session |
| **B7** 🟠 | `auth.py` มีค่า fallback ของ `AUTH_SECRET` ในซอร์ส | อ่านไฟล์ | ไม่มี fallback: ไม่ตั้ง / สั้นกว่า 32 byte ⇒ **บูตไม่ขึ้น** · ⚠️ ก่อน deploy ต้องตรวจใน Coolify ว่าตั้งแล้ว (ถ้ายังไม่ตั้ง ตั้งก่อน 1 deploy) · เปลี่ยน secret = ทุก session หลุด ต้อง login ใหม่ | — |
| **B8** 🟡 | ไม่มี security header · โชว์ `server: uvicorn` | curl จริง | ASGI middleware ใน backend (อยู่ในโค้ด ตรวจย้อนได้ ไม่พึ่งค่าใน UI Coolify): `Strict-Transport-Security: max-age=31536000` · `X-Content-Type-Options: nosniff` · `X-Frame-Options: DENY` · `Referrer-Policy: no-referrer` · `Permissions-Policy` ปิดกล้อง/ไมค์/ตำแหน่ง · `/api/*` ใส่ `Cache-Control: no-store` · CSP: UI ใหม่ ตาม F3 · legacy + login.html เริ่มแบบ `Content-Security-Policy-Report-Only` (login.html มี inline script/style) แล้วค่อยบังคับหลังแก้ · uvicorn `--no-server-header` | legacy ไม่พังเพราะ CSP เริ่มแบบ report-only |
| **B9** 🟡 | `/api/auth/login` ไม่จำกัดจำนวนครั้ง | อ่านโค้ด | จำกัดต่อ IP + ต่อ username (เช่น 5 ครั้ง/นาที แล้วหน่วงทวีคูณ) ตอบ 429 · ⚠️ ต้องได้ IP จริง: uvicorn ค่าเริ่ม `FORWARDED_ALLOW_IPS=127.0.0.1` (ซอร์ส uvicorn) ⇒ หลัง Traefik ทุกคนเป็น IP เดียว ⇒ ตั้ง `--proxy-headers` + `FORWARDED_ALLOW_IPS` = ช่วง IP network ของ Coolify **[ยืนยันว่า port 9999 ไม่ได้ map ออก host ใน Coolify]** | — |
| **B10** 🟡 | `requirements.txt` ไม่ pin เลย · `tvdatafeed` จาก git HEAD | อ่านไฟล์ | `requirements.in` (รายชื่อ) → `uv pip compile --generate-hashes` → `requirements.lock` · tvdatafeed pin commit `e6f6aaa7de43…` (SHA เต็ม) · Dockerfile `pip install --require-hashes` · ทดสอบชุดเดิม (`test_*.py`) ผ่านก่อน deploy | ถ้าเวอร์ชัน pin ต่างจากที่รันอยู่ ให้ pin ตามที่ image ปัจจุบันใช้ก่อน แล้วค่อยขยับ |
| **B11** 🟡 | lockfile legacy มีช่องโหว่ 11 ตัว · axios 1.17.0 ใน bundle | `npm audit` | `npm audit fix` (lockfile เท่านั้น) · `npm run build` · เปิด 9 แท็บเช็ค · commit แยก | security-only |
| **B12** 🟡 | ไม่มี `HEALTHCHECK` ⇒ Coolify ถือว่า container ที่สตาร์ตได้ = พร้อม (เอกสาร Coolify) · ช่วง rolling update container เก่า+ใหม่รันพร้อมกัน · autostart job ตรวจซ้ำแค่ในหน่วยความจำ (`_autostart_worker`) | เอกสาร Coolify + โค้ด | `GET /api/healthz` (public · ตอบแค่ `ok` · ไม่มีข้อมูล) + `HEALTHCHECK` ใน Dockerfile ใช้ `python -c` (image slim ไม่มี curl) · lease ใน Mongo (`automate_lease` มี owner + หมดอายุ) ให้ job รันได้ทีละ container | กัน job ซ้อนตอน deploy |
| **B13** ⚪ | `@app.on_event("startup")` เป็น API แบบเก่าของ FastAPI | อ่านโค้ด | ย้ายไป `lifespan` ตอนแตะไฟล์นี้ใน Phase S2 | — |
| **B14** 🟡 | API key ของ Gemini (`?key=`) และ Finnhub/FMP/Alpha Vantage (`token=`/`apikey=`) อยู่ใน **query string** | อ่านโค้ด `integrations/gemini.py` · `domains/gold/routes.py` · `domains/earning_scan/providers.py` | Gemini → header `x-goog-api-key` · Finnhub → header `X-Finnhub-Token` · FMP/Alpha Vantage ตรวจเอกสารว่ารองรับ header ไหม **[ยืนยันก่อนแก้]** · log ห้ามมี URL เต็ม | ไม่กระทบ |
| **B15** 🟡 | stock radar scan ส่ง Telegram แบบ `parse_mode=HTML` แต่ใส่ผล AI โดยไม่ escape + ใช้ `**` (markdown) ⇒ ข้อความที่มี `<` `&` ถูก Telegram ปฏิเสธ (400) เงียบ ๆ · มี RSS fetcher ชุดที่ 3 ของตัวเอง | อ่านโค้ด `domains/stock_radar/service.py` | `html.escape` ผล AI + ใช้ `<b>` · ใช้ `integrations/news.py` (ถ้ายอมให้ข้อความ prompt เปลี่ยน — ต้องอัปเดต golden โดยตั้งใจ) | ข้อความ Telegram เปลี่ยนรูป |
| **B16** 🟡 | gold mode (`domains/gold_mode/client.py`) มี TvDatafeed ของตัวเอง: instance เดียวใช้ร่วมทุก thread (โค้ดหลักเขียนไว้ว่าทำให้ socket ชนกัน) · login ด้วยวิธีของ tvdatafeed (ที่โค้ดหลักบันทึกว่าโดนปฏิเสธ) · ไม่ผ่าน throttle กลาง ⇒ เสี่ยงโดน rate limit ตอนเรียกพร้อม auto job | อ่านโค้ดตอนย้าย | ใช้ `integrations/tradingview` (`make_tv` + `THROTTLE` + retry) แทน · ต้องอัปเดต golden ถ้ารูปข้อมูลเปลี่ยน | ไม่กระทบผู้ใช้ |
| **✅ แก้แล้ว** | `POST /api/data` ตอบ 500 ทุกครั้งที่บันทึก: พารามิเตอร์ `store` ของ `process_symbol` บังชื่อ module `store` (`True.history_upsert`) — job ภายในใช้ `store=False` จึงไม่โดน | test ที่ fail ด้วย AttributeError ก่อนแก้ | commit `29abce9` | ปุ่มดึงทีละตัวใน Dashboard ใช้ได้แล้ว (หลัง deploy) |

### 8.2b สถานะการแก้ (ส 25 ต.ค. 2026 · branch `feat/web-ui` · ยังไม่ deploy)

| # | สถานะ | commit |
|--|--|--|
| B0 key รั่วใน git | 🟡 key ใหม่ออกแล้ว (Keychain) · หมุนจริงตอน deploy ตาม runbook §3 ขั้น 8–10 | `365a796` |
| B1 pull key เปิดทุก method | ✅ key `zsk_` มี scope · PULL_KEY เดิมใช้ได้ช่วงย้าย + audit | `4bf2d77` |
| B2 สคริปต์ปิด TLS | 🟡 helper `tools/zsvc_client.py` / `zsvc_curl.sh` ตรวจ TLS เสมอ · ย้ายสคริปต์หลัง deploy | `4bf2d77` |
| B3 key ใน query | 🟡 key ใหม่รับเฉพาะ header · PULL_KEY ใน query ยังรับช่วงย้าย (audit บอกใครยังใช้) | `4bf2d77` |
| B4 token ใน localStorage | ✅ cookie `__Host-zs_session` (HttpOnly) + CSRF แบบ signed double-submit + Fetch Metadata · legacy ยังใช้ token เดิมได้ | `e464bd9` |
| B5 CORS `*` + credentials | ✅ ไม่เปิด CORS ใน production · dev อ่านจาก `ZS_CORS_ORIGINS` · `*` ถูกปฏิเสธ | `f12f7b0` |
| B6 `/docs` สาธารณะ | ✅ ต้อง login · `ZS_DOCS=0` ปิดได้ | `f12f7b0` |
| B7 AUTH_SECRET fallback | ✅ ไม่มี fallback · ไม่ตั้ง = ไม่บูต | `365a796` |
| B8 security header | ✅ ครบทุก response · CSP บังคับที่ `/app/` · legacy report-only | `f12f7b0` |
| B9 login ไม่จำกัด | ✅ 5 ครั้ง/นาที/IP+username → 429 · ต้องตั้ง `FORWARDED_ALLOW_IPS` (runbook) | `e464bd9` |
| B10 dependency ไม่ pin | ✅ `requirements.lock` (hash ทุก wheel · Python 3.12) + git dep pin commit · ทดสอบบน Python 3.12.15 ผ่าน 129/129 | `5a530de` |
| B11 lockfile legacy | ✅ 11 → 0 ช่องโหว่ (lockfile เท่านั้น · cooldown 7 วัน · build ผ่าน) | `c58ec28` |
| B12 HEALTHCHECK + job ซ้อน | ✅ heartbeat ข้าม container + HEALTHCHECK ใน Dockerfile | `cd573c9` |
| B13 on_event | ✅ lifespan | `f12f7b0` |
| B14 key ใน URL (Gemini/Finnhub/FMP) | ✅ header · FMP ส่ง header ก่อน ถอยไป query 1 ครั้งถ้าถูกปฏิเสธ (§8.2c F12) · Alpha Vantage รับ query อย่างเดียวตาม docs ⇒ ปิดค่าใน log แทน (F10) | `16f1d07` · `422193e` |
| B16 gold mode ใช้ TradingView client กลาง | ✅ `make_tv()` ใหม่ทุก request (login/token กลาง · ไม่แชร์ socket ข้าม thread) + slot จาก `THROTTLE` · ไม่ trip cooldown กลางเมื่อได้ค่าว่าง (symbol คู่บางตัวว่างจริง จะไปหยุด job หุ้น 120 วิ) · ทดสอบสด OANDA:XAUUSD ผ่าน · export swing ช้าลง ~5 วิเฉพาะตอน cache miss | (commit นี้) |
| B15 Telegram HTML ไม่ escape | ✅ escape + `<b>` · ตัดก่อน escape · ≤ 4,000 ตัวอักษร | `888103b` |

### 8.2c รอบหาช่องโหว่ 25 ต.ค. 2026 (ตรวจโค้ดทุก route + dependency + image · แก้แล้วทุกข้อที่แก้ได้ก่อน deploy)

| # | ช่องโหว่ / ส่วนที่ขาด | หลักฐานที่เจอ | วิธีแก้ | สถานะ |
|--|--|--|--|--|
| D1 | dependency มี advisory | OSV ตรวจ 50 pin: pymongo 4.17.0 (HIGH ×2: BSON heap overflow CVE-2026-96749 · host injection CVE-2026-96748) · certifi (CRITICAL: CA emSign ที่ key รั่ว) · setuptools (MODERATE+LOW) | pymongo 4.19.0 · certifi 2026.10.19 · setuptools 84.1.0 · lock ใช้ `--exclude-newer` 7 วัน (เหมือน npm) ยกเว้นตัวแก้ advisory ตัวแรกสุด · `tools/osv_audit.py` | ✅ `461b4dc` (0 advisory · npm audit web/dash 0) |
| F1 | cookie `z_token` (legacy · JS ตั้ง · SameSite=Lax) ผ่าน gate ได้โดยไม่เช็ค CSRF | `_session_token` ข้าม `csrf_failure` ถ้ามาจาก z_token · Lax กัน cross-site แต่ไม่กัน subdomain ข้างเคียง (same-site) | คำสั่งเปลี่ยนข้อมูลที่ยืนยันด้วย z_token อย่างเดียว = 403 · อ่านได้เหมือนเดิม · legacy ส่ง Bearer ทุกครั้งอยู่แล้ว | ✅ `981b053` |
| F2 | ตาราง rate limit โตไม่สิ้นสุด | key = IP+username ที่ผู้โจมตีเลือกเองได้ | ตัด key ที่เงียบเกินหน้าต่าง + เพดาน 10,000 (LRU) | ✅ `981b053` |
| F3 | login: PBKDF2 120k รอบ (OWASP แนะนำ 600k) · username ที่ไม่มีตอบเร็วกว่า (เดาชื่อได้จากเวลา) · ฐานข้อมูลถูกล้าง = ใครก็สมัครเป็นเจ้าของได้ · ไม่จำกัดต่อ IP · ไม่จำกัดความยาว | อ่านโค้ด `tokens.py` / `auth/routes.py` | 600k + อัปเกรด hash ตอน login · hash หลอกเมื่อไม่มี user · `ZS_ALLOW_REGISTER` (ปิดเป็นค่าเริ่ม) + insert แบบ atomic · จำกัดต่อ IP 20/นาที · username ≤64 password ≤1024 · รหัสใหม่ ≥12 (NIST 800-63B rev.4) | ✅ `981b053` |
| F4 | `/api/auth/status` (สาธารณะ) ส่งข้อความ error ของ driver ออกไป (ชื่อ host ฐานข้อมูล) | `f"DB error: {e}"` | log ฝั่ง server · ตอบ `DB error` | ✅ `981b053` |
| F5 | logout ไม่จบ session ที่ server · UI ใหม่ logout แล้ว cookie HttpOnly ยังใช้ได้ | JWT ไม่มีสถานะ · `session.ts logout()` ไม่เรียก server | `revocation.py` (jti รายตัว + เวลาตัด · cache 15 วิ) · logout ต้องพิสูจน์ว่าเป็นเจ้าของ (Bearer หรือ cookie+CSRF) · web เรียก `POST /api/auth/logout` · 401 ล้างแค่ในเครื่อง | ✅ `981b053` |
| F6 | **ส่วนที่ขาด:** เปลี่ยนรหัสผ่านไม่ได้เลย (ต้องแก้ใน DB) | — | `POST /api/auth/password` + ฟอร์มหน้า Settings 3 ภาษา · รหัสเดิมผิด = 403 (ไม่ใช่ 401 ⇒ พิมพ์ผิดไม่หลุดระบบ — test จับได้ตอนทำ) · จบ session เก่าทั้งหมด + ได้ token ใหม่ | ✅ `981b053` |
| F7 | input ไม่มีขอบเขต: body ไม่จำกัดขนาด · `rows` ไม่จำกัด · list ไม่จำกัด · `symbols: list[dict]` ให้ `{"$ne": null}` ไหลไปถึง filter ของ Mongo ได้ · `limit=0` = ดึงทั้ง collection | อ่าน schema ทุกตัว | `BodySizeLimit` (2 MiB · นับทั้ง chunked) · `SymbolRef` string ล้วน · rows 1..5000 · list/string มีเพดาน · clamp limit | ✅ `981b053` |
| F8 | ชื่อ model ของ Gemini ทำ path traversal ได้ (request พก key ของ server) | `quote(model)` ไม่ encode `/` | pattern 1 segment + `quote(safe='')` · ทั้งที่ schema และใน client | ✅ `981b053` |
| F9 | container รันเป็น root · `git` ค้างใน image · cache token TradingView อ่านได้ทุก user · `automate.log` ไม่หมุนไฟล์ และจะทำให้บูตไม่ขึ้นถ้าเขียนไม่ได้ | Dockerfile ไม่มี `USER` · `open(..., "w")` | `USER app` (uid 10001) + `/app/state` · purge git ใน layer เดียว · compileall · cache 0600 + เขียนแบบ atomic · log หมุน 5 MB×3 + เปิดไม่ได้ก็ไม่ล่ม | ✅ `422193e` · ⏳ ยืนยันตอน Coolify build (Docker ในเครื่องไม่ได้เปิด) |
| F10 | `pull_key` / token ใน query ไปโผล่ใน access log ของ uvicorn | uvicorn log path+query ทุก request | filter บน `uvicorn.access` ปิดค่า `pull_key token access_token api_key key secret password` | ✅ `422193e` |
| F11 | หน้า legacy มีแค่ CSP report-only (ไม่บล็อก script แปลกปลอม) ทั้งที่ token อยู่ใน localStorage | `headers.py` | บังคับ `script-src 'self'` + hash ของ script inline หน้า login (คำนวณจากไฟล์ตอนบูต) + `object-src/base-uri/frame-ancestors/form-action` · CSP เต็มยัง report-only (style ยังไม่ได้พิสูจน์) · ตรวจแล้ว bundle legacy ไม่มี inline script/`eval` | ✅ `422193e` |
| F12 | key FMP อยู่ใน URL (B14 ที่ค้าง) | FMP docs: รับ header `apikey` ได้ | ส่ง header ก่อน · ถ้า 401/403 ลอง query 1 ครั้ง + log (ยังไม่มี key จริงให้ยืนยันกับ `/api/v3`) · Alpha Vantage รับ query อย่างเดียว (docs) ⇒ คง query + F10 | ✅ `422193e` |
| F13 | ข้อความ Telegram ใส่ label เวลา/ชื่อ symbol ดิบ (Telegram ปฏิเสธทั้งข้อความถ้ามี `<` `&`) | `jobs/summary.py` · `gold/telegram.py` | escape ทุกค่าที่มาจาก settings/request | ✅ `422193e` |
| F14 | id ของ Drive ไม่ตรวจรูปแบบก่อนต่อเข้า query `q` | `drive_list` | `[A-Za-z0-9_-]{10,200}` ก่อนเรียก API ทุกครั้ง | ✅ `422193e` |
| F15 | PULL_KEY เดิม (รั่วใน git) ผ่านได้**ทุก route** รวมลบประวัติทั้งหมด · admin · settings · Drive · scan ที่เสียเงิน Gemini | `_legacy()` ไม่เช็ค scope | จำกัดเท่าที่สคริปต์บ้านเรียกจริง (ไล่ grep สคริปต์ stock-radar + z-service ราก: export/status/symbols/history อ่าน · auto/automate · gold automate · watchlist) = scope `read jobs gold:jobs watchlist:write` · นอกนั้น 403 + บันทึกใน key_audit | ✅ `9a27f0d` |
| R1 | e2e Playwright ตามแผน §12 | — | **รอ user ตัดสิน:** ต้องเปิด browser headless ซึ่งขัดกฎ global (ควบคุม browser ได้เฉพาะ 127.0.0.1:9222) | ⏳ |
| R2 | หลัง deploy: ลบ Bearer legacy ออกจาก UI ใหม่ · หมุน PULL_KEY (B0/B3) · ย้ายสคริปต์บ้าน (B2) | — | ตาม runbook §3 ขั้น 7–10 | ⏳ หลัง deploy |

ทดสอบกับ uvicorn จริงในเครื่อง (ไม่ต่อ DB): header CSP ของ `/login` = hash ที่คำนวณจากไฟล์ build · สมัคร = 403 `auth.registration_closed` · body 3 MB = 413 · z_token อ่านได้/เขียน 403 · Bearer เขียนได้ · model `../` = 422 · access log แสดง `pull_key=***`

ตรวจแล้วไม่พบปัญหา: ลายเซ็น JWT (บังคับ HS256 เสมอ ไม่อ่าน `alg` · compare แบบเวลาคงที่) · scope ของ key เครื่อง (regex ยึดหัวท้าย · path แปลก ๆ ไม่ตรง route) · ไม่มี `$regex/$where` · markdown ของ legacy escape ก่อนแทนที่ · web ใช้ markdown-to-jsx ปิด raw HTML · หน้า login ไม่มี redirect parameter · `/api/healthz` ตอบค่าคงที่ · GET ไม่มีตัวไหนเปลี่ยนข้อมูล · CORS ปิดใน production · Content-Disposition ใช้ค่าที่ validate แล้ว

### 8.3 ลำดับทำ (ความเสี่ยงสูงก่อน · ทุกขั้นเครื่องที่บ้านใช้ได้)

| ขั้น | ทำ | ทำไมก่อน |
|--|--|--|
| S0 (ไม่แตะโค้ด backend) | ตรวจ `AUTH_SECRET` ใน Coolify · ตรวจ port mapping | เป็นเงื่อนไขของ B7/B9 |
| S1 | B1 + B0 + B2 + B3 (§9 ทั้งชุด) | key รั่วอยู่ใน git + เปิดทุก method |
| S2 | B7 + B6 + B5 + B8 + B12 + B13 | ไม่กระทบผู้ใช้ |
| S3 | B4 + B9 | ต้องมีก่อน UI ใหม่ขึ้น production |
| S4 | B10 + B11 | เปลี่ยนเวอร์ชัน dependency → ต้องทดสอบชุดใหญ่ |

---

## 9. เครื่องที่บ้านสั่ง backend ตรง (machine access) — กรณีพิเศษแบบปลอดภัย

### 9.1 หลักที่ใช้ (อ้าง OWASP REST Security Cheat Sheet)
- key ต้องมีในทุกคำขอ · ส่งใน header เท่านั้น (ห้ามอยู่ใน URL)
- ตรวจสิทธิ์ราย method + ราย resource · method ที่ไม่อนุญาตตอบ 405/403
- เกินอัตรา = 429 · ทำผิดเงื่อนไข = เพิกถอน key
- ใช้ HTTPS เท่านั้น และ client ต้องตรวจใบรับรอง
- "อย่าพึ่ง API key อย่างเดียวกับทรัพยากรมูลค่าสูง" ⇒ สิทธิ์ `admin` ไม่ออกให้เครื่อง (ทำผ่านหน้าเว็บที่ login)

### 9.2 รูปแบบ key + ขอบเขตสิทธิ์
- รูปแบบ: `zsk_<id>_<secret>` · secret สุ่ม 32 byte (`secrets.token_urlsafe(32)`)
- server **ไม่เก็บตัว key** — เก็บแค่ SHA-256 ของ secret ใน env `ZS_API_KEYS` (Coolify secret · JSON: `id` · `name` · `scopes` · `sha256` · `expires`) · ตรวจด้วย `hmac.compare_digest`
- ส่งด้วย `Authorization: Bearer zsk_…` (แยกจาก JWT ด้วยคำนำหน้า `zsk_`)
- ตารางสิทธิ์ (โค้ดที่เดียว · route ที่ไม่มีในตาราง = ปฏิเสธเมื่อใช้ key):

| scope | อนุญาต | ใครใช้ |
|--|--|--|
| `read` | GET `/api/*` (export_zip · automate/status · history · watchlist · symbols · version · radar_round ฯลฯ) | `load_all.sh` · `fetch_csv.sh` · `fill_short_hist.py` · `wait_zsvc_*.py` |
| `jobs` | POST `/api/automate` `/api/auto/start` `/api/auto/stop` `/api/auto/start_all` `/api/radar_round/run` | `fetch_new_symbols.py` · `start_auto_all.py` |
| `watchlist:write` | POST/PUT/DELETE `/api/watchlist*` | `add_symbols_*.py` · `fix_tickers_1019.py` |
| `admin` | settings · tv_token · ลบ history/round · portfolio write | **ไม่ออกให้เครื่อง** |

- key เครื่องบ้าน 1 ตัว: `read jobs watchlist:write` · อายุ 180 วัน · ใครต้องการแค่อ่าน (เช่น agent) ออก key `read` แยก

### 9.3 การป้องกันรอบ key
- จำกัดอัตราต่อ key (ค่าใน config ไม่ใช่ literal ในโค้ด) · export_zip ยาว 25 นาทีได้ (ไม่นับเวลา แค่นับครั้ง)
- audit log ทุกคำขอที่ใช้ key: เวลา · key id · method · path · status · IP — **ไม่ log ตัว key** · ดูได้ที่ `/api/admin/key_audit` (scope admin / login)
- หมุน key: ใส่ hash ใหม่คู่ hash เก่า → deploy → เปลี่ยน Keychain เครื่องบ้าน → ลบ hash เก่า → deploy (ไม่มีช่วงใช้ไม่ได้)
- เพิกถอนฉุกเฉิน: ลบ entry ใน env แล้ว redeploy
- **ไม่เลือกตอนนี้ (พร้อมเหตุผล):** HMAC signing ต่อคำขอ (TLS ที่ client ตรวจจริงกันดักกลางทางแล้ว · เพิ่มความซับซ้อนทุกสคริปต์) · mTLS ผ่าน Traefik (OWASP ให้ "พิจารณา" สำหรับบริการสิทธิ์สูง — เราไม่ออก admin ให้เครื่อง) · IP allowlist (IP บ้านเปลี่ยนได้) · VPN/Tailscale — ถ้าวันหน้าต้องให้เครื่องใช้สิทธิ์ admin ค่อยใช้ mTLS หรือ VPN ตัวใดตัวหนึ่ง

### 9.4 ฝั่งเครื่องบ้าน (stock-radar + สคริปต์ใน z-service)
- เก็บ key ใน **macOS Keychain**: `security add-generic-password -s z-service -a home -w` (พิมพ์ key ตอนถาม ไม่ติด history) · อ่านด้วย `security find-generic-password -s z-service -a home -w`
- env `ZS_API_KEY` ใช้แทนได้ (เช่น รันใน agent)
- helper กลาง 2 ตัว (ไม่มี key ในไฟล์ · TLS ตรวจเสมอ · header เท่านั้น · timeout/retry ที่เดียว · base URL จาก env `ZS_BASE_URL` ค่าเริ่ม = โดเมนจริง):
  - Python: `zsvc_client.py` (`get` / `post` / `download`)
  - shell: `zsvc_curl.sh` (ห่อ `curl --fail-with-body -H "Authorization: Bearer …"`)
- ย้ายทุกสคริปต์ใน §6 มาใช้ helper · ลบ `PULL_KEY = "…"` · ลบ regex ที่อ่าน key จาก `add_symbols_0811.py`

### 9.5 ช่วงย้ายแบบไม่มีวันใช้ไม่ได้

| วัน | server | เครื่องบ้าน |
|--|--|--|
| T0 | deploy: รับ `zsk_` + **รับ PULL_KEY เดิมต่อ (header เท่านั้น · scope เท่าเครื่องบ้าน · log คำว่า deprecated)** | — |
| T0 | | ใส่ key ใหม่ใน Keychain · ย้ายสคริปต์มาใช้ helper · รัน `load_all.sh` + `fetch_new_symbols.py --dry` ทดสอบ |
| T0+1 | ดู audit log: ไม่มีคำขอ PULL_KEY เดิมแล้ว | |
| T0+1 | ลบ `PULL_KEY` ออกจาก env ⇒ key เก่า (ที่รั่วใน git) ใช้ไม่ได้ · ปิดการรับจาก query | ลบ literal ออกจาก `cmd.md` · `ADD_SYMBOLS.md` · `add_symbols_0811.py` · memory ที่อ้างวิธีเก่า |

---

## 10. ความเร็ว — งบที่ build บังคับ

| ตัววัด | legacy (วัดแล้ว) | งบ UI ใหม่ |
|--|--|--|
| JS แรกเข้า (gzip) | 196 KB ก้อนเดียว | **≤ 120 KB** (รวมภาษาที่เลือก 1 ภาษา) · route chunk ≤ 60 KB · chart โหลดเฉพาะ route ที่มีกราฟ |
| CSS (gzip) | 11.7 KB | ≤ 15 KB (สองธีมใช้ CSS ชุดเดียว เปลี่ยนแค่ตัวแปร) |
| ตาราง | render ทุกแถว | ทุกตารางแบ่งหน้า (10/25/50/100 แถว) ⇒ แถวใน DOM ≤ 100 · งานเรียง/กรอง > 5 ms ย้ายไป Web Worker **[วัดใน Phase 3]** |
| network | `setInterval` 13 จุด | Query: `staleTime` ตามชนิดข้อมูล · dedupe · poll เฉพาะหน้าที่เปิดและหน้าต่าง focus · หยุดเมื่อ job จบ |
| เปลี่ยนหน้า | — | `preload: 'intent'` (โหลด chunk + data ตอน hover) |

วัด: สคริปต์งบ bundle รันใน build (เกิน = fail) · Playwright วัดเวลาเปิด route และ scroll ตาราง 1,000 แถว (หน้าอยู่หลัง login ⇒ ใช้ Playwright + `PerformanceObserver` แทน Lighthouse)

---

## 11. CI = Coolify + pre-push hook (ไม่ใช้ GitHub Actions)

- **ใน Docker build (Coolify รันทุก deploy):** `npm run verify` ของ UI ใหม่ (typecheck · lint · unit · i18n ครบ · no-hardcode · build · route shell · งบ bundle · ตรวจ lockfile) + `pytest` ชุดความปลอดภัย backend (§13) ใน stage แยก
  - build พัง ⇒ Coolify รันเวอร์ชันเดิมต่อ (เอกสาร Coolify: *a failed source build leaves the current application version running*)
- **ไม่ใส่ใน Docker:** `npm audit` / `pip-audit` (ต้องใช้เน็ต · ผลเปลี่ยนตามวัน · ไม่ควรขวาง deploy patch ความปลอดภัย) ⇒ อยู่ใน pre-push hook
- **pre-push hook** (`scripts/pre-push.sh` · ติดตั้งด้วย `git config core.hooksPath .githooks`): `verify` ทั้ง legacy (`npm run build` ใน `dash/`) และ UI ใหม่ · `npm audit --audit-level=moderate` ทั้งสองโฟลเดอร์ · `pytest` · grep secret (`zsk_` · `PULL_KEY = "`) ใน diff · รันด้วย `nice -n 15` (กฎ CPU ≤ 65%)
- **health check:** `HEALTHCHECK` ใน Dockerfile (B12) ⇒ Coolify ทำ rolling update ได้จริง · ถ้า container ใหม่ไม่ healthy จะคงตัวเดิมไว้
- typecheck ระดับ project ให้ครอบ references (บทเรียน 20 ต.ค.: `tsc --noEmit` ที่ root ไม่จับ)

---

## 12. สถาปัตยกรรมที่ขยายได้

### 12.1 โครง `web/`
```
web/
├─ .npmrc · package.json · package-lock.json
├─ vite.config.ts           # base จาก env `APP_BASE` (ค่าเริ่ม '/app/') · router-plugin(autoCodeSplitting) · paraglide · proxy จาก env
├─ index.html               # CSP meta · theme-init.js
├─ messages/{th,en,it}.json # ข้อความ UI ทั้งหมด
├─ public/theme-init.js
├─ scripts/                 # emit-route-shells · check-budget · check-i18n · check-hardcode · check-lockfile · gen-api-types
└─ src/
   ├─ main.tsx
   ├─ app/                  # router · queryClient · providers · error boundary
   ├─ routes/               # __root · index · gold · radar · radar-summary · earning-scan · watchlist · portfolio · history · export · settings
   ├─ features/<feature>/   # api.ts · schemas.ts · model.ts (logic ล้วน + test) · components/ · index.ts
   └─ shared/
      ├─ api/               # client (fetch + CSRF header + error + zod) · openapi.gen.ts
      ├─ auth/session.ts    # สถานะ login · logout (ไม่แตะ token)
      ├─ config/            # env.ts (zod) · app.ts (poll · page size · threshold)
      ├─ i18n/              # ตัวเลือกภาษา · formatter ตาม locale
      ├─ theme/             # token · ตัวสลับธีม · สีกราฟ
      ├─ ui/                # component จาก shadcn
      └─ lib/               # markdown → element · เวลา · ตัวเลข
```

### 12.2 กฎกันหนี้ (lint/build บังคับ)
- `features/A` ห้าม import `features/B` · ใช้ร่วม = ย้ายไป `shared/`
- `routes/` บาง: อ่าน search params → เรียก feature
- ไฟล์ > 400 บรรทัด = error · component > 150 บรรทัด = warning
- ห้าม `any` · ห้าม literal `/api/` นอก `shared/api` · ห้าม `dangerouslySetInnerHTML` · ห้ามค่าสีตรง · ห้ามข้อความ UI ใน JSX
- logic อยู่ใน `model.ts` เป็นฟังก์ชันล้วน + unit test

### 12.3 สัญญา API
- request type: generate จาก `openapi.json` (Pydantic 17 model) → `openapi-fetch` (path/body ผิด = compile error)
- response: backend ยังไม่มี `response_model` ⇒ zod ราย endpoint ใน `features/*/schemas.ts`
- fixture จาก response จริง (ตัดข้อมูลส่วนตัวก่อน commit) ใช้ทั้ง unit test และ MSW
- ต่อไป: backend เพิ่ม `response_model` ทีละ endpoint → UI ใหม่ เลิกเขียน zod ตัวนั้นแล้วใช้ type ที่ generate

### 12.4 เลิก hard code — ย้ายไปไหน

| legacy hard code | UI ใหม่ ได้ค่าจาก |
|--|--|
| `SYMBOLS` ~830 แถว · `EXCHANGES` · `US_STOCK_SYMBOLS` | `GET /api/symbols` (build ∪ Mongo) · exchange คำนวณจากข้อมูล · กฎ filter ใน `model.ts` |
| `TAB_IDS` + เมนู | route tree + `staticData` (key ข้อความ · icon · ลำดับ) |
| URL `/api/...` 45 จุด | `shared/api` ที่เดียว |
| `VITE_API_BASE` · เวลา poll · page size | `shared/config` (ตรวจด้วย zod ตอนบูต) |
| สี | token ธีม |
| `TIMEZONE_OPTIONS` | ค่าจาก `/api/settings/timezone` · รายการจาก `Intl` **[ยืนยันว่า format ตรงกับที่ backend รับ (offset นาที + label)]** |
| ป้าย provider · ข้อความไทยกระจาย | `messages/{th,en,it}.json` |
| backend: scope ↔ route · อัตราจำกัด · origin dev | ตาราง/ค่าใน `backend/security_config.py` + env (ไม่กระจายในโค้ด) |

### 12.5 เพิ่มแท็บใหม่
1. `src/features/<new>/`
2. `src/routes/<new>.tsx` + `staticData`
3. key ข้อความใน 3 ไฟล์ภาษา
- เมนู · code split · route shell · type ของลิงก์ ได้เองทั้งหมด

---

## 13. ทดสอบ

| ชั้น | ทดสอบอะไร |
|--|--|
| unit (vitest) | `model.ts` · schema · formatter 3 ภาษา · ตัวสลับธีม |
| e2e (Playwright + MSW) | 11 route เปิดได้ · deep link F5 · ปุ่มหลักทำงาน · ไม่มี error ใน console · CSP ไม่มี violation · ภาพทุกหน้า × 3 ภาษา × 2 ธีม · ข้อความไม่ล้นกรอบ (อิตาลียาวกว่าไทย) |
| backend (pytest) | key: ถูก/ผิด/หมดอายุ/scope ไม่พอ/ส่งใน query = ปฏิเสธ · route ที่ไม่มีในตาราง = ปฏิเสธเมื่อใช้ key · CSRF: ไม่มี header / `cross-site` / Origin ผิด = 403 · Bearer legacy ยังผ่าน · rate limit 429 · ไม่มี `AUTH_SECRET` = บูตไม่ขึ้น · header ความปลอดภัยครบ · `/docs` ต้อง login · healthz ไม่มีข้อมูล · lease job ทีละ container |
| ทดสอบกับของจริง | หลังแต่ละขั้น S: `load_all.sh` · `fetch_new_symbols.py` (ช่วง cooldown ของ auto job) · legacy 9 แท็บ · UI ใหม่ ทุก route |

---

## 14. Phase

| Phase | ทำอะไร | ผ่านเมื่อ | rollback |
|--|--|--|--|
| **S0** | ตรวจ `AUTH_SECRET` + port mapping ใน Coolify (user ดู/ผมบอกจุด) | รู้ค่าจริง | — |
| **0 Spike** | `web/` เปล่า + `.npmrc` · ยืนยันทุกจุด **[ยืนยันใน Phase 0]** (Paraglide · Table v9 · trailing slash · CSP กับ chart · lib markdown · timezone format) · route shell บน StaticFiles ในเครื่อง | ทุกจุดมีผลจริง | ลบโฟลเดอร์ |
| **S1** | machine access §9 (backend + helper + ย้ายสคริปต์ + หมุน key) | §9.5 ครบ · key เก่าตาย · สคริปต์บ้านผ่านหมด | คืน `PULL_KEY` ใน env |
| **1 โครงกลาง UI ใหม่** | shell · router · query · config · api client · ธีม · i18n 3 ภาษา · หน้าภาพรวม | `verify` ผ่าน | — |
| **S2** | B5 B6 B7 B8 B12 B13 | pytest ผ่าน · legacy ปกติ · CSP report-only ไม่มีเสียงดังผิดปกติ | revert commit |
| **S3** | B4 (cookie + CSRF) + B9 | legacy login/ใช้งานปกติ · UI ใหม่ ผ่าน CSRF test | revert |
| **2 UI ใหม่ขึ้น production (อ่านอย่างเดียว)** | stage ใน Dockerfile + HEALTHCHECK | `/app/` เปิดได้ · legacy ปกติ · `load_all.sh` ปกติ | ลบบรรทัด COPY |
| **3 แท็บอ่านข้อมูล** | Watchlist · Portfolio · History · Radar Summary · Stock Radar history · Earning Scan history | ข้อมูลตรง legacy ทุกแถว (เทียบอัตโนมัติจาก API เดียวกัน) | ซ่อน route |
| **4 แท็บสั่งงาน** | Dashboard · Export · Gold · Settings · ปุ่มลบ | ตาราง parity ครบ · ทดสอบ job จริงช่วง cooldown | ใช้ legacy |
| **S4** | B10 + B11 | pytest + ทดสอบของจริง · legacy 9 แท็บ | revert lock |
| **5 ใช้คู่กัน** | user ใช้ UI ใหม่ เป็นหลัก · ตรวจคำแปลอิตาลี/อังกฤษ | user ยืนยัน | ใช้ legacy |
| **6 Cutover** | `/` = UI ใหม่ · legacy rebuild base `/legacy/` แล้วเสิร์ฟที่นั่น | ทั้งสองทำงาน | สลับกลับ |
| **L2** | ย้ายรายชื่อหุ้นจาก App.tsx ไปแหล่งข้อมูลเดียว (Mongo + ไฟล์ข้อมูลที่ build_meta อ่าน) · แก้ทุกแถว §6 ใน commit เดียว | ทุกสคริปต์ผลเดิม | revert |

**ตาราง parity (endpoint ที่ legacy เรียกจริง):**

| แท็บ | endpoint |
|--|--|
| Dashboard | `/api/data` `/api/automate` `/api/automate/status` `/api/auto/start` `/api/auto/stop` `/api/settings/auto_skip_minutes` `/api/settings/tv_mode` `/api/tv/test` `/api/watchlist` |
| Export | `/api/export` `/api/export/check` `/api/export_formula` `/api/export_news` `/api/export_zip` `/api/automate` `/api/automate/status` `/api/watchlist` |
| History | `/api/history` `/api/history/{id}` `/api/settings/destinations` `/api/settings/timezone` |
| Gold | `/api/gold/config` `/api/gold/price` `/api/gold/models` `/api/gold/automate` `/api/gold/automate/stop` `/api/gold/status` `/api/gold/export` |
| Stock Radar | `/api/stock_radar/scan` `/api/stock_radar/history` `/api/settings/timezone` |
| Radar Summary | `/api/radar_round/run` `/status` `/tf_status` `/list` `/{stamp}` (+ DELETE) |
| Earning Scan | `/api/earning_scan/scan` `/api/earning_scan/history` |
| Portfolio | `/api/portfolio` (GET/POST/PUT/DELETE) |
| Watchlist | `/api/watchlist` (GET/POST/PUT/DELETE) |
| ส่วนกลาง | `/api/version` `/api/symbols` `/api/settings/tv_token` `/api/history/cleanup` |

---

## 15. ความเสี่ยง

| ความเสี่ยง | ป้องกัน |
|--|--|
| UI ใหม่ build พังทำ legacy deploy ไม่ได้ | pre-push hook รัน verify ทั้งคู่ · Coolify คงเวอร์ชันเดิม |
| เปลี่ยน auth แล้วสคริปต์บ้านสั่งงานไม่ได้ | §9.5 รับทั้งเก่าและใหม่ช่วงย้าย · ทดสอบ `load_all.sh` ทุกขั้น |
| `AUTH_SECRET` ไม่ได้ตั้ง แล้ว B7 ทำบูตไม่ขึ้น | S0 ตรวจก่อน · HEALTHCHECK ⇒ Coolify ไม่สลับไป container ที่พัง |
| rate limit เห็น IP เดียวทั้งโลก | B9 ตั้ง proxy headers ก่อนเปิดใช้ |
| ปุ่ม UI ใหม่ ฆ่า auto job ที่รันอยู่ | ทดสอบช่วง cooldown · e2e ใช้ MSW · lease B12 |
| response จริงไม่ตรง schema | fixture จริง · `.passthrough()` · error บอก endpoint/field |
| dependency ใหม่ไม่นิ่ง | cooldown · Phase 0 ยืนยัน · มีตัวสำรอง |
| คำแปลอิตาลีผิดความหมาย | ศัพท์ตลาดไม่แปล · user ตรวจ Phase 5 |
| scope บวม | Phase 3–4 = parity เท่านั้น · ฟีเจอร์ใหม่หลัง Phase 5 |
| ย้ายโค้ด backend แล้วพฤติกรรมเปลี่ยนเงียบ ๆ | §17.4 characterization test ก่อนย้ายทุกก้อน · ย้ายทีละ domain ต่อ commit |

---

## 17. จัดระเบียบ backend + frontend (user สั่ง 24 ต.ค.: module folder · ห้ามยัดไฟล์ · ห้ามบรรทัดยาว · โค้ด/คอมเมนต์ภาษาอังกฤษ)

### 17.1 กติกาโค้ด (บังคับด้วยเครื่องมือ ไม่ใช่แค่ข้อตกลง)

| กติกา | backend (Python) | frontend (`web/`) |
|--|--|--|
| ภาษาในโค้ด | ชื่อ · คอมเมนต์ · docstring · ข้อความ log = **อังกฤษ** | ชื่อ · คอมเมนต์ = อังกฤษ · ข้อความ UI อยู่ใน `messages/{th,en,it}.json` เท่านั้น |
| ความยาวบรรทัด | ≤ 100 (ruff `E501` + `ruff format`) | ≤ 100 (formatter/lint ใน `npm run verify`) |
| ขนาดไฟล์ | เป้า ≤ 300 บรรทัด | ESLint `max-lines` 300 |
| ขนาดฟังก์ชัน | เป้า ≤ 60 บรรทัด | `max-lines-per-function` 120 (component) |
| lint | ruff 0.17.2 ชุด `E W F I B UP S SIM RUF` (`ruff.toml` ที่ราก repo) | ESLint 10 + typescript-eslint + react-hooks |
| test | pytest 9.1.1 ใน `backend/tests/<module>/` | vitest + Playwright |
| ขอบเขตตอนนี้ | ruff ครอบเฉพาะ `backend/zservice/` `backend/tests/` `tools/` · ไฟล์ legacy เข้ารายการ `include` เมื่อย้ายเข้า `zservice/` แล้วเท่านั้น (ไม่ format ไฟล์ legacy ทั้งก้อนครั้งเดียว — diff จะใหญ่จนตรวจไม่ได้) | ทั้งโฟลเดอร์ `web/` |

### 17.2 วิเคราะห์ `backend/main.py` (วัดจริง 24 ต.ค.)
- 4,030 บรรทัด · บรรทัดยาวเกิน 100 = **240** · `global` 7 จุด (token TradingView · throttle · cooldown · tf bar key) · state ระดับโมดูลอีก 2 ก้อนใหญ่ (`job` · `gold_job`)
- **17 domain ปนอยู่ในไฟล์เดียว** (เลขบรรทัดก่อนย้าย):

| domain | บรรทัด | หมายเหตุ |
|--|--|--|
| app + middleware + static | 1–120 · 3875–3885 · 4008– | CORS · auth gate · no-cache html · mount `/` |
| auth (register/login) | 120–170 | ใช้ `auth.py` |
| settings (tz · tv_mode · skip · destinations) | 174–250 · 2366–2492 | getter/setter อยู่คนละที่กับ route |
| TradingView client (login · token cache · throttle · exchange resolve · fetch retry) | 340–546 · 734–869 | global 5 ตัว |
| ตลาด/แท่ง (calendar · session · bar closed · resample 4h) | 548–733 | logic ล้วน ทดสอบได้ |
| fetch pipeline `process_symbol` | 870–1315 | **ฟังก์ชันเดียว 445 บรรทัด** |
| history | 1316–1370 | |
| export (csv · formula · news · zip) | 1371–1992 · 2328–2365 | `_build_export_csv_bytes` ถูกเรียกจาก adapter + สคริปต์ stock-radar |
| gold analysis (Gemini) + gold job | 1993–2327 · 3036–3159 | และยังมี `gold.py` (gold mode แยก 398 บรรทัด) |
| Telegram | 2493–2526 | |
| automate job engine | 2527–3035 | state `job` + worker thread |
| TV connection test | 2661–2777 | |
| Google Drive | 3160–3410 | |
| stock radar scan (AI) | 3411–3528 | |
| earning scan | 3529–3758 | **route portfolio DELETE/PUT แทรกอยู่กลาง (3585–3607)** |
| symbols · version · autostart | 3759–3874 | |
| watchlist · portfolio | 3886–4007 | |

- **ชื่อที่โค้ดอื่น import จาก `main` (ห้ามหาย):** `app` (uvicorn `main:app`) · `current_tz` · `_fetch_export_rows` · `_build_export_csv_bytes` · `_build_formula_csv_bytes` (`radar_engine/adapter.py`) · `_build_export_csv_bytes` (stock-radar `fill_short_hist.py` · test) · `_select_export_symbols` (test) · `process_symbol` (test)
- **โค้ดซ้ำที่เจอ:** `_build_formula_csv_bytes` มีสำเนา `NEWS_FEEDS` + `fetch_single_feed` ของ `fetch_all_news` ทั้งก้อนอยู่ข้างใน (บรรทัด ~1863–1900) และรวมผลด้วย `as_completed` ⇒ ลำดับข่าวในไฟล์ formula เปลี่ยนทุกครั้งที่ดึง · ตอนย้าย domain `exports` ให้เหลือแหล่งข่าวที่เดียว (`integrations/news.py`) · ถ้าจะทำให้ลำดับคงที่ = เปลี่ยนพฤติกรรม → commit แยก + อัปเดต golden โดยตั้งใจ
- `store.py` 502 บรรทัด 41 ฟังก์ชัน (ทุก collection ปนกัน) · `gold.py` 398 · `radar_api.py` 93 · `radar_engine/lib.py` = สำเนาจาก stock-radar **ห้ามแก้** (memory zservice-lib-sync)

### 17.3 โครงปลายทาง backend
```
backend/
├─ main.py                    # uvicorn entry (`main:app` คงเดิม) + re-export ชื่อ legacy (§17.2)
├─ zservice/
│  ├─ app.py                  # create_app(): ลำดับ middleware · include routers · mount static
│  ├─ core/                   # env.py (อ่าน env ที่เดียว) · clock.py (current_tz) · logging.py · errors.py
│  ├─ security/               # rate_limit.py · machine/ (keys · scopes · auth · audit) ✅ ทำแล้ว
│  │                          #   sessions.py (JWT + password จาก auth.py) · csrf.py · headers.py · middleware.py
│  ├─ db/                     # client.py · repos/{settings,history,watchlist,portfolio,scans,rounds,users}.py
│  ├─ integrations/           # tradingview/{auth,throttle,client,exchanges}.py · gemini.py · telegram.py
│  │                          #   drive.py · earnings/{finnhub,fmp,alpha_vantage}.py
│  ├─ market/                 # calendar.py · sessions.py · bars.py (closed · resample_4h)
│  └─ domains/                # แต่ละ domain = routes.py (บาง) · service.py · schemas.py
│     ├─ auth/ · health/ · admin/ · settings/ · symbols/ · watchlist/ · portfolio/ · history/
│     ├─ market_data/         # fetch pipeline (process_symbol แตกเป็นขั้น)
│     ├─ jobs/                # state.py (class แทน dict) · steps.py · runner.py · autostart.py (+ lease)
│     ├─ exports/             # stock_csv.py · formula_csv.py · news.py · zip.py · gold_csv.py
│     ├─ gold/                # analysis · job · mode (gold.py เดิม)
│     ├─ stock_radar/ · earning_scan/ · radar_rounds/ (radar_api.py เดิม) · drive/
├─ radar_engine/              # คงเดิม (lib.py สำเนาจาก stock-radar)
└─ tests/                     # pytest แยกตาม module: security/ ✅ · integration/ ✅ · domains/... · golden/
```
- โครงเดียวกับ frontend (`web/src/features/<x>/` ↔ `zservice/domains/<x>/`) — เปิดหา feature เดียวกันได้ทั้งสองฝั่ง
- `routes.py` ห้ามมี logic (รับ request → เรียก service → คืน schema) · service ห้าม import FastAPI · repo เท่านั้นที่แตะ Mongo
- state ที่เปลี่ยนได้ (token TV · throttle · job) เป็น object ของ module เจ้าของเดียว · ไม่มี `global`
- ค่าตั้ง/ค่าคงที่ (`AUTO_COOLDOWN_SECONDS` · `GOLD_SOURCES` · `NEWS_FEEDS` · `EARNING_SCAN_QUARTERS_BACK` ฯลฯ) ย้ายไป `core` หรือ `domains/<x>/config.py` ที่เดียวต่อ domain

### 17.4 วิธีย้ายแบบพฤติกรรมไม่เปลี่ยน (strangler · ทีละ domain)
1. **ก่อนย้ายครั้งแรก — ล็อกพฤติกรรม (characterization tests):**
   - route inventory: method + path + พารามิเตอร์ของทุก route จาก `app.routes` → ไฟล์อ้างอิง · หลังย้ายต้องเท่ากันทุกตัว
   - golden bytes: `_build_export_csv_bytes` / formula / news / gold csv บน fixture rows ออฟไลน์ → sha256 ต้องเท่ากันก่อน–หลัง
   - `process_symbol` บน DataFrame fixture (TradingView ปลอม) → ผลต้องเท่ากันทุก field
   - import-compat: ชื่อใน §17.2 ต้อง import จาก `main` ได้
   - test เดิม 5 ตัว (`test_export_short_history` ฯลฯ) ผ่าน
2. **ย้ายทีละ domain ต่อ 1 commit** (ลำดับ: เสี่ยงน้อย → มาก): health/admin → settings → symbols/watchlist/portfolio → history → exports → market → TradingView → market_data (`process_symbol` แตกเป็นขั้นหลังย้าย) → jobs → gold → scans/drive → app factory
   - `main.py` re-export ชื่อเดิมจากที่ใหม่ ⇒ adapter / สคริปต์ / test ไม่ต้องแก้
   - ทุก commit: ruff + pytest + golden + route inventory ผ่าน
3. **ไม่ปน commit:** ย้ายโค้ด ≠ แก้พฤติกรรม ≠ format · format ไฟล์ที่ย้ายแล้วเท่านั้น
4. Dockerfile ใช้ `COPY backend/zservice/ ./zservice/` (✅ เพิ่มแล้ว) · Python 3.12 ใน image (ตรวจ syntax ด้วย `ruff target-version = py312`)

### 17.5 ความคืบหน้า (branch `feat/web-ui`)

| งาน | สถานะ |
|--|--|
| แผน | ✅ |
| `zservice/security/machine/` (keys · scopes · auth · audit) + `security/rate_limit.py` + `core/env.py` | ✅ ruff ผ่าน · pytest 56 ผ่าน · test legacy 5 ตัวผ่าน |
| middleware ใน `main.py` ใช้ machine auth + `GET /api/admin/key_audit` | ✅ PULL_KEY เดิมใช้ได้เหมือนเดิม (header + query) แต่ถูกบันทึกว่า deprecated |
| `tools/manage_keys.py` (ออก key → Keychain ทาง stdin) · `tools/zsvc_client.py` · `tools/zsvc_curl.sh` | ✅ ทดสอบกับ Keychain จริง (service ทดสอบแล้วลบทิ้ง) + เซิร์ฟเวอร์จริง (TLS ตรวจผ่าน) |
| `ruff.toml` · `backend/pyproject.toml` (pytest) · Dockerfile copy `zservice/` | ✅ |
| characterization tests (§17.4 ข้อ 1): route inventory 53 คู่ (method+path+query+body fields) · ชื่อ import-compat 7 ชื่อ · golden sha256 ของ export 1w/1d part1–2 · formula · news (ตัดเน็ต) | ✅ `backend/tests/characterization/` · รันซ้ำ 2 รอบผลเท่ากัน · ยังขาด golden ของ `process_symbol` (ทำก่อนย้าย market_data) |
| Phase 0 frontend (`web/`) | ✅ commit `44b30df` · ผลยืนยันครบ 7 ข้อใน `web/PHASE0.md` (ตรวจซ้ำแล้ว: verify เขียว · audit 0 · ไม่มี v2/ภาษาไทยในโค้ด/CDN) |
| ผล Phase 0 ที่เปลี่ยนแผน | ① Paraglide ใส่ทั้ง 3 ภาษาใน bundle (ไม่ใช่เฉพาะภาษาที่เลือกตามที่ §7.1 เขียนไว้) — 2.4 KB gzip ที่ 17 key ⇒ ยอมรับ · เฝ้าในงบ · ② Paraglide ดึง plugin จาก jsDelivr ตอน build โดยค่าเริ่ม และ **ถ้าดึงไม่ได้ build ผ่านแต่ข้อความว่าง** ⇒ ใช้ `@inlang/plugin-message-format` จาก npm + `tsc -b` หลัง generate จับข้อความว่าง · ③ สลับภาษาต้องห่อ route ด้วย `withLocale(Page)` (router cache หน้า) · ④ zod เต็มทำ JS แรกเข้าเกินงบ (126 KB) ⇒ เบราว์เซอร์ใช้ `zod/mini` · zod เต็มเฉพาะ script · ⑤ CSP: lightweight-charts ฉีด `<style>` ของโลโก้ ⇒ `attributionLogo: false` + ลิงก์ให้เครดิต TradingView เอง · ⑥ trailing slash = `createRouter({ trailingSlash: 'always' })` · ⑦ markdown = **markdown-to-jsx 9.10.3** + `disableParsingRawHTML: true` (0 dep · มี provenance · advisory เก่า 2 ตัวกระทบเฉพาะ < 7.4.0) · ⑧ Table = v9.3.1 ใช้ได้ (API ใหม่: ลง feature แล้วเรียก `useTable`) · ⑨ line length บังคับด้วย `@stylistic/eslint-plugin` (`max-len` ของ ESLint ถูก deprecate · Prettier `printWidth` ไม่ใช่เพดานจริง) |
| B7 `AUTH_SECRET` ไม่มี fallback แล้ว: ไม่ตั้ง/สั้นกว่า 32 byte ⇒ server ไม่ยอมบูต (startup) + ทุก token ถูกปฏิเสธ · import `main` แบบ offline (fill_short_hist · test) ยังใช้ได้ | ✅ test 5 ตัว (รวมพิสูจน์ว่าจับ fallback เดิมได้) |
| ออก secret จริงแล้ว (24 ต.ค.): `AUTH_SECRET` ใหม่ 64 byte + key เครื่องบ้าน `home` (read · jobs · watchlist:write · หมดอายุ 2027-04-22) เก็บใน Keychain `z-service` | ✅ ไม่เคยพิมพ์ออกจอ · `tools/manage_keys.py copy` → clipboard |
| push branch `feat/web-ui` (ไม่แตะ main · user สั่ง) | ✅ |
| **ลำดับ deploy ที่ปลอดภัย:** ① ตั้ง `AUTH_SECRET` + `ZS_API_KEYS` ใน Coolify **ก่อน** ② merge เข้า main เมื่อ user สั่ง ③ ย้ายสคริปต์บ้านไปใช้ `tools/zsvc_client.py` / `zsvc_curl.sh` ④ ดู `/api/admin/key_audit` จนไม่มี PULL_KEY ⑤ ลบ `PULL_KEY` จาก env + ลบ literal ออกจากไฟล์ | ⏳ ①–⑤ · **ห้ามย้ายสคริปต์ก่อน ②** (เซิร์ฟเวอร์เดิมไม่รู้จัก `zsk_`) |
| backend จัดระเบียบ (§17.4) | ✅ `main.py` 4,030 → **50 บรรทัด** (entry + re-export) · ย้ายครบ 18 domain/integration: admin · health · settings · watchlist · portfolio · history · exports (formula เป็นข้อมูล `formula_rules.json`) · market · tradingview · market_data · symbols · jobs · gold · stock_radar · earning_scan · auth · drive · telegram/gemini/drive/news · app factory `zservice/app.py` · ทุกก้อนผ่าน golden (route 62 ตัว · export/formula/news/zip bytes · process_symbol 5 กรณีบนแท่ง TradingView จริงที่บันทึกไว้ · job runner · gold prompt 22,389 ตัวอักษร · stock radar prompt/Telegram · earnings) · pytest 112 · ruff สะอาด |
| legacy ใน backend (อัปเดต 25 ต.ค.) | ✅ ย้ายครบแล้ว: `store.py` → `zservice/db/` (facade · AST เหมือนเดิม 40/41) · `auth.py` → `security/tokens.py` · `gold.py` → `domains/gold_mode/` (ข้อความเป็น JSON) · `radar_api.py` → `domains/radar_rounds/` (adapter เลิก import main) · สคริปต์ครั้งเดียว → `backend/scripts/` · ที่รากเหลือ: facade 5 ตัว (`main` `store` `auth` `gold` `radar_api`) · `build_meta.py` (Dockerfile) · test legacy 8 ตัว (เอกสาร/skill stock-radar อ้าง path อยู่) · `radar_engine/` (lib.py สำเนา stock-radar) |
| ฟังก์ชันยาวใน `zservice/` (25 ต.ค.) | ✅ แตกครบ — ยาวสุดเหลือ ~56 บรรทัด (เป้า ≤ 60): `process_symbol` 445 → `market_data/` 6 ขั้น (`220da8f`) · `build_export_csv_bytes` 237 → metadata/แถว (`677fcdb` · golden + เทียบเก่า-ใหม่ 50 กรณีไบต์ตรงกัน) · jobs runner → `step` / `summary` / `worker` (`0f40f35`) · gold analysis 172 → `inputs` / `prompt` (`01cef4e`) · TV self-test 138 (`9b0906e`) · `get_tv_data_with_retry` 96 (`b394805`) · gold job / snapshots / gold-mode CSV (`2fbbddc`) · **ทุกก้อนเขียน characterization test บนโค้ดเก่าก่อนแตก** (เพิ่ม 33 test: job stop/resume/error · gold input เสีย/ไม่มี template · self-test ทุกโหมด auth ทุก verdict · retry 8 กรณี · gold job 6 กรณี) · pytest 165 · ทดสอบ TradingView จริง (SPY) ผ่าน |
| บั๊กที่เจอระหว่างแตก | ✅ แก้แล้ว `9052b3e`: ข้อความ Telegram ของ gold job ขึ้น `&lt;b&gt;1. Bias:&lt;/b&gt;` ตรง ๆ (หัวข้อใส่ `<b>` แล้วโดน `html.escape` ทั้งก้อน) + ตัดที่ 3,500 ตัวอักษรอาจตัดกลาง `&amp;` ⇒ Telegram ปฏิเสธทั้งข้อความ · ตอนนี้ escape เฉพาะข้อความโมเดล/ค่าในหัว และตัดไม่ผ่ากลาง entity/tag (test กวาดทุกความยาว) · golden เปลี่ยนเฉพาะหัวข้อ 2 บรรทัด |
| ข้อสังเกต (ยังไม่แก้ = เปลี่ยนพฤติกรรม) | ① `get_tv_data_with_retry` รอ backoff หลังครั้งสุดท้ายด้วย (2–4 วิ/ตัวที่ fail + อีก 2 วิในรอบ fallback) — ถ้าจะตัดต้อง commit แยก + วัดว่า rate limit ไม่เพิ่ม ② export CSV เดิมคำนวณ `half_day` แต่ไม่เคยเขียนลงไฟล์ (ตัดโค้ดที่ไม่มีผลออกแล้ว ไฟล์ไม่เปลี่ยน) |
| error ของ API แปลได้ (25 ต.ค.) | ✅ `zservice/core/errors.py` `ApiError(status, code, detail, params=)` → `{"detail", "code", "params"}` · `detail` เดิมทุกตัว (legacy แสดงตรง ๆ · pytest 167 เดิมผ่านหมด) · 43 code ทั่ว 16 ไฟล์ · web แปลจาก `err_<code>` th/en/it ผ่าน map ชัด ๆ (`shared/api/errorMessages.ts` · ไม่ใช้ `m[key]` เพราะจะลากข้อความทั้งหมดเข้า bundle แรก — JS แรกเข้ายัง 105.0 KB) · code ที่ web ไม่รู้จัก/422 ของ FastAPI = แสดง detail เหมือนเดิม · test คุมสองฝั่ง: backend อ่าน `ApiError(...)` ทุกจุดด้วย AST แล้วเช็คว่ามีข้อความครบ 3 ภาษา + placeholder ตรง params · web เช็คว่าทุก `err_*` มีใน map · mock MSW ตอบ code เหมือนเซิร์ฟเวอร์ |
| ค้างจัดระเบียบ | ✅ ราก repo จัดแล้ว (25 ต.ค.): สคริปต์ symbol/watchlist → `scripts/symbols/` · patch/scratch ครั้งเดียว → `scripts/legacy/` · dev → `scripts/dev/` · คู่มือ → `docs/ops/` · `task.pid` ออกจาก git · ราก repo เหลือ Dockerfile · package.json · ruff.toml + โฟลเดอร์ · stock-radar `fill_short_hist.py` อ่าน key จาก path ใหม่ |
| กติกาเรียกข้าม domain (backend) | domain เรียกอีก domain ได้ **เฉพาะ module สาธารณะ** (`service.py` / builder ที่ประกาศ) ห้าม import `routes.py` หรือของภายใน · `integrations/` และ `core/` ห้าม import `domains/` (เหตุผลที่ job state อยู่ `core/job_state.py`) |
| web Phase 1–2 | ✅ `c32476f` · `73f2162` · ครบเท่า legacy ทุกแท็บ (อ่าน + สั่งงาน + ยืนยัน 2 ชั้นทุกปุ่มลบ/เสียเงิน) · JS แรกเข้า **105.0 KB** · test 68 · 209 key × 3 ภาษา |
| เหตุการณ์ | `29abce9` (commit ฝั่ง backend) กวาด rename ที่ agent หน้าเว็บ stage ไว้ติดไปด้วย 3 ไฟล์ — แก้ครบใน `73f2162` · `tools/check_and_commit.sh` ตอนนี้ commit เฉพาะ path ที่ระบุ |
| import ตรง module (25 ต.ค.) | ✅ `8546c7c` ลบ facade `store.py` `auth.py` `gold.py` `radar_api.py` · ทุกจุด import module จริงพร้อมชื่อย่อ (`from zservice.db.repos import settings as settings_repo`) ตาม fastapi-best-practices · `main.py` เหลือแค่โหลด env + สร้าง app (มี test คุม) |
| config แยกตาม domain (25 ต.ค.) | ✅ pydantic-settings 2.16.0 · 16 คลาส `config.py` ใน domain/integration ของตัวเอง (FastAPI "Settings and Environment Variables" + fastapi-best-practices "Decouple Pydantic BaseSettings") · `get_settings()` cache ต่อ process · ตรวจทุกคลาสตอนบูต (ค่าผิด = ไม่บูต + บอกชื่อตัวแปร) · secret เป็น `SecretStr` · ไม่มี module ไหนอ่าน `os.environ` เอง (`tools/check_structure.py` บังคับ) · `docs/config-reference.md` สร้างจากโค้ด + test กันตกรุ่น · test ไม่โหลด `.env` ของเครื่องอีก และ `MONGO_URI` ว่างเสมอ (เดิม shell ที่ export ไว้หลุดเข้า test ได้) · ต่างจากเอกสาร FastAPI 1 จุด: ผู้อ่านส่วนใหญ่ไม่ใช่ route (job/integration) จึงใช้ `config.reset()` + fixture `env` แทน `dependency_overrides` |

---

## 18. แหล่งอ้างอิง (ดึงจริง 24 ต.ค. 2026)

- npm registry · PyPI JSON API — เวอร์ชันใน §4
- nodejs.org `dist/index.json` · `nodejs/Release/schedule.json` — Node 24/26 LTS · npm ที่มากับ Node
- GitHub Advisory Database — next · react-server-dom-* · vite · axios · react-router · @tanstack/* · CVE-2026-45321 · i18next/paraglide/lingui/react-intl
- เอกสาร npm 11.19 ในเครื่อง — `min-release-age` · `strict-allow-scripts` · `allow-git`
- react.dev — Build a React app from Scratch: https://react.dev/learn/build-a-react-app-from-scratch
- Next.js — Static Exports: https://nextjs.org/docs/app/guides/static-exports
- TanStack Router — Search Params · Automatic Code Splitting · Static Route Data: https://tanstack.com/router/latest/docs/framework/react/guide/search-params · https://tanstack.com/router/latest/docs/framework/react/guide/automatic-code-splitting · https://tanstack.com/router/latest/docs/framework/react/guide/static-route-data
- FastAPI — Settings and Environment Variables: https://fastapi.tiangolo.com/advanced/settings/ (ดึง 25 ต.ค.)
- zhanymkanov/fastapi-best-practices — Decouple Pydantic BaseSettings · project structure: https://github.com/zhanymkanov/fastapi-best-practices (ดึง 25 ต.ค.)
- OWASP REST Security Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/REST_Security_Cheat_Sheet.html
- OWASP CSRF Prevention Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html
- OWASP HTML5 Security Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/HTML5_Security_Cheat_Sheet.html
- Coolify — Build and Deployment Model: https://next.coolify.io/docs/core/build-deployment-model · Rolling Updates: https://coolify.io/docs/applications/deployments/rolling-updates
- ซอร์สในเครื่อง: Starlette 1.3.1 `middleware/cors.py` (167–168) · `staticfiles.py` · uvicorn `config.py` (`FORWARDED_ALLOW_IPS` ค่าเริ่ม 127.0.0.1) · z-service `Dockerfile` · `backend/main.py` · `backend/auth.py` · `backend/build_meta.py` · `dash/`
- ตรวจเซิร์ฟเวอร์จริงด้วย curl/openssl: TLS · header · `/docs` `/openapi.json` 200
