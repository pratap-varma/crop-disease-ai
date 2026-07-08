import json
import os
import sqlite3
from datetime import datetime
from functools import wraps

from flask import Flask, jsonify, redirect, render_template, request, session, url_for
from werkzeug.utils import secure_filename

from config import Config
from ai_service import analyze_crop_disease

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "crop-disease-secret-key")

# -----------------------------
# Configuration
# -----------------------------
if os.environ.get("VERCEL"):
    app.config["UPLOAD_FOLDER"] = "/tmp"
else:
    app.config["UPLOAD_FOLDER"] = Config.UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = Config.MAX_CONTENT_LENGTH

# Create upload folder if it doesn't exist
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

DB_NAME = "crop_disease.db"
if os.environ.get("VERCEL"):
    DB_PATH = os.path.join("/tmp", DB_NAME)
else:
    DB_PATH = os.path.join(os.path.dirname(__file__), DB_NAME)


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                result_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                email TEXT UNIQUE,
                password TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS contact_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        # Migrate existing DB: add email column if it doesn't exist
        try:
            conn.execute("ALTER TABLE users ADD COLUMN email TEXT")
        except sqlite3.OperationalError:
            # Column already exists
            pass

        conn.execute(
            "INSERT OR IGNORE INTO users (username, email, password, created_at) VALUES (?, ?, ?, ?)",
            ("admin", "admin@cropdisease.com", "crop123", datetime.utcnow().isoformat()),
        )
        conn.execute(
            "UPDATE users SET email = ? WHERE username = ? AND email IS NULL",
            ("admin@cropdisease.com", "admin")
        )
        conn.commit()


