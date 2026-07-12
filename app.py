import json
import os
from datetime import datetime
from functools import wraps

from flask import Flask, jsonify, redirect, render_template, request, session, url_for
from werkzeug.utils import secure_filename

import firebase_admin
from firebase_admin import credentials, firestore

from config import Config
from ai_service import analyze_crop_disease
from treatment_db import init_treatment_db, get_treatment_guidance

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

# -----------------------------
# Firebase Initialization
# -----------------------------
firebase_creds_json = os.environ.get("FIREBASE_CREDENTIALS")
if firebase_creds_json:
    try:
        creds_dict = json.loads(firebase_creds_json)
        cred = credentials.Certificate(creds_dict)
        firebase_admin.initialize_app(cred)
    except Exception as e:
        print(f"Failed to initialize Firebase with environment variable credentials: {e}")
        firebase_admin.initialize_app()
else:
    cred_path = os.path.join(os.path.dirname(__file__), "serviceAccountKey.json")
    if os.path.exists(cred_path):
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
    else:
        try:
            firebase_admin.initialize_app()
        except ValueError:
            pass

def get_db():
    try:
        return firestore.client()
    except Exception as e:
        print(f"Error: Failed to initialize firestore client: {e}")
        return None


def init_db():
    try:
        client = get_db()
        if client is None:
            print("Warning: Firestore client is not initialized.")
            return
        users_ref = client.collection("users")
        admin_doc = users_ref.document("admin").get()
        if not admin_doc.exists:
            users_ref.document("admin").set({
                "username": "admin",
                "email": "admin@cropdisease.com",
                "password": "crop123",
                "created_at": datetime.utcnow().isoformat()
            })
    except Exception as e:
        print(f"Warning: Failed to seed admin user: {e}")


def save_prediction(filename, result):
    try:
        client = get_db()
        if client is None:
            print("Warning: Firestore client is not initialized. Cannot save prediction.")
            return
        client.collection("predictions").add({
            "filename": filename,
            "result_json": json.dumps(result),
            "created_at": datetime.utcnow().isoformat()
        })
    except Exception as e:
        print(f"Failed to save prediction: {e}")


init_db()
init_treatment_db()


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

        # 1. Save to Firestore database
        try:
            client = get_db()
            if client is None:
                raise RuntimeError("Database client not available.")
            client.collection("contact_messages").add({
                "name": name,
                "email": email,
                "message": message,
                "created_at": datetime.utcnow().isoformat()
            })
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

        try:
            client = get_db()
            if client is None:
                raise RuntimeError("Database client not available.")
            users_ref = client.collection("users")
            user = None
            if "@" in username_or_email:
                # 1. Try matching by email
                docs = users_ref.where("email", "==", username_or_email).get()
                for doc in docs:
                    u_data = doc.to_dict()
                    if u_data.get("password") == password:
                        user = u_data
                        break

            if not user:
                # 2. Try matching by username
                docs = users_ref.where("username", "==", username_or_email).get()
                for doc in docs:
                    u_data = doc.to_dict()
                    if u_data.get("password") == password:
                        user = u_data
                        break
        except Exception as e:
            print(f"Login database error: {e}")
            user = None

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

        try:
            client = get_db()
            if client is None:
                raise RuntimeError("Database client not available.")
            users_ref = client.collection("users")
            
            # Check by username or email
            existing_username = users_ref.where("username", "==", username).get()
            existing_email = users_ref.where("email", "==", email).get()

            if existing_username or existing_email:
                return render_template("signup.html", error_message="Username or email already exists.")

            users_ref.document(username).set({
                "username": username,
                "email": email,
                "password": password,
                "created_at": datetime.utcnow().isoformat(),
            })
        except Exception as e:
            print(f"Signup database error: {e}")
            return render_template("signup.html", error_message="An error occurred during sign up. Please try again.")

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
    try:
        client = get_db()
        if client is None:
            raise RuntimeError("Database client not available.")
        doc = client.collection("users").document(username).get()
        user = doc.to_dict() if doc.exists else None
    except Exception as e:
        print(f"Profile retrieval error: {e}")
        user = None
    return render_template("profile.html", user=user)


@app.route("/history")
@login_required
def history():
    try:
        client = get_db()
        if client is None:
            raise RuntimeError("Database client not available.")
        predictions_ref = client.collection("predictions")
        docs = predictions_ref.order_by("created_at", direction=firestore.Query.DESCENDING).get()
        
        history_items = []
        for doc in docs:
            row = doc.to_dict()
            history_items.append({
                "id": doc.id,
                "filename": row["filename"],
                "result": json.loads(row["result_json"]),
                "created_at": row["created_at"],
            })
    except Exception as e:
        print(f"History retrieval error: {e}")
        history_items = []

    return render_template("history.html", history_items=history_items)


@app.route("/history/delete/<string:history_id>", methods=["POST"])
@login_required
def delete_history(history_id):
    try:
        client = get_db()
        if client is None:
            raise RuntimeError("Database client not available.")
        client.collection("predictions").document(history_id).delete()
    except Exception as e:
        print(f"Failed to delete prediction history: {e}")

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

        # Retrieve treatment guidance from database
        treatment_info = get_treatment_guidance(result.get("crop_name"), result.get("disease_name"))

        return jsonify({
            "success": True,
            "result": result,
            "treatment_guidance": treatment_info
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