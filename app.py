import json
import os
import uuid
from datetime import datetime
from functools import wraps

from flask import Flask, jsonify, redirect, render_template, request, session, url_for, send_from_directory
from werkzeug.utils import secure_filename

import firebase_admin
from firebase_admin import credentials, firestore

from config import Config
from ai_service import analyze_crop_disease
from treatment_db import init_treatment_db, get_treatment_guidance, get_all_treatments_raw, save_treatment_record, delete_treatment_record

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


@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

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
            result = json.loads(row["result_json"])
            treatment_guidance = get_treatment_guidance(result.get("crop_name"), result.get("disease_name"))
            history_items.append({
                "id": doc.id,
                "filename": row["filename"],
                "result": result,
                "treatment_guidance": treatment_guidance,
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
        doc_ref = client.collection("predictions").document(history_id)
        doc = doc_ref.get()
        if doc.exists:
            filename = doc.to_dict().get("filename")
            if filename:
                filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                if os.path.exists(filepath):
                    try:
                        os.remove(filepath)
                    except Exception as fe:
                        print(f"Failed to remove file {filepath}: {fe}")
        doc_ref.delete()
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

    # Generate unique filename to prevent collisions in history
    ext = os.path.splitext(file.filename)[1]
    filename = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex}{ext}"
    filename = secure_filename(filename)

    filepath = os.path.join(
        app.config["UPLOAD_FOLDER"],
        filename
    )

    try:
        # Save uploaded image
        file.save(filepath)

        # Analyze using Gemini
        result = analyze_crop_disease(filepath)

        # Validate image clarity and plant presence
        if not result.get("is_clear", True):
            # Delete uploaded image to save space
            if os.path.exists(filepath):
                os.remove(filepath)
            return jsonify({
                "success": False,
                "message": result.get("additional_notes") or "The uploaded image is blurry, unclear, or improper. Please upload a clear, high-quality close-up of the crop leaf."
            }), 400

        save_prediction(filename, result)

        # Retrieve treatment guidance from database
        treatment_info = get_treatment_guidance(result.get("crop_name"), result.get("disease_name"))
        if not treatment_info and result.get("crop_name") not in [None, "", "Unknown"] and result.get("disease_name") not in [None, "", "Unable to Detect", "Error"]:
            try:
                from ai_service import generate_treatment_guidance_ai
                generated_data = generate_treatment_guidance_ai(result.get("crop_name"), result.get("disease_name"))
                if generated_data:
                    ok, res_id = save_treatment_record(generated_data)
                    if ok:
                        treatment_info = get_treatment_guidance(result.get("crop_name"), result.get("disease_name"))
            except Exception as ge:
                print(f"Failed to auto-generate treatment record on prediction: {ge}")

        return jsonify({
            "success": True,
            "result": result,
            "filename": filename,
            "treatment_guidance": treatment_info
        })

    except Exception as e:
        # Delete uploaded image on failure to save space
        if os.path.exists(filepath):
            os.remove(filepath)

        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


# -----------------------------
# Admin Management Functions
# -----------------------------
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("logged_in") or session.get("username") != "admin":
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function


@app.route("/admin/treatments")
@admin_required
def admin_treatments():
    treatments = get_all_treatments_raw()
    return render_template("admin.html", treatments=treatments)


@app.route("/admin/treatments/save", methods=["POST"])
@admin_required
def save_treatment():
    def parse_textarea(field_name):
        text = request.form.get(field_name, "")
        return [line.strip() for line in text.split("\n") if line.strip()]

    cost_estimate_medicine = request.form.get("cost_estimate_medicine", "0")
    cost_estimate_labour = request.form.get("cost_estimate_labour", "0")
    cost_estimate_total = request.form.get("cost_estimate_total", "0")
    
    try:
        cost_medicine = float(cost_estimate_medicine) if cost_estimate_medicine else 0.0
    except ValueError:
        cost_medicine = 0.0
    try:
        cost_labour = float(cost_estimate_labour) if cost_estimate_labour else 0.0
    except ValueError:
        cost_labour = 0.0
    try:
        cost_total = float(cost_estimate_total) if cost_estimate_total else 0.0
    except ValueError:
        cost_total = 0.0

    data = {
        "id": request.form.get("id") if request.form.get("id") else None,
        "crop_name": request.form.get("crop_name", "").strip(),
        "disease_name": request.form.get("disease_name", "").strip(),
        "disease_type": request.form.get("disease_type", "Fungal").strip(),
        "verified": 1 if request.form.get("verified") else 0,
        "disabled": 1 if request.form.get("disabled") else 0,
        "organic_treatment_json": json.dumps(parse_textarea("organic_treatment")),
        "chemical_treatment_name": request.form.get("chemical_treatment_name", "").strip(),
        "active_ingredient": request.form.get("active_ingredient", "").strip(),
        "purpose": request.form.get("purpose", "").strip(),
        "example_brand_names": request.form.get("example_brand_names", "").strip(),
        "mixing_quantity": request.form.get("mixing_quantity", "").strip(),
        "water_quantity": request.form.get("water_quantity", "").strip(),
        "spray_tank_size": request.form.get("spray_tank_size", "").strip(),
        "mixing_steps_json": json.dumps(parse_textarea("mixing_steps")),
        "application_method": request.form.get("application_method", "Foliar Spray").strip(),
        "where_to_spray_json": json.dumps(parse_textarea("where_to_spray")),
        "spray_timing": request.form.get("spray_timing", "").strip(),
        "spray_interval": request.form.get("spray_interval", "").strip(),
        "number_of_applications": int(request.form.get("number_of_applications") or 3),
        "precautions_json": json.dumps(parse_textarea("precautions")),
        "ppe_required": request.form.get("ppe_required", "").strip(),
        "waiting_period_before_harvest": request.form.get("waiting_period_before_harvest", "").strip(),
        "cost_estimate_medicine": cost_medicine,
        "cost_estimate_labour": cost_labour,
        "cost_estimate_total": cost_total,
        "alternative_organic_solutions": request.form.get("alternative_organic_solutions", "").strip(),
        "government_advisory_source": request.form.get("government_advisory_source", "").strip(),
        "last_updated_date": datetime.utcnow().strftime("%Y-%m-%d"),
        "country": request.form.get("country", "India").strip(),
        "state_or_region": request.form.get("state_or_region", "All").strip()
    }
    
    ok, res = save_treatment_record(data)
    if ok:
        return redirect(url_for("admin_treatments"))
    else:
        return f"Error saving treatment record: {res}", 500


@app.route("/admin/treatments/delete/<string:treatment_id>", methods=["POST"])
@admin_required
def delete_treatment(treatment_id):
    if delete_treatment_record(treatment_id):
        return redirect(url_for("admin_treatments"))
    return "Error deleting treatment record", 500


@app.route("/admin/treatments/toggle-verify/<string:treatment_id>", methods=["POST"])
@admin_required
def toggle_verify(treatment_id):
    rows = get_all_treatments_raw()
    found = None
    for r in rows:
        if r["id"] == treatment_id:
            found = r
            break
    if not found:
        return "Record not found", 404
        
    data = {
        "id": found["id"],
        "crop_name": found["crop_name"],
        "disease_name": found["disease_name"],
        "disease_type": found["disease_type"],
        "verified": 0 if found["verified"] == 1 else 1,
        "disabled": found["disabled"],
        "organic_treatment_json": found["organic_treatment_json"],
        "chemical_treatment_name": found["chemical_treatment_name"],
        "active_ingredient": found["active_ingredient"],
        "purpose": found["purpose"],
        "example_brand_names": found["example_brand_names"],
        "mixing_quantity": found["mixing_quantity"],
        "water_quantity": found["water_quantity"],
        "spray_tank_size": found["spray_tank_size"],
        "mixing_steps_json": found["mixing_steps_json"],
        "application_method": found["application_method"],
        "where_to_spray_json": found["where_to_spray_json"],
        "spray_timing": found["spray_timing"],
        "spray_interval": found["spray_interval"],
        "number_of_applications": found["number_of_applications"],
        "precautions_json": found["precautions_json"],
        "ppe_required": found["ppe_required"],
        "waiting_period_before_harvest": found["waiting_period_before_harvest"],
        "cost_estimate_medicine": found["cost_estimate_medicine"],
        "cost_estimate_labour": found["cost_estimate_labour"],
        "cost_estimate_total": found["cost_estimate_total"],
        "alternative_organic_solutions": found["alternative_organic_solutions"],
        "government_advisory_source": found["government_advisory_source"],
        "last_updated_date": datetime.utcnow().strftime("%Y-%m-%d"),
        "country": found["country"],
        "state_or_region": found["state_or_region"]
    }
    
    ok, res = save_treatment_record(data)
    if ok:
        return redirect(url_for("admin_treatments"))
    return "Error toggling verification", 500


@app.route("/admin/treatments/import", methods=["POST"])
@admin_required
def import_treatments():
    import csv
    if "file" not in request.files:
        return jsonify({"success": False, "message": "No file uploaded"}), 400
        
    file = request.files["file"]
    if not file or not file.filename:
        return jsonify({"success": False, "message": "Empty file uploaded"}), 400
        
    filename = file.filename.lower()
    success_count = 0
    duplicate_count = 0
    errors = []
    
    try:
        if filename.endswith(".json"):
            content = file.read().decode("utf-8")
            data_list = json.loads(content)
            if not isinstance(data_list, list):
                return jsonify({"success": False, "message": "JSON must be a list of objects"}), 400
                
            for idx, item in enumerate(data_list):
                crop_name = item.get("crop_name", "").strip()
                disease_name = item.get("disease_name", "").strip()
                if not crop_name or not disease_name:
                    errors.append(f"Row {idx+1}: Missing crop_name or disease_name")
                    continue
                
                guidance = get_treatment_guidance(crop_name, disease_name)
                if guidance:
                    duplicate_count += 1
                    continue
                
                record_data = {
                    "crop_name": crop_name,
                    "disease_name": disease_name,
                    "disease_type": item.get("disease_type", "Fungal"),
                    "organic_treatment_json": json.dumps(item.get("organic_treatment", [])),
                    "chemical_treatment_name": item.get("chemical_treatment_name", ""),
                    "active_ingredient": item.get("active_ingredient", ""),
                    "purpose": item.get("purpose", ""),
                    "example_brand_names": item.get("example_brand_names", ""),
                    "application_method": item.get("application_method", "Foliar Spray"),
                    "mixing_quantity": item.get("mixing_quantity", ""),
                    "water_quantity": item.get("water_quantity", ""),
                    "spray_tank_size": item.get("spray_tank_size", ""),
                    "mixing_steps_json": json.dumps(item.get("mixing_steps", [])),
                    "spray_timing": item.get("spray_timing", ""),
                    "spray_interval": item.get("spray_interval", ""),
                    "number_of_applications": int(item.get("number_of_applications") or 3),
                    "where_to_spray_json": json.dumps(item.get("where_to_spray", [])),
                    "precautions_json": json.dumps(item.get("precautions", [])),
                    "ppe_required": item.get("ppe_required", ""),
                    "waiting_period_before_harvest": item.get("waiting_period_before_harvest", ""),
                    "cost_estimate_medicine": float(item.get("cost_estimate_medicine") or 0),
                    "cost_estimate_labour": float(item.get("cost_estimate_labour") or 0),
                    "cost_estimate_total": float(item.get("cost_estimate_total") or 0),
                    "alternative_organic_solutions": item.get("alternative_organic_solutions", ""),
                    "government_advisory_source": item.get("government_advisory_source", ""),
                    "last_updated_date": item.get("last_updated_date", datetime.utcnow().strftime("%Y-%m-%d")),
                    "verified": int(item.get("verified", 1)),
                    "disabled": int(item.get("disabled", 0)),
                    "country": item.get("country", "India"),
                    "state_or_region": item.get("state_or_region", "All")
                }
                
                ok, err = save_treatment_record(record_data)
                if ok:
                    success_count += 1
                else:
                    errors.append(f"Row {idx+1}: {err}")
                    
        elif filename.endswith(".csv"):
            import io
            stream = io.StringIO(file.read().decode("utf-8"), newline=None)
            reader = csv.DictReader(stream)
            for idx, row in enumerate(reader):
                crop_name = row.get("crop_name", "").strip()
                disease_name = row.get("disease_name", "").strip()
                if not crop_name or not disease_name:
                    errors.append(f"Row {idx+1}: Missing crop_name or disease_name")
                    continue
                
                guidance = get_treatment_guidance(crop_name, disease_name)
                if guidance:
                    duplicate_count += 1
                    continue
                
                def list_from_field(f):
                    val = row.get(f, "")
                    if not val:
                        return []
                    if val.startswith("[") and val.endswith("]"):
                        try:
                            return json.loads(val)
                        except Exception:
                            pass
                    return [x.strip() for x in val.replace("\r", "").split(";") if x.strip()]
                
                record_data = {
                    "crop_name": crop_name,
                    "disease_name": disease_name,
                    "disease_type": row.get("disease_type", "Fungal"),
                    "organic_treatment_json": json.dumps(list_from_field("organic_treatment")),
                    "chemical_treatment_name": row.get("chemical_treatment_name", ""),
                    "active_ingredient": row.get("active_ingredient", ""),
                    "purpose": row.get("purpose", ""),
                    "example_brand_names": row.get("example_brand_names", ""),
                    "application_method": row.get("application_method", "Foliar Spray"),
                    "mixing_quantity": row.get("mixing_quantity", ""),
                    "water_quantity": row.get("water_quantity", ""),
                    "spray_tank_size": row.get("spray_tank_size", ""),
                    "mixing_steps_json": json.dumps(list_from_field("mixing_steps")),
                    "spray_timing": row.get("spray_timing", ""),
                    "spray_interval": row.get("spray_interval", ""),
                    "number_of_applications": int(row.get("number_of_applications") or 3),
                    "where_to_spray_json": json.dumps(list_from_field("where_to_spray")),
                    "precautions_json": json.dumps(list_from_field("precautions")),
                    "ppe_required": row.get("ppe_required", ""),
                    "waiting_period_before_harvest": row.get("waiting_period_before_harvest", ""),
                    "cost_estimate_medicine": float(row.get("cost_estimate_medicine") or 0),
                    "cost_estimate_labour": float(row.get("cost_estimate_labour") or 0),
                    "cost_estimate_total": float(row.get("cost_estimate_total") or 0),
                    "alternative_organic_solutions": row.get("alternative_organic_solutions", ""),
                    "government_advisory_source": row.get("government_advisory_source", ""),
                    "last_updated_date": row.get("last_updated_date", datetime.utcnow().strftime("%Y-%m-%d")),
                    "verified": int(row.get("verified") if row.get("verified") is not None else 1),
                    "disabled": int(row.get("disabled") if row.get("disabled") is not None else 0),
                    "country": row.get("country", "India"),
                    "state_or_region": row.get("state_or_region", "All")
                }
                
                ok, err = save_treatment_record(record_data)
                if ok:
                    success_count += 1
                else:
                    errors.append(f"Row {idx+1}: {err}")
        else:
            return jsonify({"success": False, "message": "Unsupported file format"}), 400
            
        return jsonify({
            "success": True,
            "success_count": success_count,
            "duplicate_count": duplicate_count,
            "errors": errors
        })
    except Exception as e:
        return jsonify({"success": False, "message": f"Import failed: {str(e)}"}), 500


@app.route("/admin/treatments/export/<string:format_type>")
@admin_required
def export_treatments(format_type):
    rows = get_all_treatments_raw()
    
    if format_type == "json":
        export_data = []
        for r in rows:
            export_data.append({
                "crop_name": r["crop_name"],
                "disease_name": r["disease_name"],
                "disease_type": r["disease_type"],
                "organic_treatment": r["organic_treatment"],
                "chemical_treatment_name": r["chemical_treatment_name"],
                "active_ingredient": r["active_ingredient"],
                "purpose": r["purpose"],
                "example_brand_names": r["example_brand_names"],
                "application_method": r["application_method"],
                "mixing_quantity": r["mixing_quantity"],
                "water_quantity": r["water_quantity"],
                "spray_tank_size": r["spray_tank_size"],
                "mixing_steps": r["mixing_steps"],
                "spray_timing": r["spray_timing"],
                "spray_interval": r["spray_interval"],
                "number_of_applications": r["number_of_applications"],
                "where_to_spray": r["where_to_spray"],
                "precautions": r["precautions"],
                "ppe_required": r["ppe_required"],
                "waiting_period_before_harvest": r["waiting_period_before_harvest"],
                "cost_estimate_medicine": r["cost_estimate_medicine"],
                "cost_estimate_labour": r["cost_estimate_labour"],
                "cost_estimate_total": r["cost_estimate_total"],
                "alternative_organic_solutions": r["alternative_organic_solutions"],
                "government_advisory_source": r["government_advisory_source"],
                "last_updated_date": r["last_updated_date"],
                "verified": r["verified"],
                "disabled": r["disabled"],
                "country": r["country"],
                "state_or_region": r["state_or_region"]
            })
        
        response_body = json.dumps(export_data, indent=2)
        from flask import Response
        return Response(
            response_body,
            mimetype="application/json",
            headers={"Content-Disposition": "attachment;filename=treatments_export.json"}
        )
        
    elif format_type == "csv":
        import csv
        import io
        from flask import Response
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        headers = [
            "crop_name", "disease_name", "disease_type", "organic_treatment",
            "chemical_treatment_name", "active_ingredient", "purpose", "example_brand_names",
            "application_method", "mixing_quantity", "water_quantity", "spray_tank_size",
            "mixing_steps", "spray_timing", "spray_interval", "number_of_applications",
            "where_to_spray", "precautions", "ppe_required", "waiting_period_before_harvest",
            "cost_estimate_medicine", "cost_estimate_labour", "cost_estimate_total",
            "alternative_organic_solutions", "government_advisory_source", "last_updated_date",
            "verified", "disabled", "country", "state_or_region"
        ]
        writer.writerow(headers)
        
        for r in rows:
            def join_list(l):
                return ";".join(l) if isinstance(l, list) else ""
                
            writer.writerow([
                r["crop_name"], r["disease_name"], r["disease_type"], join_list(r["organic_treatment"]),
                r["chemical_treatment_name"], r["active_ingredient"], r["purpose"], r["example_brand_names"],
                r["application_method"], r["mixing_quantity"], r["water_quantity"], r["spray_tank_size"],
                join_list(r["mixing_steps"]), r["spray_timing"], r["spray_interval"], r["number_of_applications"],
                join_list(r["where_to_spray"]), join_list(r["precautions"]), r["ppe_required"], r["waiting_period_before_harvest"],
                r["cost_estimate_medicine"], r["cost_estimate_labour"], r["cost_estimate_total"],
                r["alternative_organic_solutions"], r["government_advisory_source"], r["last_updated_date"],
                r["verified"], r["disabled"], r["country"], r["state_or_region"]
            ])
            
        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment;filename=treatments_export.csv"}
        )
    else:
        return "Invalid export format", 400


# -----------------------------
# Error Handlers
# -----------------------------
# PDF Report Generation Route
# -----------------------------
@app.route("/generate-pdf", methods=["POST"])
def generate_pdf():
    import io
    from flask import send_file
    from pdf_generator import generate_pdf_report
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "message": "No data provided"}), 400
            
        username = session.get("username")
        pdf_bytes = generate_pdf_report(data, username=username)
        
        # Format filename: CropName_DiseaseName_Date.pdf
        crop = data.get("crop_name", "Crop").replace(" ", "")
        disease = data.get("disease_name", "Disease").replace(" ", "")
        date_str = datetime.now().strftime("%Y-%m-%d")
        download_name = f"{crop}_{disease}_{date_str}.pdf"
        
        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype="application/pdf",
            as_attachment=True,
            download_name=download_name
        )
    except Exception as e:
        print(f"Error generating PDF: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


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