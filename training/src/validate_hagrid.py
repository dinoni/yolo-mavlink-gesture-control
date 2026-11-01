import json
from pathlib import Path
from collections import Counter


BASE_PATH = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "raw"
    / "hagrid"
    / "annotations"
    / "annotations"
)

# Klase koje ćemo zasad koristiti
SELECTED_GESTURES = {
    "fist",
    "palm",
    "like",
    "dislike",
    "one",
    "two_up",
    "three",
    "no_gesture",
}


def load_split(split_name):
    """Učitaj sve anotacije jednog splita."""

    split_path = BASE_PATH / split_name

    annotations = {}

    for json_file in split_path.glob("*.json"):

        gesture = json_file.stem

        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        annotations[gesture] = data

    return annotations


def check_basic_structure(split_name, annotations):
    """Provjeri osnovnu strukturu anotacija."""

    print(f"\n{'=' * 70}")
    print(f" BASIC STRUCTURE: {split_name.upper()}")
    print(f"{'=' * 70}")

    errors = 0

    for gesture, images in annotations.items():

        for image_name, annotation in images.items():

            if not isinstance(annotation, dict):
                print(
                    f"ERROR: {split_name}/{gesture}/{image_name} "
                    f"is not a dictionary"
                )
                errors += 1
                continue

            if "bboxes" not in annotation:
                print(
                    f"ERROR: Missing bboxes: "
                    f"{split_name}/{gesture}/{image_name}"
                )
                errors += 1

            if "labels" not in annotation:
                print(
                    f"ERROR: Missing labels: "
                    f"{split_name}/{gesture}/{image_name}"
                )
                errors += 1

            if "user_id" not in annotation:
                print(
                    f"ERROR: Missing user_id: "
                    f"{split_name}/{gesture}/{image_name}"
                )
                errors += 1

    print(f"\nStructure errors: {errors}")

    return errors


def check_bboxes(split_name, annotations):
    """Provjeri osnovnu valjanost bounding boxova."""

    print(f"\n{'=' * 70}")
    print(f" BOUNDING BOX CHECK: {split_name.upper()}")
    print(f"{'=' * 70}")

    invalid_boxes = 0
    images_with_multiple_boxes = Counter()

    for gesture, images in annotations.items():

        for image_name, annotation in images.items():

            bboxes = annotation.get("bboxes", [])
            labels = annotation.get("labels", [])

            if len(bboxes) != len(labels):
                print(
                    f"ERROR: bbox/label mismatch: "
                    f"{split_name}/{gesture}/{image_name}"
                )
                invalid_boxes += 1

            if len(bboxes) > 1:
                images_with_multiple_boxes[len(bboxes)] += 1

            for bbox in bboxes:

                if len(bbox) != 4:
                    print(
                        f"ERROR: Invalid bbox length: "
                        f"{split_name}/{gesture}/{image_name}"
                    )
                    invalid_boxes += 1
                    continue

                # HaGRID koristi normalizirane koordinate.
                if not all(0 <= value <= 1 for value in bbox):
                    print(
                        f"ERROR: Bbox outside [0,1]: "
                        f"{split_name}/{gesture}/{image_name}: {bbox}"
                    )
                    invalid_boxes += 1

    print(f"Invalid bounding boxes: {invalid_boxes}")

    print("\nImages with multiple bounding boxes:")

    if images_with_multiple_boxes:
        for count, images in sorted(images_with_multiple_boxes.items()):
            print(f"  {count} boxes: {images:,} images")
    else:
        print("  None")

    return invalid_boxes


def get_users(annotations):
    """Vrati skup svih user_id vrijednosti."""

    users = set()

    for images in annotations.values():

        for annotation in images.values():

            user_id = annotation.get("user_id")

            if user_id is not None:
                users.add(user_id)

    return users


def check_user_leakage(all_splits):
    """Provjeri postoji li isti user u više službenih splitova."""

    print(f"\n{'=' * 70}")
    print(" USER LEAKAGE CHECK")
    print(f"{'=' * 70}")

    users = {}

    for split_name, annotations in all_splits.items():
        users[split_name] = get_users(annotations)

        print(
            f"{split_name.upper():<10}: "
            f"{len(users[split_name]):,} unique users"
        )

    train_val = users["train"] & users["val"]
    train_test = users["train"] & users["test"]
    val_test = users["val"] & users["test"]

    print("\nUser overlap:")

    print(f"  Train ∩ Val:   {len(train_val):,}")
    print(f"  Train ∩ Test:  {len(train_test):,}")
    print(f"  Val ∩ Test:    {len(val_test):,}")

    if not train_val and not train_test and not val_test:
        print("\n✓ NO USER LEAKAGE DETECTED")
    else:
        print("\n⚠ USER LEAKAGE DETECTED")


def selected_class_statistics(annotations):
    """Statistika samo za naše odabrane klase."""

    print(f"\n{'=' * 70}")
    print(" SELECTED GESTURES")
    print(f"{'=' * 70}")

    print(
        f"{'Gesture':<20}"
        f"{'Images':>12}"
        f"{'BBoxes':>12}"
        f"{'Users':>12}"
    )

    print("-" * 56)

    for gesture in sorted(SELECTED_GESTURES):

        if gesture not in annotations:
            print(f"{gesture:<20} NOT FOUND")
            continue

        images = annotations[gesture]

        bbox_count = 0
        users = set()

        for annotation in images.values():

            bbox_count += len(annotation.get("bboxes", []))

            user_id = annotation.get("user_id")

            if user_id is not None:
                users.add(user_id)

        print(
            f"{gesture:<20}"
            f"{len(images):>12,}"
            f"{bbox_count:>12,}"
            f"{len(users):>12,}"
        )


def main():

    if not BASE_PATH.exists():

        print("ERROR: HaGRID annotations were not found.")
        print(BASE_PATH)

        return

    print("HaGRID Dataset Validation")
    print()
    print("Path:")
    print(BASE_PATH)

    all_splits = {}

    # ---------------------------------------------------------
    # Učitaj splitove
    # ---------------------------------------------------------

    for split_name in ["train", "val", "test"]:

        split_path = BASE_PATH / split_name

        if not split_path.exists():

            print(f"ERROR: Missing split: {split_name}")
            return

        print(f"\nLoading {split_name}...")

        annotations = load_split(split_name)

        all_splits[split_name] = annotations

        print(
            f"Loaded {len(annotations)} gesture classes."
        )

    # ---------------------------------------------------------
    # Validacija
    # ---------------------------------------------------------

    total_errors = 0

    for split_name, annotations in all_splits.items():

        total_errors += check_basic_structure(
            split_name,
            annotations
        )

        total_errors += check_bboxes(
            split_name,
            annotations
        )

    # ---------------------------------------------------------
    # User leakage
    # ---------------------------------------------------------

    check_user_leakage(all_splits)

    # ---------------------------------------------------------
    # Naše klase
    # ---------------------------------------------------------

    print("\n\nTRAINING CLASSES")

    selected_class_statistics(
        all_splits["train"]
    )

    print("\n\nVALIDATION CLASSES")

    selected_class_statistics(
        all_splits["val"]
    )

    print("\n\nTEST CLASSES")

    selected_class_statistics(
        all_splits["test"]
    )

    # ---------------------------------------------------------
    # Završetak
    # ---------------------------------------------------------

    print(f"\n{'=' * 70}")
    print(" VALIDATION FINISHED")
    print(f"{'=' * 70}")

    print(f"Total structural errors: {total_errors}")

    if total_errors == 0:
        print("\n✓ No structural errors detected.")


if __name__ == "__main__":
    main()