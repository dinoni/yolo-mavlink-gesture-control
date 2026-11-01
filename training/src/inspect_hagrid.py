import json
from pathlib import Path


BASE_PATH = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "raw"
    / "hagrid"
    / "annotations"
    / "annotations"
)


def inspect_split(split_path):
    """Analizira jedan HaGRID split."""

    print("\n" + "=" * 70)
    print(f" SPLIT: {split_path.name.upper()}")
    print("=" * 70)

    total_images = 0
    total_bboxes = 0
    all_users = set()

    gesture_stats = {}

    for json_file in sorted(split_path.glob("*.json")):

        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        gesture = json_file.stem

        num_images = len(data)
        num_bboxes = 0
        users = set()

        for image_name, annotation in data.items():

            user_id = annotation.get("user_id")

            if user_id is not None:
                users.add(user_id)
                all_users.add(user_id)

            bboxes = annotation.get("bboxes", [])
            num_bboxes += len(bboxes)

        gesture_stats[gesture] = {
            "images": num_images,
            "users": len(users),
            "bboxes": num_bboxes,
        }

        total_images += num_images
        total_bboxes += num_bboxes

    print(
        f"{'Gesture':<25}"
        f"{'Images':>12}"
        f"{'Users':>12}"
        f"{'BBoxes':>12}"
    )

    print("-" * 61)

    for gesture, stats in gesture_stats.items():

        print(
            f"{gesture:<25}"
            f"{stats['images']:>12,}"
            f"{stats['users']:>12,}"
            f"{stats['bboxes']:>12,}"
        )

    print("-" * 61)

    print(f"Total images:       {total_images:,}")
    print(f"Total bounding boxes: {total_bboxes:,}")
    print(f"Unique users:       {len(all_users):,}")


def main():

    if not BASE_PATH.exists():

        print("ERROR: HaGRID annotations folder was not found.")
        print()
        print("Expected path:")
        print(BASE_PATH)

        return

    print("HaGRID Dataset Audit")
    print()
    print("Annotations path:")
    print(BASE_PATH)

    for split_name in ["train", "val", "test"]:

        split_path = BASE_PATH / split_name

        if split_path.exists():

            inspect_split(split_path)

        else:

            print()
            print(f"WARNING: Split '{split_name}' was not found.")


if __name__ == "__main__":
    main()