"""Dataset Converter: Prepares GTSDB detection annotations for YOLOv8 and GTSRB for CNN classification."""

import os
import csv
import argparse
import random
import shutil
from typing import Tuple, List
import cv2
import numpy as np


def convert_gtsdb_to_yolo(
    gtsdb_dir: str,
    output_dir: str,
    val_split: float = 0.20,
    seed: int = 42,
):
    """
    Converts GTSDB detection dataset (gt.txt with format: Filename;X1;Y1;X2;Y2;ClassId)
    to YOLOv8 format with images/ and labels/ subdirectories.
    """
    random.seed(seed)
    gt_file = os.path.join(gtsdb_dir, "gt.txt")
    if not os.path.exists(gt_file):
        print(f"Warning: GTSDB ground truth file not found at {gt_file}")
        return

    images_dir = gtsdb_dir
    train_img_dir = os.path.join(output_dir, "images", "train")
    val_img_dir = os.path.join(output_dir, "images", "val")
    train_lbl_dir = os.path.join(output_dir, "labels", "train")
    val_lbl_dir = os.path.join(output_dir, "labels", "val")

    for d in [train_img_dir, val_img_dir, train_lbl_dir, val_lbl_dir]:
        os.makedirs(d, exist_ok=True)

    # Parse ground truth
    annotations = {}
    with open(gt_file, "r") as f:
        reader = csv.reader(f, delimiter=";")
        for row in reader:
            if not row or len(row) < 6:
                continue
            filename = row[0].strip()
            x1, y1, x2, y2 = float(row[1]), float(row[2]), float(row[3]), float(row[4])
            cls_id = int(row[5])
            if filename not in annotations:
                annotations[filename] = []
            annotations[filename].append((cls_id, x1, y1, x2, y2))

    all_images = list(annotations.keys())
    random.shuffle(all_images)
    n_val = int(len(all_images) * val_split)
    val_files = set(all_images[:n_val])

    for img_name in all_images:
        src_path = os.path.join(images_dir, img_name)
        if not os.path.exists(src_path):
            continue

        img = cv2.imread(src_path)
        if img is None:
            continue
        h, w = img.shape[:2]

        is_val = img_name in val_files
        dest_img_dir = val_img_dir if is_val else train_img_dir
        dest_lbl_dir = val_lbl_dir if is_val else train_lbl_dir

        base_name = os.path.splitext(img_name)[0]
        # Copy image
        cv2.imwrite(os.path.join(dest_img_dir, f"{base_name}.jpg"), img)

        # Write YOLO label: class x_center y_center width height
        lbl_path = os.path.join(dest_lbl_dir, f"{base_name}.txt")
        with open(lbl_path, "w") as lf:
            for cls_id, x1, y1, x2, y2 in annotations[img_name]:
                xc = ((x1 + x2) / 2.0) / w
                yc = ((y1 + y2) / 2.0) / h
                bw = (x2 - x1) / w
                bh = (y2 - y1) / h
                lf.write(f"{cls_id} {xc:.6f} {yc:.6f} {bw:.6f} {bh:.6f}\n")

    # Generate YOLO data.yaml
    yaml_content = f"""# GTSDB YOLO Dataset Config
path: {os.path.abspath(output_dir)}
train: images/train
val: images/val
names:
  0: prohibitory
  1: danger
  2: mandatory
  3: other
"""
    with open(os.path.join(output_dir, "data.yaml"), "w") as yf:
        yf.write(yaml_content)

    print(f"GTSDB conversion complete. Saved to {output_dir}")


