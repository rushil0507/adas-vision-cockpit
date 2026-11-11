"""Trains 43-class Traffic Sign CNN on GTSRB dataset with data augmentation."""

import os
import argparse
import logging
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, Dataset
import torchvision.transforms as transforms
from PIL import Image

from src.modules.signs import TrafficSignCNN, GTSRB_CLASSES

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("train_sign_classifier")


class SyntheticSignDataset(Dataset):
    """Generates synthetic colored traffic sign images for testing and benchmarking."""

    def __init__(self, num_samples: int = 500, num_classes: int = 43, transform=None):
        self.num_samples = num_samples
        self.num_classes = num_classes
        self.transform = transform

    def __len__(self):
        return self.num_samples

    def __getitem__(self, idx):
        label = idx % self.num_classes
        # Synthetic RGB pattern based on label
        img = Image.new("RGB", (48, 48), color=((label * 17) % 255, (label * 31) % 255, (label * 53) % 255))
        if self.transform:
            img = self.transform(img)
        return img, label


def get_transforms():
    """Returns training and validation image augmentations."""
    train_transform = transforms.Compose([
        transforms.Resize((48, 48)),
        transforms.RandomRotation(degrees=15),
        transforms.ColorJitter(brightness=0.3, contrast=0.3),
        transforms.GaussianBlur(kernel_size=(3, 3), sigma=(0.1, 1.5)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])

    val_transform = transforms.Compose([
        transforms.Resize((48, 48)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])
    return train_transform, val_transform


def train_classifier(
    data_dir: str = "data/datasets/gtsrb",
    epochs: int = 20,
    batch_size: int = 64,
    lr: float = 1e-3,
    output_path: str = "weights/sign_cls.pt",
    use_dummy: bool = False,
):
    """Trains TrafficSignCNN model."""
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"Using compute device: {device}")

    train_tf, val_tf = get_transforms()

    if use_dummy or not os.path.exists(data_dir):
        logger.info("Using synthetic dataset for sign classifier demonstration/testing...")
        train_dataset = SyntheticSignDataset(num_samples=640, num_classes=43, transform=train_tf)
        val_dataset = SyntheticSignDataset(num_samples=160, num_classes=43, transform=val_tf)
    else:
        from torchvision.datasets import ImageFolder

        train_path = os.path.join(data_dir, "train")
        val_path = os.path.join(data_dir, "val")
        train_dataset = ImageFolder(train_path, transform=train_tf)
        val_dataset = ImageFolder(val_path, transform=val_tf)

    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)

    model = TrafficSignCNN(num_classes=len(GTSRB_CLASSES)).to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode="max", factor=0.5, patience=2)

    best_acc = 0.0

    for epoch in range(1, epochs + 1):
        model.train()
        running_loss = 0.0
        correct = 0
        total = 0

        for images, labels in train_loader:
            images, labels = images.to(device), labels.to(device)
            optimizer.zero_grad()
            outputs = model(images)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()

            running_loss += loss.item() * images.size(0)
            _, preds = torch.max(outputs, 1)
            correct += (preds == labels).sum().item()
            total += labels.size(0)

        train_acc = correct / max(1, total)

        # Validation
        model.eval()
        val_correct = 0
        val_total = 0
        with torch.no_grad():
            for images, labels in val_loader:
                images, labels = images.to(device), labels.to(device)
                outputs = model(images)
                _, preds = torch.max(outputs, 1)
                val_correct += (preds == labels).sum().item()
                val_total += labels.size(0)

        val_acc = val_correct / max(1, val_total)
        scheduler.step(val_acc)

        logger.info(
            f"Epoch {epoch:02d}/{epochs:02d} - Loss: {running_loss/max(1, total):.4f} "
            f"- Train Acc: {train_acc*100:.1f}% - Val Acc: {val_acc*100:.1f}%"
        )

        if val_acc >= best_acc or epoch == 1:
            best_acc = val_acc
            torch.save(model.state_dict(), output_path)
            logger.info(f"Model saved to {output_path} (acc: {val_acc*100:.1f}%)")

    logger.info(f"Training finished. Best Validation Accuracy: {best_acc*100:.2f}%")
    return best_acc


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train Traffic Sign Classifier CNN")
    parser.add_argument("--data", type=str, default="data/datasets/gtsrb")
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--batch", type=int, default=64)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--output", type=str, default="weights/sign_cls.pt")
    parser.add_argument("--dummy", action="store_true", help="Use synthetic dataset for quick testing")
    args = parser.parse_args()

    train_classifier(
        data_dir=args.data,
        epochs=args.epochs,
        batch_size=args.batch,
        lr=args.lr,
        output_path=args.output,
        use_dummy=args.dummy,
    )

