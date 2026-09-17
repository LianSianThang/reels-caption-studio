# 1GB VPS Production Hosting Guide

This guide walks you through deploying **Reel Caption Studio** on any Ubuntu/Debian cloud VPS (Hetzner, DigitalOcean, Linode, AWS Lightsail, etc.) with 1GB RAM.

---

## 1. Initial VPS Setup (Ubuntu 22.04 / 24.04 LTS)

SSH into your VPS as root:
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-pip python3-venv git ffmpeg nginx certbot python3-certbot-nginx
```

---

## 2. Clone / Upload Project Files

```bash
mkdir -p /var/www
cd /var/www
git clone <YOUR_REPO_URL> reels-caption-studio
cd /var/www/reels-caption-studio
```

---

## 3. Set Up Backend Virtual Environment

```bash
cd /var/www/reels-caption-studio/backend
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

Create `/var/www/reels-caption-studio/backend/.env`:
```ini
ENVIRONMENT=production
HOST=127.0.0.1
PORT=8000
ALLOWED_ORIGINS=*
TRUSTED_PROXIES=127.0.0.1,::1
ADMIN_ALLOWED_IPS=YOUR_HOME_IP,127.0.0.1
ADMIN_DEFAULT_EMAIL=admin@reels.ai
ADMIN_DEFAULT_PASSWORD=Admin@123456
MAX_UPLOAD_SIZE_MB=200
FFMPEG_THREADS=1
```
*(Replace `YOUR_HOME_IP` with your real public home/office IP so you can access the Admin Hub).*

---

## 4. Frontend (Two Options)

### Option A (Recommended for 1GB VPS — Zero Node.js Required):
Since your local machine already compiled the production build in `frontend/dist`, you can simply upload or commit `frontend/dist` with your project files.
FastAPI will detect `frontend/dist` and serve it automatically! You do **NOT** need to install Node.js or `npm` on the server at all.

### Option B (Build on VPS):
If you prefer building from source directly on your VPS:
```bash
sudo apt install -y nodejs npm
cd /var/www/reels-caption-studio/frontend
npm install
npm run build
```
*(Tip: On a 1GB VPS without swap, Option A is recommended to save memory and avoid npm build spikes).*

---

## 5. Enable Systemd Service

```bash
sudo cp /var/www/reels-caption-studio/deploy/reel-caption.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable reel-caption
sudo systemctl start reel-caption
sudo systemctl status reel-caption
```

---

## 6. Configure Nginx & Free SSL (Let's Encrypt)

```bash
sudo cp /var/www/reels-caption-studio/deploy/nginx.conf /etc/nginx/sites-available/reel-caption
sudo ln -s /etc/nginx/sites-available/reel-caption /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

Obtain automatic free SSL with Certbot for DuckDNS:
```bash
sudo certbot --nginx -d your-reels-tran.duckdns.org
```

---

## 7. First Login & Security

1. Visit `https://your-reels-tran.duckdns.org`
2. Click the shield icon or visit `https://your-reels-tran.duckdns.org/admin`
3. Log in with `admin@reels.ai` and `Admin@123456`
4. Under **"Admin Security & Password"**, immediately update your password to a strong personal password!
5. In **"Global Gemini API Key"**, configure your Gemini key once. It is now globally active for all users with the 3 video/day rate limit.

