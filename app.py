from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "smart_student_management_secret_2026"

DATABASE = "student_management.db"


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_db():
    conn = sqlite3.connect(
        DATABASE,
        timeout=30,
        check_same_thread=False,
        isolation_level=None
    )
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=30000")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA journal_mode=WAL")
    return conn
# ============================================================
# PASSWORD COLUMN COMPATIBILITY
# ============================================================

def get_password_column(conn=None):
    close_conn = False

    if conn is None:
        conn = get_db()
        close_conn = True

    columns = [
    row["name"] if isinstance(row, sqlite3.Row) else row[1]
    for row in conn.execute(
        "PRAGMA table_info(users)"
    ).fetchall()
]

    if close_conn:
        conn.close()

    if "password" in columns:
        return "password"

    if "password_hash" in columns:
        return "password_hash"

    return None


def verify_password(stored_password, entered_password):
    try:
        return check_password_hash(
            stored_password,
            entered_password
        )
    except Exception:
        return stored_password == entered_password


# ============================================================
# LOGIN REQUIRED
# ============================================================

def login_required(function):

    @wraps(function)
    def wrapper(*args, **kwargs):

        if "user_id" not in session:
            return redirect(url_for("login"))

        return function(*args, **kwargs)

    return wrapper


# ============================================================
# DATABASE INITIALIZATION
# ============================================================

