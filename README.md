# 🧾 Receipt Tracker

A full-stack mobile-style app that reads your receipts, understands your spending in plain English or Bahasa Melayu, detects unusual charges, and summarizes everything with AI.

Built with **React + Vite** (frontend), **FastAPI + SQLite** (backend), **Tesseract OCR**, and AI via **Gemini** + **DeepSeek**.

---

## ✨ What it does

| Feature | How it works |
| --- | --- |
| 📸 **Scan a receipt** | Take a photo (camera or gallery/PDF) → EXIF rotation is corrected → **Gemini 3.7 Flash** vision AI reads the receipt directly (highly accurate) → Tesseract OCR + DeepSeek used as a fallback if Gemini is unavailable |
| 🎬 **Morph animation** | The raw photo visibly scans with a modern sweeping gradient and pulse rings |
| ✏️ **Confirm total** | After scanning, the extracted total shows in an editable field — check it against the receipt and correct it if the AI got it wrong, before it's final |
| 🗂️ **Receipt gallery** | Every scanned receipt image is stored and viewable. **Select mode** lets you tap multiple receipts and delete them. Filter by **Day / Week / Month**. Close button is sticky at the top for long receipts. |
| 📥 **Export CSV** | One tap downloads all transactions as a `.csv` (Date, Merchant, Category, Amount, Description) for Excel/Sheets |
| 🔍 **Ask AI** | Type a question in plain English or Malay — DeepSeek answers using your real transactions |
| 📊 **Dashboard** | Spending today / this week / this month, a monthly bar chart, breakdown by category, a filterable transaction list, and an **AI-written summary** of your spending habits. The summary follows your chosen currency (RM/$) and language |
| 🚨 **Alerts** | Detects purchases that are unusually expensive for your normal habits, then **DeepSeek reviews each one** and confirms or dismisses it with a reason (in your language) |
| ⚙️ **Settings** | Language (**English / Bahasa Melayu** — the whole UI + AI replies), currency (**Ringgit RM / Dollar $**), default category, and an **AI toggle** (on = auto-read, off = manual entry). All saved per device |
| 🖼️ **Multi-format support** | JPEG, PNG, WebP (Android), HEIC (iPhone), and PDF (first page) are all resized and converted before sending to Gemini |
| ➕ **Custom categories** | Add your own categories (e.g. "pets") when scanning |
| 🚫 **Duplicate protection** | Scanning the same receipt twice is rejected — no double-counted expenses |

**Important:** the only way to add receipts is through the **Scan** page — no import buttons elsewhere, so every expense is a verified scan.

## 🌐 Languages

- **English** and **Bahasa Melayu** are fully supported.
- Switching language in Settings translates the **entire UI** (labels, buttons, categories, messages).
- **AI-generated text follows too** — the dashboard summary, Ask AI answers, and anomaly reasons are generated in the selected language (the app passes `lang` to DeepSeek).

## 🧰 Tech stack

- **Frontend:** React 19, Vite, lucide-react icons, axios
- **Backend:** FastAPI, SQLAlchemy, SQLite
- **Vision AI:** Gemini 3.7 Flash (Primary)
- **Fallback OCR & Logic:** Tesseract + DeepSeek API (OCR cleanup, NLQ, summary, anomaly review)
- **Document processing:** Pillow (EXIF rotation, resizing), PyMuPDF (PDF rendering)

## 📁 Project structure

