"""Fine-tunes YOLOv8 on traffic sign detection datasets (e.g. GTSDB / Mapillary)."""

import os
import argparse
import logging
from ultralytics import YOLO

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("train_sign_detector")


def train_sign_detector(
    data_yaml: str = "data/datasets/gtsdb_yolo/data.yaml",
    model_name: str = "yolov8n.pt",
    epochs: int = 50,
    batch_size: int = 16,
    imgsz: int = 640,
    device: str = "auto",
    output_weights: str = "weights/sign_det.pt",
):
    """Fine-tunes YOLOv8 detector on road sign dataset."""
    os.makedirs(os.path.dirname(os.path.abspath(output_weights)), exist_ok=True)

    if not os.path.exists(data_yaml):
        logger.warning(
            f"Dataset configuration {data_yaml} not found. Please run convert_dataset.py first."
        )
        return

    logger.info(f"Initializing YOLO model from {model_name}...")
    model = YOLO(model_name)

    logger.info(f"Starting training on {data_yaml} for {epochs} epochs...")
    results = model.train(
        data=data_yaml,
        epochs=epochs,
        batch=batch_size,
        imgsz=imgsz,
        device=device,
        project="runs/detect",
        name="sign_detector",
        save=True,
        verbose=True,
    )

    # Copy best weights to target location
    best_pt = os.path.join("runs", "detect", "sign_detector", "weights", "best.pt")
    if os.path.exists(best_pt):
        import shutil

        shutil.copy(best_pt, output_weights)
        logger.info(f"Best detector model weights saved to {output_weights}")
    else:
        logger.info(f"Training complete. Results: {results}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train YOLOv8 Traffic Sign Detector")
    parser.add_argument("--data", type=str, default="data/datasets/gtsdb_yolo/data.yaml")
    parser.add_argument("--model", type=str, default="yolov8n.pt")
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--device", type=str, default="auto")
    parser.add_argument("--output", type=str, default="weights/sign_det.pt")
    args = parser.parse_args()

    train_sign_detector(
        data_yaml=args.data,
        model_name=args.model,
        epochs=args.epochs,
        batch_size=args.batch,
        imgsz=args.imgsz,
        device=args.device,
        output_weights=args.output,
    )

