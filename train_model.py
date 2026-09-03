import os
import cv2
import numpy as np
from PIL import Image

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "images")
CLASSIFIER_PATH = os.path.join(BASE_DIR, "classifier.xml")


def train_classifier(progress_callback=None):
    """
    Trains the LBPH Face Recognizer on all captured face images.
    Returns a dict with status, message, total_images, and total_students.
    """
    if not os.path.exists(DATA_DIR):
        return {
            "success": False,
            "message": f"Images directory not found: {DATA_DIR}",
            "total_images": 0,
            "total_students": 0
        }

    faces = []
    ids = []
    student_folders = []

    # 1. Look for subfolders like "0_Parmjeet" or "1_StudentName"
    for item in os.listdir(DATA_DIR):
        item_path = os.path.join(DATA_DIR, item)
        if os.path.isdir(item_path):
            student_folders.append((item, item_path))

    # Also look for flat files like "user.1.0.jpg" in DATA_DIR
    flat_files = [f for f in os.listdir(DATA_DIR) if os.path.isfile(os.path.join(DATA_DIR, f)) and f.lower().endswith(('.jpg', '.jpeg', '.png'))]

    total_items = sum(len(os.listdir(p[1])) for p in student_folders) + len(flat_files)
    if total_items == 0:
        return {
            "success": False,
            "message": "No training face images found in images/ directory. Please capture samples first.",
            "total_images": 0,
            "total_students": 0
        }

    processed_count = 0

    # Process subfolders
    for folder_name, folder_path in student_folders:
        # Extract student ID from folder name (e.g. "0_Parmjeet" -> 0, "101_Alice" -> 101)
        try:
            student_id = int(folder_name.split("_")[0])
        except (ValueError, IndexError):
            # If no numeric prefix, hash or skip
            continue

        for filename in os.listdir(folder_path):
            if filename.lower().endswith(('.jpg', '.jpeg', '.png')):
                img_path = os.path.join(folder_path, filename)
                try:
                    pil_img = Image.open(img_path).convert('L')
                    img_np = np.array(pil_img, 'uint8')

                    faces.append(img_np)
                    ids.append(student_id)
                    processed_count += 1

                    if progress_callback:
                        progress_callback(processed_count, total_items)
                except Exception as e:
                    print(f"Error loading {img_path}: {e}")

    # Process any flat files
    for filename in flat_files:
        try:
            # Expected format: user.<id>.<count>.jpg or <id>.<count>.jpg
            parts = filename.split(".")
            if len(parts) >= 3 and parts[0].lower() == "user":
                student_id = int(parts[1])
            else:
                student_id = int(parts[0])

            img_path = os.path.join(DATA_DIR, filename)
            pil_img = Image.open(img_path).convert('L')
            img_np = np.array(pil_img, 'uint8')

            faces.append(img_np)
            ids.append(student_id)
            processed_count += 1

            if progress_callback:
                progress_callback(processed_count, total_items)
        except Exception:
            continue

    if len(faces) == 0:
        return {
            "success": False,
            "message": "No valid face crops could be processed for training.",
            "total_images": 0,
            "total_students": 0
        }

    # Train LBPH Face Recognizer
    clf = cv2.face.LBPHFaceRecognizer_create()
    clf.train(faces, np.array(ids, dtype=np.int32))
    clf.write(CLASSIFIER_PATH)

    unique_students = len(set(ids))
    return {
        "success": True,
        "message": f"Successfully trained model with {len(faces)} photos across {unique_students} student(s).",
        "total_images": len(faces),
        "total_students": unique_students,
        "classifier_path": CLASSIFIER_PATH
    }


if __name__ == "__main__":
    print("Starting face classifier training...")

    def console_progress(current, total):
        print(f"\rTraining progress: {current}/{total} ({(current/total)*100:.1f}%)", end="", flush=True)

    result = train_classifier(console_progress)
    print()
    if result["success"]:
        print(f"[SUCCESS] {result['message']}")
        print(f"Saved classifier model to: {result['classifier_path']}")
    else:
        print(f"[ERROR] {result['message']}")
