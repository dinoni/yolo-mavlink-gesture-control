import cv2
import os
import time
from datetime import datetime
from collections import deque
from ultralytics import YOLO

# ============================================================
# POSTAVKE
# ============================================================

MODEL_PATH = "best.pt"

CONFIDENCE = 0.50
IMG_SIZE = 512

# Stabilizacija geste
CONFIRM_FRAMES = 5

# Proporcionalno pojačanje za praćenje dlana
KP = 2.0

# Maksimalna brzina virtualnog drona
MAX_SPEED = 500.0

# Zona u kojoj smatramo da je dron dovoljno blizu dlana
DEAD_ZONE = 0.05

# ============================================================
# MODEL
# ============================================================
import torch

model = YOLO(MODEL_PATH)

# Automatski odabir uređaja
if torch.cuda.is_available():
    DEVICE = 0
    print("Koristi se NVIDIA GPU.")
else:
    DEVICE = "cpu"
    print("NVIDIA GPU nije pronađen - koristi se CPU.")
# ============================================================
# MAPA ZA SNIMLJENE SLIKE
# ============================================================

os.makedirs("captured_images", exist_ok=True)

# ============================================================
# KAMERA
# ============================================================

cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("Greška: kamera se ne može otvoriti.")
    exit()

print("DRONE HAND FOLLOW")
print()
print("GESTE:")
print("  PALM    -> prati dlan")
print("  FIST    -> STOP / HOLD")
print("  LIKE    -> snimi sliku")
print("  DISLIKE -> nema naredbe")
print()
print("Pritisni Q za izlaz.")

# ============================================================
# STABILIZACIJA GESTE
# ============================================================

gesture_history = deque(maxlen=CONFIRM_FRAMES)

confirmed_gesture = None
confirmed_confidence = 0.0

# ============================================================
# SNIMANJE SLIKE
# ============================================================

capture_ready = True

# ============================================================
# VRIJEME
# ============================================================

previous_time = time.perf_counter()

# ============================================================
# VIRTUALNI DRON
# ============================================================

drone_x = None
drone_y = None

# ============================================================
# GLAVNA PETLJA
# ============================================================

