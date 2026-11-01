import json
import shutil
from pathlib import Path


# ============================================================
# HaGRID v2 512 -> YOLO DATASET PREPARATION
# ============================================================

PROJECT_DIR = Path(__file__).resolve().parent.parent

ANNOTATIONS_DIR = (
    PROJECT_DIR
    / "data"
    / "raw"
    / "hagrid"
    / "annotations"
    / "annotations"
)

IMAGES_DIR = (
    PROJECT_DIR
    / "data"
    / "raw"
    / "hagrid"
    / "images_512"
)

OUTPUT_DIR = (
    PROJECT_DIR
    / "data"
    / "processed"
    / "yolo_gestures"
)


# ============================================================
# ODABRANE KLASE
# ============================================================

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

CLASS_TO_ID = {
    name: i
    for i, name in enumerate(CLASSES)
}


# ============================================================
# POSTAVKE
# ============================================================

# Prvo provjeravamo bez kopiranja slika.
DRY_RUN = False

# None = sve slike
# npr. 1000 = maksimalno 1000 slika po klasi
MAX_IMAGES_PER_CLASS = None


# ============================================================
# UČITAVANJE ANOTACIJA
# ============================================================

def load_annotations(json_path):
    """
    HaGRID JSON je organiziran približno ovako:

    {
        "UUID_SLIKE": {
            "bboxes": [...],
            "labels": [...],
            "user_id": "..."
        },
        ...
    }

    UUID slike nalazi se kao KLJUČ JSON objekta.
    """

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise ValueError(
            f"Neočekivani format JSON-a: {json_path}"
        )

    return data


# ============================================================
# BOUNDING BOX
# ============================================================

def convert_bbox(bbox):
    """
    HaGRID bbox:
        [x, y, width, height]

    YOLO format:
        x_center y_center width height

    Sve vrijednosti moraju biti 0-1.
    """

    if not isinstance(bbox, (list, tuple)):
        return None

    if len(bbox) < 4:
        return None

    x, y, w, h = map(float, bbox[:4])

    if w <= 0 or h <= 0:
        return None

    # HaGRID koristi x,y kao gornji-lijevi kut.
    x_center = x + w / 2
    y_center = y + h / 2

    # Ograniči na 0-1 zbog mogućih rubnih slučajeva.
    x_center = max(0.0, min(1.0, x_center))
    y_center = max(0.0, min(1.0, y_center))
    w = max(0.0, min(1.0, w))
    h = max(0.0, min(1.0, h))

    if w <= 0 or h <= 0:
        return None

    return x_center, y_center, w, h


# ============================================================
# PRONALAŽENJE JSON DATOTEKE
# ============================================================

def find_annotation_file(gesture, split):

    split_dir = ANNOTATIONS_DIR / split

    if not split_dir.exists():
        return None

    path = split_dir / f"{gesture}.json"

    if path.exists():
        return path

    return None


# ============================================================
# OBRADA SPLITA
# ============================================================

