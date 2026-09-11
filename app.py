from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
import os, json

app = Flask(__name__)

# =========================================================
# SMART SCHOOL MANAGEMENT SYSTEM - POSTGRESQL VERSION
# Render-ready persistent database
# =========================================================

app.secret_key = os.environ.get("SECRET_KEY", "smart-school-neon-demo-key")

database_url = os.environ.get("DATABASE_URL", "").strip()

# Render may provide postgres://; SQLAlchemy expects postgresql://
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

# Local fallback: SQLite. On Render, DATABASE_URL should point to PostgreSQL.
if not database_url:
    database_url = "sqlite:///" + os.path.join(os.path.dirname(os.path.abspath(__file__)), "school_local.db")

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


# =========================
# DATABASE MODELS
# =========================

class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)


class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    roll = db.Column(db.String(50), nullable=False)
    class_name = db.Column(db.String(50))
    section = db.Column(db.String(20))
    gender = db.Column(db.String(30))
    phone = db.Column(db.String(30))
    email = db.Column(db.String(150))
    date = db.Column(db.String(20))


class Teacher(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    subject = db.Column(db.String(100))
    department = db.Column(db.String(100))
    phone = db.Column(db.String(30))
    email = db.Column(db.String(150))
    date = db.Column(db.String(20))


class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student = db.Column(db.String(150))
    date = db.Column(db.String(20))
    status = db.Column(db.String(30))


class Mark(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student = db.Column(db.String(150))
    subject = db.Column(db.String(100))
    marks = db.Column(db.String(30))
    max_marks = db.Column(db.String(30))
    date = db.Column(db.String(20))


class Fee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student = db.Column(db.String(150))
    amount = db.Column(db.String(30))
    status = db.Column(db.String(30))
    month = db.Column(db.String(50))
    date = db.Column(db.String(20))


class Notice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    message = db.Column(db.Text)
    date = db.Column(db.String(20))


# =========================
# DATABASE INITIALIZATION
# =========================

def initialize_database():
    db.create_all()

    # Create the requested admin account if no admin exists.
    if Admin.query.count() == 0:
        db.session.add(
            Admin(
                username="Prince",
                password=generate_password_hash("Prince@2008")
            )
        )
        db.session.commit()

    # Optional one-time migration from the old JSON database.
    # Useful if school_data.json is placed beside app.py locally.
    migrate_old_json()


def migrate_old_json():
    if os.environ.get("SKIP_JSON_MIGRATION") == "1":
        return

    json_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "school_data.json")
    if not os.path.exists(json_file):
        return

    # Do not import repeatedly.
    if Student.query.count() or Teacher.query.count() or Attendance.query.count() or \
       Mark.query.count() or Fee.query.count() or Notice.query.count():
        return

    try:
        with open(json_file, "r", encoding="utf-8") as f:
            old = json.load(f)

        # Import admin only if the old file has a valid admin.
        old_admin = old.get("admin", {})
        if old_admin.get("username") and old_admin.get("password"):
            admin = Admin.query.first()
            if admin:
                admin.username = old_admin["username"]
                admin.password = old_admin["password"]

        for s in old.get("students", []):
            db.session.add(Student(
                id=s.get("id"),
                name=s.get("name", ""),
                roll=s.get("roll", ""),
                class_name=s.get("class", ""),
                section=s.get("section", ""),
                gender=s.get("gender", ""),
                phone=s.get("phone", ""),
                email=s.get("email", ""),
                date=s.get("date", "")
            ))

        for t in old.get("teachers", []):
            db.session.add(Teacher(
                id=t.get("id"),
                name=t.get("name", ""),
                subject=t.get("subject", ""),
                department=t.get("department", ""),
                phone=t.get("phone", ""),
                email=t.get("email", ""),
                date=t.get("date", "")
            ))

        for a in old.get("attendance", []):
            db.session.add(Attendance(
                student=a.get("student", ""),
                date=a.get("date", ""),
                status=a.get("status", "Present")
            ))

        for m in old.get("marks", []):
            db.session.add(Mark(
                student=m.get("student", ""),
                subject=m.get("subject", ""),
                marks=m.get("marks", "0"),
                max_marks=m.get("max_marks", "100"),
                date=m.get("date", "")
            ))

        for f in old.get("fees", []):
            db.session.add(Fee(
                student=f.get("student", ""),
                amount=f.get("amount", "0"),
                status=f.get("status", "Pending"),
                month=f.get("month", ""),
                date=f.get("date", "")
            ))

        for n in old.get("notices", []):
            db.session.add(Notice(
                title=n.get("title", ""),
                message=n.get("message", ""),
                date=n.get("date", "")
            ))

        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print("JSON migration skipped:", e)


# =========================
# HELPERS
# =========================

def student_dict(s):
    return {
        "id": s.id, "name": s.name, "roll": s.roll,
        "class": s.class_name, "section": s.section, "gender": s.gender,
        "phone": s.phone, "email": s.email, "date": s.date
    }

def teacher_dict(t):
    return {
        "id": t.id, "name": t.name, "subject": t.subject,
        "department": t.department, "phone": t.phone,
        "email": t.email, "date": t.date
    }

def attendance_dict(a):
    return {"id": a.id, "student": a.student, "date": a.date, "status": a.status}

def mark_dict(m):
    return {
        "id": m.id, "student": m.student, "subject": m.subject,
        "marks": m.marks, "max_marks": m.max_marks, "date": m.date
    }

def fee_dict(f):
    return {
        "id": f.id, "student": f.student, "amount": f.amount,
        "status": f.status, "month": f.month, "date": f.date
    }

def notice_dict(n):
    return {"id": n.id, "title": n.title, "message": n.message, "date": n.date}


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if "logged_in" not in session:
            flash("Please login first.", "warning")
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper


# =========================
# ROUTES
# =========================

@app.route("/")
def home():
    return render_template("home.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        admin = Admin.query.filter_by(username=username).first()

        if admin and check_password_hash(admin.password, password):
            session["logged_in"] = True
            session["username"] = admin.username
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
    fees = Fee.query.order_by(Fee.id.asc()).all()

    total = 0
    paid = 0
    for fee in fees:
        try:
            amount = float(fee.amount or 0)
            total += amount
            if fee.status == "Paid":
                paid += amount
        except (ValueError, TypeError):
            pass

    students = [student_dict(x) for x in Student.query.order_by(Student.id.asc()).all()]
    notices = [notice_dict(x) for x in Notice.query.order_by(Notice.id.asc()).all()]

    return render_template(
        "dashboard.html",
        total_students=Student.query.count(),
        total_teachers=Teacher.query.count(),
        total_attendance=Attendance.query.count(),
        total_marks=Mark.query.count(),
        total_notices=Notice.query.count(),
        total_fees=total,
        paid_fees=paid,
        pending_fees=total - paid,
        recent_students=students[-5:],
        recent_notices=notices[-5:]
    )


@app.route("/students", methods=["GET", "POST"])
@login_required
def students():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        roll = request.form.get("roll", "").strip()

        if not name or not roll:
            flash("Student name and roll number are required.", "danger")
        else:
            db.session.add(Student(
                name=name,
                roll=roll,
                class_name=request.form.get("class", "").strip(),
                section=request.form.get("section", "").strip(),
                gender=request.form.get("gender", "").strip(),
                phone=request.form.get("phone", "").strip(),
                email=request.form.get("email", "").strip(),
                date=datetime.now().strftime("%d-%m-%Y")
            ))
            db.session.commit()
            flash("Student added successfully!", "success")

        return redirect(url_for("students"))

    data = [student_dict(x) for x in Student.query.order_by(Student.id.asc()).all()]
    return render_template("students.html", students=data)


@app.route("/delete_student/<int:student_id>")
@login_required
def delete_student(student_id):
    student = db.session.get(Student, student_id)
    if student:
        db.session.delete(student)
        db.session.commit()
        flash("Student deleted.", "info")
    else:
        flash("Student not found.", "warning")
    return redirect(url_for("students"))


@app.route("/teachers", methods=["GET", "POST"])
@login_required
def teachers():
    if request.method == "POST":
        name = request.form.get("name", "").strip()

        if not name:
            flash("Teacher name is required.", "danger")
        else:
            db.session.add(Teacher(
                name=name,
                subject=request.form.get("subject", "").strip(),
                department=request.form.get("department", "").strip(),
                phone=request.form.get("phone", "").strip(),
                email=request.form.get("email", "").strip(),
                date=datetime.now().strftime("%d-%m-%Y")
            ))
            db.session.commit()
            flash("Teacher added successfully!", "success")

        return redirect(url_for("teachers"))

    data = [teacher_dict(x) for x in Teacher.query.order_by(Teacher.id.asc()).all()]
    return render_template("teachers.html", teachers=data)


@app.route("/attendance", methods=["GET", "POST"])
@login_required
def attendance():
    if request.method == "POST":
        db.session.add(Attendance(
            student=request.form.get("student", "").strip(),
            date=request.form.get("date", datetime.now().strftime("%Y-%m-%d")),
            status=request.form.get("status", "Present")
        ))
        db.session.commit()
        flash("Attendance recorded!", "success")
        return redirect(url_for("attendance"))

    data = [attendance_dict(x) for x in Attendance.query.order_by(Attendance.id.asc()).all()]
    students_data = [student_dict(x) for x in Student.query.order_by(Student.id.asc()).all()]
    return render_template("attendance.html", attendance=data, students=students_data)


@app.route("/marks", methods=["GET", "POST"])
@login_required
def marks():
    if request.method == "POST":
        db.session.add(Mark(
            student=request.form.get("student", "").strip(),
            subject=request.form.get("subject", "").strip(),
            marks=request.form.get("marks", "0").strip(),
            max_marks=request.form.get("max_marks", "100").strip(),
            date=datetime.now().strftime("%d-%m-%Y")
        ))
        db.session.commit()
        flash("Marks added successfully!", "success")
        return redirect(url_for("marks"))

    data = [mark_dict(x) for x in Mark.query.order_by(Mark.id.asc()).all()]
    students_data = [student_dict(x) for x in Student.query.order_by(Student.id.asc()).all()]
    return render_template("marks.html", marks=data, students=students_data)


@app.route("/fees", methods=["GET", "POST"])
@login_required
def fees():
    if request.method == "POST":
        db.session.add(Fee(
            student=request.form.get("student", "").strip(),
            amount=request.form.get("amount", "0").strip(),
            status=request.form.get("status", "Pending"),
            month=request.form.get("month", "").strip(),
            date=datetime.now().strftime("%d-%m-%Y")
        ))
        db.session.commit()
        flash("Fee record added!", "success")
        return redirect(url_for("fees"))

    data = [fee_dict(x) for x in Fee.query.order_by(Fee.id.asc()).all()]
    students_data = [student_dict(x) for x in Student.query.order_by(Student.id.asc()).all()]
    return render_template("fees.html", fees=data, students=students_data)


@app.route("/notices", methods=["GET", "POST"])
@login_required
def notices():
    if request.method == "POST":
        title = request.form.get("title", "").strip()

        if not title:
            flash("Notice title is required.", "danger")
        else:
            db.session.add(Notice(
                title=title,
                message=request.form.get("message", "").strip(),
                date=datetime.now().strftime("%d-%m-%Y")
            ))
            db.session.commit()
            flash("Notice published successfully!", "success")

        return redirect(url_for("notices"))

    data = [notice_dict(x) for x in Notice.query.order_by(Notice.id.asc()).all()]
    return render_template("notices.html", notices=data)


# =========================
# EDIT / UPDATE ROUTES
# =========================

@app.route("/edit_student/<int:student_id>", methods=["GET", "POST"])
@login_required
def edit_student(student_id):
    student = db.session.get(Student, student_id)
    if not student:
        flash("Student not found.", "warning")
        return redirect(url_for("students"))
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        roll = request.form.get("roll", "").strip()
        if not name or not roll:
            flash("Student name and roll number are required.", "danger")
        else:
            student.name = name
            student.roll = roll
            student.class_name = request.form.get("class", "").strip()
            student.section = request.form.get("section", "").strip()
            student.gender = request.form.get("gender", "").strip()
            student.phone = request.form.get("phone", "").strip()
            student.email = request.form.get("email", "").strip()
            db.session.commit()
            flash("Student updated successfully!", "success")
            return redirect(url_for("students"))
    return render_template("edit_student.html", student=student_dict(student))


@app.route("/edit_teacher/<int:teacher_id>", methods=["GET", "POST"])
@login_required
def edit_teacher(teacher_id):
    teacher = db.session.get(Teacher, teacher_id)
    if not teacher:
        flash("Teacher not found.", "warning")
        return redirect(url_for("teachers"))
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("Teacher name is required.", "danger")
        else:
            teacher.name = name
            teacher.subject = request.form.get("subject", "").strip()
            teacher.department = request.form.get("department", "").strip()
            teacher.phone = request.form.get("phone", "").strip()
            teacher.email = request.form.get("email", "").strip()
            db.session.commit()
            flash("Teacher updated successfully!", "success")
            return redirect(url_for("teachers"))
    return render_template("edit_teacher.html", teacher=teacher_dict(teacher))


@app.route("/edit_attendance/<int:attendance_id>", methods=["GET", "POST"])
@login_required
def edit_attendance(attendance_id):
    record = db.session.get(Attendance, attendance_id)
    if not record:
        flash("Attendance record not found.", "warning")
        return redirect(url_for("attendance"))
    if request.method == "POST":
        record.student = request.form.get("student", "").strip()
        record.date = request.form.get("date", "").strip()
        record.status = request.form.get("status", "Present")
        db.session.commit()
        flash("Attendance updated successfully!", "success")
        return redirect(url_for("attendance"))
    students_data = [student_dict(x) for x in Student.query.order_by(Student.id.asc()).all()]
    return render_template("edit_attendance.html", record=attendance_dict(record), students=students_data)


@app.route("/edit_mark/<int:mark_id>", methods=["GET", "POST"])
@login_required
def edit_mark(mark_id):
    record = db.session.get(Mark, mark_id)
    if not record:
        flash("Marks record not found.", "warning")
        return redirect(url_for("marks"))
    if request.method == "POST":
        record.student = request.form.get("student", "").strip()
        record.subject = request.form.get("subject", "").strip()
        record.marks = request.form.get("marks", "0").strip()
        record.max_marks = request.form.get("max_marks", "100").strip()
        db.session.commit()
        flash("Marks updated successfully!", "success")
        return redirect(url_for("marks"))
    students_data = [student_dict(x) for x in Student.query.order_by(Student.id.asc()).all()]
    return render_template("edit_mark.html", mark=mark_dict(record), students=students_data)


@app.route("/edit_fee/<int:fee_id>", methods=["GET", "POST"])
@login_required
def edit_fee(fee_id):
    record = db.session.get(Fee, fee_id)
    if not record:
        flash("Fee record not found.", "warning")
        return redirect(url_for("fees"))
    if request.method == "POST":
        record.student = request.form.get("student", "").strip()
        record.amount = request.form.get("amount", "0").strip()
        record.status = request.form.get("status", "Pending")
        record.month = request.form.get("month", "").strip()
        db.session.commit()
        flash("Fee record updated successfully!", "success")
        return redirect(url_for("fees"))
    students_data = [student_dict(x) for x in Student.query.order_by(Student.id.asc()).all()]
    return render_template("edit_fee.html", fee=fee_dict(record), students=students_data)


@app.route("/edit_notice/<int:notice_id>", methods=["GET", "POST"])
@login_required
def edit_notice(notice_id):
    notice = db.session.get(Notice, notice_id)
    if not notice:
        flash("Notice not found.", "warning")
        return redirect(url_for("notices"))
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        message = request.form.get("message", "").strip()
        if not title or not message:
            flash("Notice title and message are required.", "danger")
        else:
            notice.title = title
            notice.message = message
            db.session.commit()
            flash("Notice updated successfully!", "success")
            return redirect(url_for("notices"))
    return render_template("edit_notice.html", notice=notice_dict(notice))


@app.route("/admin")
@login_required
def admin():
    return render_template(
        "admin.html",
        students=Student.query.count(),
        teachers=Teacher.query.count(),
        attendance=Attendance.query.count(),
        marks=Mark.query.count(),
        fees=Fee.query.count(),
        notices=Notice.query.count()
    )


@app.route("/change_password", methods=["POST"])
@login_required
def change_password():
    admin = Admin.query.filter_by(username=session.get("username")).first()
    cur = request.form.get("current_password", "")
    new = request.form.get("new_password", "")

    if not admin or not check_password_hash(admin.password, cur):
        flash("Current password is incorrect.", "danger")
    elif len(new) < 4:
        flash("New password must contain at least 4 characters.", "danger")
    else:
        admin.password = generate_password_hash(new)
        db.session.commit()
        flash("Password changed successfully!", "success")

    return redirect(url_for("admin"))


# Create database tables when the app starts.
with app.app_context():
    initialize_database()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