while True:

    ret, frame = cap.read()

    if not ret:
        print("Greška pri čitanju slike.")
        break

    frame_height, frame_width = frame.shape[:2]

    # ========================================================
    # INICIJALNA POZICIJA DRONA
    # ========================================================

    if drone_x is None:
        drone_x = frame_width / 2
        drone_y = frame_height / 2

    # ========================================================
    # DELTA TIME
    # ========================================================

    current_time = time.perf_counter()

    dt = current_time - previous_time
    previous_time = current_time

    # Zaštita od velikih skokova vremena
    dt = min(dt, 0.1)

    # ========================================================
    # YOLO
    # ========================================================

    results = model.predict(
        source=frame,
        imgsz=IMG_SIZE,
        conf=CONFIDENCE,
        device=DEVICE,
        verbose=False
    )

    result = results[0]

    # YOLO prikaz
    annotated_frame = result.plot()

    # ========================================================
    # DETEKCIJA
    # ========================================================

    current_gesture = None
    current_confidence = 0.0

    hand_x = None
    hand_y = None

    if result.boxes is not None and len(result.boxes) > 0:

        # Najsigurnija detekcija
        best_index = result.boxes.conf.argmax()

        class_id = int(
            result.boxes.cls[best_index]
        )

        current_confidence = float(
            result.boxes.conf[best_index]
        )

        current_gesture = model.names[class_id]

        # Bounding box
        box = result.boxes.xyxy[best_index]

        x1, y1, x2, y2 = map(int, box)

        # Centar dlana
        hand_x = (x1 + x2) / 2
        hand_y = (y1 + y2) / 2

        # Točka centra dlana
        cv2.circle(
            annotated_frame,
            (int(hand_x), int(hand_y)),
            8,
            (0, 0, 255),
            -1
        )

    # ========================================================
    # STABILIZACIJA GESTE
    # ========================================================

    if current_gesture is not None:

        gesture_history.append(current_gesture)

        if (
            len(gesture_history) == CONFIRM_FRAMES
            and len(set(gesture_history)) == 1
        ):

            confirmed_gesture = current_gesture
            confirmed_confidence = current_confidence

    # ========================================================
    # NAREDBA
    # ========================================================

    command = "NO COMMAND"

    velocity_x = 0.0
    velocity_y = 0.0

    error_x = 0.0
    error_y = 0.0

    # ========================================================
    # FIST → STOP
    # ========================================================

    if confirmed_gesture == "fist":

        command = "STOP / HOLD"

    # ========================================================
    # LIKE → SNIMI TRENUTNU SLIKU
    # ========================================================

    elif confirmed_gesture == "like":

        command = "CAPTURE IMAGE"

        if capture_ready:

            timestamp = datetime.now().strftime(
                "%Y%m%d_%H%M%S_%f"
            )

            filename = os.path.join(
                "captured_images",
                f"capture_{timestamp}.jpg"
            )

            success = cv2.imwrite(
                filename,
                frame
            )

            if success:

                print(
                    f"Slika spremljena: {filename}"
                )

                capture_ready = False

            else:

                print(
                    "Greška: slika nije spremljena."
                )

    # ========================================================
    # DISLIKE → NEMA NAREDBE
    # ========================================================

    elif confirmed_gesture == "dislike":

        command = "NO COMMAND"

    # ========================================================
    # PALM → PRATI DLANS
    # ========================================================

    elif (
        confirmed_gesture == "palm"
        and hand_x is not None
    ):

        # ----------------------------------------------------
        # GREŠKA IZMEĐU DRONA I DLANA
        # ----------------------------------------------------

        error_x = hand_x - drone_x
        error_y = hand_y - drone_y

        # ----------------------------------------------------
        # NORMALIZACIJA
        # ----------------------------------------------------

        normalized_x = (
            error_x / (frame_width / 2)
        )

        normalized_y = (
            error_y / (frame_height / 2)
        )

        # ----------------------------------------------------
        # DEAD ZONE
        # ----------------------------------------------------

        if abs(normalized_x) < DEAD_ZONE:
            normalized_x = 0

        if abs(normalized_y) < DEAD_ZONE:
            normalized_y = 0

        # ----------------------------------------------------
        # PROPORCIONALNA KONTROLA
        # ----------------------------------------------------

        velocity_x = (
            normalized_x
            * MAX_SPEED
            * KP
        )

        velocity_y = (
            normalized_y
            * MAX_SPEED
            * KP
        )

        # ----------------------------------------------------
        # OGRANIČENJE BRZINE
        # ----------------------------------------------------

        velocity_x = max(
            -MAX_SPEED,
            min(MAX_SPEED, velocity_x)
        )

        velocity_y = max(
            -MAX_SPEED,
            min(MAX_SPEED, velocity_y)
        )

        # ----------------------------------------------------
        # STATUS
        # ----------------------------------------------------

        if (
            velocity_x == 0
            and velocity_y == 0
        ):

            command = "HAND CENTERED - HOLD"

        else:

            command = "FOLLOW HAND"

    # ========================================================
    # POMAK VIRTUALNOG DRONA
    # ========================================================

    drone_x += velocity_x * dt
    drone_y += velocity_y * dt

    # ========================================================
    # OGRANIČENJE DRONA NA EKRAN
    # ========================================================

    drone_x = max(
        30,
        min(frame_width - 30, drone_x)
    )

    drone_y = max(
        30,
        min(frame_height - 30, drone_y)
    )

    # ========================================================
    # RESET ZA NOVO SNIMANJE
    # ========================================================

    if confirmed_gesture != "like":

        capture_ready = True

    # ========================================================
    # CRTANJE VIRTUALNOG DRONA
    # ========================================================

    dx = int(drone_x)
    dy = int(drone_y)

    # Tijelo drona
    cv2.rectangle(
        annotated_frame,
        (dx - 25, dy - 12),
        (dx + 25, dy + 12),
        (0, 255, 0),
        -1
    )

    # Lijevi rotor
    cv2.circle(
        annotated_frame,
        (dx - 40, dy - 20),
        12,
        (255, 0, 0),
        2
    )

    # Desni rotor
    cv2.circle(
        annotated_frame,
        (dx + 40, dy - 20),
        12,
        (255, 0, 0),
        2
    )

    # ========================================================
    # LINIJA DLANA → DRON
    # ========================================================

    if (
        confirmed_gesture == "palm"
        and hand_x is not None
    ):

        cv2.line(
            annotated_frame,
            (dx, dy),
            (int(hand_x), int(hand_y)),
            (0, 255, 255),
            2
        )

    # ========================================================
    # INFORMACIJE
    # ========================================================

    cv2.putText(
        annotated_frame,
        f"GESTA: {confirmed_gesture or 'NEMA'}",
        (20, 35),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (0, 255, 0),
        2
    )

    cv2.putText(
        annotated_frame,
        f"NAREDBA: {command}",
        (20, 70),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (0, 255, 255),
        2
    )

    cv2.putText(
        annotated_frame,
        f"DRONE: ({dx}, {dy})",
        (20, 105),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (255, 255, 255),
        2
    )

    if hand_x is not None:

        cv2.putText(
            annotated_frame,
            f"HAND: ({int(hand_x)}, {int(hand_y)})",
            (20, 140),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (0, 0, 255),
            2
        )

    cv2.putText(
        annotated_frame,
        f"ERROR X: {error_x:.0f}",
        (20, 175),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (255, 255, 255),
        2
    )

    cv2.putText(
        annotated_frame,
        f"ERROR Y: {error_y:.0f}",
        (20, 210),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (255, 255, 255),
        2
    )

    cv2.putText(
        annotated_frame,
        f"VX: {velocity_x:.0f}",
        (20, 245),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (255, 255, 255),
        2
    )

    cv2.putText(
        annotated_frame,
        f"VY: {velocity_y:.0f}",
        (20, 280),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (255, 255, 255),
        2
    )

    # ========================================================
    # PRIKAZ
    # ========================================================

    cv2.imshow(
        "Drone Hand Follow - 2D SIMULATION",
        annotated_frame
    )

    # ========================================================
    # Q → IZLAZ
    # ========================================================

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

# ============================================================
# ZATVARANJE
# ============================================================

cap.release()
cv2.destroyAllWindows()