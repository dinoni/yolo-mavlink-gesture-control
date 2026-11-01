import cv2
import time
from collections import deque
from ultralytics import YOLO

# =========================
# POSTAVKE
# =========================

MODEL_PATH = "best.pt"

IMG_SIZE = 512
CONFIDENCE = 0.50

# Koliko uzastopnih frameova treba potvrditi istu gestu
CONFIRM_FRAMES = 5

# =========================
# MODEL
# =========================

model = YOLO(MODEL_PATH)

# =========================
# KAMERA
# =========================

cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("Greška: kamera se ne može otvoriti.")
    exit()

# Poželjna rezolucija kamere
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

print("Kamera pokrenuta.")
print("Pritisni Q za izlaz.")

# =========================
# STABILIZACIJA GESTE
# =========================

gesture_history = deque(maxlen=CONFIRM_FRAMES)

confirmed_gesture = "NEMA"
confirmed_confidence = 0.0

# =========================
# FPS
# =========================

prev_time = time.time()
fps = 0

# =========================
# GLAVNA PETLJA
# =========================

while True:

    ret, frame = cap.read()

    if not ret:
        print("Greška pri čitanju slike s kamere.")
        break

    # YOLO detekcija
    results = model.predict(
        source=frame,
        imgsz=IMG_SIZE,
        conf=CONFIDENCE,
        device=0,
        verbose=False
    )

    result = results[0]

    # Crtanje bounding boxova
    annotated_frame = result.plot()

    # =========================
    # NAJBOLJA DETEKCIJA
    # =========================

    current_gesture = None
    current_confidence = 0.0

    if result.boxes is not None and len(result.boxes) > 0:

        # Uzimamo detekciju s najvećim confidenceom
        best_index = result.boxes.conf.argmax()

        class_id = int(result.boxes.cls[best_index])
        confidence = float(result.boxes.conf[best_index])

        current_gesture = model.names[class_id]
        current_confidence = confidence

    # =========================
    # STABILIZACIJA
    # =========================

    if current_gesture is not None:

        gesture_history.append(current_gesture)

        # Ako je ista gesta potvrđena kroz dovoljno frameova
        if (
            len(gesture_history) == CONFIRM_FRAMES
            and len(set(gesture_history)) == 1
        ):
            confirmed_gesture = current_gesture
            confirmed_confidence = current_confidence

    else:
        gesture_history.clear()

    # =========================
    # FPS
    # =========================

    current_time = time.time()
    elapsed = current_time - prev_time

    if elapsed > 0:
        fps = 1 / elapsed

    prev_time = current_time

    # =========================
    # INFORMACIJE NA EKRANU
    # =========================

    cv2.putText(
        annotated_frame,
        f"GESTA: {confirmed_gesture}",
        (20, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        (0, 255, 0),
        2
    )

    cv2.putText(
        annotated_frame,
        f"CONFIDENCE: {confirmed_confidence * 100:.1f}%",
        (20, 80),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (255, 255, 255),
        2
    )

    cv2.putText(
        annotated_frame,
        f"FPS: {fps:.1f}",
        (20, 120),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (255, 255, 255),
        2
    )

    cv2.putText(
        annotated_frame,
        f"Potvrda: {len(gesture_history)}/{CONFIRM_FRAMES}",
        (20, 160),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (255, 255, 255),
        2
    )

    # =========================
    # PRIKAZ
    # =========================

    cv2.imshow(
        "YOLO11n - Stabilno prepoznavanje gesti",
        annotated_frame
    )

    # Q = izlaz
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

# =========================
# ZATVARANJE
# =========================

cap.release()
cv2.destroyAllWindows()