import os
import sqlite3
from datetime import datetime
import pandas as pd

DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "attendance.db")
EXCEL_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "attendance.xlsx")


def get_connection():
    """Returns a connection to the SQLite database with row-access capabilities."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initializes the database schema and performs non-destructive migrations."""
    conn = get_connection()
    cursor = conn.cursor()

    # 1. Ensure students table exists
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            roll_no TEXT UNIQUE,
            name TEXT NOT NULL,
            course TEXT,
            department TEXT,
            semester TEXT,
            gender TEXT,
            contact TEXT,
            created_at TEXT
        )
    """)

    # 2. Ensure attendance table exists
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            roll_no TEXT,
            name TEXT,
            course TEXT,
            date TEXT,
            time TEXT,
            status TEXT
        )
    """)

    # 3. Check for existing columns in attendance and migrate if needed
    cursor.execute("PRAGMA table_info(attendance)")
    existing_cols = [col["name"] for col in cursor.fetchall()]

    if "roll_no" not in existing_cols:
        cursor.execute("ALTER TABLE attendance ADD COLUMN roll_no TEXT")
    if "course" not in existing_cols:
        cursor.execute("ALTER TABLE attendance ADD COLUMN course TEXT")
    if "status" not in existing_cols:
        cursor.execute("ALTER TABLE attendance ADD COLUMN status TEXT")

    # Update existing attendance records where status is null
    cursor.execute("UPDATE attendance SET status = 'Present' WHERE status IS NULL")

    conn.commit()
    conn.close()


def add_student(roll_no, name, course, department, semester, gender, contact):
    """Registers a new student. Returns the new student ID."""
    conn = get_connection()
    cursor = conn.cursor()
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
        INSERT INTO students (roll_no, name, course, department, semester, gender, contact, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (roll_no.strip(), name.strip(), course.strip(), department.strip(), semester.strip(), gender.strip(), contact.strip(), created_at))

    student_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return student_id


def update_student(student_id, roll_no, name, course, department, semester, gender, contact):
    """Updates an existing student's details."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE students
        SET roll_no = ?, name = ?, course = ?, department = ?, semester = ?, gender = ?, contact = ?
        WHERE id = ?
    """, (roll_no.strip(), name.strip(), course.strip(), department.strip(), semester.strip(), gender.strip(), contact.strip(), student_id))
    conn.commit()
    conn.close()


def delete_student(student_id):
    """Deletes a student by ID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM students WHERE id = ?", (student_id,))
    conn.commit()
    conn.close()


def get_all_students():
    """Retrieves all registered students."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM students ORDER BY id ASC")
    students = cursor.fetchall()
    conn.close()
    return students


def get_student_by_id(student_id):
    """Fetches a single student by numeric ID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM students WHERE id = ?", (student_id,))
    student = cursor.fetchone()
    conn.close()
    return student


def get_student_by_roll_no(roll_no):
    """Fetches a single student by Roll Number."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM students WHERE roll_no = ?", (roll_no,))
    student = cursor.fetchone()
    conn.close()
    return student


def get_next_suggested_student_info():
    """Generates the next suggested student ID and formatted Roll Number."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(id) as max_id, COUNT(*) as cnt FROM students")
    row = cursor.fetchone()
    conn.close()

    if row and row["cnt"] > 0 and row["max_id"] is not None:
        next_id = row["max_id"] + 1
    else:
        next_id = 1
    suggested_roll = f"STU-{next_id:03d}"
    return next_id, suggested_roll


def clear_all_data():
    """Clears all student records, attendance logs, and resets SQLite sequences."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM students")
    cursor.execute("DELETE FROM attendance")
    try:
        cursor.execute("DELETE FROM sqlite_sequence WHERE name IN ('students', 'attendance')")
    except Exception:
        pass
    conn.commit()
    conn.close()
    try:
        export_attendance_to_excel()
    except Exception:
        pass


def mark_attendance(roll_no, name, course=None, status="Present"):
    """
    Marks attendance for a student on the current date.
    Prevents duplicate attendance for the same student on the same calendar date.
    Returns a tuple: (success: bool, message: str)
    """
    today_date = datetime.now().strftime("%Y-%m-%d")
    current_time = datetime.now().strftime("%H:%M:%S")

    conn = get_connection()
    cursor = conn.cursor()

    # Check if student already marked present today
    cursor.execute("""
        SELECT id FROM attendance
        WHERE (roll_no = ? OR (roll_no IS NULL AND name = ?)) AND date = ?
    """, (roll_no, name, today_date))

    existing = cursor.fetchone()
    if existing:
        conn.close()
        return False, f"Attendance already recorded today for {name}"

    # If course is not provided, look it up
    if not course:
        cursor.execute("SELECT course FROM students WHERE roll_no = ? OR name = ?", (roll_no, name))
        stu = cursor.fetchone()
        course = stu["course"] if stu and stu["course"] else "General"

    cursor.execute("""
        INSERT INTO attendance (roll_no, name, course, date, time, status)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (roll_no, name, course, today_date, current_time, status))

    conn.commit()
    conn.close()

    # Auto sync to Excel
    try:
        export_attendance_to_excel()
    except Exception:
        pass

    return True, f"Attendance marked for {name} ({roll_no})"


def get_attendance_records(date_filter=None, name_filter=None):
    """Fetches attendance records with optional filtering."""
    conn = get_connection()
    cursor = conn.cursor()

    query = "SELECT id, COALESCE(roll_no, 'N/A') as roll_no, name, COALESCE(course, 'General') as course, date, time, COALESCE(status, 'Present') as status FROM attendance WHERE 1=1"
    params = []

    if date_filter:
        query += " AND date = ?"
        params.append(date_filter)
    if name_filter:
        query += " AND (name LIKE ? OR roll_no LIKE ?)"
        params.append(f"%{name_filter}%")
        params.append(f"%{name_filter}%")

    query += " ORDER BY id DESC"
    cursor.execute(query, params)
    records = cursor.fetchall()
    conn.close()
    return records


def export_attendance_to_excel(excel_path=None):
    """Exports all attendance records to an Excel file using pandas."""
    if not excel_path:
        excel_path = EXCEL_FILE

    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT id, COALESCE(roll_no, 'N/A') as roll_no, name, COALESCE(course, 'General') as course, date, time, COALESCE(status, 'Present') as status
        FROM attendance
        ORDER BY id ASC
    """, conn)
    conn.close()

    df.to_excel(excel_path, index=False)
    return excel_path


def delete_attendance_record(record_id):
    """Deletes an attendance record by ID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM attendance WHERE id = ?", (record_id,))
    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")
    students = get_all_students()
    print(f"Total students registered: {len(students)}")
    for s in students:
        print(f"- ID: {s['id']}, Roll: {s['roll_no']}, Name: {s['name']}, Course: {s['course']}")