```
Scan/
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI app, CORS, route registration
│   │   ├── database.py        # SQLite connection
│   │   ├── models.py          # Transaction & Receipt tables
│   │   ├── schemas.py         # Pydantic request/response models
│   │   ├── ocr.py             # Tesseract OCR + preprocessing + regex parser + HEIC/PDF
│   │   ├── deskew.py          # OpenCV auto-deskew (detect corners, perspective-correct)
│   │   ├── nlq.py             # Rule-based NLQ fallback engine
│   │   ├── anomalies.py       # IQR statistical anomaly detector (small-sample aware)
│   │   ├── deepseek.py        # DeepSeek API calls (OCR cleanup, NLQ, summary, anomaly review)
│   │   ├── gemini.py          # Gemini vision receipt reading (+ LHDN relief mapping)
│   │   ├── database.py        # SQLite/Postgres + current_user_id() (multi-user prep)
│   │   └── routes/
│   │       ├── transactions.py  # CRUD, stats, dashboard (SQL GROUP BY), AI summary, PATCH
│   │       ├── receipts.py      # upload → Gemini/OCR → AI, list/serve/delete receipts
│   │       ├── query.py         # NLQ (DeepSeek first, rules fallback, cached)
│   │       ├── analytics.py     # anomalies (statistics + AI review, per-user)
│   │       ├── lhdn.py          # LHDN tax relief aggregation (per-year, capped) + summary
│   │       └── backup.py        # backup/restore (DB + uploads as zip)
│   ├── uploads/               # saved receipt images
│   ├── migrate_lhdn.py        # DB migration: LHDN columns + user_id + relief caps
│   ├── seed.py                # generates ~350 sample transactions
│   ├── requirements.txt
│   └── .env                   # DEEPSEEK_API_KEY + GEMINI_API_KEY (not committed)
└── frontend/                  # React app (Vite)
    └── src/
        ├── App.jsx            # entire UI (home, scan, receipts, dashboard, alerts, settings)
        ├── i18n.js            # English + Bahasa Melayu translations
        └── index.css
```

## 📝 Recent Updates

- **Backup & restore:** One-tap **Download backup** (SQLite DB + all receipt images as a zip) and **Restore from backup** in Settings — plus an "Alert sensitivity" setting (1x/1.5x/2x/3x).
- **Duplicate-scan → open existing:** Re-scanning an already-uploaded receipt now returns a `409` with the receipt id, and the app asks whether to open the existing receipt. Also fixed a bug where the `ai=off` field was silently ignored (it now actually disables AI).
- **LHDN Tax Relief view:** Receipt Gallery has a **Tax Relief** filter showing per-year totals vs. caps with progress bars, an **AI summary**, and relief CSV export. Relief can be corrected in the edit modal or set on manual adds.
- **Postgres-ready:** `DATABASE_URL` env var switches SQLite ↔ PostgreSQL; monthly aggregation is dialect-aware; backup/restore work on SQLite.
- **Multi-user prep (user_id):** Added a `user_id` column to `transactions` and `receipts` (defaults to `local-user`). Every query filters by `current_user_id()` — so when Supabase/Auth arrives, you swap one function and the app is per-user. Run `migrate_lhdn.py` on any existing deployment to add the column.
- **LHDN Tax Relief:** Receipts are auto-mapped to Malaysian tax-relief categories (medical, lifestyle, sports, etc.). A **Tax Relief view** in the Receipt Gallery shows per-year totals vs. caps with progress bars. You can correct the AI's relief guess via the edit modal, and export a relief summary CSV.
- **Edit & delete transactions:** Each transaction in the Dashboard list has pencil (edit merchant/amount/category/date/relief) and trash (delete) buttons.
- **Manual entry mode:** When AI is off, scanning shows a full manual form (merchant, amount, category, date) so non-AI users can still add receipts.
- **CSV respects filters:** The export button now only includes transactions matching the current Day/Week/Month filter.
- **Ask AI cached answers:** The same question is answered once, then served from cache until new data arrives (saves AI tokens/cost).
- **SQL aggregation:** Dashboard today/week/month, monthly, and category totals now use SQL `GROUP BY` instead of loading all rows into Python (faster with hundreds of receipts).
- **AI token optimizations:** Compact AI payloads (aggregates, not raw rows) + fingerprint-cached dashboard summary — see the "AI token & cost optimizations" section.
- **Languages:** Added full **Bahasa Melayu** support — the whole UI translates (Settings → Language), and **AI replies follow** (dashboard summary, Ask AI, anomaly reasons are generated in the selected language via a `lang` parameter).
- **Receipt gallery filters:** Filter receipts by **Day / Week / Month / Tax Relief**.
- **Export CSV:** One-tap download of all transactions as a `.csv` file.
- **Settings:** Added **AI toggle** (on = AI auto-read, off = manual entry — the future free-tier mode) and a **Feedback box**.
- **Upgraded Vision API:** Switched the default model to the latest **`gemini-3.7-flash`** for highly accurate receipt parsing (fixed a 404 error from an invalid model name).
- **Fixed Photo Rotation (EXIF):** Uploaded phone photos are now correctly rotated and compressed (<1600px) *before* being sent to Gemini, fixing issues where sideways receipts caused bad reads.
- **Fixed Total Calculation Bug:** Removed a bug where a 6% tax multiplier was blindly applied even when the AI had already correctly computed the sum.
- **Fixed Duplicate Bug:** Fixed an issue where the duplicate receipt check blocked all uploads handled by Gemini (because the OCR text was empty).
- **UI & Defaults:** Set Ringgit (RM) as the default currency. The Receipt Gallery modal now has consistent styling with a sticky "Close" button at the top for long receipts.

