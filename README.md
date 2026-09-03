# Face Recognition Attendance System

An automated, real-time facial recognition attendance management desktop application built with **Python**, **OpenCV**, **Tkinter**, **SQLite**, and **Pandas**.

---

## 📌 Overview

The **Face Recognition Attendance System** replaces manual roll-call with automated computer vision. It guides students through a **6-angle facial capture process**, trains an **LBPH (Local Binary Patterns Histograms)** classifier, recognizes students in real-time via webcam, and automatically logs attendance with timestamps into SQLite and Excel.

---

## ✨ Features

- ✔ **Streamlined Student Registration Portal**:
  - **"➕ Add New Student"**: Automatically prepares form with auto-incremented Student ID and Roll Number (e.g. `STU-002`).
  - **"📝 Register Student"**: Validates student details, prevents duplicates, saves to SQLite, and immediately prompts to capture face samples.
- ✔ **Guided Multi-Angle Facial Feature Capture**:
  - Automatically guides the student through **6 distinct angle stages** (10 samples each = 60 photos total):
    1. **Stage 1 (Look Straight)**: Captures eyes, eyebrows, nose bridge, and frontal hairstyle.
    2. **Stage 2 (Turn Slightly Left)**: Captures left cheek structure, jawline, and left ear profile.
    3. **Stage 3 (Turn Slightly Right)**: Captures right cheek structure, jawline, and right ear profile.
    4. **Stage 4 (Tilt Slightly Up)**: Captures chin structure, neck contour, and under-nose angle.
    5. **Stage 5 (Tilt Slightly Down)**: Captures forehead, hairline contour, and top of eyebrows.
    6. **Stage 6 (Smile & Expression)**: Captures lips, smile lines, and dynamic facial muscle movement.
  - **Dual-Cascade Tracking**: Combines frontal (`haarcascade_frontalface_default.xml`) and profile (`haarcascade_profileface.xml`) cascades for reliable tracking as the head rotates.
  - **CLAHE Enhancement**: Applies Contrast-Limited Adaptive Histogram Equalization to highlight edge and texture details across eyes, nose, lips, and cheekbones.
- ✔ **One-Click Classifier Training**: Trains an LBPH face recognizer across all student folders in `images/` and outputs `classifier.xml`.
- ✔ **Real-Time Recognition & Verification**:
  - Live webcam stream with bounding boxes and student name, roll number, course, and confidence score.
  - Highlights unknown persons in red with "Unknown Person" tag.
- ✔ **Smart Attendance Logging**:
  - Automatically marks status as Present with Date (`YYYY-MM-DD`) and Time (`HH:MM:SS`).
  - Intelligent cooldown / debounce prevents duplicate records on the same day.
- ✔ **Excel Synchronization & Export**:
  - Seamlessly syncs all logs with `attendance.xlsx`.
  - In-app attendance record viewer with date and student search filters.
- ✔ **Modern Tkinter GUI**: Polished dark-themed interface with live digital clock, metric cards, and responsive controls.

---

## 🛠️ Technologies Used

| Technology | Purpose |
|------------|---------|
| **Python 3.11+** | Core programming language |
| **OpenCV (`opencv-contrib-python`)** | Frontal & profile Haar cascades, CLAHE texture equalization, and LBPH face recognition |
| **Tkinter & ttk** | Desktop GUI dashboard, modal dialogs, and tables |
| **SQLite 3** | Local relational database for students & attendance logs (`attendance.db`) |
| **Pandas & OpenPyXL** | Attendance data manipulation and Excel export (`attendance.xlsx`) |
| **Pillow (PIL)** | Image loading and preprocessing |

---

## 📁 Project Structure

```
Face-Recognition-Attendance-System/
├── haarcascade_frontalface_default.xml # OpenCV Frontal Face Haar Cascade
├── haarcascade_profileface.xml         # OpenCV Profile Face Haar Cascade
├── haarcascade_eye.xml                 # OpenCV Eye Haar Cascade
├── classifier.xml                      # Trained LBPH face recognizer model
├── attendance.db                       # SQLite database (students & attendance)
├── attendance.xlsx                     # Excel export sheet
├── requirements.txt                    # Project dependencies
├── database.py                         # Database CRUD & Excel sync operations
├── train_model.py                      # LBPH Model trainer engine
├── face_recognition_system.py          # Real-time face detection & attendance marker
├── face recognition system.py          # Legacy runner script
├── main.py                             # Master Tkinter GUI dashboard
├── README.md                           # Documentation
└── images/                             # Face dataset directory
    └── 0_Parmjeet/                     # Sample face crops for ID 0
        ├── 0.jpg
        ├── ...
        └── 29.jpg
```

---

## 🚀 Installation & Quickstart

### 1. Clone the Repository
```bash
git clone https://github.com/PARMJEETYADAV/Face-Recognition-Attendance-System.git
cd Face-Recognition-Attendance-System
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Launch the Application
```bash
python main.py
```

*Or launch the standalone face recognition camera:*
```bash
python "face recognition system.py"
```

---

## 📖 How to Use the System

1. **Register a Student**:
   - Go to the **Student Registration** tab.
   - Click **➕ Add New Student** to clear the form and auto-generate the next Roll Number and ID.
   - Enter Full Name, Course, Department, etc.
   - Click **📝 Register Student**.
2. **Multi-Angle Face Capture**:
   - The application will automatically prompt to capture face samples.
   - Follow the on-screen camera instructions through the 6 stages (Straight, Left, Right, Up, Down, Smile).
   - Once all 60 samples are captured, confirm the prompt to train the model.
3. **Take Attendance**:
   - On the **Dashboard**, click **📷 Start Camera Recognition**.
   - Look at the camera. The system recognizes the student, shows a green box with confidence score, and marks attendance.
   - Press **Q** or **ESC** to exit the camera.
4. **View & Export Attendance**:
   - Go to the **Attendance Records & Excel** tab.
   - Filter by date or student name.
   - Click **📊 Export / Open Excel** to inspect `attendance.xlsx`.

---

## 👤 Author

**Parmjeet Yadav**
- GitHub: [@PARMJEETYADAV](https://github.com/PARMJEETYADAV)
