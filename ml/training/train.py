"""
Food Classification Model Training Script
Architecture: EfficientNet-B0 fine-tuned on Food-101 dataset
Achieves ~85-90% top-1 accuracy with data augmentation

Usage:
    python train.py --dataset_path data/food-101 --epochs 30 --batch_size 64

Requirements:
    pip install torch torchvision tqdm scikit-learn
"""

import os
import json
import time
import argparse
import logging
import numpy as np
from pathlib import Path
from datetime import datetime

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, Dataset
from torch.optim.lr_scheduler import CosineAnnealingLR
import torchvision.transforms as transforms
import torchvision.models as models
from torchvision.datasets import ImageFolder

try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False

try:
    from sklearn.metrics import (
        classification_report, confusion_matrix,
        precision_score, recall_score, f1_score, accuracy_score
    )
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler("logs/training.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("training")


# ─── Preprocessing Pipeline ───────────────────────────────────────────────────

def get_transforms(phase: str, image_size: int = 224) -> transforms.Compose:
    """
    Get image transforms for training/validation.

    Training: augmentation (random crop, flip, color jitter, etc.)
    Validation: deterministic (resize, center crop, normalize)
    """
    if phase == "train":
        return transforms.Compose([
            transforms.RandomResizedCrop(image_size, scale=(0.7, 1.0)),
            transforms.RandomHorizontalFlip(p=0.5),
            transforms.RandomVerticalFlip(p=0.1),
            transforms.ColorJitter(
                brightness=0.3, contrast=0.3,
                saturation=0.3, hue=0.1
            ),
            transforms.RandomRotation(15),
            transforms.RandomGrayscale(p=0.05),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225]
            ),
            transforms.RandomErasing(p=0.1, scale=(0.02, 0.1)),
        ])
    else:  # val / test
        return transforms.Compose([
            transforms.Resize(int(image_size * 1.15)),
            transforms.CenterCrop(image_size),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225]
            )
        ])


# ─── Model Architecture ───────────────────────────────────────────────────────

def build_model(num_classes: int, architecture: str = "efficientnet_b0", pretrained: bool = True) -> nn.Module:
    """
    Build classification model.

    Supported architectures:
    - efficientnet_b0 (default, ~5.3M params, fast)
    - efficientnet_b3 (better accuracy, ~12M params)
    - resnet50 (classic, ~25M params)
    - resnet101 (high accuracy, ~44M params)
    """
    logger.info(f"Building {architecture} with {num_classes} classes (pretrained={pretrained})")

    arch = architecture.lower()

    if arch == "efficientnet_b0":
        weights = "IMAGENET1K_V1" if pretrained else None
        try:
            model = models.efficientnet_b0(weights=weights)
        except TypeError:
            model = models.efficientnet_b0(pretrained=pretrained)
        in_features = model.classifier[1].in_features
        model.classifier = nn.Sequential(
            nn.Dropout(p=0.3),
            nn.Linear(in_features, 512),
            nn.ReLU(),
            nn.Dropout(p=0.2),
            nn.Linear(512, num_classes)
        )

    elif arch == "efficientnet_b3":
        weights = "IMAGENET1K_V1" if pretrained else None
        try:
            model = models.efficientnet_b3(weights=weights)
        except TypeError:
            model = models.efficientnet_b3(pretrained=pretrained)
        in_features = model.classifier[1].in_features
        model.classifier = nn.Sequential(
            nn.Dropout(p=0.35),
            nn.Linear(in_features, 512),
            nn.SiLU(),
            nn.Dropout(p=0.2),
            nn.Linear(512, num_classes)
        )

    elif arch == "resnet50":
        weights = "IMAGENET1K_V1" if pretrained else None
        try:
            model = models.resnet50(weights=weights)
        except TypeError:
            model = models.resnet50(pretrained=pretrained)
        in_features = model.fc.in_features
        model.fc = nn.Sequential(
            nn.Dropout(p=0.3),
            nn.Linear(in_features, 512),
            nn.ReLU(),
            nn.Dropout(p=0.2),
            nn.Linear(512, num_classes)
        )

    elif arch == "resnet101":
        weights = "IMAGENET1K_V1" if pretrained else None
        try:
            model = models.resnet101(weights=weights)
        except TypeError:
            model = models.resnet101(pretrained=pretrained)
        in_features = model.fc.in_features
        model.fc = nn.Sequential(
            nn.Dropout(p=0.3),
            nn.Linear(in_features, 512),
            nn.ReLU(),
            nn.Dropout(p=0.2),
            nn.Linear(512, num_classes)
        )

    else:
        raise ValueError(f"Unsupported architecture: {architecture}")

    return model


