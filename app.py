import os
import sqlite3
from datetime import datetime
from functools import wraps
from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, send_from_directory, session, abort, jsonify
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from PIL import Image

# ==================== CONFIG ====================
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "saurav-app-store-change-this-in-production-2026")

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
ICON_FOLDER = os.path.join(BASE_DIR, "static", "icons")
DATABASE = os.path.join(BASE_DIR, "store.db")

ALLOWED_EXTENSIONS = {"apk", "zip", "exe", "dmg", "msi", "deb", "AppImage", "ipa"}
ALLOWED_ICON_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(ICON_FOLDER, exist_ok=True)

# Change this password before deploying!
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "Saurav@123"   # ← CHANGE THIS!

# ==================== DATABASE ====================
def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS apps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            version TEXT DEFAULT '1.0',
            filename TEXT NOT NULL,
            icon TEXT,
            is_admin_only INTEGER DEFAULT 0,
            download_count INTEGER DEFAULT 0,
            created_at TEXT,
            updated_at TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS ratings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            app_id INTEGER NOT NULL,
            user_name TEXT NOT NULL,
            stars INTEGER NOT NULL CHECK(stars BETWEEN 1 AND 5),
            feedback TEXT,
            created_at TEXT,
            FOREIGN KEY (app_id) REFERENCES apps (id) ON DELETE CASCADE
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS admin (
            id INTEGER PRIMARY KEY,
            username TEXT UNIQUE,
            password_hash TEXT
        )
    """)

    # Create default admin if not exists
    c.execute("SELECT * FROM admin WHERE username = ?", (ADMIN_USERNAME,))
    if not c.fetchone():
        c.execute(
            "INSERT INTO admin (username, password_hash) VALUES (?, ?)",
            (ADMIN_USERNAME, generate_password_hash(ADMIN_PASSWORD))
        )

    conn.commit()
    conn.close()

init_db()
# ==================== HELPERS ====================
def allowed_file(filename, allowed):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("admin_logged_in"):
            flash("Please login as admin first.", "warning")
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return decorated

def get_avg_rating(app_id):
    conn = get_db()
    row = conn.execute(
        "SELECT AVG(stars) as avg, COUNT(*) as count FROM ratings WHERE app_id = ?",
        (app_id,)
    ).fetchone()
    conn.close()
    return {
        "average": round(row["avg"], 1) if row["avg"] else 0,
        "count": row["count"] or 0
    }

def resize_icon(path, size=(128, 128)):
    try:
        img = Image.open(path)
        img = img.convert("RGBA")
        img.thumbnail(size, Image.Resampling.LANCZOS)
        img.save(path, "PNG")
    except Exception:
        pass

# ==================== ROUTES ====================
@app.route("/")
def index():
    conn = get_db()
    is_admin = session.get("admin_logged_in", False)

    if is_admin:
        apps = conn.execute("SELECT * FROM apps ORDER BY created_at DESC").fetchall()
    else:
        apps = conn.execute(
            "SELECT * FROM apps WHERE is_admin_only = 0 ORDER BY created_at DESC"
        ).fetchall()

    app_list = []
    for a in apps:
        rating = get_avg_rating(a["id"])
        app_list.append({**dict(a), **rating})

    conn.close()
    return render_template("index.html", apps=app_list, is_admin=is_admin)


@app.route("/app/<int:app_id>")
def app_detail(app_id):
    conn = get_db()
    app_row = conn.execute("SELECT * FROM apps WHERE id = ?", (app_id,)).fetchone()

    if not app_row:
        conn.close()
        abort(404)

    # Hide admin-only apps from normal users
    if app_row["is_admin_only"] and not session.get("admin_logged_in"):
        conn.close()
        abort(403)

    ratings = conn.execute(
        "SELECT * FROM ratings WHERE app_id = ? ORDER BY created_at DESC",
        (app_id,)
    ).fetchall()

    rating_info = get_avg_rating(app_id)
    conn.close()

    return render_template(
        "app_detail.html",
        app=app_row,
        ratings=ratings,
        rating_info=rating_info,
        is_admin=session.get("admin_logged_in", False)
    )


@app.route("/download/<int:app_id>")
def download(app_id):
    conn = get_db()
    app_row = conn.execute("SELECT * FROM apps WHERE id = ?", (app_id,)).fetchone()

    if not app_row:
        conn.close()
        abort(404)

    if app_row["is_admin_only"] and not session.get("admin_logged_in"):
        conn.close()
        abort(403)

    # Increment download count
    conn.execute(
        "UPDATE apps SET download_count = download_count + 1 WHERE id = ?",
        (app_id,)
    )
    conn.commit()
    conn.close()

    return send_from_directory(
        UPLOAD_FOLDER,
        app_row["filename"],
        as_attachment=True,
        download_name=f"{app_row['name']}.{app_row['filename'].rsplit('.', 1)[-1]}"
    )


@app.route("/rate/<int:app_id>", methods=["POST"])
def rate_app(app_id):
    name = request.form.get("user_name", "").strip()
    stars = request.form.get("stars")
    feedback = request.form.get("feedback", "").strip()

    if not name or not stars:
        flash("Name and rating are required.", "danger")
        return redirect(url_for("app_detail", app_id=app_id))

    try:
        stars = int(stars)
        if stars < 1 or stars > 5:
            raise ValueError
    except ValueError:
        flash("Invalid rating.", "danger")
        return redirect(url_for("app_detail", app_id=app_id))

    conn = get_db()
    # Check app exists and is public (or admin)
    app_row = conn.execute("SELECT * FROM apps WHERE id = ?", (app_id,)).fetchone()
    if not app_row or (app_row["is_admin_only"] and not session.get("admin_logged_in")):
        conn.close()
        abort(403)

    conn.execute(
        "INSERT INTO ratings (app_id, user_name, stars, feedback, created_at) VALUES (?, ?, ?, ?, ?)",
        (app_id, name, stars, feedback, datetime.utcnow().isoformat())
    )
    conn.commit()
    conn.close()

    flash("Thank you for your feedback!", "success")
    return redirect(url_for("app_detail", app_id=app_id))


# ==================== ADMIN ====================
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if session.get("admin_logged_in"):
        return redirect(url_for("admin_dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        conn = get_db()
        admin = conn.execute(
            "SELECT * FROM admin WHERE username = ?", (username,)
        ).fetchone()
        conn.close()

        if admin and check_password_hash(admin["password_hash"], password):
            session["admin_logged_in"] = True
            session["admin_username"] = username
            flash("Welcome Admin!", "success")
            return redirect(url_for("admin_dashboard"))
        else:
            flash("Invalid username or password.", "danger")

    return render_template("admin_login.html")


@app.route("/admin/logout")
def admin_logout():
    session.clear()
    flash("Logged out successfully.", "info")
    return redirect(url_for("index"))


@app.route("/admin")
@login_required
def admin_dashboard():
    conn = get_db()
    apps = conn.execute("SELECT * FROM apps ORDER BY created_at DESC").fetchall()
    total_downloads = conn.execute("SELECT SUM(download_count) FROM apps").fetchone()[0] or 0
    total_ratings = conn.execute("SELECT COUNT(*) FROM ratings").fetchone()[0]
    conn.close()

    return render_template(
        "admin_dashboard.html",
        apps=apps,
        total_apps=len(apps),
        total_downloads=total_downloads,
        total_ratings=total_ratings
    )


@app.route("/admin/add", methods=["GET", "POST"])
@login_required
def add_app():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        version = request.form.get("version", "1.0").strip()
        is_admin_only = 1 if request.form.get("is_admin_only") else 0

        file = request.files.get("app_file")
        icon = request.files.get("icon")

        if not name or not file or file.filename == "":
            flash("App name and file are required.", "danger")
            return redirect(url_for("add_app"))

        if not allowed_file(file.filename, ALLOWED_EXTENSIONS):
            flash("Invalid file type. Allowed: " + ", ".join(ALLOWED_EXTENSIONS), "danger")
            return redirect(url_for("add_app"))

        # Save app file
        filename = secure_filename(file.filename)
        # Make unique
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        filename = f"{timestamp}_{filename}"
        file.save(os.path.join(UPLOAD_FOLDER, filename))

        icon_name = None
        if icon and icon.filename and allowed_file(icon.filename, ALLOWED_ICON_EXTENSIONS):
            icon_name = f"{timestamp}_{secure_filename(icon.filename)}"
            icon_path = os.path.join(ICON_FOLDER, icon_name)
            icon.save(icon_path)
            resize_icon(icon_path)

        now = datetime.utcnow().isoformat()
        conn = get_db()
        conn.execute(
            """INSERT INTO apps 
               (name, description, version, filename, icon, is_admin_only, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (name, description, version, filename, icon_name, is_admin_only, now, now)
        )
        conn.commit()
        conn.close()

        flash(f"App '{name}' added successfully!", "success")
        return redirect(url_for("admin_dashboard"))

    return render_template("add_app.html")


