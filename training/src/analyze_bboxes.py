import json
from pathlib import Path
from collections import defaultdict
import statistics


# ============================================================
# PUTANJA DO HAGRID ANOTACIJA
# ============================================================

BASE_PATH = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "raw"
    / "hagrid"
    / "annotations"
    / "annotations"
)


# ============================================================
# GESTE KOJE ĆEMO KORISTITI
# ============================================================

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


# ============================================================
# ANALIZA JEDNOG SPLITA
# ============================================================

def analyze_split(split_name):

    split_path = BASE_PATH / split_name

    results = defaultdict(list)

    for gesture in sorted(SELECTED_GESTURES):

        json_file = split_path / f"{gesture}.json"

        if not json_file.exists():

            print(f"WARNING: {json_file} not found")

            continue

        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        # U HaGRID-u je struktura:
        #
        # image_name:
        #   {
        #       "bboxes": [...],
        #       "labels": [...],
        #       "user_id": ...
        #   }

        for image_name, annotation in data.items():

            bboxes = annotation.get("bboxes", [])

            for bbox in bboxes:

                if len(bbox) != 4:
                    continue

                # ====================================================
                # VAŽNO:
                #
                # HaGRID koristi:
                #
                # [x, y, width, height]
                #
                # a NE:
                #
                # [x1, y1, x2, y2]
                # ====================================================

                x, y, width, height = bbox

                # Površina bounding boxa u odnosu
                # na ukupnu površinu slike.
                area = width * height

                results[gesture].append(
                    {
                        "width": width,
                        "height": height,
                        "area": area,
                    }
                )

    return results


# ============================================================
# ISPIS STATISTIKE PO GESTI
# ============================================================

def print_statistics(split_name, results):

    print("\n" + "=" * 80)
    print(f" BOUNDING BOX ANALYSIS: {split_name.upper()}")
    print("=" * 80)

    print(
        f"{'Gesture':<18}"
        f"{'Samples':>12}"
        f"{'Avg W':>12}"
        f"{'Avg H':>12}"
        f"{'Avg Area':>14}"
        f"{'Min Area':>14}"
        f"{'Max Area':>14}"
    )

    print("-" * 96)

    for gesture in sorted(results):

        samples = results[gesture]

        if not samples:
            continue

        widths = [
            sample["width"]
            for sample in samples
        ]

        heights = [
            sample["height"]
            for sample in samples
        ]

        areas = [
            sample["area"]
            for sample in samples
        ]

        print(
            f"{gesture:<18}"
            f"{len(samples):>12,}"
            f"{statistics.mean(widths):>12.4f}"
            f"{statistics.mean(heights):>12.4f}"
            f"{statistics.mean(areas):>14.4f}"
            f"{min(areas):>14.4f}"
            f"{max(areas):>14.4f}"
        )


# ============================================================
# DISTRIBUCIJA VELIČINE RUKU
# ============================================================

def calculate_size_distribution(results):

    all_areas = []

    for samples in results.values():

        for sample in samples:

            all_areas.append(
                sample["area"]
            )

    if not all_areas:

        print("No bounding boxes found.")

        return

    # ========================================================
    # KATEGORIJE
    #
    # area = površina bboxa / površina slike
    #
    # 0.02 = 2%
    # 0.05 = 5%
    # 0.15 = 15%
    # itd.
    # ========================================================

    thresholds = [
        ("Very small", 0.00, 0.02),
        ("Small", 0.02, 0.05),
        ("Medium", 0.05, 0.15),
        ("Large", 0.15, 0.30),
        ("Very large", 0.30, 1.01),
    ]

    print("\n" + "=" * 80)
    print(" OVERALL BOUNDING BOX SIZE DISTRIBUTION")
    print("=" * 80)

    print(
        f"{'Category':<18}"
        f"{'Samples':>14}"
        f"{'Percentage':>16}"
    )

    print("-" * 50)

    total = len(all_areas)

    for name, lower, upper in thresholds:

        count = sum(
            lower <= area < upper
            for area in all_areas
        )

        percentage = (
            count / total * 100
        )

        print(
            f"{name:<18}"
            f"{count:>14,}"
            f"{percentage:>15.2f}%"
        )

    print("-" * 50)

    print(
        f"{'Total':<18}"
        f"{total:>14,}"
        f"{'100.00%':>16}"
    )


# ============================================================
# DODATNA ANALIZA
# ============================================================

def calculate_extreme_cases(results):

    all_samples = []

    for gesture, samples in results.items():

        for sample in samples:

            all_samples.append(
                (
                    gesture,
                    sample["width"],
                    sample["height"],
                    sample["area"],
                )
            )

    if not all_samples:
        return

    smallest = sorted(
        all_samples,
        key=lambda x: x[3]
    )[:10]

    largest = sorted(
        all_samples,
        key=lambda x: x[3],
        reverse=True
    )[:10]

    print("\n" + "=" * 80)
    print(" SMALLEST BOUNDING BOXES")
    print("=" * 80)

    for gesture, width, height, area in smallest:

        print(
            f"{gesture:<18}"
            f"W={width:.4f} "
            f"H={height:.4f} "
            f"Area={area:.6f}"
        )

    print("\n" + "=" * 80)
    print(" LARGEST BOUNDING BOXES")
    print("=" * 80)

    for gesture, width, height, area in largest:

        print(
            f"{gesture:<18}"
            f"W={width:.4f} "
            f"H={height:.4f} "
            f"Area={area:.6f}"
        )


# ============================================================
# MAIN
# ============================================================

def main():

    # --------------------------------------------------------
    # Provjera postoji li dataset
    # --------------------------------------------------------

    if not BASE_PATH.exists():

        print(
            "ERROR: HaGRID annotations were not found."
        )

        print()
        print("Expected path:")
        print(BASE_PATH)

        return

    # --------------------------------------------------------
    # Naslov
    # --------------------------------------------------------

    print("HaGRID Bounding Box Analysis")

    print()
    print("Annotations path:")
    print(BASE_PATH)

    print()
    print("Using selected gestures:")

    for gesture in sorted(SELECTED_GESTURES):

        print(f"  - {gesture}")

    # --------------------------------------------------------
    # Analiza sva tri splita
    # --------------------------------------------------------

    all_results = {}

    for split in ["train", "val", "test"]:

        print()
        print(f"Loading {split}...")

        results = analyze_split(split)

        all_results[split] = results

        print_statistics(
            split,
            results
        )

    # --------------------------------------------------------
    # Distribucija veličina
    #
    # Za početak koristimo TRAIN.
    # --------------------------------------------------------

    calculate_size_distribution(
        all_results["train"]
    )

    # --------------------------------------------------------
    # Ekstremni slučajevi
    # --------------------------------------------------------

    calculate_extreme_cases(
        all_results["train"]
    )

    # --------------------------------------------------------
    # Kraj
    # --------------------------------------------------------

    print("\n" + "=" * 80)
    print(" ANALYSIS FINISHED")
    print("=" * 80)


# ============================================================
# POKRETANJE
# ============================================================

if __name__ == "__main__":
    main()