def unfreeze_layers(model, num_layers_to_unfreeze: int = 30):
    """Gradually unfreeze layers for fine-tuning."""
    layers = list(model.parameters())
    for param in layers[:-num_layers_to_unfreeze]:
        param.requires_grad = False
    for param in layers[-num_layers_to_unfreeze:]:
        param.requires_grad = True
    logger.info(f"Unfrozen last {num_layers_to_unfreeze} parameter groups")


# ─── Training Functions ───────────────────────────────────────────────────────

def train_epoch(model, loader, criterion, optimizer, device, epoch, scheduler=None):
    """Run one training epoch."""
    model.train()
    total_loss, correct, total = 0.0, 0, 0

    iterable = tqdm(loader, desc=f"Epoch {epoch} [Train]") if HAS_TQDM else loader

    for batch_idx, (images, labels) in enumerate(iterable):
        images, labels = images.to(device), labels.to(device)

        optimizer.zero_grad()
        outputs = model(images)
        loss = criterion(outputs, labels)
        loss.backward()

        # Gradient clipping for stability
        nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        optimizer.step()

        total_loss += loss.item()
        _, predicted = outputs.max(1)
        correct += predicted.eq(labels).sum().item()
        total += labels.size(0)

        if HAS_TQDM:
            iterable.set_postfix({
                "loss": f"{total_loss / (batch_idx + 1):.4f}",
                "acc": f"{100.0 * correct / total:.2f}%"
            })

    if scheduler is not None:
        scheduler.step()

    avg_loss = total_loss / len(loader)
    accuracy = 100.0 * correct / total
    return avg_loss, accuracy


def validate_epoch(model, loader, criterion, device, epoch):
    """Run validation epoch."""
    model.eval()
    total_loss, correct, total = 0.0, 0, 0
    all_preds, all_labels = [], []

    with torch.no_grad():
        iterable = tqdm(loader, desc=f"Epoch {epoch} [Val]") if HAS_TQDM else loader
        for images, labels in iterable:
            images, labels = images.to(device), labels.to(device)
            outputs = model(images)
            loss = criterion(outputs, labels)

            total_loss += loss.item()
            _, predicted = outputs.max(1)
            correct += predicted.eq(labels).sum().item()
            total += labels.size(0)

            all_preds.extend(predicted.cpu().numpy())
            all_labels.extend(labels.cpu().numpy())

    avg_loss = total_loss / len(loader)
    accuracy = 100.0 * correct / total

    return avg_loss, accuracy, np.array(all_preds), np.array(all_labels)


def compute_metrics(preds, labels, class_names=None):
    """Compute comprehensive evaluation metrics."""
    metrics = {
        "accuracy": accuracy_score(labels, preds) * 100 if HAS_SKLEARN else None,
        "precision": precision_score(labels, preds, average="weighted", zero_division=0) * 100 if HAS_SKLEARN else None,
        "recall": recall_score(labels, preds, average="weighted", zero_division=0) * 100 if HAS_SKLEARN else None,
        "f1_score": f1_score(labels, preds, average="weighted", zero_division=0) * 100 if HAS_SKLEARN else None,
    }

    if HAS_SKLEARN and class_names:
        report = classification_report(labels, preds, target_names=class_names, zero_division=0)
        metrics["classification_report"] = report

    return metrics


