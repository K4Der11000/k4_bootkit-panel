from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory
import os, json, hashlib, datetime
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "bootkit_secret_key"

# بيانات المستخدمين
USERS_FILE = "users.json"
DEVICES_FILE = "devices.json"
os.makedirs("payloads", exist_ok=True)
os.makedirs("output", exist_ok=True)

# تحميل المستخدمين
def load_users():
    if not os.path.exists(USERS_FILE):
        return {}
    with open(USERS_FILE, "r") as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)

# تسجيل الدخول
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        users = load_users()
        username = request.form["username"]
        password = request.form["password"]
        hashed = hashlib.sha256(password.encode()).hexdigest()
        if username in users and users[username]["password"] == hashed:
            session["user"] = username
            return redirect("/")
        return render_template("login.html", error="Wrong credentials.")
    return render_template("login.html")

# تسجيل حساب جديد
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        users = load_users()
        username = request.form["username"]
        password = request.form["password"]
        if username in users:
            return render_template("register.html", error="User already exists.")
        users[username] = {
            "password": hashlib.sha256(password.encode()).hexdigest()
        }
        save_users(users)
        return redirect("/login")
    return render_template("register.html")

# تسجيل خروج
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# واجهة رئيسية
@app.route("/", methods=["GET", "POST"])
def index():
    if "user" not in session:
        return redirect("/login")
    
    os.makedirs(f"payloads/{session['user']}", exist_ok=True)
    os.makedirs(f"output/{session['user']}", exist_ok=True)
    
    logs = load_logs()
    devices = load_devices()

    return render_template("index.html", username=session["user"], logs=logs[-10:], devices=devices)

# رفع بايلود
@app.route("/upload", methods=["POST"])
def upload_payload():
    if "user" not in session:
        return redirect("/login")
    file = request.files["payload"]
    system = request.form["system"]
    if file:
        filename = secure_filename(file.filename)
        path = f"payloads/{system}/{session['user']}"
        os.makedirs(path, exist_ok=True)
        file.save(os.path.join(path, filename))
        log_event(f"{session['user']} uploaded payload for {system}: {filename}")
    return redirect("/")

# حقن هوك وهمي
@app.route("/inject", methods=["POST"])
def inject_hook():
    if "user" not in session:
        return redirect("/login")
    system = request.form["system"]
    filename = request.form["filename"]
    path = f"payloads/{system}/{session['user']}/{filename}"
    output_path = f"output/{system}/{session['user']}/hooked_{filename}"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(path, "rb") as f:
        content = f.read() + b"\n// Hook inserted"
    with open(output_path, "wb") as f:
        f.write(content)
    
    log_event(f"{session['user']} injected hook into {filename}")
    return redirect("/")

# تشفير بايلود
@app.route("/encrypt", methods=["POST"])
def encrypt_payload():
    if "user" not in session:
        return redirect("/login")
    system = request.form["system"]
    filename = request.form["filename"]
    input_path = f"output/{system}/{session['user']}/{filename}"
    output_path = f"output/{system}/{session['user']}/enc_{filename}"
    
    with open(input_path, "rb") as f:
        data = f.read()
    encrypted = bytes([b ^ 0xAA for b in data])
    with open(output_path, "wb") as f:
        f.write(encrypted)
    
    log_event(f"{session['user']} encrypted {filename}")
    return redirect("/")

# تحميل ملف
@app.route("/download/<system>/<user>/<filename>")
def download(system, user, filename):
    path = f"output/{system}/{user}"
    return send_from_directory(path, filename, as_attachment=True)

# محاكاة تشغيل البايلود
@app.route("/simulate", methods=["POST"])
def simulate_payload():
    if "user" not in session:
        return redirect("/login")
    device = f"{session['user']}-PC"
    now = datetime.datetime.now().isoformat()
    
    devices = load_devices()
    devices[device] = {"user": session["user"], "last_seen": now}
    with open(DEVICES_FILE, "w") as f:
        json.dump(devices, f, indent=2)
    
    log_event(f"{session['user']} simulated execution on {device}")
    return redirect("/")

# تسجيل التبليغ من جهاز
@app.route("/report", methods=["POST"])
def report_device():
    data = request.json
    if not data or "device" not in data:
        return "Invalid", 400
    devices = load_devices()
    devices[data["device"]] = {"user": data.get("user", "unknown"), "last_seen": datetime.datetime.now().isoformat()}
    with open(DEVICES_FILE, "w") as f:
        json.dump(devices, f, indent=2)
    return "OK", 200

# تحميل السجلات والأجهزة
def log_event(event):
    with open("logs.json", "a") as f:
        f.write(f"{datetime.datetime.now().isoformat()} - {event}\n")

def load_logs():
    if not os.path.exists("logs.json"):
        return []
    with open("logs.json") as f:
        return f.readlines()

def load_devices():
    if not os.path.exists(DEVICES_FILE):
        return {}
    with open(DEVICES_FILE) as f:
        return json.load(f)

if __name__ == "__main__":
    app.run(debug=True)
