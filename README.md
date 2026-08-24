# 🧾 Receipt Tracker

A full-stack mobile-style app that reads your receipts, understands your spending in plain English, detects unusual charges, and summarizes everything with AI.

Built with **React + Vite** (frontend), **FastAPI + SQLite** (backend), **Tesseract OCR**, and the **DeepSeek API**.

---

## ✨ What it does

| Feature | How it works |
| --- | --- |
| 📸 **Scan a receipt** | Take a photo (camera or gallery/PDF) → a scanning animation plays → the image is **auto-deskewed** (edges detected, perspective-corrected into a straight document) → Tesseract OCR reads the text → DeepSeek corrects OCR errors and extracts clean data (merchant, total, date, category, items) |
| 🎬 **Morph animation** | The raw tilted photo visibly straightens itself into the clean deskewed document in one smooth animation |
| ✏️ **Confirm total** | After scanning, the extracted total shows in an editable field — check it against the receipt and correct it if OCR/DeepSeek got it wrong, before it's final |
| 🗂️ **Receipt gallery** | Every scanned receipt image is stored and viewable. **Select mode** lets you tap multiple receipts and delete them (removes the linked transactions + image files) |
| 🔍 **Ask AI** | Type a question in plain English ("how much did I spend on dining in May?") — DeepSeek answers using your real transactions |
| 📊 **Dashboard** | Spending today / this week / this month, a monthly bar chart, breakdown by category, a filterable transaction list, and an **AI-written summary** of your spending habits |
| 🚨 **Alerts** | Detects purchases that are unusually expensive for your normal habits, then **DeepSeek reviews each one** and confirms or dismisses it with a reason |
| ⚙️ **Settings** | Choose your currency — **Dollar ($)** or **Ringgit (RM)** — shown everywhere and saved between sessions |
| 🖼️ **Multi-format support** | JPEG, PNG, WebP (Android), HEIC (iPhone), and PDF (first page) are all OCR'd and converted to a displayable PNG |
| ➕ **Custom categories** | Add your own categories (e.g. "pets") when scanning |
| 🚫 **Duplicate protection** | Scanning the same receipt twice is rejected — no double-counted expenses |

**Important:** the only way to add receipts is through the **Scan** page — no import buttons elsewhere, so every expense is a verified scan.

## 🧰 Tech stack

- **Frontend:** React 19, Vite, lucide-react icons, axios
- **Backend:** FastAPI, SQLAlchemy, SQLite
- **OCR:** Tesseract + Pillow + pytesseract + pillow-heif (HEIC)
- **Document processing:** OpenCV (auto-deskew), PyMuPDF (PDF rendering)
- **AI:** DeepSeek API (OpenAI-compatible chat completions)

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
        ├── App.jsx            # entire UI (home, scan, receipts, dashboard, alerts)
        └── index.css
```

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
| GET | `/api/dashboard/summary` | AI plain-English spending summary |
| GET | `/api/query?q=...` | Natural language question answered by AI |
| GET | `/api/anomalies` | Anomaly candidates reviewed by AI |
| POST | `/api/receipts/upload` | Upload receipt (image/PDF/HEIC) → deskew → OCR → AI → create transaction |
| GET | `/api/receipts` | List receipts |
| GET | `/api/receipts/{id}/image` | Serve a saved receipt image |
| DELETE | `/api/receipts/{id}` | Delete a receipt + its transactions + image |

## 🧠 How the pipeline works

1. **Scan:** camera/gallery/PDF → scanning animation → backend **auto-deskews** the photo (OpenCV finds the receipt's corners and perspective-corrects it into a straight document) → Tesseract extracts text → DeepSeek returns clean structured JSON (fixes "1674" → 16.74, "CORNERCAFE" → "Corner Cafe", sums items + tax when the total line is unreadable). You **confirm the total** (editable) before it's final.
2. **Ask:** your question + up to 200 real transactions sent to DeepSeek → a natural-language answer with matching items.
3. **Anomalies:** IQR detector flags outliers per category → DeepSeek reviews each candidate against category context (median/max) and confirms or rejects it with a reason.
4. **Dashboard:** aggregates real data, and DeepSeek writes a concise summary of your habits and month-over-month trends.

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