def process_split(split):

    print()
    print("=" * 70)
    print(f"PROCESSING: {split.upper()}")
    print("=" * 70)

    total_annotations = 0
    matched_images = 0
    missing_images = 0
    invalid_boxes = 0

    for gesture in CLASSES:

        print()
        print(gesture)

        json_path = find_annotation_file(
            gesture,
            split
        )

        if json_path is None:
            print("  ERROR: JSON not found")
            continue

        print(f"  JSON: {json_path.name}")

        data = load_annotations(json_path)

        print(
            f"  Annotations: {len(data):,}"
        )

        processed_class = 0

        # ----------------------------------------------------
        # KLJUČ JE UUID SLIKE
        # ----------------------------------------------------

        for image_id, annotation in data.items():

            if (
                MAX_IMAGES_PER_CLASS is not None
                and processed_class >= MAX_IMAGES_PER_CLASS
            ):
                break

            if not isinstance(annotation, dict):
                continue

            # ------------------------------------------------
            # Pronađi sliku
            # ------------------------------------------------

            image_id = Path(str(image_id)).stem

            image_path = (
                IMAGES_DIR
                / gesture
                / f"{image_id}.jpg"
            )

            if not image_path.exists():

                missing_images += 1

                continue

            # ------------------------------------------------
            # Bounding boxes
            # ------------------------------------------------

            bboxes = annotation.get(
                "bboxes",
                []
            )

            if not isinstance(bboxes, list):
                continue

            yolo_lines = []

            for bbox in bboxes:

                converted = convert_bbox(bbox)

                if converted is None:

                    invalid_boxes += 1

                    continue

                x_center, y_center, w, h = converted

                class_id = CLASS_TO_ID[gesture]

                line = (
                    f"{class_id} "
                    f"{x_center:.6f} "
                    f"{y_center:.6f} "
                    f"{w:.6f} "
                    f"{h:.6f}"
                )

                yolo_lines.append(line)

            if not yolo_lines:
                continue

            total_annotations += 1
            matched_images += 1
            processed_class += 1

            # ------------------------------------------------
            # DRY RUN
            # ------------------------------------------------

            if DRY_RUN:
                continue

            # ------------------------------------------------
            # Output directories
            # ------------------------------------------------

            image_output_dir = (
                OUTPUT_DIR
                / "images"
                / split
            )

            label_output_dir = (
                OUTPUT_DIR
                / "labels"
                / split
            )

            image_output_dir.mkdir(
                parents=True,
                exist_ok=True
            )

            label_output_dir.mkdir(
                parents=True,
                exist_ok=True
            )

            # ------------------------------------------------
            # Kopiranje slike
            # ------------------------------------------------

            output_image = (
                image_output_dir
                / f"{image_id}.jpg"
            )

            shutil.copy2(
                image_path,
                output_image
            )

            # ------------------------------------------------
            # YOLO label
            # ------------------------------------------------

            output_label = (
                label_output_dir
                / f"{image_id}.txt"
            )

            output_label.write_text(
                "\n".join(yolo_lines),
                encoding="utf-8"
            )

        print(
            f"  Matched images: {processed_class:,}"
        )

    # --------------------------------------------------------
    # Rezultat splita
    # --------------------------------------------------------

    print()
    print("-" * 70)

    print(
        f"Total matched images : {matched_images:,}"
    )

    print(
        f"Missing images       : {missing_images:,}"
    )

    print(
        f"Invalid boxes        : {invalid_boxes:,}"
    )

    print("-" * 70)

    return (
        matched_images,
        missing_images,
        invalid_boxes,
    )


# ============================================================
# DATA.YAML
# ============================================================

def create_yaml():

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    yaml_path = OUTPUT_DIR / "data.yaml"

    names = "\n".join(
        f"  {i}: {name}"
        for i, name in enumerate(CLASSES)
    )

    content = f"""path: {OUTPUT_DIR.as_posix()}
train: images/train
val: images/val
test: images/test

nc: {len(CLASSES)}

names:
{names}
"""

    yaml_path.write_text(
        content,
        encoding="utf-8"
    )

    print()
    print(
        f"Created data.yaml: {yaml_path}"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("HaGRID v2 512 -> YOLO DATASET PREPARATION")
    print()

    print("Project:")
    print(PROJECT_DIR)

    print()
    print("Annotations:")
    print(ANNOTATIONS_DIR)

    print()
    print("Images:")
    print(IMAGES_DIR)

    print()
    print("Output:")
    print(OUTPUT_DIR)

    print()
    print("Selected classes:")

    for i, gesture in enumerate(CLASSES):
        print(
            f"{i}: {gesture}"
        )

    print()
    print(f"DRY_RUN = {DRY_RUN}")
    print(
        f"MAX_IMAGES_PER_CLASS = "
        f"{MAX_IMAGES_PER_CLASS}"
    )

    # --------------------------------------------------------
    # Provjera putanja
    # --------------------------------------------------------

    if not ANNOTATIONS_DIR.exists():

        print()
        print("ERROR: Annotation directory does not exist.")
        print(ANNOTATIONS_DIR)

        return

    if not IMAGES_DIR.exists():

        print()
        print("ERROR: Image directory does not exist.")
        print(IMAGES_DIR)

        return

    # --------------------------------------------------------
    # Obrada
    # --------------------------------------------------------

    results = {}

    for split in [
        "train",
        "val",
        "test"
    ]:

        results[split] = process_split(
            split
        )

    # --------------------------------------------------------
    # Ako nije DRY RUN, napravi YAML
    # --------------------------------------------------------

    if not DRY_RUN:
        create_yaml()

    # --------------------------------------------------------
    # Završetak
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("PREPARATION FINISHED")
    print("=" * 70)

    for split, result in results.items():

        matched, missing, invalid = result

        print(
            f"{split.upper():5} "
            f"images={matched:,} "
            f"missing={missing:,} "
            f"invalid_boxes={invalid:,}"
        )

    print()

    if DRY_RUN:

        print(
            "DRY_RUN is TRUE."
        )

        print(
            "No files were copied."
        )

        print()
        print(
            "Ako su rezultati dobri, promijeni:"
        )

        print()
        print(
            "DRY_RUN = False"
        )

        print()
        print(
            "i ponovno pokreni skriptu."
        )


# ============================================================
# START
# ============================================================

if __name__ == "__main__":
    main()