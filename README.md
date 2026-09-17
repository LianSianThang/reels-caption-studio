# 🎬 Reel Caption Studio

> **AI-Powered Short-Form Video Translation & Viral Caption Studio**  
> Tailored specifically for TikTok, Instagram Reels, and YouTube Shorts with complex font shaping for Burmese (Unicode) and viral animated karaoke styles.

[![Live Demo](https://img.shields.io/badge/Live%20Demo-your--reels--tran.duckdns.org-blue?style=for-the-badge&logo=google-chrome)](https://your-reels-tran.duckdns.org)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/Frontend-React%20%2B%20Vite-61DAFB?style=for-the-badge&logo=react)](https://vitejs.dev/)
[![TailwindCSS](https://img.shields.io/badge/UI-Tailwind%20CSS-38B2AC?style=for-the-badge&logo=tailwind-css)](https://tailwindcss.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)

---

## 🌟 Overview

Content creators and video editors often spend hours transcribing audio, translating dialogue, and fixing broken fonts when styling non-Latin scripts (like Burmese) in Premiere Pro or CapCut.

**Reel Caption Studio** automates the entire workflow:
1. **Listens & Transcribes**: Extracts audio and produces timestamps with word-level accuracy.
2. **Translates Colloquially**: Translates into natural, spoken conversational Burmese using Gemini 2.5 Flash.
3. **Flawless Font Shaping**: Uses **HarfBuzz + FreeType** to guarantee that Burmese consonants, subscript stacks (*yapint*, *yahat*), and tall vowels never clip, detach, or break across lines.
4. **Viral Animated Subtitles**: Renders animated, trendy word-by-word Karaoke captions directly into vertical videos (MP4) or exports .srt / .ass files.
5. **1GB VPS Optimized**: Consumes **< 70MB RAM** under production load!

---

## ✨ Key Features

* 🎙️ **Speech-to-Text**: Whisper (via Groq) & Gemini Flash for lightning-fast, highly accurate multi-lingual audio transcription.
* 🇲🇲 **Syllable-Aware Burmese Text Engine**: Custom syllable segmenter prevents breaking syllables across subtitle wraps and lines.
* 🎨 **Viral Reel Styling**:
  * Karaoke word-by-word active glow & color highlight
  * Heavy outlines & drop shadows for maximum contrast on dynamic video backgrounds
  * Multi-font support (Padauk, Noto Sans Myanmar, Pyidaungsu, MMRText)
* 📱 **Interactive Real-Time Preview**: 9:16 mobile frame player with instant text editing, timing adjustments, and font customization.
* 📥 **YouTube Shorts & Direct Video Import**: Paste a YouTube Short link or drag-and-drop any .mp4, .mov, or .webm up to 200MB.
* 🛡️ **Enterprise-Grade Security Hardening**:
  * In-memory sliding-window rate limiting (prevents brute-force logins and registration spam)
  * Daily quota system (3 videos/day per user)
  * Anti-SSRF protection for YouTube URL importers
  * Path traversal defense with strict filename sanitization
  * Dedicated Admin Hub with IP whitelisting
* ⚡ **Ultra-Low Memory Footprint**: Runs comfortably on a \/mo 1GB Cloud VPS (Vultr, Hetzner, DigitalOcean) with 500MB+ RAM to spare.

---

## 🛠️ Tech Stack

### Backend
* **Python 3.10+ / FastAPI** — Asynchronous web framework
* **HarfBuzz (uharfbuzz) & FreeType** — Native font shaping and glyph rendering
* **FFmpeg** — Stream extraction, frame inspection, and hardware-efficient subtitle burning
* **SQLite / aiosqlite** — Embedded, zero-maintenance database
* **PyJWT & Passlib** — Secure authentication and PBKDF2 hashing

### Frontend
* **React 18 & TypeScript** — Type-safe component architecture
* **Vite** — Lightning-fast build tool
* **Tailwind CSS** — Modern dark-mode creator UI
* **Lucide Icons** — Crisp, clean visual design

---

## 🚀 Quickstart (Local Development)

### 1. Clone the repository
`ash
git clone https://github.com/LianSianThang/reels-caption-studio.git
cd reels-caption-studio
`

### 2. Backend Setup
`ash
cd backend
python -m venv .venv
# On Linux/macOS:
source .venv/bin/activate
# On Windows:
.venv\Scripts\activate

pip install -r requirements.txt
`

Create ackend/.env:
`ini
ENVIRONMENT=development
HOST=127.0.0.1
PORT=8000
ALLOWED_ORIGINS=*
ADMIN_ALLOWED_IPS=127.0.0.1,::1
ADMIN_DEFAULT_EMAIL=admin@reels.ai
ADMIN_DEFAULT_PASSWORD=Admin@123456
`

Start the backend:
`ash
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
`

### 3. Frontend Setup
`ash
cd ../frontend
npm install
npm run dev
`
Open http://localhost:5173 in your browser.

---

## 🌐 Production Hosting (1GB VPS)

For a complete step-by-step production deployment guide with Nginx, Systemd, and free Let's Encrypt SSL, check out:
👉 **[deploy/HOSTING_GUIDE.md](deploy/HOSTING_GUIDE.md)**

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