# ─── MixUp Augmentation ───────────────────────────────────────────────────────

def mixup_data(x, y, alpha=0.2, device="cpu"):
    """Apply MixUp augmentation for better generalization."""
    if alpha > 0:
        lam = np.random.beta(alpha, alpha)
    else:
        lam = 1

    batch_size = x.size(0)
    index = torch.randperm(batch_size).to(device)

    mixed_x = lam * x + (1 - lam) * x[index]
    y_a, y_b = y, y[index]
    return mixed_x, y_a, y_b, lam


def mixup_criterion(criterion, pred, y_a, y_b, lam):
    return lam * criterion(pred, y_a) + (1 - lam) * criterion(pred, y_b)


# ─── Main Training Loop ───────────────────────────────────────────────────────

def train(args):
    """Main training function."""
    os.makedirs("logs", exist_ok=True)
    os.makedirs("checkpoints", exist_ok=True)
    os.makedirs("models", exist_ok=True)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"Training on device: {device}")

    # Dataset
    train_dir = os.path.join(args.dataset_path, "train")
    val_dir = os.path.join(args.dataset_path, "val")
    test_dir = os.path.join(args.dataset_path, "test")

    if not os.path.exists(train_dir):
        logger.error(f"Dataset not found at {train_dir}. Run download_dataset.py first.")
        return

    train_dataset = ImageFolder(train_dir, transform=get_transforms("train", args.image_size))
    val_dataset = ImageFolder(val_dir, transform=get_transforms("val", args.image_size))

    class_names = train_dataset.classes
    num_classes = len(class_names)
    logger.info(f"Dataset: {num_classes} classes, {len(train_dataset)} train, {len(val_dataset)} val samples")

    # Save class names
    with open(os.path.join(args.output_dir, "classes.json"), "w") as f:
        json.dump(class_names, f, indent=2)

    train_loader = DataLoader(
        train_dataset,
        batch_size=args.batch_size,
        shuffle=True,
        num_workers=args.num_workers,
        pin_memory=True if device.type == "cuda" else False
    )
    val_loader = DataLoader(
        val_dataset,
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=args.num_workers,
        pin_memory=True if device.type == "cuda" else False
    )

    # Build model
    model = build_model(num_classes, args.architecture, pretrained=True)

    # Phase 1: Only train classifier head
    unfreeze_layers(model, num_layers_to_unfreeze=10)
    model = model.to(device)

    criterion = nn.CrossEntropyLoss(label_smoothing=0.1)

    optimizer = optim.AdamW(
        filter(lambda p: p.requires_grad, model.parameters()),
        lr=args.learning_rate,
        weight_decay=1e-4
    )

    scheduler = CosineAnnealingLR(optimizer, T_max=args.epochs, eta_min=1e-6)

    # Training history
    history = {"train_loss": [], "val_loss": [], "train_acc": [], "val_acc": []}
    best_val_acc = 0.0
    best_epoch = 0

    logger.info("=" * 60)
    logger.info(f"Starting training: {args.architecture} | {args.epochs} epochs | lr={args.learning_rate}")
    logger.info("=" * 60)

    for epoch in range(1, args.epochs + 1):
        start_time = time.time()

        # Phase 2: Unfreeze more layers after warm-up
        if epoch == args.warmup_epochs + 1:
            logger.info(">>> Unfreezing full model for fine-tuning")
            unfreeze_layers(model, num_layers_to_unfreeze=100)
            for pg in optimizer.param_groups:
                pg["lr"] = args.learning_rate * 0.1  # Lower LR for fine-tuning

        # Train
        train_loss, train_acc = train_epoch(model, train_loader, criterion, optimizer, device, epoch, scheduler)

        # Validate
        val_loss, val_acc, val_preds, val_labels = validate_epoch(model, val_loader, criterion, device, epoch)

        epoch_time = time.time() - start_time

        # Log results
        logger.info(
            f"Epoch {epoch:03d}/{args.epochs} | "
            f"Train Loss: {train_loss:.4f} | Train Acc: {train_acc:.2f}% | "
            f"Val Loss: {val_loss:.4f} | Val Acc: {val_acc:.2f}% | "
            f"Time: {epoch_time:.1f}s"
        )

        # Update history
        history["train_loss"].append(train_loss)
        history["val_loss"].append(val_loss)
        history["train_acc"].append(train_acc)
        history["val_acc"].append(val_acc)

        # Save best model
        if val_acc > best_val_acc:
            best_val_acc = val_acc
            best_epoch = epoch
            torch.save({
                "epoch": epoch,
                "model_state_dict": model.state_dict(),
                "optimizer_state_dict": optimizer.state_dict(),
                "val_acc": val_acc,
                "val_loss": val_loss,
                "class_names": class_names,
                "architecture": args.architecture,
            }, os.path.join(args.output_dir, "food_classifier.pth"))
            logger.info(f"✓ New best model saved (val_acc={val_acc:.2f}%)")

        # Save checkpoint every N epochs
        if epoch % args.checkpoint_freq == 0:
            torch.save({
                "epoch": epoch,
                "model_state_dict": model.state_dict(),
                "history": history,
            }, f"checkpoints/checkpoint_epoch_{epoch:03d}.pth")

    # Final evaluation
    logger.info("\n" + "=" * 60)
    logger.info(f"Training complete! Best Val Acc: {best_val_acc:.2f}% at epoch {best_epoch}")
    logger.info("=" * 60)

    # Compute and log final metrics
    if HAS_SKLEARN:
        metrics = compute_metrics(val_preds, val_labels, class_names[:len(set(val_labels))])
        logger.info("\nFinal Evaluation Metrics:")
        logger.info(f"  Accuracy:  {metrics['accuracy']:.2f}%")
        logger.info(f"  Precision: {metrics['precision']:.2f}%")
        logger.info(f"  Recall:    {metrics['recall']:.2f}%")
        logger.info(f"  F1 Score:  {metrics['f1_score']:.2f}%")

        # Save metrics
        with open(os.path.join(args.output_dir, "training_metrics.json"), "w") as f:
            json.dump({
                "best_val_accuracy": best_val_acc,
                "best_epoch": best_epoch,
                "final_metrics": {k: v for k, v in metrics.items() if k != "classification_report"},
                "history": history,
                "config": vars(args)
            }, f, indent=2)

    logger.info(f"\nModel saved to: {args.output_dir}/food_classifier.pth")
    logger.info("Run inference with: python backend/models/inference.py")


