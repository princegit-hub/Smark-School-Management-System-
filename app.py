from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime
import json, os, threading

app = Flask(__name__)
app.secret_key = "smart-school-neon-demo-key"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "school_data.json")
LOCK = threading.Lock()

DEFAULT_DATA = {
    "admin": {"username": "admin", "password": generate_password_hash("admin123")},
    "students": [], "teachers": [], "attendance": [], "marks": [], "fees": [], "notices": []
}

def load_data():
    if not os.path.exists(DATA_FILE):
        save_data(DEFAULT_DATA)
        return DEFAULT_DATA.copy()
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return DEFAULT_DATA.copy()

def save_data(data):
    with LOCK:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if "logged_in" not in session:
            flash("Please login first.", "warning")
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper

@app.route("/")
def home(): return render_template("home.html")

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username","").strip()
        password = request.form.get("password","")
        admin = load_data().get("admin", {})
        if username == admin.get("username") and check_password_hash(admin.get("password",""), password):
            session["logged_in"] = True
            session["username"] = username
            flash("Login successful!", "success")
            return redirect(url_for("dashboard"))
        flash("Invalid username or password.", "danger")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))

@app.route("/dashboard")
@login_required
def dashboard():
    data = load_data()
    fees = data.get("fees", [])
    total = paid = 0
    for fee in fees:
        try:
            amount = float(fee.get("amount",0)); total += amount
            if fee.get("status") == "Paid": paid += amount
        except: pass
    return render_template("dashboard.html",
        total_students=len(data.get("students",[])),
        total_teachers=len(data.get("teachers",[])),
        total_attendance=len(data.get("attendance",[])),
        total_marks=len(data.get("marks",[])),
        total_notices=len(data.get("notices",[])),
        total_fees=total, paid_fees=paid, pending_fees=total-paid,
        recent_students=data.get("students",[])[-5:],
        recent_notices=data.get("notices",[])[-5:])

@app.route("/students", methods=["GET","POST"])
@login_required
def students():
    data=load_data()
    if request.method=="POST":
        s={"id":len(data["students"])+1,"name":request.form.get("name","").strip(),
           "roll":request.form.get("roll","").strip(),"class":request.form.get("class","").strip(),
           "section":request.form.get("section","").strip(),"gender":request.form.get("gender","").strip(),
           "phone":request.form.get("phone","").strip(),"email":request.form.get("email","").strip(),
           "date":datetime.now().strftime("%d-%m-%Y")}
        if not s["name"] or not s["roll"]:
            flash("Student name and roll number are required.","danger")
        else:
            data["students"].append(s); save_data(data); flash("Student added successfully!","success")
        return redirect(url_for("students"))
    return render_template("students.html", students=data.get("students",[]))

@app.route("/delete_student/<int:student_id>")
@login_required
def delete_student(student_id):
    data=load_data(); data["students"]=[s for s in data["students"] if s.get("id")!=student_id]
    save_data(data); flash("Student deleted.","info"); return redirect(url_for("students"))

@app.route("/teachers", methods=["GET","POST"])
@login_required
def teachers():
    data=load_data()
    if request.method=="POST":
        t={"id":len(data["teachers"])+1,"name":request.form.get("name","").strip(),
           "subject":request.form.get("subject","").strip(),"department":request.form.get("department","").strip(),
           "phone":request.form.get("phone","").strip(),"email":request.form.get("email","").strip(),
           "date":datetime.now().strftime("%d-%m-%Y")}
        if not t["name"]: flash("Teacher name is required.","danger")
        else: data["teachers"].append(t); save_data(data); flash("Teacher added successfully!","success")
        return redirect(url_for("teachers"))
    return render_template("teachers.html", teachers=data.get("teachers",[]))

@app.route("/attendance", methods=["GET","POST"])
@login_required
def attendance():
    data=load_data()
    if request.method=="POST":
        data["attendance"].append({"student":request.form.get("student","").strip(),
            "date":request.form.get("date",datetime.now().strftime("%Y-%m-%d")),
            "status":request.form.get("status","Present")})
        save_data(data); flash("Attendance recorded!","success"); return redirect(url_for("attendance"))
    return render_template("attendance.html", attendance=data.get("attendance",[]), students=data.get("students",[]))

@app.route("/marks", methods=["GET","POST"])
@login_required
def marks():
    data=load_data()
    if request.method=="POST":
        data["marks"].append({"student":request.form.get("student","").strip(),
            "subject":request.form.get("subject","").strip(),"marks":request.form.get("marks","0").strip(),
            "max_marks":request.form.get("max_marks","100").strip(),"date":datetime.now().strftime("%d-%m-%Y")})
        save_data(data); flash("Marks added successfully!","success"); return redirect(url_for("marks"))
    return render_template("marks.html", marks=data.get("marks",[]), students=data.get("students",[]))

@app.route("/fees", methods=["GET","POST"])
@login_required
def fees():
    data=load_data()
    if request.method=="POST":
        data["fees"].append({"student":request.form.get("student","").strip(),
            "amount":request.form.get("amount","0").strip(),"status":request.form.get("status","Pending"),
            "month":request.form.get("month","").strip(),"date":datetime.now().strftime("%d-%m-%Y")})
        save_data(data); flash("Fee record added!","success"); return redirect(url_for("fees"))
    return render_template("fees.html", fees=data.get("fees",[]), students=data.get("students",[]))

@app.route("/notices", methods=["GET","POST"])
@login_required
def notices():
    data=load_data()
    if request.method=="POST":
        n={"title":request.form.get("title","").strip(),"message":request.form.get("message","").strip(),
           "date":datetime.now().strftime("%d-%m-%Y")}
        if not n["title"]: flash("Notice title is required.","danger")
        else: data["notices"].append(n); save_data(data); flash("Notice published successfully!","success")
        return redirect(url_for("notices"))
    return render_template("notices.html", notices=data.get("notices",[]))

@app.route("/admin")
@login_required
def admin():
    d=load_data()
    return render_template("admin.html", students=len(d["students"]),teachers=len(d["teachers"]),
        attendance=len(d["attendance"]),marks=len(d["marks"]),fees=len(d["fees"]),notices=len(d["notices"]))

@app.route("/change_password", methods=["POST"])
@login_required
def change_password():
    d=load_data(); cur=request.form.get("current_password",""); new=request.form.get("new_password","")
    if not check_password_hash(d["admin"]["password"],cur):
        flash("Current password is incorrect.","danger")
    elif len(new)<4:
        flash("New password must contain at least 4 characters.","danger")
    else:
        d["admin"]["password"]=generate_password_hash(new); save_data(d); flash("Password changed successfully!","success")
    return redirect(url_for("admin"))

if __name__=="__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
