import cv2
import time
from collections import deque
from ultralytics import YOLO

# ============================================================
# POSTAVKE
# ============================================================

MODEL_PATH = "best.pt"

CONFIDENCE = 0.50
IMG_SIZE = 512

CONFIRM_FRAMES = 5

# Proporcionalno pojačanje
KP = 1.5

# Maksimalna brzina virtualnog drona
MAX_SPEED = 500.0

# Dead-zone
DEAD_ZONE = 0.08

# ============================================================
# MODEL
# ============================================================

model = YOLO(MODEL_PATH)

# ============================================================
# KAMERA
# ============================================================

cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("Greška: kamera se ne može otvoriti.")
    exit()

print("2D DRONE VISUAL SERVOING SIMULATION")
print("Pritisni Q za izlaz.")

# ============================================================
# STABILIZACIJA
# ============================================================

gesture_history = deque(maxlen=CONFIRM_FRAMES)

confirmed_gesture = None
confirmed_confidence = 0.0

# ============================================================
# VRIJEME
# ============================================================

previous_time = time.perf_counter()

# ============================================================
# GLAVNA PETLJA
# ============================================================

while True:

    ret, frame = cap.read()

    if not ret:
        break

    frame_height, frame_width = frame.shape[:2]

    # ========================================================
    # DELTA TIME
    # ========================================================

    current_time = time.perf_counter()

    dt = current_time - previous_time
    previous_time = current_time

    dt = min(dt, 0.1)

    # ========================================================
    # YOLO
    # ========================================================

    results = model.predict(
        source=frame,
        imgsz=IMG_SIZE,
        conf=CONFIDENCE,
        device=0,
        verbose=False
    )

    result = results[0]

    annotated_frame = result.plot()

    # ========================================================
    # CENTAR EKRANA
    # ========================================================

    center_x = frame_width / 2
    center_y = frame_height / 2

    # ========================================================
    # DETEKCIJA
    # ========================================================

    current_gesture = None
    current_confidence = 0.0

    hand_x = None
    hand_y = None

    if result.boxes is not None and len(result.boxes) > 0:

        best_index = result.boxes.conf.argmax()

        class_id = int(
            result.boxes.cls[best_index]
        )

        current_confidence = float(
            result.boxes.conf[best_index]
        )

        current_gesture = model.names[class_id]

        box = result.boxes.xyxy[best_index]

        x1, y1, x2, y2 = map(int, box)

        # Centar dlana
        hand_x = (x1 + x2) / 2
        hand_y = (y1 + y2) / 2

        cv2.circle(
            annotated_frame,
            (int(hand_x), int(hand_y)),
            8,
            (0, 0, 255),
            -1
        )

    # ========================================================
    # STABILIZACIJA
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
    # 2D SIMULACIJA
    # ========================================================

    # Virtualni dron počinje u centru slike
    if "drone_x" not in locals():

        drone_x = center_x
        drone_y = center_y

    # ========================================================
    # NAREDBA
    # ========================================================

    command = "NO COMMAND"

    error_x = 0
    error_y = 0

    velocity_x = 0
    velocity_y = 0

    # ========================================================
    # FIST
    # ========================================================

    if confirmed_gesture == "fist":

        command = "STOP / HOLD"

    # ========================================================
    # LIKE
    # ========================================================

    elif confirmed_gesture == "like":

        command = "MOVE RIGHT"

        velocity_x = MAX_SPEED

    # ========================================================
    # DISLIKE
    # ========================================================

    elif confirmed_gesture == "dislike":

        command = "MOVE LEFT"

        velocity_x = -MAX_SPEED

    # ========================================================
    # PALM
    # ========================================================

    elif (
        confirmed_gesture == "palm"
        and hand_x is not None
    ):

        # ----------------------------------------------------
        # GREŠKA
        # ----------------------------------------------------

        error_x = center_x - hand_x
        error_y = center_y - hand_y

        # ----------------------------------------------------
        # NORMALIZACIJA
        # ----------------------------------------------------

        normalized_x = error_x / (frame_width / 2)
        normalized_y = error_y / (frame_height / 2)

        # ----------------------------------------------------
        # DEAD ZONE
        # ----------------------------------------------------

        if abs(normalized_x) < DEAD_ZONE:
            normalized_x = 0

        if abs(normalized_y) < DEAD_ZONE:
            normalized_y = 0

        # ----------------------------------------------------
        # PROPORCIONALNI REGULATOR
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

        # Ograničenje brzine
        velocity_x = max(
            -MAX_SPEED,
            min(MAX_SPEED, velocity_x)
        )

        velocity_y = max(
            -MAX_SPEED,
            min(MAX_SPEED, velocity_y)
        )

        # ----------------------------------------------------
        # NAREDBA
        # ----------------------------------------------------

        if (
            abs(velocity_x) < 1
            and abs(velocity_y) < 1
        ):

            command = "PALM CENTERED - HOLD"

        else:

            command = (
                f"FOLLOW PALM"
            )

    # ========================================================
    # POMAK VIRTUALNOG DRONA
    # ========================================================

    drone_x += velocity_x * dt
    drone_y += velocity_y * dt

    # ========================================================
    # OGRANIČENJE NA EKRAN
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
    # CRTANJE CENTRA
    # ========================================================

    cv2.drawMarker(
        annotated_frame,
        (int(center_x), int(center_y)),
        (255, 255, 0),
        cv2.MARKER_CROSS,
        30,
        2
    )

    # ========================================================
    # CRTANJE DRONA
    # ========================================================

    dx = int(drone_x)
    dy = int(drone_y)

    # Tijelo
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
    # VEKTOR DLANA → DRON
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
        f"GESTURE: {confirmed_gesture or 'NONE'}",
        (20, 35),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (0, 255, 0),
        2
    )

    cv2.putText(
        annotated_frame,
        f"COMMAND: {command}",
        (20, 70),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (0, 255, 255),
        2
    )

    cv2.putText(
        annotated_frame,
        f"VX: {velocity_x:.1f}",
        (20, 105),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (255, 255, 255),
        2
    )

    cv2.putText(
        annotated_frame,
        f"VY: {velocity_y:.1f}",
        (20, 140),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (255, 255, 255),
        2
    )

    cv2.putText(
        annotated_frame,
        f"DRONE: ({dx}, {dy})",
        (20, 175),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (255, 255, 255),
        2
    )

    if hand_x is not None:

        cv2.putText(
            annotated_frame,
            f"PALM: ({int(hand_x)}, {int(hand_y)})",
            (20, 210),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (0, 0, 255),
            2
        )

    cv2.putText(
        annotated_frame,
        f"ERROR: ({int(error_x)}, {int(error_y)})",
        (20, 245),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (255, 255, 255),
        2
    )

    # ========================================================
    # PRIKAZ
    # ========================================================

    cv2.imshow(
        "2D Drone Visual Servoing",
        annotated_frame
    )

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

# ============================================================
# KRAJ
# ============================================================

cap.release()
cv2.destroyAllWindows()