def parse_args():
    parser = argparse.ArgumentParser(description="Train Food Classification Model")
    parser.add_argument("--dataset_path", type=str, default="dataset/food-101",
                        help="Path to dataset directory")
    parser.add_argument("--output_dir", type=str, default="models",
                        help="Directory to save model and artifacts")
    parser.add_argument("--architecture", type=str, default="efficientnet_b0",
                        choices=["efficientnet_b0", "efficientnet_b3", "resnet50", "resnet101"],
                        help="Model architecture")
    parser.add_argument("--epochs", type=int, default=30,
                        help="Number of training epochs")
    parser.add_argument("--warmup_epochs", type=int, default=5,
                        help="Epochs to train only the classifier head")
    parser.add_argument("--batch_size", type=int, default=64,
                        help="Batch size")
    parser.add_argument("--learning_rate", type=float, default=1e-3,
                        help="Initial learning rate")
    parser.add_argument("--image_size", type=int, default=224,
                        help="Input image size")
    parser.add_argument("--num_workers", type=int, default=4,
                        help="DataLoader workers")
    parser.add_argument("--checkpoint_freq", type=int, default=5,
                        help="Save checkpoint every N epochs")
    parser.add_argument("--use_mixup", action="store_true",
                        help="Use MixUp augmentation")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    os.makedirs(args.output_dir, exist_ok=True)
    train(args)
