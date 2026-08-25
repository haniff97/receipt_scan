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
│   │   ├── anomalies.py       # IQR statistical anomaly detector
│   │   ├── deepseek.py        # DeepSeek API calls (OCR cleanup, NLQ, summary, anomaly review)
│   │   └── routes/
│   │       ├── transactions.py  # CRUD, stats, dashboard, AI summary, PATCH amount
│   │       ├── receipts.py      # upload → deskew → OCR → AI, list/serve/delete receipts
│   │       ├── query.py         # NLQ (DeepSeek first, rules fallback)
│   │       └── analytics.py     # anomalies (statistics + AI review)
│   ├── uploads/               # saved receipt images
│   ├── seed.py                # generates ~350 sample transactions
│   ├── requirements.txt
│   └── .env                   # DEEPSEEK_API_KEY (not committed)
└── frontend/                  # React app (Vite)
    └── src/
        ├── App.jsx            # entire UI (home, scan, receipts, dashboard, alerts, settings)
        ├── i18n.js            # English + Bahasa Melayu translations
        └── index.css
```

## 📝 Recent Updates

- **Languages:** Added full **Bahasa Melayu** support — the whole UI translates (Settings → Language), and **AI replies follow** (dashboard summary, Ask AI, anomaly reasons are generated in the selected language via a `lang` parameter).
- **Receipt gallery filters:** Filter receipts by **Day / Week / Month**.
- **Export CSV:** One-tap download of all transactions as a `.csv` file.
- **Settings:** Added **default category** and an **AI toggle** (on = AI auto-read, off = manual entry — the future free-tier mode).
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
| POST | `/api/receipts/upload` | Upload receipt (image/PDF/HEIC) → deskew → OCR → AI → create transaction |
| GET | `/api/receipts` | List receipts |
| GET | `/api/receipts/{id}/image` | Serve a saved receipt image |
| DELETE | `/api/receipts/{id}` | Delete a receipt + its transactions + image |

## 🧠 How the pipeline works

1. **Scan:** camera/gallery/PDF → EXIF rotation fixed + image compressed → **Gemini 3.7 Flash** reads the receipt natively (highly accurate, no deskew distortion) → falls back to Tesseract + DeepSeek only if Gemini fails. You **confirm the total** (editable) before it's final.
2. **Ask:** your question + a **compact aggregated summary** of your transactions (totals per category, totals per month, latest 15 items) sent to DeepSeek → a natural-language answer with matching items. Compact payloads = fewer tokens, faster and cheaper than sending raw rows.
3. **Anomalies:** IQR detector flags outliers per category → DeepSeek reviews each candidate against category context (median/max) and confirms or rejects it with a reason.
4. **Dashboard:** aggregates real data, and DeepSeek writes a concise summary of your habits and month-over-month trends. The summary is **cached by data version** — it regenerates only when a new receipt is scanned, so simply opening the dashboard costs zero AI tokens.

## 💰 AI token & cost optimizations

Two mechanisms keep AI costs low:

- **Compact payloads** — instead of sending every transaction row to the LLM, the backend aggregates them first (`build_compact_payload`): `total_spent`, `by_category`, `monthly`, and the latest 15 transactions. This drops input tokens from thousands to a couple hundred per call.
- **Fingerprint-based summary cache** — the dashboard summary is regenerated by the AI only when the data actually changes. The server tracks `(transaction_count, latest_date, currency, lang)`; opening the Dashboard with unchanged data serves the cached answer instantly with **zero AI calls**.

Together these make per-user AI cost a fraction of a cent for normal usage — which is what makes a flat monthly subscription viable.

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