@app.route("/admin/edit/<int:app_id>", methods=["GET", "POST"])
@login_required
def edit_app(app_id):
    conn = get_db()
    app_row = conn.execute("SELECT * FROM apps WHERE id = ?", (app_id,)).fetchone()

    if not app_row:
        conn.close()
        abort(404)

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        version = request.form.get("version", "1.0").strip()
        is_admin_only = 1 if request.form.get("is_admin_only") else 0

        if not name:
            flash("Name is required.", "danger")
            return redirect(url_for("edit_app", app_id=app_id))

        icon = request.files.get("icon")
        icon_name = app_row["icon"]

        if icon and icon.filename and allowed_file(icon.filename, ALLOWED_ICON_EXTENSIONS):
            # Delete old icon
            if icon_name:
                old_path = os.path.join(ICON_FOLDER, icon_name)
                if os.path.exists(old_path):
                    os.remove(old_path)

            timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
            icon_name = f"{timestamp}_{secure_filename(icon.filename)}"
            icon_path = os.path.join(ICON_FOLDER, icon_name)
            icon.save(icon_path)
            resize_icon(icon_path)

        # Optional new file
        file = request.files.get("app_file")
        filename = app_row["filename"]
        if file and file.filename and allowed_file(file.filename, ALLOWED_EXTENSIONS):
            # Delete old file
            old_file = os.path.join(UPLOAD_FOLDER, filename)
            if os.path.exists(old_file):
                os.remove(old_file)

            timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
            filename = f"{timestamp}_{secure_filename(file.filename)}"
            file.save(os.path.join(UPLOAD_FOLDER, filename))

        now = datetime.utcnow().isoformat()
        conn.execute(
            """UPDATE apps SET name=?, description=?, version=?, filename=?, icon=?,
               is_admin_only=?, updated_at=? WHERE id=?""",
            (name, description, version, filename, icon_name, is_admin_only, now, app_id)
        )
        conn.commit()
        conn.close()

        flash("App updated successfully!", "success")
        return redirect(url_for("admin_dashboard"))

    conn.close()
    return render_template("edit_app.html", app=app_row)


