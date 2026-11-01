import random
from pathlib import Path

import cv2


# ============================================================
# POSTAVKE
# ============================================================

PROJECT_DIR = Path(__file__).resolve().parent.parent

IMAGES_DIR = (
    PROJECT_DIR
    / "data"
    / "processed"
    / "yolo_gestures"
    / "images"
    / "train"
)

LABELS_DIR = (
    PROJECT_DIR
    / "data"
    / "processed"
    / "yolo_gestures"
    / "labels"
    / "train"
)

OUTPUT_DIR = (
    PROJECT_DIR
    / "data"
    / "processed"
    / "yolo_gestures"
    / "preview"
)

NUM_IMAGES = 20

CLASSES = [
    "dislike",
    "fist",
    "like",
    "no_gesture",
    "one",
    "palm",
    "three",
    "two_up",
]


# ============================================================
# GLAVNI PROGRAM
# ============================================================

def main():

    print("YOLO DATASET VISUALIZATION")
    print("=" * 60)

    print(f"Images: {IMAGES_DIR}")
    print(f"Labels: {LABELS_DIR}")
    print(f"Output: {OUTPUT_DIR}")

    if not IMAGES_DIR.exists():
        print("\nERROR: Images directory does not exist.")
        return

    if not LABELS_DIR.exists():
        print("\nERROR: Labels directory does not exist.")
        return

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    # --------------------------------------------------------
    # Pronađi slike
    # --------------------------------------------------------

    images = list(IMAGES_DIR.glob("*.jpg"))

    if not images:
        print("\nERROR: No JPG images found.")
        return

    print(f"\nFound images: {len(images):,}")

    # --------------------------------------------------------
    # Odaberi slučajne slike
    # --------------------------------------------------------

    sample_size = min(
        NUM_IMAGES,
        len(images)
    )

    selected_images = random.sample(
        images,
        sample_size
    )

    print(
        f"Visualizing {sample_size} random images..."
    )

    # --------------------------------------------------------
    # Obradi slike
    # --------------------------------------------------------

    processed = 0

    for image_path in selected_images:

        label_path = (
            LABELS_DIR
            / f"{image_path.stem}.txt"
        )

        if not label_path.exists():
            print(
                f"WARNING: Label missing: "
                f"{image_path.name}"
            )
            continue

        image = cv2.imread(
            str(image_path)
        )

        if image is None:
            print(
                f"WARNING: Could not read: "
                f"{image_path.name}"
            )
            continue

        height, width = image.shape[:2]

        # ----------------------------------------------------
        # Učitaj YOLO label
        # ----------------------------------------------------

        lines = label_path.read_text(
            encoding="utf-8"
        ).splitlines()

        for line in lines:

            parts = line.split()

            if len(parts) != 5:
                continue

            class_id = int(parts[0])

            x_center = float(parts[1])
            y_center = float(parts[2])
            box_width = float(parts[3])
            box_height = float(parts[4])

            # YOLO normalizirane vrijednosti
            x_center *= width
            y_center *= height
            box_width *= width
            box_height *= height

            # Centar -> kutovi
            x1 = int(
                x_center - box_width / 2
            )

            y1 = int(
                y_center - box_height / 2
            )

            x2 = int(
                x_center + box_width / 2
            )

            y2 = int(
                y_center + box_height / 2
            )

            # Ograniči na sliku
            x1 = max(0, min(width - 1, x1))
            y1 = max(0, min(height - 1, y1))
            x2 = max(0, min(width - 1, x2))
            y2 = max(0, min(height - 1, y2))

            # ------------------------------------------------
            # Bounding box
            # ------------------------------------------------

            cv2.rectangle(
                image,
                (x1, y1),
                (x2, y2),
                (0, 255, 0),
                2
            )

            # ------------------------------------------------
            # Naziv klase
            # ------------------------------------------------

            if 0 <= class_id < len(CLASSES):
                class_name = CLASSES[class_id]
            else:
                class_name = f"class_{class_id}"

            label = (
                f"{class_name}"
            )

            # Pozadina za tekst
            (text_width, text_height), baseline = (
                cv2.getTextSize(
                    label,
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    2
                )
            )

            text_y = max(
                text_height + 5,
                y1
            )

            cv2.rectangle(
                image,
                (
                    x1,
                    text_y - text_height - baseline - 5
                ),
                (
                    x1 + text_width + 5,
                    text_y
                ),
                (0, 255, 0),
                -1
            )

            cv2.putText(
                image,
                label,
                (x1 + 2, text_y - 4),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 0, 0),
                2
            )

        # ----------------------------------------------------
        # Spremi rezultat
        # ----------------------------------------------------

        output_path = (
            OUTPUT_DIR
            / image_path.name
        )

        cv2.imwrite(
            str(output_path),
            image
        )

        processed += 1

        print(
            f"[{processed}/{sample_size}] "
            f"{image_path.name}"
        )

    # --------------------------------------------------------
    # Završetak
    # --------------------------------------------------------

    print()
    print("=" * 60)
    print("VISUALIZATION FINISHED")
    print("=" * 60)

    print(
        f"Created previews: {processed}"
    )

    print(
        f"Preview directory:\n{OUTPUT_DIR}"
    )


if __name__ == "__main__":
    main()