def create_synthetic_demo_data(base_dir: str):
    """Generates synthetic dataset and demo video for offline testing."""
    os.makedirs(base_dir, exist_ok=True)
    samples_dir = os.path.join(base_dir, "data", "samples")
    os.makedirs(samples_dir, exist_ok=True)
    demo_video_path = os.path.join(samples_dir, "demo.mp4")

    # If demo video already exists and is non-empty, skip
    if os.path.exists(demo_video_path) and os.path.getsize(demo_video_path) > 1000:
        print(f"Demo video already exists at {demo_video_path}")
        return demo_video_path

    print(f"Creating synthetic realistic dashcam demo video at {demo_video_path}...")
    w, h = 1280, 720
    fps = 25
    num_frames = 150  # 6-second looping dashcam video
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(demo_video_path, fourcc, fps, (w, h))

    for i in range(num_frames):
        # Road asphalt background
        frame = np.full((h, w, 3), (50, 50, 55), dtype=np.uint8)

        # Sky and horizon
        horizon = int(h * 0.45)
        frame[0:horizon, :] = [180, 150, 100]  # Dusk/daylight sky

        # Distant scenery/trees
        cv2.rectangle(frame, (0, horizon - 30), (w, horizon), (40, 80, 40), -1)

        # Lane markings: perspective lines
        # Center dashed line
        offset_shift = int(15 * np.sin(i / 15.0))  # slight vehicle wobble to trigger lane offset changes
        left_bottom = (int(w * 0.20) + offset_shift, h)
        left_top = (int(w * 0.44), horizon)
        right_bottom = (int(w * 0.80) + offset_shift, h)
        right_top = (int(w * 0.56), horizon)

        # Solid white left lane
        cv2.line(frame, left_bottom, left_top, (240, 240, 240), 6, lineType=cv2.LINE_AA)
        # Solid white right lane
        cv2.line(frame, right_bottom, right_top, (240, 240, 240), 6, lineType=cv2.LINE_AA)

        # Dashed yellow lane in middle
        dash_step = (i * 12) % 60
        for y_dash in range(horizon, h, 60):
            yd = y_dash + dash_step
            if yd < h:
                interp = (yd - horizon) / float(h - horizon)
                xd = int((w * 0.50) + (offset_shift * interp))
                cv2.line(frame, (xd, yd), (xd, min(h, yd + 25)), (30, 220, 240), 4, lineType=cv2.LINE_AA)

        # Moving pedestrian: crosses the road into the danger zone
        ped_x = int(w * 0.35 + (i * 2.5))
        ped_y = int(h * 0.60 + (i * 0.8))
        ped_h = int(60 + i * 0.5)
        ped_w = int(ped_h * 0.4)

        # Draw realistic pedestrian silhouette
        head_radius = ped_w // 2
        cv2.circle(frame, (ped_x, ped_y - ped_h + head_radius), head_radius, (30, 30, 180), -1)
        cv2.rectangle(
            frame,
            (ped_x - ped_w // 2, ped_y - ped_h + head_radius * 2),
            (ped_x + ped_w // 2, ped_y),
            (30, 50, 200),
            -1,
        )

        # Road Sign on right shoulder: Speed Limit 50 or Stop Sign
        sign_x = int(w * 0.85 - (i * 0.5))
        sign_y = int(horizon + 20)
        sign_r = int(24 + (i * 0.2))

        # Sign pole
        cv2.line(frame, (sign_x, sign_y), (sign_x, sign_y + 120), (120, 120, 120), 4)

        # Circular Speed Limit 50 sign
        cv2.circle(frame, (sign_x, sign_y), sign_r, (40, 40, 230), -1)  # Red outer ring
        cv2.circle(frame, (sign_x, sign_y), int(sign_r * 0.75), (240, 240, 240), -1)  # White center
        cv2.putText(
            frame,
            "50",
            (sign_x - int(sign_r * 0.45), sign_y + int(sign_r * 0.35)),
            cv2.FONT_HERSHEY_SIMPLEX,
            sign_r / 45.0,
            (10, 10, 10),
            2,
            cv2.LINE_AA,
        )

        out.write(frame)

    out.release()
    print(f"Synthetic demo video generated successfully ({num_frames} frames).")
    return demo_video_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--gtsdb-dir", type=str, default="data/datasets/gtsdb")
    parser.add_argument("--output-dir", type=str, default="data/datasets/gtsdb_yolo")
    parser.add_argument("--create-demo-video", action="store_true")
    args = parser.parse_args()

    if args.create_demo_video:
        create_synthetic_demo_data(os.getcwd())
    else:
        convert_gtsdb_to_yolo(args.gtsdb_dir, args.output_dir)
