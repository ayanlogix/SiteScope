# 🔭 SiteScope

**A professional-grade, browser-based Website Crawler, Technical SEO Auditor, and WebP Image Packer** — built with a Python backend and a fully responsive flat dark-matte UI.

---

## ✨ Features

### 1. 🔍 Site-Wide Crawl Scanner
- Recursively crawls internal pages up to configurable depth (1–3)
- Detects **broken hyperlinks** (404/5xx page links)
- Finds **broken images** (missing src, 404 images)
- Checks **missing or broken CSS/JS asset files**
- Scans for **PHP server errors**, **database exceptions**, and **duplicate HTML element IDs** leaked into page source

### 2. ✅ 10-Point Technical SEO & DOM Audit
Performs standardized technical checks on the target homepage:

| # | Check | What it Verifies |
|---|-------|-----------------|
| 1 | **Meta Description** | Present & non-empty |
| 2 | **Canonical Link Tag** | `rel="canonical"` defined |
| 3 | **Robots Indexing** | No `noindex` blocking directive |
| 4 | **Image Alt Text** | All `<img>` have alt attributes |
| 5 | **Insecure HTTP Links** | No hardcoded `http://` anchor links |
| 6 | **Unsafe External Tabs** | `target="_blank"` includes `rel="noopener"` |
| 7 | **Duplicate Title Tags** | Only one `<title>` per page |
| 8 | **Favicon & Apple Icons** | Favicon link tags present in `<head>` |
| 9 | **Iframe Titles** | All `<iframe>` have `title` attributes |
| 10 | **Empty Link Elements** | No anchor tags with empty text/alt |

### 3. 📦 WebP Image Packer
- Extracts all PNG/JPG images from the target site
- Converts them to **WebP format** (quality 80) in-memory using Pillow
- Shows **original size**, **WebP size**, and **% savings** per image
- Download a **ZIP file** containing all converted WebP images + an HTML audit report

---

## 🚀 Getting Started

### Requirements
- **Python 3.8+**
- Python packages: `requests`, `beautifulsoup4`, `Pillow`

Install dependencies:
```bash
pip install requests beautifulsoup4 Pillow
```

### Launch the App
Run the batch file included in the project:
```
run_server.bat
```
This starts the local Python backend on **port 8085** and opens your browser automatically.

Or manually:
```bash
python server.py
```
Then open `http://localhost:8085` in your browser.

---

## 🖥️ Interface Overview

```
┌─────────────────────────────────────────────────────────┐
│  SIDEBAR                 │  MAIN WORKSPACE              │
│  - Audit Studio logo     │  [URL Input] [Depth] [Scan]  │
│  - Crawl Scanner view    │                              │
│  - SEO & DOM Checklist   │  View A: Console + Issues    │
│  - Image WebP Packer     │  View B: 10-Point Accordion  │
│  - Backend status pill   │  View C: Image Table + ZIP   │
└─────────────────────────────────────────────────────────┘
```

**Mobile Responsive**: The sidebar collapses into a hamburger menu on screens under 992px.

---

## 🎨 Design System
- **Theme**: Flat dark-matte palette (no glassmorphism)
- **Colors**: Deep slate blues `#080c14` → `#12192c`, accent blue `#3b82f6`
- **Typography**: Inter (sans) + Fira Code (monospace)
- **Layout**: CSS Grid + Flexbox, mobile-first responsive

---

## 📁 Project Structure

```
dev-utility-suite/
├── index.html          # Main dashboard HTML shell
├── server.py           # Python HTTP backend (API endpoints)
├── run_server.bat      # Local launcher (Windows)
├── styles/
│   ├── main.css        # Global CSS design system
│   └── dashboard.css   # Component-level styles
└── js/
    ├── api.js          # Frontend API client module
    └── dashboard.js    # UI controller & renderer
```

---

## ⚙️ API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/crawl` | POST | Site-wide crawler — broken links, images, assets |
| `/api/seo-audit` | POST | 10-point SEO + DOM quality audit |
| `/api/extract-images` | POST | Image scraper + WebP conversion with size stats |
| `/api/download-zip` | POST | Packages WebP images + HTML report into ZIP |

---

## 📄 License
MIT License — Open to personal and commercial use.