def save_prediction(filename, result):
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO predictions (filename, result_json, created_at)
            VALUES (?, ?, ?)
            """,
            (filename, json.dumps(result), datetime.utcnow().isoformat()),
        )
        conn.commit()


init_db()


# -----------------------------
# Helper Function
# -----------------------------
def allowed_file(filename):
    return (
        "." in filename and
        filename.rsplit(".", 1)[1].lower() in Config.ALLOWED_EXTENSIONS
    )


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)

    return decorated_function


# -----------------------------
# Routes
# -----------------------------
@app.route("/")
def home():
    return render_template("index.html")


@app.route("/detect")
@login_required
def detect():
    return render_template("detect.html")


@app.route("/about")
@login_required
def about():
    return render_template("about.html")


@app.route("/awareness")
@login_required
def awareness():
    return render_template("awareness.html")


def send_contact_email(name, email_address, message_body):
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    # Check if SMTP configuration exists
    if not Config.SMTP_SERVER or not Config.SMTP_USERNAME or not Config.SMTP_PASSWORD or not Config.RECIPIENT_EMAIL:
        print("SMTP settings are not configured. Message will not be emailed but is saved in the database.")
        return False

    try:
        # Create message container
        msg = MIMEMultipart()
        msg['From'] = Config.SMTP_USERNAME
        msg['To'] = Config.RECIPIENT_EMAIL
        msg['Subject'] = f"New Contact Form Submission from {name}"

        # Email body content
        body = f"You have received a new message from your website contact form.\n\nDetails:\nName: {name}\nEmail: {email_address}\nMessage:\n{message_body}"
        msg.attach(MIMEText(body, 'plain'))

        # Connect to server
        server = smtplib.SMTP(Config.SMTP_SERVER, Config.SMTP_PORT)
        server.starttls()
        server.login(Config.SMTP_USERNAME, Config.SMTP_PASSWORD)
        server.sendmail(Config.SMTP_USERNAME, Config.RECIPIENT_EMAIL, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"Failed to send email via SMTP: {e}")
        return False


@app.route("/contact", methods=["GET", "POST"])
@login_required
def contact():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        message = request.form.get("message", "").strip()

        if not name or not email or not message:
            return render_template("contact.html", error_message="All fields are required.")

        # 1. Save to SQLite database
        try:
            with get_db() as conn:
                conn.execute(
                    "INSERT INTO contact_messages (name, email, message, created_at) VALUES (?, ?, ?, ?)",
                    (name, email, message, datetime.utcnow().isoformat())
                )
                conn.commit()
        except Exception as e:
            print(f"Failed to save contact message to database: {e}")
            return render_template("contact.html", error_message="An error occurred saving your message. Please try again.")

        # 2. Attempt to send email
        email_sent = send_contact_email(name, email, message)

        if email_sent:
            return render_template("contact.html", success_message="Thank you! Your message has been sent successfully.")
        else:
            return render_template("contact.html", success_message="Thank you! Your message has been received and saved successfully (email delivery pending).")

    return render_template("contact.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username_or_email = request.form.get("username_or_email", "").strip()
        password = request.form.get("password", "").strip()

        with get_db() as conn:
            user = None
            if "@" in username_or_email:
                # 1. Try matching by email
                u = conn.execute(
                    "SELECT id, username, password FROM users WHERE email = ?",
                    (username_or_email,),
                ).fetchone()
                if u and password == u["password"]:
                    user = u

            if not user:
                # 2. Try matching by username
                u = conn.execute(
                    "SELECT id, username, password FROM users WHERE username = ?",
                    (username_or_email,),
                ).fetchone()
                if u and password == u["password"]:
                    user = u

        if user:
            session["logged_in"] = True
            session["username"] = user["username"]
            return redirect(url_for("detect"))

        return render_template("login.html", error_message="Invalid username/email or password.")

    return render_template("login.html")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()

        if not username or not email or not password:
            return render_template("signup.html", error_message="Username, email and password are required.")

        with get_db() as conn:
            existing_user = conn.execute(
                "SELECT id FROM users WHERE username = ? OR email = ? OR username = ? OR email = ?",
                (username, username, email, email),
            ).fetchone()

            if existing_user:
                return render_template("signup.html", error_message="Username or email already exists.")

            conn.execute(
                "INSERT INTO users (username, email, password, created_at) VALUES (?, ?, ?, ?)",
                (username, email, password, datetime.utcnow().isoformat()),
            )
            conn.commit()

        session["logged_in"] = True
        session["username"] = username
        return redirect(url_for("detect"))

    return render_template("signup.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/profile")
@login_required
def profile():
    username = session.get("username")
    with get_db() as conn:
        user = conn.execute(
            "SELECT id, username, email, created_at FROM users WHERE username = ?",
            (username,),
        ).fetchone()
    return render_template("profile.html", user=user)


@app.route("/history")
@login_required
def history():
    with get_db() as conn:
        predictions = conn.execute(
            "SELECT id, filename, result_json, created_at FROM predictions ORDER BY id DESC"
        ).fetchall()

    history_items = []
    for row in predictions:
        history_items.append({
            "id": row["id"],
            "filename": row["filename"],
            "result": json.loads(row["result_json"]),
            "created_at": row["created_at"],
        })

    return render_template("history.html", history_items=history_items)


@app.route("/history/delete/<int:history_id>", methods=["POST"])
@login_required
def delete_history(history_id):
    with get_db() as conn:
        conn.execute("DELETE FROM predictions WHERE id = ?", (history_id,))
        conn.commit()

    return redirect(url_for("history"))


# -----------------------------
# AI Prediction Route
# -----------------------------
@app.route("/predict", methods=["POST"])
def predict():

    # Check image exists
    if "image" not in request.files:
        return jsonify({
            "success": False,
            "message": "No image uploaded."
        }), 400

    file = request.files["image"]

    # Empty filename
    if file.filename == "":
        return jsonify({
            "success": False,
            "message": "Please select an image."
        }), 400

    # Invalid extension
    if not allowed_file(file.filename):
        return jsonify({
            "success": False,
            "message": "Only JPG, JPEG and PNG images are allowed."
        }), 400

    filename = secure_filename(file.filename)

    filepath = os.path.join(
        app.config["UPLOAD_FOLDER"],
        filename
    )

    try:
        # Save uploaded image
        file.save(filepath)

        # Analyze using Gemini
        result = analyze_crop_disease(filepath)
        save_prediction(filename, result)

        return jsonify({
            "success": True,
            "result": result
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "message": str(e)
        }), 500

    finally:

        # Delete uploaded image
        if os.path.exists(filepath):
            os.remove(filepath)


# -----------------------------
# Error Handlers
# -----------------------------
@app.errorhandler(404)
def page_not_found(error):
    return "<h1>404 - Page Not Found</h1>", 404


@app.errorhandler(413)
def file_too_large(error):
    return jsonify({
        "success": False,
        "message": "Image size must be less than 10 MB."
    }), 413


@app.errorhandler(500)
def internal_server_error(error):
    return jsonify({
        "success": False,
        "message": "Internal Server Error"
    }), 500


# -----------------------------
# Run Application
# -----------------------------
if __name__ == "__main__":
    app.run(
        debug=True,
        host="0.0.0.0",
        port=5000
    )