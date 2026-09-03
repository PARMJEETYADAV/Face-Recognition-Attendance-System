import os
import time
import cv2
import database

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CLASSIFIER_PATH = os.path.join(BASE_DIR, "classifier.xml")
CASCADE_PATH = os.path.join(BASE_DIR, "haarcascade_frontalface_default.xml")
PROFILE_CASCADE_PATH = os.path.join(BASE_DIR, "haarcascade_profileface.xml")


class FaceRecognitionSystem:
    def __init__(self, on_attendance_marked=None):
        self.on_attendance_marked = on_attendance_marked
        self.running = False

    def load_classifier_and_cascade(self):
        """Validates and loads the cascade classifiers and trained model."""
        if not os.path.exists(CASCADE_PATH):
            raise FileNotFoundError(f"Haar Cascade file not found at: {CASCADE_PATH}")

        face_cascade = cv2.CascadeClassifier(CASCADE_PATH)
        if face_cascade.empty():
            raise RuntimeError(f"Failed to load Haar Cascade from: {CASCADE_PATH}")

        profile_cascade = None
        if os.path.exists(PROFILE_CASCADE_PATH):
            profile_cascade = cv2.CascadeClassifier(PROFILE_CASCADE_PATH)

        if not os.path.exists(CLASSIFIER_PATH):
            raise FileNotFoundError(
                "Trained classifier model (classifier.xml) not found! "
                "Please train the model first by clicking 'Train Classifier'."
            )

        recognizer = cv2.face.LBPHFaceRecognizer_create()
        recognizer.read(CLASSIFIER_PATH)

        return face_cascade, profile_cascade, recognizer

    def get_student_lookup(self):
        """Fetches all registered students from SQLite to map ID -> Student details."""
        database.init_db()
        students = database.get_all_students()
        lookup = {}
        for s in students:
            lookup[s["id"]] = {
                "id": s["id"],
                "roll_no": s["roll_no"] or f"STU-{s['id']}",
                "name": s["name"],
                "course": s["course"] or "General"
            }
        return lookup

    def start_recognition(self, camera_index=0):
        """Starts real-time video capture and face recognition."""
        try:
            face_cascade, profile_cascade, recognizer = self.load_classifier_and_cascade()
        except Exception as e:
            return False, str(e)

        student_lookup = self.get_student_lookup()
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))

        # Try opening camera with DirectShow first (smoother on Windows), fallback to default
        cap = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
        if not cap.isOpened():
            cap = cv2.VideoCapture(camera_index)

        if not cap.isOpened():
            return False, f"Cannot access webcam at index {camera_index}. Please check camera connections or permissions."

        self.running = True
        window_title = "Face Recognition Attendance System - Press 'Q' to Exit"
        cv2.namedWindow(window_title, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(window_title, 800, 600)

        last_attendance_msg = ""
        last_msg_time = 0
        cooldown_tracker = {}  # student_id -> last_marked_epoch

        try:
            while self.running:
                ret, frame = cap.read()
                if not ret:
                    break

                # Flip horizontally for mirror effect
                frame = cv2.flip(frame, 1)
                h, w, _ = frame.shape
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

                # Detect frontal faces
                faces = face_cascade.detectMultiScale(
                    gray,
                    scaleFactor=1.2,
                    minNeighbors=5,
                    minSize=(60, 60)
                )

                # Fallback to profile detection if turned sideways
                if len(faces) == 0 and profile_cascade:
                    p_faces = profile_cascade.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=4, minSize=(60, 60))
                    if len(p_faces) > 0:
                        faces = p_faces
                    else:
                        flipped_gray = cv2.flip(gray, 1)
                        flipped_p_faces = profile_cascade.detectMultiScale(flipped_gray, scaleFactor=1.2, minNeighbors=4, minSize=(60, 60))
                        if len(flipped_p_faces) > 0:
                            fx, fy, fw, fh = flipped_p_faces[0]
                            faces = [(w - (fx + fw), fy, fw, fh)]

                current_epoch = time.time()

                for (x, y, fw, fh) in faces:
                    face_roi = gray[y:y + fh, x:x + fw]
                    try:
                        face_roi_enhanced = clahe.apply(face_roi)
                    except Exception:
                        face_roi_enhanced = face_roi

                    student_id, distance = recognizer.predict(face_roi_enhanced)

                    # LBPH distance: 0 is exact match, 100+ is poor match.
                    # Good threshold is generally <= 75
                    confidence = max(0, min(100, int(100 - distance)))

                    if distance < 75 and student_id in student_lookup:
                        student = student_lookup[student_id]
                        name = student["name"]
                        roll_no = student["roll_no"]
                        course = student["course"]

                        # Border color: Green (Recognized)
                        box_color = (0, 200, 0)

                        # Draw bounding box
                        cv2.rectangle(frame, (x, y), (x + fw, y + fh), box_color, 2)

                        # Top label background
                        label_text = f"{name} ({confidence}%)"
                        sub_text = f"Roll: {roll_no} | {course}"

                        cv2.rectangle(frame, (x, y - 48), (x + fw, y), box_color, cv2.FILLED)
                        cv2.putText(frame, label_text, (x + 6, y - 26), cv2.FONT_HERSHEY_DUPLEX, 0.55, (255, 255, 255), 1)
                        cv2.putText(frame, sub_text, (x + 6, y - 8), cv2.FONT_HERSHEY_DUPLEX, 0.45, (255, 255, 255), 1)

                        # Attempt attendance logging with cooldown (debounce logging calls)
                        last_logged = cooldown_tracker.get(student_id, 0)
                        if current_epoch - last_logged > 5:  # Check every 5 seconds
                            cooldown_tracker[student_id] = current_epoch
                            success, msg = database.mark_attendance(roll_no, name, course)
                            last_attendance_msg = msg
                            last_msg_time = current_epoch

                            if self.on_attendance_marked:
                                self.on_attendance_marked(student, success, msg)

                    else:
                        # Unknown face
                        box_color = (0, 0, 220)  # Red
                        cv2.rectangle(frame, (x, y), (x + fw, y + fh), box_color, 2)
                        cv2.rectangle(frame, (x, y - 25), (x + fw, y), box_color, cv2.FILLED)
                        cv2.putText(frame, "Unknown Person", (x + 6, y - 6), cv2.FONT_HERSHEY_DUPLEX, 0.55, (255, 255, 255), 1)

                # Header Overlay banner
                cv2.rectangle(frame, (0, 0), (w, 40), (40, 40, 40), cv2.FILLED)
                cv2.putText(
                    frame,
                    "Face Attendance System | Press 'Q' or ESC to Exit",
                    (15, 26),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (220, 220, 220),
                    2
                )

                # Footer Overlay for attendance status notification
                if current_epoch - last_msg_time < 3.5 and last_attendance_msg:
                    cv2.rectangle(frame, (0, h - 40), (w, h), (20, 120, 20), cv2.FILLED)
                    cv2.putText(
                        frame,
                        f"[STATUS] {last_attendance_msg}",
                        (15, h - 14),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        (255, 255, 255),
                        2
                    )

                cv2.imshow(window_title, frame)

                key = cv2.waitKey(1) & 0xFF
                if key == ord('q') or key == ord('Q') or key == 27:
                    break

                # Break if user closed the window manually
                if cv2.getWindowProperty(window_title, cv2.WND_PROP_VISIBLE) < 1:
                    break

        finally:
            cap.release()
            cv2.destroyAllWindows()
            self.running = False

        return True, "Recognition session ended."


def start_system():
    app = FaceRecognitionSystem()
    success, msg = app.start_recognition()
    print(msg)


if __name__ == "__main__":
    start_system()