## 🚀 Getting started

> **Note:** Because sensitive and machine-specific files (like `.env`, `.venv/`, and the local database) are safely ignored by git, you will need to re-create the environment when setting up on a new device or deployment. Follow these steps to generate them freshly!

### 1. Backend

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Set your DeepSeek key:

```bash
echo "DEEPSEEK_API_KEY=your-key-here" > .env
```

Seed sample data (optional):

```bash
.venv/bin/python seed.py
```

Run the API:

```bash
.venv/bin/uvicorn app.main:app --reload
```

API docs: http://127.0.0.1:8000/docs

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173

### 3. Install OCR engine

On macOS: `brew install tesseract`

---

## 🔌 API endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/transactions` | List transactions (filter by `category`, `start`, `end`) |
| POST | `/api/transactions` | Add a transaction manually |
| PATCH | `/api/transactions/{id}` | Update a transaction (used to correct a scanned total) |
| DELETE | `/api/transactions/{id}` | Delete a transaction |
| GET | `/api/stats` | Total spent + transaction count |
| GET | `/api/categories` | Spend per category |
| GET | `/api/dashboard` | Today / week / month spend, monthly + category breakdown |
| GET | `/api/dashboard/summary?currency=RM&lang=ms` | AI plain-English/Bahasa Melayu spending summary |
| GET | `/api/query?q=...&lang=ms` | Natural language question answered by AI (in chosen language) |
| GET | `/api/anomalies?lang=ms` | Anomaly candidates reviewed by AI (reasons in chosen language) |
| GET | `/api/lhdn/relief?year=2025` | LHDN relief totals per category (SQL GROUP BY, capped) for a tax year |
| GET | `/api/lhdn/summary?year=2025` | Cached AI summary of claimable reliefs |
| GET | `/api/backup` | Download zip of SQLite DB + receipt images |
| POST | `/api/backup/restore` | Replace DB + uploads from an uploaded backup zip (restart required) |
| POST | `/api/receipts/upload` | Upload receipt (image/PDF/HEIC) → Gemini → AI → create transaction |
| GET | `/api/receipts` | List receipts |
| GET | `/api/receipts/{id}/image` | Serve a saved receipt image |
| DELETE | `/api/receipts/{id}` | Delete a receipt + its transactions + image |

## 🧠 How the pipeline works

1. **Scan:** camera/gallery/PDF → EXIF rotation fixed + image compressed → **Gemini 3.7 Flash** reads the receipt natively (highly accurate, no deskew distortion) → falls back to Tesseract + DeepSeek only if Gemini fails. You **confirm the total** (editable) before it's final.
2. **Ask:** your question + a **compact aggregated summary** of your transactions (totals per category, totals per month, latest 15 items) sent to DeepSeek → a natural-language answer with matching items. Compact payloads = fewer tokens, faster and cheaper than sending raw rows.
3. **Anomalies:** IQR detector flags outliers per category → DeepSeek reviews each candidate against category context (median/max) and confirms or rejects it with a reason.
4. **Dashboard:** aggregates real data, and DeepSeek writes a concise summary of your habits and month-over-month trends. The summary is **cached by data version** — it regenerates only when a new receipt is scanned, so simply opening the dashboard costs zero AI tokens.

## 💰 AI token & cost optimizations

Three mechanisms keep AI costs low — together they make per-user AI cost a fraction of a cent, which is what makes a flat monthly subscription viable.

### 1. Compact payloads (fewer input tokens)

Instead of sending every transaction row to the LLM, the backend aggregates them first (`build_compact_payload` in `deepseek.py`). Raw rows are expensive — 200 transactions is easily thousands of tokens. The compact payload is:

```json
{
  "count": 350,
  "total_spent": 33377.29,
  "by_category": { "dining": 1200.5, "travel": 8000.0, ... },
  "monthly": { "2026-06": 8138.11, "2026-07": 6505.21, ... },
  "recent": [ { "date": "2026-08-24", "merchant": "Cafe", "amount": 43.46, "category": "dining" }, ... ]
}
```