@app.route("/admin/delete/<int:app_id>", methods=["POST"])
@login_required
def delete_app(app_id):
    conn = get_db()
    app_row = conn.execute("SELECT * FROM apps WHERE id = ?", (app_id,)).fetchone()

    if app_row:
        # Delete files
        if app_row["filename"]:
            path = os.path.join(UPLOAD_FOLDER, app_row["filename"])
            if os.path.exists(path):
                os.remove(path)
        if app_row["icon"]:
            path = os.path.join(ICON_FOLDER, app_row["icon"])
            if os.path.exists(path):
                os.remove(path)

        conn.execute("DELETE FROM ratings WHERE app_id = ?", (app_id,))
        conn.execute("DELETE FROM apps WHERE id = ?", (app_id,))
        conn.commit()
        flash("App deleted.", "info")

    conn.close()
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/delete_rating/<int:rating_id>", methods=["POST"])
@login_required
def delete_rating(rating_id):
    conn = get_db()
    rating = conn.execute("SELECT app_id FROM ratings WHERE id = ?", (rating_id,)).fetchone()
    if rating:
        conn.execute("DELETE FROM ratings WHERE id = ?", (rating_id,))
        conn.commit()
        flash("Rating deleted.", "info")
        conn.close()
        return redirect(url_for("app_detail", app_id=rating["app_id"]))
    conn.close()
    return redirect(url_for("admin_dashboard"))


# ==================== START ====================
if __name__ == "__main__":
    init_db()
    print("=" * 50)
    print("  Saurav App Store is running!")
    print("  Open: http://127.0.0.1:5000")
    print("  Admin: /admin/login")
    print(f"  Username: {ADMIN_USERNAME}")
    print(f"  Password: {ADMIN_PASSWORD}")
    print("=" * 50)
    app.run(debug=True, host="0.0.0.0", port=5000)
