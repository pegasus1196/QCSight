"""
Train YOLO11 on the circuit-elements dataset for component detection.
This trains a real object detection model for the college assessment.

Usage:
    python backend/training/train_yolo.py

The trained model will be saved to backend/training/runs/
"""
from pathlib import Path
from ultralytics import YOLO

DATASET_DIR = Path(__file__).parent / "dataset" / "circuit-elements"
RUNS_DIR = Path(__file__).parent / "runs"


def train(epochs: int = 50, img_size: int = 640, batch: int = 8, model_size: str = "n"):
    data_yaml = DATASET_DIR / "data.yaml"
    if not data_yaml.exists():
        print(f"ERROR: data.yaml not found at {data_yaml}")
        print("Run download_dataset.py first:")
        print("  python backend/training/download_dataset.py")
        return

    print("=" * 60)
    print("CabinetSight - YOLO11 Training")
    print("=" * 60)
    print(f"Dataset:    {DATASET_DIR}")
    print(f"Model:      YOLO11{model_size}")
    print(f"Epochs:     {epochs}")
    print(f"Image size: {img_size}")
    print(f"Batch size: {batch}")
    print(f"Output:     {RUNS_DIR}")
    print("=" * 60)

    model = YOLO(f"yolo11{model_size}.pt")

    results = model.train(
        data=str(data_yaml),
        epochs=epochs,
        imgsz=img_size,
        batch=batch,
        project=str(RUNS_DIR),
        name="cabinetsight_detector",
        patience=10,
        save=True,
        plots=True,
        verbose=True,
    )

    best_model = RUNS_DIR / "cabinetsight_detector" / "weights" / "best.pt"
    if best_model.exists():
        print(f"\nBest model saved to: {best_model}")
        print("Copy it to backend/models/ for inference:")
        print(f"  copy {best_model} backend/models/best.pt")
    else:
        print("\nTraining completed. Check runs/ for results.")

    return results


def evaluate():
    best_model = RUNS_DIR / "cabinetsight_detector" / "weights" / "best.pt"
    if not best_model.exists():
        print("No trained model found. Run train() first.")
        return

    data_yaml = DATASET_DIR / "data.yaml"
    model = YOLO(str(best_model))
    metrics = model.val(data=str(data_yaml))

    print("\n" + "=" * 60)
    print("Evaluation Results")
    print("=" * 60)
    print(f"mAP@0.5:     {metrics.box.map50:.4f}")
    print(f"mAP@0.5:0.95: {metrics.box.map:.4f}")
    print(f"Precision:    {metrics.box.mp:.4f}")
    print(f"Recall:       {metrics.box.mr:.4f}")
    print("=" * 60)

    return metrics


def predict_image(image_path: str):
    best_model = RUNS_DIR / "cabinetsight_detector" / "weights" / "best.pt"
    if not best_model.exists():
        print("No trained model found. Run train() first.")
        return

    model = YOLO(str(best_model))
    results = model.predict(
        source=image_path,
        save=True,
        conf=0.25,
        project=str(RUNS_DIR),
        name="predictions",
    )

    for r in results:
        print(f"\nDetections in {Path(image_path).name}:")
        for box in r.boxes:
            cls_id = int(box.cls[0])
            conf = float(box.conf[0])
            name = r.names[cls_id]
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            print(f"  {name}: {conf:.2f} at [{x1:.0f},{y1:.0f},{x2:.0f},{y2:.0f}]")

    return results


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "eval":
        evaluate()
    elif len(sys.argv) > 1 and sys.argv[1] == "predict":
        predict_image(sys.argv[2] if len(sys.argv) > 2 else "assets/cabinet-demo.png")
    else:
        train(epochs=50, img_size=640, batch=8, model_size="n")