That's ~100–200 tokens instead of thousands. The LLM still has enough context (totals, trends, recent merchants) to answer meaningfully. **Note the trade-off:** specific item-level questions are less precise than the raw-row approach, so the rule-based `nlq.py` engine remains the fallback for exact lookups.

### 2. Fingerprint-based caching (zero AI calls on repeat)

Two caches, both keyed on a **data fingerprint** = `(transaction_count, latest_transaction_date)`:

| Cache | Key | When it regenerates |
| --- | --- | --- |
| Dashboard summary | `(fingerprint, currency, lang)` | only when a new receipt is scanned |
| Ask AI answers | `(question, lang, fingerprint)` | only when a new receipt is scanned |

- **Same data + same question** → served from an in-memory dict, zero LLM calls.
- **New receipt scanned** → fingerprint changes → every cache entry invalidates and regenerates once.
- Every cached response returns a `"cached": true/false` flag so you can verify.
- The cache is a module-level dict (`_query_cache`, `_summary_cache`) — fine for single-worker. For multi-worker/scale, swap to Redis with the same key scheme.

### 3. SQL aggregation (no full-table loads)

The dashboard no longer loads all rows into Python. Queries now use SQL aggregation, which scales to hundreds/thousands of receipts:

```sql
-- today/week/month in one pass (SQLite syntax)
SELECT COALESCE(SUM(CASE WHEN date >= :start_today THEN amount ELSE 0 END), 0)
FROM transactions;

-- monthly totals
SELECT strftime('%Y-%m', date) AS month, SUM(amount)
FROM transactions
GROUP BY month ORDER BY month;

-- category totals
SELECT category, SUM(amount)
FROM transactions
GROUP BY category;
```

- `CASE WHEN ... THEN amount ELSE 0 END` lets one query compute each time bucket.
- `GROUP BY` moves the heavy lifting from Python to the database engine.
- `/api/dashboard`, `/api/categories`, and `/api/stats` all use SQL aggregation now.
- **Postgres note:** swap `strftime('%Y-%m', date)` for `date_trunc('month', date)` and use proper indexes on `(date)` and `(category)`.

## 🧹 Removing the dummy/seed data

The app starts empty. If you ran `seed.py`, you can wipe everything:

```bash
# from the backend/ folder
rm receipts.db          # delete the database
rm -rf uploads          # delete saved receipt images
```

Then restart the server — the app recreates empty tables on startup:

```bash
.venv/bin/uvicorn app.main:app --reload
```

Verify it's empty:

```bash
curl -s http://127.0.0.1:8000/api/stats
# → {"total_spent": 0.0, "transaction_count": 0, ...}
```

> `seed.py` will **not** re-seed by itself (it skips when data already exists). To add sample data back later, just run `.venv/bin/python seed.py`.

## 🐳 Deploying with Docker (ARM64 servers)

The project ships Dockerfiles + `docker-compose.yml`. Key gotchas on ARM boards (Raspberry Pi, Orange Pi, etc.):

- **OpenCV:** use `opencv-python-headless==4.10.0.84` — version 5.x has no ARM64 wheels and fails to compile on the device.
- **`pillow-heif`:** leave unpinned so pip grabs the ARM64 wheel.
- **nginx upload limit:** add `client_max_body_size 20m;` to `frontend/nginx.conf` — the default 1MB rejects phone photos.

```bash
docker compose up -d --build
```

**⚠️ After deploying new backend code, always run the DB migration** (adds `user_id`, LHDN columns, and relief caps). Skipping it causes "no such column: transactions.user_id" errors:

```bash
docker exec -it receipt_scan-backend-1 python migrate_lhdn.py
docker compose restart backend
```

Test the deployment end-to-end (the file must exist on the *host*, not inside a container):

```bash
curl -s -X POST "http://localhost:4006/api/receipts/upload" \
  -F "file=@/tmp/receipt.png" -F "category=dining"
```

## 🔐 API keys (.env)

Both keys go in `backend/.env` (never committed):

```
DEEPSEEK_API_KEY=...     # Ask AI, dashboard summary, anomaly review, OCR fallback
GEMINI_API_KEY=...       # primary vision-based receipt reading
```

- Get DeepSeek: https://platform.deepseek.com
- Get Gemini (free): https://aistudio.google.com/apikey

