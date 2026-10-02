# 🛒 Saurav App Store

A simple, clean, free App Store like Google Play Store — built just for you.

## Features

✅ **Free apps for everyone** — Anyone can visit and download  
✅ **Admin-only apps** — Some apps visible only to you (the admin)  
✅ **Add apps with description, version & icon**  
✅ **Star ratings + feedback** that stay forever  
✅ **Only admin can upload** — Users can only download  
✅ **Simple & user-friendly** — No complicated categories  
✅ **Easily shareable** — Just share the website link  

---

## Quick Start (Local)

### 1. Install Python packages
```bash
cd saurav_app_store
pip install -r requirements.txt
```

### 2. Run the store
```bash
python app.py
```

### 3. Open in browser
```
http://127.0.0.1:5000
```

### Admin Login
- **URL**: http://127.0.0.1:5000/admin/login  
- **Username**: `admin`  
- **Password**: `Saurav@123`  

> ⚠️ **Important**: Change the password in `app.py` (line ~25) before sharing publicly!

---

## How to Use

### As Admin
1. Login at `/admin/login`
2. Click **Add New App**
3. Fill name, description, version
4. Upload the APK / ZIP / EXE file
5. Optionally upload an icon
6. Check “Admin Only” if you want it hidden from public
7. Click Upload

### As Visitor
1. Open the store link
2. Browse free public apps
3. Click **Details** → Rate & leave feedback
4. Click **Download** to get the file

---

## Deploy Online (Free Options)

### Option A: Render.com (Recommended)
1. Create account at [render.com](https://render.com)
2. New → Web Service
3. Connect your GitHub repo (or upload the folder)
4. Settings:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:app`
5. Add environment variable: `SECRET_KEY=any-random-string`
6. Deploy → Get a public URL like `https://saurav-app-store.onrender.com`

### Option B: Railway.app / PythonAnywhere / Fly.io
Similar process — just point to `app.py` and use gunicorn.

### Option C: Share via Local Network
```bash
python app.py
```
Then share `http://YOUR-COMPUTER-IP:5000` with people on the same Wi-Fi.

---

## Folder Structure
```
saurav_app_store/
├── app.py                 ← Main application
├── requirements.txt
├── store.db               ← Created automatically (SQLite)
├── static/
│   ├── css/style.css
│   ├── icons/             ← App icons
│   └── uploads/           ← App files (APK etc.)
└── templates/             ← HTML pages
```

---

## Security Notes
- Change `ADMIN_PASSWORD` and `SECRET_KEY` before going public
- The store uses SQLite (perfect for small-medium use)
- Files are stored on the server — make sure you have enough disk space
- For production, consider adding HTTPS (most free hosts do this automatically)

---

## Need Help?
Just ask! You can request more features like:
- Search bar
- Categories
- Download history
- Better analytics
- Dark mode

Enjoy your **Saurav App Store**! 🚀
