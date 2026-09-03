import os
import sys
import time
import threading
import subprocess
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import cv2
from PIL import Image

import database
import train_model
from face_recognition_system import FaceRecognitionSystem

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CASCADE_PATH = os.path.join(BASE_DIR, "haarcascade_frontalface_default.xml")
PROFILE_CASCADE_PATH = os.path.join(BASE_DIR, "haarcascade_profileface.xml")
IMAGES_DIR = os.path.join(BASE_DIR, "images")
EXCEL_FILE = os.path.join(BASE_DIR, "attendance.xlsx")


class AttendanceApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Face Recognition Attendance System")
        self.root.geometry("1280x760")
        self.root.minsize(1100, 680)

        # Apply system styling
        self.style = ttk.Style()
        self.style.theme_use("clam")
        self.configure_styles()

        # Initialize Database
        database.init_db()

        # State variables
        self.var_id = tk.StringVar()
        self.var_roll = tk.StringVar()
        self.var_name = tk.StringVar()
        self.var_course = tk.StringVar()
        self.var_dept = tk.StringVar()
        self.var_sem = tk.StringVar()
        self.var_gender = tk.StringVar()
        self.var_contact = tk.StringVar()
        self.var_search_student = tk.StringVar()
        self.var_search_attendance = tk.StringVar()
        self.var_date_filter = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))

        # Build UI Layout
        self.create_header()
        self.create_footer()
        self.create_main_tabs()

        # Initial data loading
        self.load_students_table()
        self.load_attendance_table()

        # Start live clock updater
        self.update_clock()

    def configure_styles(self):
        """Configure modern widgets, treeview styles and colors."""
        self.colors = {
            "bg_dark": "#0f172a",       # Slate 900
            "panel": "#1e293b",         # Slate 800
            "panel_light": "#334155",   # Slate 700
            "text": "#f8fafc",          # Slate 50
            "muted": "#94a3b8",         # Slate 400
            "accent_blue": "#2563eb",   # Blue 600
            "accent_hover": "#1d4ed8",  # Blue 700
            "green": "#059669",         # Emerald 600
            "amber": "#d97706",         # Amber 600
            "red": "#dc2626",           # Red 600
            "border": "#475569"
        }

        self.root.configure(bg=self.colors["bg_dark"])

        self.style.configure("TNotebook", background=self.colors["bg_dark"], borderwidth=0)
        self.style.configure(
            "TNotebook.Tab",
            background=self.colors["panel"],
            foreground=self.colors["text"],
            padding=[18, 8],
            font=("Segoe UI", 10, "bold")
        )
        self.style.map(
            "TNotebook.Tab",
            background=[("selected", self.colors["accent_blue"])],
            foreground=[("selected", "#ffffff")]
        )

        self.style.configure(
            "Treeview",
            background="#ffffff",
            foreground="#1e293b",
            rowheight=26,
            fieldbackground="#ffffff",
            font=("Segoe UI", 9)
        )
        self.style.configure(
            "Treeview.Heading",
            background=self.colors["panel"],
            foreground="#ffffff",
            font=("Segoe UI", 9, "bold")
        )
        self.style.map("Treeview.Heading", background=[("active", self.colors["accent_blue"])])

    def create_header(self):
        """Top banner with Title, Subtitle, and Live Clock."""
        header_frame = tk.Frame(self.root, bg=self.colors["panel"], height=75)
        header_frame.pack(fill=tk.X, side=tk.TOP)

        title_container = tk.Frame(header_frame, bg=self.colors["panel"])
        title_container.pack(side=tk.LEFT, padx=25, pady=12)

        lbl_title = tk.Label(
            title_container,
            text="FACE RECOGNITION ATTENDANCE SYSTEM",
            font=("Segoe UI", 16, "bold"),
            fg="#ffffff",
            bg=self.colors["panel"]
        )
        lbl_title.pack(anchor="w")

        lbl_sub = tk.Label(
            title_container,
            text="Automated Student Attendance & Facial Recognition Management",
            font=("Segoe UI", 9),
            fg=self.colors["muted"],
            bg=self.colors["panel"]
        )
        lbl_sub.pack(anchor="w")

        # Right-side Live Clock and Quick Action Buttons
        right_container = tk.Frame(header_frame, bg=self.colors["panel"])
        right_container.pack(side=tk.RIGHT, padx=25, pady=12)

        self.lbl_clock = tk.Label(
            right_container,
            text="",
            font=("Segoe UI", 11, "bold"),
            fg="#38bdf8",
            bg=self.colors["panel"]
        )
        self.lbl_clock.pack(anchor="e")

        btn_about = tk.Button(
            right_container,
            text="About System",
            command=self.show_about,
            bg=self.colors["panel_light"],
            fg="#ffffff",
            activebackground=self.colors["accent_blue"],
            activeforeground="#ffffff",
            font=("Segoe UI", 8),
            relief="flat",
            padx=10,
            pady=2,
            cursor="hand2"
        )
        btn_about.pack(anchor="e", pady=(4, 0))

    def update_clock(self):
        """Updates live digital clock every second."""
        now_str = datetime.now().strftime("%A, %d %B %Y | %I:%M:%S %p")
        self.lbl_clock.config(text=now_str)
        self.root.after(1000, self.update_clock)

    def create_main_tabs(self):
        """Creates notebook with tabs for Dashboard, Students, and Attendance."""
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=20, pady=(15, 10))

        # 1. Main Dashboard Tab
        self.tab_dashboard = tk.Frame(self.notebook, bg=self.colors["bg_dark"])
        self.notebook.add(self.tab_dashboard, text="  Dashboard & Camera  ")
        self.build_dashboard_tab()

        # 2. Student Registration Tab
        self.tab_students = tk.Frame(self.notebook, bg=self.colors["bg_dark"])
        self.notebook.add(self.tab_students, text="  Student Registration  ")
        self.build_students_tab()

        # 3. Attendance Records Tab
        self.tab_attendance = tk.Frame(self.notebook, bg=self.colors["bg_dark"])
        self.notebook.add(self.tab_attendance, text="  Attendance Records & Excel  ")
        self.build_attendance_tab()

    # =========================================================================
    # TAB 1: DASHBOARD & QUICK ACTIONS
    # =========================================================================
    def build_dashboard_tab(self):
        # Stats Cards Row
        stats_frame = tk.Frame(self.tab_dashboard, bg=self.colors["bg_dark"])
        stats_frame.pack(fill=tk.X, padx=20, pady=20)

        self.card_students = self.create_stat_card(stats_frame, "Total Students", "0", self.colors["accent_blue"])
        self.card_today_att = self.create_stat_card(stats_frame, "Today's Attendance", "0", self.colors["green"])
        self.card_total_att = self.create_stat_card(stats_frame, "Total Logs", "0", self.colors["amber"])

        # Main Action Banner Cards
        cards_container = tk.Frame(self.tab_dashboard, bg=self.colors["bg_dark"])
        cards_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        # Configure 3 equal columns
        cards_container.columnconfigure(0, weight=1)
        cards_container.columnconfigure(1, weight=1)
        cards_container.columnconfigure(2, weight=1)

        # Card 1: Face Recognition
        self.create_action_card(
            cards_container,
            col=0,
            title="TAKE ATTENDANCE",
            desc="Launch real-time facial recognition camera to detect faces, recognize students, and record present timestamps automatically.",
            btn_text="Start Camera Recognition",
            btn_color=self.colors["green"],
            action=self.start_attendance_camera
        )

        # Card 2: Train Classifier
        self.create_action_card(
            cards_container,
            col=1,
            title="TRAIN CLASSIFIER",
            desc="Train the LBPH face recognition model on all captured student face crops saved in images/ dataset to update classifier.xml.",
            btn_text="Train Face Model",
            btn_color=self.colors["accent_blue"],
            action=self.start_training_thread
        )

        # Card 3: Export & Open Excel
        self.create_action_card(
            cards_container,
            col=2,
            title="ATTENDANCE EXCEL",
            desc="Export full attendance history into attendance.xlsx or open the spreadsheet directly for reporting and administration.",
            btn_text="Export / Open Excel",
            btn_color=self.colors["amber"],
            action=self.export_and_open_excel
        )

        # Bottom Utilities Bar
        utils_bar = tk.Frame(self.tab_dashboard, bg=self.colors["panel"])
        utils_bar.pack(fill=tk.X, padx=20, pady=(15, 20))

        lbl_util = tk.Label(
            utils_bar,
            text="Quick Tools:",
            font=("Segoe UI", 10, "bold"),
            fg="#ffffff",
            bg=self.colors["panel"]
        )
        lbl_util.pack(side=tk.LEFT, padx=15, pady=12)

        btn_photos = tk.Button(
            utils_bar,
            text="Open Images Folder",
            command=self.open_images_folder,
            bg=self.colors["panel_light"],
            fg="#ffffff",
            font=("Segoe UI", 9),
            relief="flat",
            padx=12,
            pady=4,
            cursor="hand2"
        )
        btn_photos.pack(side=tk.LEFT, padx=5)

        btn_refresh = tk.Button(
            utils_bar,
            text="Refresh Dashboard Stats",
            command=self.update_dashboard_stats,
            bg=self.colors["panel_light"],
            fg="#ffffff",
            font=("Segoe UI", 9),
            relief="flat",
            padx=12,
            pady=4,
            cursor="hand2"
        )
        btn_refresh.pack(side=tk.LEFT, padx=5)

        # Initial update of dashboard numbers
        self.update_dashboard_stats()

    def create_stat_card(self, parent, title, value, color):
        card = tk.Frame(parent, bg=self.colors["panel"], highlightbackground=color, highlightthickness=1)
        card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10)

        lbl_val = tk.Label(card, text=value, font=("Segoe UI", 24, "bold"), fg=color, bg=self.colors["panel"])
        lbl_val.pack(anchor="w", padx=20, pady=(15, 2))

        lbl_title = tk.Label(card, text=title.upper(), font=("Segoe UI", 9, "bold"), fg=self.colors["muted"], bg=self.colors["panel"])
        lbl_title.pack(anchor="w", padx=20, pady=(0, 15))

        return lbl_val

    def create_action_card(self, parent, col, title, desc, btn_text, btn_color, action):
        card = tk.Frame(parent, bg=self.colors["panel"], highlightbackground=self.colors["border"], highlightthickness=1)
        card.grid(row=0, column=col, sticky="nsew", padx=10, pady=10)

        title_lbl = tk.Label(card, text=title, font=("Segoe UI", 13, "bold"), fg="#ffffff", bg=self.colors["panel"])
        title_lbl.pack(anchor="w", padx=20, pady=(20, 10))

        desc_lbl = tk.Label(
            card,
            text=desc,
            font=("Segoe UI", 9),
            fg=self.colors["muted"],
            bg=self.colors["panel"],
            wraplength=280,
            justify=tk.LEFT
        )
        desc_lbl.pack(anchor="w", padx=20, pady=(0, 20), fill=tk.BOTH, expand=True)

        btn = tk.Button(
            card,
            text=btn_text,
            command=action,
            bg=btn_color,
            fg="#ffffff",
            activebackground="#ffffff",
            activeforeground=btn_color,
            font=("Segoe UI", 10, "bold"),
            relief="flat",
            pady=10,
            cursor="hand2"
        )
        btn.pack(fill=tk.X, padx=20, pady=(0, 20))

    def update_dashboard_stats(self):
        """Recalculates counts for dashboard cards."""
        try:
            students = database.get_all_students()
            today_date = datetime.now().strftime("%Y-%m-%d")
            today_att = database.get_attendance_records(date_filter=today_date)
            all_att = database.get_attendance_records()

            self.card_students.config(text=str(len(students)))
            self.card_today_att.config(text=str(len(today_att)))
            self.card_total_att.config(text=str(len(all_att)))
            self.set_status(f"Dashboard refreshed. Total students: {len(students)}, Today's attendance: {len(today_att)}")
        except Exception as e:
            self.set_status(f"Error updating stats: {e}")

    # =========================================================================
    # TAB 2: STUDENT REGISTRATION
    # =========================================================================
    def build_students_tab(self):
        container = tk.Frame(self.tab_students, bg=self.colors["bg_dark"])
        container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Left Panel: Registration Form
        left_frame = tk.LabelFrame(
            container,
            text=" Student Information Form ",
            font=("Segoe UI", 10, "bold"),
            fg="#ffffff",
            bg=self.colors["panel"],
            padx=15,
            pady=15
        )
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=5)

        fields = [
            ("Student ID (Auto):", self.var_id, True),
            ("Roll Number *:", self.var_roll, False),
            ("Full Name *:", self.var_name, False),
            ("Course *:", self.var_course, False),
            ("Department:", self.var_dept, False),
            ("Semester:", self.var_sem, False),
            ("Gender:", self.var_gender, False),
            ("Contact Number:", self.var_contact, False),
        ]

        course_options = ["B.Tech (CSE)", "B.Tech (IT)", "B.Tech (ECE)", "BCA", "MCA", "B.Sc", "M.Tech", "MBA"]
        dept_options = ["Computer Science", "Information Technology", "Electronics", "Mechanical", "Civil", "Management"]
        sem_options = ["1st Semester", "2nd Semester", "3rd Semester", "4th Semester", "5th Semester", "6th Semester", "7th Semester", "8th Semester"]
        gender_options = ["Male", "Female", "Other"]

        for idx, (label_text, var, is_readonly) in enumerate(fields):
            lbl = tk.Label(left_frame, text=label_text, font=("Segoe UI", 9, "bold"), fg=self.colors["text"], bg=self.colors["panel"])
            lbl.grid(row=idx, column=0, sticky="w", pady=4, padx=5)

            if label_text.startswith("Course"):
                entry = ttk.Combobox(left_frame, textvariable=var, values=course_options, width=24, state="normal")
                self.combo_course = entry
            elif label_text.startswith("Department"):
                entry = ttk.Combobox(left_frame, textvariable=var, values=dept_options, width=24, state="normal")
            elif label_text.startswith("Semester"):
                entry = ttk.Combobox(left_frame, textvariable=var, values=sem_options, width=24, state="normal")
            elif label_text.startswith("Gender"):
                entry = ttk.Combobox(left_frame, textvariable=var, values=gender_options, width=24, state="readonly")
            else:
                entry = tk.Entry(left_frame, textvariable=var, font=("Segoe UI", 9), width=26, bg="#ffffff")
                if is_readonly:
                    entry.config(state="readonly")
                if label_text.startswith("Roll Number"):
                    self.ent_roll = entry
                elif label_text.startswith("Full Name"):
                    self.ent_name = entry

            entry.grid(row=idx, column=1, sticky="w", pady=4, padx=5)

        # Form Buttons Grid
        btn_frame = tk.Frame(left_frame, bg=self.colors["panel"])
        btn_frame.grid(row=len(fields), column=0, columnspan=2, pady=(15, 0), sticky="ew")

        # Top Prominent Action Buttons: "Add New Student" & "Register Student"
        primary_btn_grid = tk.Frame(btn_frame, bg=self.colors["panel"])
        primary_btn_grid.pack(fill=tk.X, pady=(0, 6))

        btn_add_new = tk.Button(
            primary_btn_grid,
            text="➕ Add New Student",
            command=self.prepare_add_new_student,
            bg=self.colors["green"],
            fg="#ffffff",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            pady=7,
            cursor="hand2"
        )
        btn_add_new.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 3))

        btn_register = tk.Button(
            primary_btn_grid,
            text="📝 Register Student",
            command=self.save_student,
            bg=self.colors["accent_blue"],
            fg="#ffffff",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            pady=7,
            cursor="hand2"
        )
        btn_register.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(3, 0))

        # Photo capture button for 6-Angle Face Dataset
        btn_take_photo = tk.Button(
            btn_frame,
            text="📸 Multi-Angle Face Capture (6 Angles / 60 Photos)",
            command=self.capture_face_samples,
            bg=self.colors["panel_light"],
            fg="#38bdf8",
            activebackground=self.colors["accent_blue"],
            activeforeground="#ffffff",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            pady=7,
            cursor="hand2"
        )
        btn_take_photo.pack(fill=tk.X, pady=(0, 8))

        # Secondary Actions: Update, Delete, Clear
        secondary_btn_grid = tk.Frame(btn_frame, bg=self.colors["panel"])
        secondary_btn_grid.pack(fill=tk.X)

        btn_update = tk.Button(
            secondary_btn_grid,
            text="✏️ Update",
            command=self.update_student,
            bg=self.colors["panel_light"],
            fg="#ffffff",
            font=("Segoe UI", 8, "bold"),
            relief="flat",
            width=9,
            pady=4,
            cursor="hand2"
        )
        btn_update.pack(side=tk.LEFT, expand=True, padx=2)

        btn_delete = tk.Button(
            secondary_btn_grid,
            text="🗑️ Delete",
            command=self.delete_student,
            bg=self.colors["red"],
            fg="#ffffff",
            font=("Segoe UI", 8, "bold"),
            relief="flat",
            width=9,
            pady=4,
            cursor="hand2"
        )
        btn_delete.pack(side=tk.LEFT, expand=True, padx=2)

        btn_reset = tk.Button(
            secondary_btn_grid,
            text="🔄 Clear",
            command=self.clear_student_form,
            bg=self.colors["panel_light"],
            fg="#ffffff",
            font=("Segoe UI", 8, "bold"),
            relief="flat",
            width=9,
            pady=4,
            cursor="hand2"
        )
        btn_reset.pack(side=tk.LEFT, expand=True, padx=2)

        # Right Panel: Student Table
        right_frame = tk.LabelFrame(
            container,
            text=" Registered Students Database ",
            font=("Segoe UI", 10, "bold"),
            fg="#ffffff",
            bg=self.colors["panel"],
            padx=10,
            pady=10
        )
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Search Bar
        search_frame = tk.Frame(right_frame, bg=self.colors["panel"])
        search_frame.pack(fill=tk.X, pady=(0, 10))

        lbl_search = tk.Label(search_frame, text="Search:", font=("Segoe UI", 9, "bold"), fg=self.colors["text"], bg=self.colors["panel"])
        lbl_search.pack(side=tk.LEFT, padx=5)

        ent_search = tk.Entry(search_frame, textvariable=self.var_search_student, font=("Segoe UI", 9), width=24)
        ent_search.pack(side=tk.LEFT, padx=5)

        btn_search = tk.Button(
            search_frame,
            text="Search",
            command=self.search_students,
            bg=self.colors["accent_blue"],
            fg="#ffffff",
            font=("Segoe UI", 8, "bold"),
            relief="flat",
            padx=10,
            cursor="hand2"
        )
        btn_search.pack(side=tk.LEFT, padx=5)

        btn_all = tk.Button(
            search_frame,
            text="Show All",
            command=self.load_students_table,
            bg=self.colors["panel_light"],
            fg="#ffffff",
            font=("Segoe UI", 8),
            relief="flat",
            padx=10,
            cursor="hand2"
        )
        btn_all.pack(side=tk.LEFT, padx=5)

        # Table with Scrollbar
        table_container = tk.Frame(right_frame)
        table_container.pack(fill=tk.BOTH, expand=True)

        scroll_y = ttk.Scrollbar(table_container, orient=tk.VERTICAL)
        scroll_x = ttk.Scrollbar(table_container, orient=tk.HORIZONTAL)

        cols = ("id", "roll_no", "name", "course", "department", "semester", "gender", "contact")
        self.student_tree = ttk.Treeview(
            table_container,
            columns=cols,
            show="headings",
            yscrollcommand=scroll_y.set,
            xscrollcommand=scroll_x.set
        )

        scroll_y.config(command=self.student_tree.yview)
        scroll_x.config(command=self.student_tree.xview)

        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.student_tree.pack(fill=tk.BOTH, expand=True)

        col_widths = {
            "id": 45,
            "roll_no": 90,
            "name": 140,
            "course": 110,
            "department": 120,
            "semester": 90,
            "gender": 70,
            "contact": 100
        }

        for col in cols:
            self.student_tree.heading(col, text=col.replace("_", " ").title())
            self.student_tree.column(col, width=col_widths.get(col, 100), anchor="w")

        self.student_tree.bind("<<TreeviewSelect>>", self.on_student_select)

    def load_students_table(self, filter_query=None):
        """Loads students from SQLite into Treeview."""
        self.student_tree.delete(*self.student_tree.get_children())
        students = database.get_all_students()

        for s in students:
            if filter_query:
                q = filter_query.lower()
                matches = (
                    q in str(s["id"]).lower() or
                    q in str(s["roll_no"]).lower() or
                    q in str(s["name"]).lower() or
                    q in str(s["course"]).lower()
                )
                if not matches:
                    continue

            self.student_tree.insert("", tk.END, values=(
                s["id"],
                s["roll_no"],
                s["name"],
                s["course"],
                s["department"],
                s["semester"],
                s["gender"],
                s["contact"]
            ))

    def on_student_select(self, event):
        """Populates form when a row in student tree is clicked."""
        selected_item = self.student_tree.focus()
        if not selected_item:
            return
        row = self.student_tree.item(selected_item)["values"]
        if row:
            self.var_id.set(row[0])
            self.var_roll.set(row[1])
            self.var_name.set(row[2])
            self.var_course.set(row[3])
            self.var_dept.set(row[4])
            self.var_sem.set(row[5])
            self.var_gender.set(row[6])
            self.var_contact.set(row[7])

    def search_students(self):
        query = self.var_search_student.get().strip()
        self.load_students_table(filter_query=query)

    def clear_student_form(self):
        self.var_id.set("")
        self.var_roll.set("")
        self.var_name.set("")
        self.var_course.set("")
        self.var_dept.set("")
        self.var_sem.set("")
        self.var_gender.set("")
        self.var_contact.set("")

    def prepare_add_new_student(self):
        """Prepares form for registering a new student with auto-incremented suggested ID and Roll Number."""
        self.clear_student_form()
        next_id, suggested_roll = database.get_next_suggested_student_info()
        self.var_id.set(str(next_id))
        self.var_roll.set(suggested_roll)
        if hasattr(self, "ent_name"):
            self.ent_name.focus_set()

        self.set_status(f"Ready to register Student #{next_id} ({suggested_roll}). Enter Full Name & Course, then click 'Register Student'.")

    def save_student(self):
        """Validates and registers new student, then prompts for multi-angle face capture."""
        roll = self.var_roll.get().strip()
        name = self.var_name.get().strip()
        course = self.var_course.get().strip()

        if not roll or not name:
            messagebox.showerror("Validation Error", "Roll Number and Full Name are required to register a student!")
            return

        try:
            existing = database.get_student_by_roll_no(roll)
            if existing:
                messagebox.showerror("Error", f"A student with Roll Number '{roll}' is already registered in the system!")
                return

            new_id = database.add_student(
                roll_no=roll,
                name=name,
                course=course,
                department=self.var_dept.get().strip(),
                semester=self.var_sem.get().strip(),
                gender=self.var_gender.get().strip(),
                contact=self.var_contact.get().strip()
            )
            self.var_id.set(str(new_id))
            self.load_students_table()
            self.update_dashboard_stats()
            self.set_status(f"Student '{name}' registered with ID {new_id}.")

            capture_now = messagebox.askyesno(
                "Student Registered Successfully",
                f"Student '{name}' (Roll No: {roll}) has been registered!\n\n"
                "Would you like to start the Multi-Angle Face Capture (6 angles: eyes, nose, lips, cheeks, hairstyle, facial structure) now?"
            )
            if capture_now:
                self.capture_face_samples()

        except Exception as e:
            messagebox.showerror("Registration Error", str(e))

    def update_student(self):
        student_id = self.var_id.get().strip()
        if not student_id:
            messagebox.showwarning("Selection Required", "Please select a student from the table to update.")
            return

        try:
            database.update_student(
                student_id=int(student_id),
                roll_no=self.var_roll.get().strip(),
                name=self.var_name.get().strip(),
                course=self.var_course.get().strip(),
                department=self.var_dept.get().strip(),
                semester=self.var_sem.get().strip(),
                gender=self.var_gender.get().strip(),
                contact=self.var_contact.get().strip()
            )
            self.load_students_table()
            messagebox.showinfo("Success", "Student information updated successfully.")
        except Exception as e:
            messagebox.showerror("Update Error", str(e))

    def delete_student(self):
        student_id = self.var_id.get().strip()
        name = self.var_name.get().strip()
        if not student_id:
            messagebox.showwarning("Selection Required", "Please select a student from the table to delete.")
            return

        confirm = messagebox.askyesno("Confirm Deletion", f"Are you sure you want to delete student '{name}' (ID: {student_id})?")
        if confirm:
            try:
                database.delete_student(int(student_id))
                self.clear_student_form()
                self.load_students_table()
                self.update_dashboard_stats()
                messagebox.showinfo("Deleted", f"Student '{name}' removed successfully.")
            except Exception as e:
                messagebox.showerror("Error", str(e))

    def capture_face_samples(self):
        """
        Captures 60 multi-angle face samples across 6 distinct stages:
        Stage 1 (1-10): Look Straight (Eyes, Eyebrows, Nose Bridge, Hairstyle)
        Stage 2 (11-20): Turn Slightly Left (Left Cheekbone, Jawline, Left Profile)
        Stage 3 (21-30): Turn Slightly Right (Right Cheekbone, Jawline, Right Profile)
        Stage 4 (31-40): Tilt Slightly Up (Chin, Neck Contour, Lower Nose)
        Stage 5 (41-50): Tilt Slightly Down (Forehead, Eyebrows, Hairline)
        Stage 6 (51-60): Smile / Expression (Lips, Smile Lines, Cheek Elevation)
        Applies Contrast-Limited Adaptive Histogram Equalization (CLAHE) for texture clarity.
        """
        student_id = self.var_id.get().strip()
        name = self.var_name.get().strip()
        roll = self.var_roll.get().strip()

        if not name or not roll:
            messagebox.showwarning("Information Needed", "Please enter Roll Number and Full Name (and register student) before capturing face samples.")
            return

        if not student_id:
            try:
                student_id = str(database.add_student(
                    roll_no=roll,
                    name=name,
                    course=self.var_course.get().strip(),
                    department=self.var_dept.get().strip(),
                    semester=self.var_sem.get().strip(),
                    gender=self.var_gender.get().strip(),
                    contact=self.var_contact.get().strip()
                ))
                self.var_id.set(student_id)
                self.load_students_table()
                self.update_dashboard_stats()
            except Exception as e:
                messagebox.showerror("Error", f"Could not auto-register student: {e}")
                return

        # Prepare folder: images/<id>_<name>
        clean_name = "".join(c for c in name if c.isalnum() or c in (" ", "_")).rstrip().replace(" ", "_")
        target_dir = os.path.join(IMAGES_DIR, f"{student_id}_{clean_name}")
        os.makedirs(target_dir, exist_ok=True)

        if not os.path.exists(CASCADE_PATH):
            messagebox.showerror("Error", f"Haar frontal face cascade missing at: {CASCADE_PATH}")
            return

        face_cascade = cv2.CascadeClassifier(CASCADE_PATH)
        profile_cascade = None
        if os.path.exists(PROFILE_CASCADE_PATH):
            profile_cascade = cv2.CascadeClassifier(PROFILE_CASCADE_PATH)

        # Initialize CLAHE contrast equalizer for rich facial texture representation
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))

        # Open webcam
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not cap.isOpened():
            cap = cv2.VideoCapture(0)

        if not cap.isOpened():
            messagebox.showerror("Camera Error", "Cannot access webcam! Please verify camera connection.")
            return

        sample_count = 0
        target_samples = 60

        STAGES = [
            {
                "stage_num": 1,
                "title": "STAGE 1/6: LOOK STRAIGHT",
                "features": "Eyes, Eyebrows, Nose Bridge & Hairstyle",
                "instruction": "Look straight at the camera with a neutral face",
                "symbol": "[ o   o ]",
                "max_sample": 10,
                "color": (0, 230, 0),  # Emerald Green
            },
            {
                "stage_num": 2,
                "title": "STAGE 2/6: TURN SLIGHTLY LEFT",
                "features": "Left Cheekbone, Jawline & Ear Profile",
                "instruction": "Slowly turn your face slightly LEFT <-",
                "symbol": "<- TURN LEFT",
                "max_sample": 20,
                "color": (255, 190, 0),  # Cyan
            },
            {
                "stage_num": 3,
                "title": "STAGE 3/6: TURN SLIGHTLY RIGHT",
                "features": "Right Cheekbone, Jawline & Ear Profile",
                "instruction": "Slowly turn your face slightly RIGHT ->",
                "symbol": "TURN RIGHT ->",
                "max_sample": 30,
                "color": (255, 190, 0),
            },
            {
                "stage_num": 4,
                "title": "STAGE 4/6: TILT SLIGHTLY UP",
                "features": "Chin Structure, Neck Contour & Lower Nose",
                "instruction": "Tilt your chin slightly UPWARDS ^",
                "symbol": "^ TILT UP",
                "max_sample": 40,
                "color": (0, 165, 255),  # Amber / Orange
            },
            {
                "stage_num": 5,
                "title": "STAGE 5/6: TILT SLIGHTLY DOWN",
                "features": "Forehead, Eyebrows & Hairline Contour",
                "instruction": "Tilt your head slightly DOWNWARDS v",
                "symbol": "v TILT DOWN",
                "max_sample": 50,
                "color": (0, 165, 255),
            },
            {
                "stage_num": 6,
                "title": "STAGE 6/6: SMILE & EXPRESSION",
                "features": "Lips, Smile Lines & Facial Muscle Movement",
                "instruction": "Smile naturally (: or speak slightly",
                "symbol": "(: SMILE :)",
                "max_sample": 60,
                "color": (220, 0, 220),  # Magenta
            },
        ]

        window_name = f"Multi-Angle Face Capture: {name} (6 Stages)"
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(window_name, 800, 600)

        self.set_status(f"Capturing multi-angle face samples for {name}...")

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame = cv2.flip(frame, 1)
            frame_h, frame_w, _ = frame.shape
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # Determine active stage
            current_stage = STAGES[-1]
            for s in STAGES:
                if sample_count < s["max_sample"]:
                    current_stage = s
                    break

            # Face Detection: Primary frontal cascade
            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=5, minSize=(60, 60))

            # Fallback to profile cascade during angled stages if frontal face isn't detected
            if len(faces) == 0 and profile_cascade and current_stage["stage_num"] in (2, 3):
                p_faces = profile_cascade.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=4, minSize=(60, 60))
                if len(p_faces) > 0:
                    faces = p_faces
                else:
                    # Check flipped for opposite profile
                    flipped_gray = cv2.flip(gray, 1)
                    flipped_p_faces = profile_cascade.detectMultiScale(flipped_gray, scaleFactor=1.2, minNeighbors=4, minSize=(60, 60))
                    if len(flipped_p_faces) > 0:
                        fx, fy, fw, fh = flipped_p_faces[0]
                        faces = [(frame_w - (fx + fw), fy, fw, fh)]

            # Process detected face
            face_detected = len(faces) > 0
            if face_detected:
                (x, y, w, h) = faces[0]
                sample_count += 1

                # Extract face crop
                face_crop = gray[y:y+h, x:x+w]

                # Enhance facial features (eyes, nose, lips, cheeks, texture) using CLAHE
                try:
                    face_crop_enhanced = clahe.apply(face_crop)
                except Exception:
                    face_crop_enhanced = face_crop

                # Save enhanced crop
                file_path = os.path.join(target_dir, f"{sample_count - 1}.jpg")
                cv2.imwrite(file_path, face_crop_enhanced)

                # Draw bounding box and stage symbol
                cv2.rectangle(frame, (x, y), (x + w, y + h), current_stage["color"], 2)
                cv2.putText(
                    frame,
                    f"Sample: {sample_count}/{target_samples} | {current_stage['symbol']}",
                    (x, y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.55,
                    current_stage["color"],
                    2
                )
                time.sleep(0.09)  # Smooth delay between captures for gradual angle transition

            # --- RENDER MODERN HIGH-TECH HUD OVERLAY ---
            # 1. Top HUD Banner (Height: 75px)
            cv2.rectangle(frame, (0, 0), (frame_w, 75), (20, 20, 20), cv2.FILLED)

            # Stage Title & Symbol
            cv2.putText(
                frame,
                f"{current_stage['title']}  {current_stage['symbol']}",
                (15, 24),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                current_stage["color"],
                2
            )

            # Features being analyzed
            cv2.putText(
                frame,
                f"Analyzing: {current_stage['features']}",
                (15, 46),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.46,
                (200, 230, 255),
                1
            )

            # Active guidance prompt
            cv2.putText(
                frame,
                f">> {current_stage['instruction']}",
                (15, 66),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.48,
                (255, 255, 255),
                1
            )

            # 2. Target Alignment Guide in Center
            center_x, center_y = frame_w // 2, frame_h // 2 + 15
            guide_color = (0, 255, 0) if face_detected else (80, 80, 80)
            cv2.ellipse(frame, (center_x, center_y), (110, 140), 0, 0, 360, guide_color, 1, cv2.LINE_AA)

            # 3. Bottom Progress Bar (Height: 48px)
            cv2.rectangle(frame, (0, frame_h - 48), (frame_w, frame_h), (20, 20, 20), cv2.FILLED)

            pct = int((sample_count / target_samples) * 100)
            bar_x1, bar_y1 = 15, frame_h - 16
            bar_x2, bar_y2 = frame_w - 15, frame_h - 8

            # Background bar
            cv2.rectangle(frame, (bar_x1, bar_y1), (bar_x2, bar_y2), (60, 60, 60), cv2.FILLED)

            # Filled progress bar
            fill_w = int((bar_x2 - bar_x1) * (sample_count / target_samples))
            if fill_w > 0:
                cv2.rectangle(frame, (bar_x1, bar_y1), (bar_x1 + fill_w, bar_y2), current_stage["color"], cv2.FILLED)

            # Progress text above bar
            stage_samples = 10 - (current_stage["max_sample"] - sample_count)
            stage_samples = max(0, min(10, stage_samples))
            cv2.putText(
                frame,
                f"Overall Progress: {sample_count}/{target_samples} ({pct}%) | Stage: {stage_samples}/10 | 'Q' to Cancel",
                (15, frame_h - 24),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.48,
                (230, 230, 230),
                1
            )

            cv2.imshow(window_name, frame)

            if cv2.waitKey(1) & 0xFF in (ord('q'), 27) or sample_count >= target_samples:
                break

            if cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE) < 1:
                break

        cap.release()
        cv2.destroyAllWindows()

        if sample_count >= target_samples:
            self.set_status(f"Captured {sample_count} multi-angle photos for {name}.")
            train_now = messagebox.askyesno(
                "Multi-Angle Capture Complete",
                f"Successfully captured all 60 multi-angle face samples for {name}!\n\n"
                "Captured Facial Features:\n"
                "✔ Frontal (Eyes, Nose Bridge, Hairstyle)\n"
                "✔ Left & Right Profiles (Cheekbones, Jawline, Ears)\n"
                "✔ Up & Down Angles (Chin, Neck, Forehead, Hairline)\n"
                "✔ Facial Expression (Lips, Smile Lines, Cheeks)\n\n"
                "Would you like to train the face model now so this student can be recognized immediately?"
            )
            if train_now:
                self.start_training_thread()
        else:
            messagebox.showwarning("Cancelled", f"Capture stopped early. Collected {sample_count} samples.")

    # =========================================================================
    # TAB 3: ATTENDANCE RECORDS & EXCEL
    # =========================================================================
    def build_attendance_tab(self):
        container = tk.Frame(self.tab_attendance, bg=self.colors["bg_dark"])
        container.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

        # Controls Header
        ctrl_frame = tk.Frame(container, bg=self.colors["panel"], padx=15, pady=12)
        ctrl_frame.pack(fill=tk.X, pady=(0, 15))

        lbl_date = tk.Label(ctrl_frame, text="Date (YYYY-MM-DD):", font=("Segoe UI", 9, "bold"), fg=self.colors["text"], bg=self.colors["panel"])
        lbl_date.pack(side=tk.LEFT, padx=5)

        ent_date = tk.Entry(ctrl_frame, textvariable=self.var_date_filter, font=("Segoe UI", 9), width=12)
        ent_date.pack(side=tk.LEFT, padx=5)

        btn_filter_date = tk.Button(
            ctrl_frame,
            text="Filter Date",
            command=self.filter_attendance_by_date,
            bg=self.colors["accent_blue"],
            fg="#ffffff",
            font=("Segoe UI", 8, "bold"),
            relief="flat",
            padx=10,
            cursor="hand2"
        )
        btn_filter_date.pack(side=tk.LEFT, padx=5)

        btn_show_all_att = tk.Button(
            ctrl_frame,
            text="Show All Records",
            command=lambda: self.load_attendance_table(date_filter=None),
            bg=self.colors["panel_light"],
            fg="#ffffff",
            font=("Segoe UI", 8),
            relief="flat",
            padx=10,
            cursor="hand2"
        )
        btn_show_all_att.pack(side=tk.LEFT, padx=5)

        # Right side actions
        btn_open_excel = tk.Button(
            ctrl_frame,
            text="📊 Export / Open Excel",
            command=self.export_and_open_excel,
            bg=self.colors["green"],
            fg="#ffffff",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            padx=12,
            pady=3,
            cursor="hand2"
        )
        btn_open_excel.pack(side=tk.RIGHT, padx=5)

        btn_refresh_att = tk.Button(
            ctrl_frame,
            text="🔄 Refresh",
            command=self.load_attendance_table,
            bg=self.colors["panel_light"],
            fg="#ffffff",
            font=("Segoe UI", 9),
            relief="flat",
            padx=10,
            pady=3,
            cursor="hand2"
        )
        btn_refresh_att.pack(side=tk.RIGHT, padx=5)

        # Attendance Table
        table_frame = tk.Frame(container)
        table_frame.pack(fill=tk.BOTH, expand=True)

        scroll_y = ttk.Scrollbar(table_frame, orient=tk.VERTICAL)
        scroll_x = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL)

        cols = ("id", "roll_no", "name", "course", "date", "time", "status")
        self.att_tree = ttk.Treeview(
            table_frame,
            columns=cols,
            show="headings",
            yscrollcommand=scroll_y.set,
            xscrollcommand=scroll_x.set
        )

        scroll_y.config(command=self.att_tree.yview)
        scroll_x.config(command=self.att_tree.xview)

        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.att_tree.pack(fill=tk.BOTH, expand=True)

        col_widths = {
            "id": 60,
            "roll_no": 120,
            "name": 180,
            "course": 160,
            "date": 130,
            "time": 130,
            "status": 100
        }

        for col in cols:
            self.att_tree.heading(col, text=col.replace("_", " ").title())
            self.att_tree.column(col, width=col_widths.get(col, 110), anchor="center")

    def load_attendance_table(self, date_filter=None):
        """Fetches attendance records and populates treeview."""
        self.att_tree.delete(*self.att_tree.get_children())
        records = database.get_attendance_records(date_filter=date_filter)

        for r in records:
            self.att_tree.insert("", tk.END, values=(
                r["id"],
                r["roll_no"],
                r["name"],
                r["course"],
                r["date"],
                r["time"],
                r["status"]
            ))

        self.update_dashboard_stats()

    def filter_attendance_by_date(self):
        d = self.var_date_filter.get().strip()
        self.load_attendance_table(date_filter=d)

    def export_and_open_excel(self):
        """Exports attendance to Excel and opens the file in Windows."""
        try:
            excel_path = database.export_attendance_to_excel()
            self.set_status(f"Exported to {excel_path}")
            if os.path.exists(excel_path):
                # Open with default Excel spreadsheet application
                os.startfile(excel_path)
        except Exception as e:
            messagebox.showerror("Excel Error", f"Failed to export or open Excel: {e}")

    # =========================================================================
    # CORE ACTIONS: TRAINING & REAL-TIME RECOGNITION
    # =========================================================================
    def start_training_thread(self):
        """Starts model training in a background thread to prevent UI freezing."""
        self.set_status("Training face recognizer model... Please wait.")

        def run_train():
            result = train_model.train_classifier()
            # Callback to main UI thread
            self.root.after(0, lambda: self.on_training_finished(result))

        threading.Thread(target=run_train, daemon=True).start()

    def on_training_finished(self, result):
        if result["success"]:
            messagebox.showinfo("Training Complete", f"{result['message']}\nClassifier model saved successfully.")
            self.set_status(f"Trained model with {result['total_images']} photos across {result['total_students']} students.")
        else:
            messagebox.showerror("Training Error", result["message"])
            self.set_status("Training failed.")

    def start_attendance_camera(self):
        """Launches the real-time face recognition attendance system."""
        self.set_status("Launching camera recognition system...")

        def on_marked(student, success, msg):
            # Refresh attendance table in GUI thread
            self.root.after(0, self.load_attendance_table)

        def run_camera():
            system = FaceRecognitionSystem(on_attendance_marked=on_marked)
            success, msg = system.start_recognition()
            self.root.after(0, lambda: self.on_camera_closed(success, msg))

        threading.Thread(target=run_camera, daemon=True).start()

    def on_camera_closed(self, success, msg):
        self.load_attendance_table()
        self.update_dashboard_stats()
        if not success:
            messagebox.showerror("Recognition Error", msg)
        self.set_status("Face recognition session completed.")

    def open_images_folder(self):
        """Opens the images directory in Windows File Explorer."""
        os.makedirs(IMAGES_DIR, exist_ok=True)
        os.startfile(IMAGES_DIR)

    def show_about(self):
        info = (
            "Face Recognition Attendance System\n\n"
            "Author: Parmjeet Yadav\n"
            "Features:\n"
            "✔ Real-time Face Detection & Recognition\n"
            "✔ Automated Attendance Logging with Date & Time\n"
            "✔ SQLite Database & Excel Synchronization\n"
            "✔ Student Registration & Image Dataset Manager\n\n"
            "Technologies: Python, OpenCV, SQLite, Tkinter, Pandas"
        )
        messagebox.showinfo("About System", info)

    # =========================================================================
    # FOOTER & STATUS BAR
    # =========================================================================
    def create_footer(self):
        footer_frame = tk.Frame(self.root, bg=self.colors["panel"], height=28)
        footer_frame.pack(fill=tk.X, side=tk.BOTTOM)

        self.lbl_status = tk.Label(
            footer_frame,
            text="System Ready.",
            font=("Segoe UI", 9),
            fg=self.colors["muted"],
            bg=self.colors["panel"]
        )
        self.lbl_status.pack(side=tk.LEFT, padx=15, pady=4)

        lbl_author = tk.Label(
            footer_frame,
            text="Created by Parmjeet Yadav",
            font=("Segoe UI", 9, "italic"),
            fg=self.colors["muted"],
            bg=self.colors["panel"]
        )
        lbl_author.pack(side=tk.RIGHT, padx=15, pady=4)

    def set_status(self, msg):
        if hasattr(self, "lbl_status") and self.lbl_status:
            self.lbl_status.config(text=msg)


def main():
    root = tk.Tk()
    app = AttendanceApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