def init_db():

    conn = get_db()

    # USERS
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT NOT NULL,
            role TEXT NOT NULL
        )
    """)

    # STUDENTS
    conn.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            full_name TEXT NOT NULL,
            username TEXT,
            roll_no TEXT,
            class_name TEXT,
            section TEXT,
            status TEXT DEFAULT 'Active'
        )
    """)

    # TEACHERS
    conn.execute("""
        CREATE TABLE IF NOT EXISTS teachers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            full_name TEXT NOT NULL,
            username TEXT,
            employee_id TEXT,
            subject TEXT,
            status TEXT DEFAULT 'Active'
        )
    """)

    # ATTENDANCE
    conn.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            attendance_date TEXT NOT NULL,
            status TEXT NOT NULL,
            marked_by INTEGER
        )
    """)

    # MARKS
    conn.execute("""
        CREATE TABLE IF NOT EXISTS marks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            exam_name TEXT NOT NULL,
            subject TEXT NOT NULL,
            marks_obtained REAL NOT NULL,
            max_marks REAL NOT NULL,
            entered_by INTEGER
        )
    """)

    # NOTICES
    conn.execute("""
        CREATE TABLE IF NOT EXISTS notices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            created_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # PARENT-STUDENT MAPPING
    conn.execute("""
        CREATE TABLE IF NOT EXISTS parent_student (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            parent_user_id INTEGER NOT NULL,
            student_id INTEGER NOT NULL,
            UNIQUE(parent_user_id, student_id)
        )
    """)

    conn.commit()

    # Detect existing users table password column
    password_column = get_password_column(conn)

    if password_column is None:
        conn.close()
        raise Exception(
            "Users table does not contain password/password_hash column."
        )

    # ========================================================
    # DEMO USERS
    # ========================================================

    demo_users = [
        ("admin", "Admin@2026", "System Administrator", "admin"),
        ("teacher1", "Teacher@2026", "Demo Teacher", "teacher"),
        ("student1", "Student@2026", "Demo Student", "student"),
        ("parent1", "Parent@2026", "Demo Parent", "parent")
    ]

    for username, password, full_name, role in demo_users:

        existing = conn.execute(
            """
            SELECT id
            FROM users
            WHERE username = ?
            """,
            (username,)
        ).fetchone()

        if not existing:

            conn.execute(
                f"""
                INSERT INTO users
                (
                    username,
                    {password_column},
                    full_name,
                    role
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    username,
                    generate_password_hash(password),
                    full_name,
                    role
                )
            )

    # ========================================================
    # DEMO STUDENT
    # ========================================================

    student_user = conn.execute(
        """
        SELECT id
        FROM users
        WHERE username = 'student1'
        """
    ).fetchone()

    if student_user:

        student_exists = conn.execute(
            """
            SELECT id
            FROM students
            WHERE username = 'student1'
            """
        ).fetchone()

        if not student_exists:

            conn.execute(
                """
                INSERT INTO students
                (
                    user_id,
                    full_name,
                    username,
                    roll_no,
                    class_name,
                    section,
                    status
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    student_user["id"],
                    "Demo Student",
                    "student1",
                    "101",
                    "BCA 3rd Year",
                    "A",
                    "Active"
                )
            )

    # ========================================================
    # DEMO TEACHER
    # ========================================================

    teacher_user = conn.execute(
        """
        SELECT id
        FROM users
        WHERE username = 'teacher1'
        """
    ).fetchone()

    if teacher_user:

        teacher_exists = conn.execute(
            """
            SELECT id
            FROM teachers
            WHERE username = 'teacher1'
            """
        ).fetchone()

        if not teacher_exists:

            conn.execute(
                """
                INSERT INTO teachers
                (
                    user_id,
                    full_name,
                    username,
                    employee_id,
                    subject,
                    status
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    teacher_user["id"],
                    "Demo Teacher",
                    "teacher1",
                    "T001",
                    "Computer Science",
                    "Active"
                )
            )

    # ========================================================
    # DEMO NOTICE
    # ========================================================

    notice_count = conn.execute(
        """
        SELECT COUNT(*) AS total
        FROM notices
        """
    ).fetchone()["total"]

    if notice_count == 0:

        admin_user = conn.execute(
            """
            SELECT id
            FROM users
            WHERE username = 'admin'
            """
        ).fetchone()

        conn.execute(
            """
            INSERT INTO notices
            (
                title,
                message,
                created_by
            )
            VALUES (?, ?, ?)
            """,
            (
                "Welcome to Smart Student Management System",
                "System is ready for academic management.",
                admin_user["id"] if admin_user else None
            )
        )

    # ========================================================
    # PARENT -> STUDENT
    # ========================================================

    parent_user = conn.execute(
        """
        SELECT id
        FROM users
        WHERE username = 'parent1'
        """
    ).fetchone()

    demo_student = conn.execute(
        """
        SELECT id
        FROM students
        WHERE username = 'student1'
        """
    ).fetchone()

    if parent_user and demo_student:

        mapping = conn.execute(
            """
            SELECT id
            FROM parent_student
            WHERE parent_user_id = ?
            AND student_id = ?
            """,
            (
                parent_user["id"],
                demo_student["id"]
            )
        ).fetchone()

        
# ============================================================
# HOME
# ============================================================

@app.route("/")
def home():

    if "user_id" not in session:
        return redirect(url_for("login"))

    role = session.get("role")

    if role == "parent":
        return redirect(url_for("parent_dashboard"))

    if role == "student":
        return redirect(url_for("student_dashboard"))

    return redirect(url_for("dashboard"))


# ============================================================
# LOGIN
# ============================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    error = None

    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        selected_role = request.form.get(
            "role",
            ""
        ).strip().lower()

        conn = get_db()

        password_column = get_password_column(conn)

        if password_column is None:
            conn.close()
            return "Users password column not found.", 500

        user = conn.execute(
            f"""
            SELECT
                id,
                username,
                {password_column} AS stored_password,
                full_name,
                role
            FROM users
            WHERE username = ?
            """,
            (username,)
        ).fetchone()

        conn.close()

        if user and verify_password(
            user["stored_password"],
            password
        ):

            actual_role = (
                user["role"]
                .strip()
                .lower()
            )

            if selected_role and selected_role != actual_role:

                return render_template(
                    "login.html",
                    error=(
                        "Selected role does not "
                        "match this account."
                    )
                )

            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["full_name"] = user["full_name"]
            session["role"] = actual_role

            if actual_role == "parent":
                return redirect(
                    url_for("parent_dashboard")
                )

            if actual_role == "student":
                return redirect(
                    url_for("student_dashboard")
                )

            return redirect(
                url_for("dashboard")
            )

        error = "Invalid username or password."

    return render_template(
        "login.html",
        error=error
    )


# ============================================================
# LOGOUT
# ============================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(
        url_for("login")
    )


# ============================================================
# ADMIN / TEACHER DASHBOARD
# ============================================================

@app.route("/dashboard")
@login_required
def dashboard():

    if session.get("role") not in [
        "admin",
        "teacher"
    ]:
        return "Access Denied", 403

    conn = get_db()

    total_students = conn.execute(
        """
        SELECT COUNT(*) AS total
        FROM students
        """
    ).fetchone()["total"]

    total_teachers = conn.execute(
        """
        SELECT COUNT(*) AS total
        FROM teachers
        """
    ).fetchone()["total"]

    total_notices = conn.execute(
        """
        SELECT COUNT(*) AS total
        FROM notices
        """
    ).fetchone()["total"]

    total_attendance = conn.execute(
        """
        SELECT COUNT(*) AS total
        FROM attendance
        """
    ).fetchone()["total"]

    present_attendance = conn.execute(
        """
        SELECT COUNT(*) AS total
        FROM attendance
        WHERE status = 'Present'
        """
    ).fetchone()["total"]

    if total_attendance > 0:

        attendance_percentage = round(
            (
                present_attendance /
                total_attendance
            ) * 100,
            1
        )

    else:

        attendance_percentage = 0

    conn.close()

    return render_template(
        "dashboard.html",
        user_name=session.get("full_name"),
        role=session.get("role", "").title(),
        total_students=total_students,
        total_teachers=total_teachers,
        total_notices=total_notices,
        attendance_percentage=attendance_percentage
    )

@app.route("/admin/account", methods=["GET", "POST"])
@login_required
def admin_account():
    if session.get("role") != "admin":
        return "Access Denied", 403

    conn = get_db()
    password_column = get_password_column(conn)

    admin = conn.execute(
        f"""
        SELECT id, username, full_name, {password_column}
        FROM users
        WHERE id = ?
        """,
        (session["user_id"],)
    ).fetchone()

    error = None
    success = None

    if request.method == "POST":
        current_password = request.form.get("current_password", "")
        new_username = request.form.get("username", "").strip()
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not check_password_hash(
            admin[password_column],
            current_password
        ):
            error = "Current password is incorrect."

        elif not new_username:
            error = "Username is required."

        elif new_password != confirm_password:
            error = "New passwords do not match."

        else:
            existing = conn.execute(
                "SELECT id FROM users WHERE username = ? AND id != ?",
                (new_username, admin["id"])
            ).fetchone()

            if existing:
                error = "Username already exists."

            else:
                conn.execute(
                    f"""
                    UPDATE users
                    SET username = ?, {password_column} = ?
                    WHERE id = ?
                    """,
                    (
                        new_username,
                        generate_password_hash(new_password),
                        admin["id"]
                    )
                )

                conn.commit()
                session["username"] = new_username
                success = "Account updated successfully."

    conn.close()

    return render_template(
        "admin_account.html",
        admin=admin,
        error=error,
        success=success
    )





# ============================================================
# STUDENTS
# ============================================================

@app.route("/admin/students")
@login_required
def admin_students():

    if session.get("role") not in [
        "admin",
        "teacher"
    ]:
        return "Access Denied", 403

    conn = get_db()

    students = conn.execute(
        """
        SELECT *
        FROM students
        ORDER BY id DESC
        """
    ).fetchall()

    conn.close()

    return render_template(
        "students.html",
        students=students,
        user_name=session.get("full_name"),
        role=session.get("role", "").title()
    )


# ============================================================
# ADD STUDENT
# ============================================================

@app.route(
    "/admin/students/add",
    methods=["GET", "POST"]
)
@login_required
def add_student():

    if session.get("role") != "admin":
        return "Access Denied", 403

    error = None

    if request.method == "POST":

        full_name = request.form.get(
            "full_name",
            ""
        ).strip()

        username = request.form.get(
            "username",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        roll_no = request.form.get(
            "roll_no",
            ""
        ).strip()

        class_name = request.form.get(
            "class_name",
            ""
        ).strip()

        section = request.form.get(
            "section",
            ""
        ).strip()

        if not all([
            full_name,
            username,
            password,
            roll_no,
            class_name,
            section
        ]):

            error = "Please fill all fields."

        else:

            conn = get_db()

            password_column = get_password_column(conn)

            existing = conn.execute(
                """
                SELECT id
                FROM users
                WHERE username = ?
                """,
                (username,)
            ).fetchone()

            if existing:

                error = "Username already exists."
                conn.close()

            else:

                cursor = conn.execute(
                    f"""
                    INSERT INTO users
                    (
                        username,
                        {password_column},
                        full_name,
                        role
                    )
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        username,
                        generate_password_hash(password),
                        full_name,
                        "student"
                    )
                )

                user_id = cursor.lastrowid

                conn.execute(
                    """
                    INSERT INTO students
                    (
                        user_id,
                        full_name,
                        username,
                        roll_no,
                        class_name,
                        section,
                        status
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        user_id,
                        full_name,
                        username,
                        roll_no,
                        class_name,
                        section,
                        "Active"
                    )
                )

                conn.commit()
                conn.close()

                return redirect(
                    url_for("admin_students")
                )

    return render_template(
        "add_student.html",
        error=error,
        user_name=session.get("full_name"),
        role=session.get("role", "").title()
    )


# ============================================================
# TEACHERS
# ============================================================

@app.route("/admin/teachers")
@login_required
def admin_teachers():

    if session.get("role") not in [
        "admin",
        "teacher"
    ]:
        return "Access Denied", 403

    conn = get_db()

    teachers = conn.execute(
        """
        SELECT *
        FROM teachers
        ORDER BY id DESC
        """
    ).fetchall()

    conn.close()

    return render_template(
        "teachers.html",
        teachers=teachers,
        user_name=session.get("full_name"),
        role=session.get("role", "").title()
    )


# ============================================================
# ADD TEACHER
# ============================================================

@app.route(
    "/admin/teachers/add",
    methods=["GET", "POST"]
)
@login_required
def add_teacher():

    if session.get("role") != "admin":
        return "Access Denied", 403

    error = None

    if request.method == "POST":
       
        full_name = request.form.get(
           "full_name",
           ""
           ).strip()
        username = request.form.get(
            "username",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        employee_id = request.form.get(
            "employee_id",
            ""
        ).strip()

        subject = request.form.get(
            "subject",
            ""
        ).strip()

        if not all([
            full_name,
            username,
            password,
        ]):

            error = "Please fill full name username and password."

        else:

            conn = get_db()

            password_column = get_password_column(conn)

            existing = conn.execute(
                """
                SELECT id
                FROM users
                WHERE username = ?
                """,
                (username,)
            ).fetchone()

            if existing:

                error = "Username already exists."
                conn.close()

            else:

                cursor = conn.execute(
                    f"""
                    INSERT INTO users
                    (
                        username,
                        {password_column},
                        full_name,
                        role
                    )
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        username,
                        generate_password_hash(password),
                        full_name,
                        "teacher"
                    )
                )

                user_id = cursor.lastrowid

                conn.execute(
                    """
                    INSERT INTO teachers
                    (
                        user_id,
                        full_name,
                        username,
                        employee_id,
                        subject,
                        status
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        user_id,
                        full_name,
                        username,
                        employee_id,
                        subject,
                        "Active"
                    )
                )

                conn.commit()
                conn.close()

                return redirect(
                    url_for("admin_teachers")
                )

    return render_template(
        "add_teacher.html",
        error=error,
        user_name=session.get("full_name"),
        role=session.get("role", "").title()
    )


# ============================================================
# ATTENDANCE
# ============================================================

@app.route(
    "/admin/attendance",
    methods=["GET", "POST"]
)
@login_required
def admin_attendance():

    if session.get("role") not in [
        "admin",
        "teacher"
    ]:
        return "Access Denied", 403

    error = None

    conn = get_db()

    students = conn.execute(
        """
        SELECT *
        FROM students
        ORDER BY full_name
        """
    ).fetchall()

    if request.method == "POST":

        student_id = request.form.get(
            "student_id",
            ""
        )

        attendance_date = request.form.get(
            "attendance_date",
            ""
        ).strip()

        status = request.form.get(
            "status",
            ""
        ).strip()

        if not all([
            student_id,
            attendance_date,
            status
        ]):

            error = "Please enter valid attendance details."

        elif status not in [
            "Present",
            "Absent"
        ]:

            error = "Invalid attendance status."

        else:

            existing = conn.execute(
                """
                SELECT id
                FROM attendance
                WHERE student_id = ?
                AND attendance_date = ?
                """,
                (
                    student_id,
                    attendance_date
                )
            ).fetchone()

            if existing:

                conn.execute(
                    """
                    UPDATE attendance
                    SET status = ?,
                        marked_by = ?
                    WHERE id = ?
                    """,
                    (
                        status,
                        session["user_id"],
                        existing["id"]
                    )
                )

            else:

                conn.execute(
                    """
                    INSERT INTO attendance
                    (
                        student_id,
                        attendance_date,
                        status,
                        marked_by
                    )
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        student_id,
                        attendance_date,
                        status,
                        session["user_id"]
                    )
                )

            conn.commit()

    # Recent attendance records

    attendance_records = conn.execute(
        """
        SELECT
            attendance.id,
            students.full_name,
            students.roll_no,
            attendance.attendance_date,
            attendance.status
        FROM attendance
        JOIN students
        ON students.id = attendance.student_id
        ORDER BY
            attendance.attendance_date DESC,
            attendance.id DESC
        LIMIT 20
        """
    ).fetchall()

    # Today's attendance

    total_today = conn.execute(
        """
        SELECT COUNT(*) AS total
        FROM attendance
        WHERE attendance_date = date('now')
        """
    ).fetchone()["total"]

    present_today = conn.execute(
        """
        SELECT COUNT(*) AS total
        FROM attendance
        WHERE attendance_date = date('now')
        AND status = 'Present'
        """
    ).fetchone()["total"]

    if total_today > 0:

        attendance_rate = round(
            (
                present_today /
                total_today
            ) * 100,
            1
        )

    else:

        attendance_rate = 0

    total_students = conn.execute(
        """
        SELECT COUNT(*) AS total
        FROM students
        """
    ).fetchone()["total"]

    conn.close()

    return render_template(
        "attendance.html",
        students=students,
        attendance_records=attendance_records,
        total_students=total_students,
        present_today=present_today,
        attendance_rate=attendance_rate,
        error=error,
        user_name=session.get("full_name"),
        role=session.get("role", "").title()
    )


