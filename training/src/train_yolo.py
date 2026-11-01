from pathlib import Path

from ultralytics import YOLO


PROJECT_DIR = Path(__file__).resolve().parent.parent

DATASET = (
    PROJECT_DIR
    / "data"
    / "processed"
    / "yolo_gestures"
    / "data.yaml"
)

MODEL = "yolo11n.pt"

EPOCHS = 2
IMG_SIZE = 512
BATCH_SIZE = 8
DEVICE = 0
WORKERS = 0


def main():

    print("=" * 70)
    print("YOLO HAND GESTURE TEST TRAINING")
    print("=" * 70)

    print(f"Dataset : {DATASET}")
    print(f"Model   : {MODEL}")
    print(f"Epochs  : {EPOCHS}")
    print(f"Image   : {IMG_SIZE}")
    print(f"Batch   : {BATCH_SIZE}")
    print(f"Device  : GPU {DEVICE}")
    print(f"Workers : {WORKERS}")
    print()

    if not DATASET.exists():
        raise FileNotFoundError(
            f"data.yaml nije pronađen:\n{DATASET}"
        )

    model = YOLO(MODEL)

    results = model.train(
        data=str(DATASET),
        epochs=EPOCHS,
        imgsz=IMG_SIZE,
        batch=BATCH_SIZE,
        device=DEVICE,
        workers=WORKERS,

        project=str(
            PROJECT_DIR / "experiments"
        ),

        name="gesture_yolo26n_test",

        pretrained=True,

        patience=10,

        save=True,
        plots=True,

        cache=False,

        amp=True,

        verbose=True,
    )

    print()
    print("=" * 70)
    print("TEST TRAINING FINISHED")
    print("=" * 70)

    print(
        "Rezultati:\n"
        f"{PROJECT_DIR / 'experiments' / 'gesture_yolo26n_test'}"
    )


if __name__ == "__main__":
    main()