# ============================================================
# MARKS
# ============================================================

@app.route(
    "/admin/marks",
    methods=["GET", "POST"]
)
@login_required
def admin_marks():

    if session.get("role") not in [
        "admin",
        "teacher"
    ]:
        return "Access Denied", 403

    error = None

    conn = get_db()

    students = conn.execute(
        """
        SELECT *
        FROM students
        ORDER BY full_name
        """
    ).fetchall()

    if request.method == "POST":

        student_id = request.form.get(
            "student_id",
            ""
        )

        subject = request.form.get(
            "subject",
            ""
        ).strip()

        marks_obtained = request.form.get(
            "marks_obtained",
            ""
        ).strip()

        max_marks = request.form.get(
            "max_marks",
            ""
        ).strip()

        try:

            obtained = float(
                marks_obtained
            )

            maximum = float(
                max_marks
            )

            if not all([
                student_id,
                subject,
                marks_obtained,
                max_marks
            ]):

                error = "Please fill all marks fields."

            elif maximum <= 0:

                error = "Maximum marks must be greater than 0."

            elif obtained < 0 or obtained > maximum:

                error = (
                    "Marks must be between "
                    "0 and maximum marks."
                )

            else:

                conn.execute(
                    """
                    INSERT INTO marks
                    (
                        student_id,
                        exam_name,
                        subject,
                        marks_obtained,
                        max_marks,
                        entered_by
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        student_id,
                        "Internal Assessment",
                        subject,
                        obtained,
                        maximum,
                        session["user_id"]
                    )
                )

                conn.commit()

        except ValueError:

            error = "Please enter valid numeric marks."

    # Recent marks records

    marks = conn.execute(
        """
        SELECT
            marks.id,
            students.full_name,
            students.roll_no,
            marks.exam_name,
            marks.subject,
            marks.marks_obtained,
            marks.max_marks
        FROM marks
        JOIN students
        ON students.id = marks.student_id
        ORDER BY marks.id DESC
        LIMIT 20
        """
    ).fetchall()

    conn.close()

    return render_template(
        "marks.html",
        students=students,
        marks=marks,
        error=error,
        user_name=session.get("full_name"),
        role=session.get("role", "").title()
    )

# ============================================================
# NOTICES
# ============================================================

@app.route("/admin/notices")
@login_required
def admin_notices():

    if session.get("role") not in [
        "admin",
        "teacher"
    ]:
        return "Access Denied", 403

    conn = get_db()

    notices = conn.execute(
        """
        SELECT *
        FROM notices
        ORDER BY created_at DESC
        """
    ).fetchall()

    conn.close()

    return render_template(
        "notices.html",
        notices=notices,
        user_name=session.get("full_name"),
        role=session.get("role", "").title()
    )


# ============================================================
# ADD NOTICE
# ============================================================

@app.route(
    "/admin/notices/add",
    methods=["GET", "POST"]
)
@login_required
def add_notice():

    if session.get("role") not in [
        "admin",
        "teacher"
    ]:
        return "Access Denied", 403

    error = None

    if request.method == "POST":

        title = request.form.get(
            "title",
            ""
        ).strip()

        message = request.form.get(
            "message",
            ""
        ).strip()

        if not title or not message:

            error = "Please enter title and message."

        else:

            conn = get_db()

            conn.execute(
                """
                INSERT INTO notices
                (
                    title,
                    message,
                    created_by
                )
                VALUES (?, ?, ?)
                """,
                (
                    title,
                    message,
                    session["user_id"]
                )
            )

            conn.commit()
            conn.close()

            return redirect(
                url_for("admin_notices")
            )

    return render_template(
        "add_notice.html",
        error=error,
        user_name=session.get("full_name"),
        role=session.get("role", "").title()
    )

@app.route("/parent/child")
@login_required
def parent_child():
    if session.get("role") != "parent":
        return "Access Denied", 403

    conn = get_db()

    child = conn.execute("""
        SELECT
            students.full_name,
            students.roll_no,
            students.class_name AS class,
            students.section,
            users.username,
            users.role
        FROM students
        JOIN users
            ON users.id = students.user_id
        JOIN parent_student
            ON parent_student.student_id = students.id
        WHERE parent_student.parent_user_id = ?
        LIMIT 1
    """, (session["user_id"],)).fetchone()

    conn.close()

    return render_template(
        "parent_child.html",
        child=child,
        user_name=session.get("full_name"),
        role="Parent"
    )



@app.route("/parent/notices")
@login_required
def parent_notices():
    if session.get("role") != "parent":
        return "Access Denied", 403

    conn = get_db()

    notices = conn.execute("""
        SELECT
            title,
            message,
            created_at
        FROM notices
        ORDER BY created_at DESC
    """).fetchall()

    conn.close()

    return render_template(
        "parent_notices.html",
        notices=notices,
        user_name=session.get("full_name"),
        role="Parent"
    )


@app.route("/admin/performance")
@login_required
def admin_performance():
    if session.get("role") not in ["admin", "teacher"]:
        return "Access Denied", 403

    conn = get_db()

    performance = conn.execute("""
        SELECT
            students.full_name,
            students.roll_no,
            SUM(marks.marks_obtained) AS obtained,
            SUM(marks.max_marks) AS maximum
        FROM marks
        JOIN students ON students.id = marks.student_id
        GROUP BY students.id
        ORDER BY students.full_name
    """).fetchall()

    conn.close()

    return render_template(
        "performance.html",
        performance=performance,
        user_name=session.get("full_name"),
        role=session.get("role", "").title()
    )

# ============================================================
# STUDENT DASHBOARD DATA
# ============================================================

def get_student_dashboard_data(student_id):

    conn = get_db()

    # Attendance

    total_attendance = conn.execute(
        """
        SELECT COUNT(*) AS total
        FROM attendance
        WHERE student_id = ?
        """,
        (student_id,)
    ).fetchone()["total"]

    present_attendance = conn.execute(
        """
        SELECT COUNT(*) AS total
        FROM attendance
        WHERE student_id = ?
        AND status = 'Present'
        """,
        (student_id,)
    ).fetchone()["total"]

    if total_attendance > 0:

        attendance_percentage = round(
            (
                present_attendance /
                total_attendance
            ) * 100,
            1
        )

    else:

        attendance_percentage = 0

    # Marks

    marks = conn.execute(
        """
        SELECT *
        FROM marks
        WHERE student_id = ?
        ORDER BY id DESC
        """,
        (student_id,)
    ).fetchall()

    # Notices

    notices = conn.execute(
        """
        SELECT *
        FROM notices
        ORDER BY created_at DESC
        LIMIT 5
        """
    ).fetchall()

    # Overall Performance

    total_obtained = sum(
        mark["marks_obtained"]
        for mark in marks
    )

    total_maximum = sum(
        mark["max_marks"]
        for mark in marks
    )

    if total_maximum > 0:

        performance_percentage = round(
            (
                total_obtained /
                total_maximum
            ) * 100,
            1
        )

    else:

        performance_percentage = 0

    conn.close()

    return (
        attendance_percentage,
        performance_percentage,
        marks,
        notices
    )


# ============================================================
# STUDENT DASHBOARD
# ============================================================

@app.route("/student/dashboard")
@login_required
def student_dashboard():

    if session.get("role") != "student":
        return "Access Denied", 403

    conn = get_db()

    student = conn.execute(
        """
        SELECT *
        FROM students
        WHERE user_id = ?
        LIMIT 1
        """,
        (session["user_id"],)
    ).fetchone()

    conn.close()

    if not student:

        return "Student profile not found.", 404

    (
        attendance_percentage,
        performance_percentage,
        marks,
        notices
    ) = get_student_dashboard_data(
        student["id"]
    )

    return render_template(
        "student_dashboard.html",
        student=student,
        marks=marks,
        notices=notices,
        attendance_percentage=attendance_percentage,
        total_percentage=performance_percentage,
        user_name=session.get("full_name"),
        role="Student"
    )

# ==============================
# STUDENT ATTENDANCE
# ==============================

@app.route("/student/attendance")
@login_required
def student_attendance():
    if session.get("role") != "student":
        return "Access Denied", 403

    conn = get_db()

    attendance = conn.execute("""
        SELECT
            attendance.attendance_date,
            attendance.status,
            students.full_name,
            students.roll_no
        FROM attendance
        JOIN students
            ON students.id = attendance.student_id
        WHERE students.user_id = ?
        ORDER BY attendance.attendance_date DESC
    """, (session["user_id"],)).fetchall()

    conn.close()

    return render_template(
        "student_attendance.html",
        attendance=attendance,
        user_name=session.get("full_name"),
        role="Student"
    )


# ==============================
# STUDENT MARKS
# ==============================

@app.route("/student/marks")
@login_required
def student_marks():
    if session.get("role") != "student":
        return "Access Denied", 403

    conn = get_db()

    marks = conn.execute("""
        SELECT
            marks.exam_name,
            marks.subject,
            marks.marks_obtained,
            marks.max_marks,
            students.full_name,
            students.roll_no
        FROM marks
        JOIN students
            ON students.id = marks.student_id
        WHERE students.user_id = ?
        ORDER BY marks.id DESC
    """, (session["user_id"],)).fetchall()

    conn.close()

    return render_template(
        "student_marks.html",
        marks=marks,
        user_name=session.get("full_name"),
        role="Student"
    )
# ==============================
# STUDENT PERFORMANCE
# ==============================

@app.route("/student/performance")
@login_required
def student_performance():
    if session.get("role") != "student":
        return "Access Denied", 403

    conn = get_db()

    performance = conn.execute("""
        SELECT
            students.full_name,
            students.roll_no,
            SUM(marks.marks_obtained) AS obtained,
            SUM(marks.max_marks) AS maximum
        FROM marks
        JOIN students
            ON students.id = marks.student_id
        WHERE students.user_id = ?
        GROUP BY students.id
    """, (session["user_id"],)).fetchall()

    conn.close()

    return render_template(
        "student_performance.html",
        performance=performance,
        user_name=session.get("full_name"),
        role="Student"
    )

# ==============================
# STUDENT NOTICES
# ==============================

@app.route("/student/notices")
@login_required
def student_notices():
    if session.get("role") != "student":
        return "Access Denied", 403

    conn = get_db()

    notices = conn.execute("""
        SELECT
            title,
            message,
            created_at
        FROM notices
        ORDER BY created_at DESC
    """).fetchall()

    conn.close()

    return render_template(
        "student_notices.html",
        notices=notices,
        user_name=session.get("full_name"),
        role="Student"
    )


# ============================================================
# PARENT DASHBOARD
# ============================================================

@app.route("/parent/dashboard")
@login_required
def parent_dashboard():

    if session.get("role") != "parent":
        return "Access Denied", 403

    conn = get_db()

    student = conn.execute(
        """
        SELECT students.*
        FROM parent_student
        JOIN students
        ON students.id = parent_student.student_id
        WHERE parent_student.parent_user_id = ?
        LIMIT 1
        """,
        (session["user_id"],)
    ).fetchone()

    conn.close()

    if not student:

        return (
            "No student is linked "
            "with this parent account.",
            404
        )

    (
        attendance_percentage,
        performance_percentage,
        marks,
        notices
    ) = get_student_dashboard_data(
        student["id"]
    )
    return render_template(
        "parent_dashboard.html",
        student=student,
        child=student,
        marks=marks,
        notices=notices,
        attendance_percentage=attendance_percentage,
        overall_percentage=performance_percentage,
        user_name=session.get("full_name"),
        role="Parent"
    )
 

@app.route("/parent/marks")
@login_required
def parent_marks():
    if session.get("role") != "parent":
        return "Access Denied", 403

    conn = get_db()

    marks = conn.execute("""
        SELECT
            marks.subject,
            marks.marks_obtained,
            marks.max_marks,
            marks.exam_name,
            students.full_name,
            students.roll_no
        FROM marks
        JOIN students
            ON students.id = marks.student_id
        JOIN parent_student
            ON parent_student.student_id = students.id
        WHERE parent_student.parent_user_id = ?
        ORDER BY marks.id DESC
    """, (session["user_id"],)).fetchall()

    conn.close()

    return render_template(
        "parent_marks.html",
        marks=marks,
        user_name=session.get("full_name"),
        role="Parent"
    )


@app.route("/parent/performance")
@login_required
def parent_performance():
    if session.get("role") != "parent":
        return "Access Denied", 403

    conn = get_db()

    performance = conn.execute("""
        SELECT
            students.full_name,
            students.roll_no,
            SUM(marks.marks_obtained) AS obtained,
            SUM(marks.max_marks) AS maximum
        FROM marks
        JOIN students
            ON students.id = marks.student_id
        JOIN parent_student
            ON parent_student.student_id = students.id
        WHERE parent_student.parent_user_id = ?
        GROUP BY students.id
    """, (session["user_id"],)).fetchall()

    conn.close()

    return render_template(
        "parent_performance.html",
        performance=performance,
        user_name=session.get("full_name"),
        role="Parent"
    )


@app.route("/parent/attendance")
@login_required
def parent_attendance():
    if session.get("role") != "parent":
        return "Access Denied", 403

    conn = get_db()

    attendance = conn.execute("""
        SELECT
            attendance.attendance_date,
            attendance.status,
            students.full_name,
            students.roll_no
        FROM attendance
        JOIN students
            ON students.id = attendance.student_id
        JOIN parent_student
            ON parent_student.student_id = students.id
        WHERE parent_student.parent_user_id = ?
        ORDER BY attendance.attendance_date DESC
    """, (session["user_id"],)).fetchall()

    conn.close()

    return render_template(
        "parent_attendance.html",
        attendance=attendance,
        user_name=session.get("full_name"),
        role="Parent"
    )

@app.route("/admin/parents")
@login_required
def admin_parents():
    if session.get("role") != "admin":
        return "Access Denied", 403

    conn = get_db()

    parents = conn.execute("""
        SELECT
            u.id,
            u.username,
            u.full_name,
            u.role,
            s.id AS student_id,
            s.full_name AS student_name,
            s.roll_no AS student_roll_no
        FROM users u
        LEFT JOIN parent_student ps
            ON ps.parent_user_id = u.id
        LEFT JOIN students s
            ON s.id = ps.student_id
        WHERE u.role = 'parent'
        ORDER BY u.id DESC
    """).fetchall()

    conn.close()

    return render_template(
        "parents.html",
        parents=parents,
        user_name=session.get("full_name"),
        role=session.get("role", "").title()
    )


@app.route("/admin/parents/<int:parent_id>/link-child", methods=["GET", "POST"])
@login_required
def link_parent_child(parent_id):
    if session.get("role") != "admin":
        return "Access Denied", 403

    conn = get_db()

    parent = conn.execute(
        """
        SELECT id, full_name, username
        FROM users
        WHERE id = ? AND role = 'parent'
        """,
        (parent_id,)
    ).fetchone()

    if not parent:
        conn.close()
        return "Parent not found", 404

    students = conn.execute(
        """
        SELECT id, full_name, roll_no, class_name, section
        FROM students
        ORDER BY full_name
        """
    ).fetchall()

    if request.method == "POST":
        student_id = request.form.get("student_id")

        if not student_id:
            conn.close()
            return "Please select a student", 400

        existing = conn.execute(
            """
            SELECT id
            FROM parent_student
            WHERE parent_user_id = ? AND student_id = ?
            """,
            (parent_id, student_id)
        ).fetchone()

        if not existing:
            conn.execute(
                """
                INSERT INTO parent_student
                (parent_user_id, student_id)
                VALUES (?, ?)
                """,
                (parent_id, student_id)
            )
            conn.commit()

        conn.close()
        return redirect(url_for("admin_parents")) 

    conn.close()

    return render_template(
        "link_parent_child.html",
        parent=parent,
        students=students,
        user_name=session.get("full_name"),
        role=session.get("role", "").title()
    )

@app.route("/admin/parents/add", methods=["GET", "POST"])
@login_required
def add_parent():
    if session.get("role") != "admin":
        return "Access Denied", 403

    conn = get_db()
    error = None

    students = conn.execute("""
        SELECT id, full_name, roll_no, class_name, section
        FROM students
        ORDER BY full_name
    """).fetchall()

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        student_id = request.form.get("student_id", "").strip()

        if not full_name or not username or not password or not student_id:
            error = "Please fill all fields."

        elif conn.execute(
            "SELECT id FROM users WHERE username = ?",
            (username,)
        ).fetchone():
            error = "Username already exists."

        else:
            try:
                password_column = get_password_column(conn)

                cur = conn.execute(
                    f"""
                    INSERT INTO users
                    (username, {password_column}, full_name, role)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        username,
                        generate_password_hash(password),
                        full_name,
                        "parent"
                    )
                )

                parent_user_id = cur.lastrowid

                conn.execute(
                    """
                    INSERT INTO parent_student
                    (parent_user_id, student_id)
                    VALUES (?, ?)
                    """,
                    (parent_user_id, student_id)
                )

                conn.commit()
                conn.close()

                return redirect(url_for("admin_parents"))

            except sqlite3.IntegrityError:
                conn.rollback()
                error = "This parent account or student link already exists."

    conn.close()

    return render_template(
        "add_parent.html",
        students=students,
        error=error
    )



# ============================================================
# START APPLICATION
# ============================================================

init_db()


if __name__ == "__main__":

    app.run(
        debug=False,
        use_reloader=False
    )
