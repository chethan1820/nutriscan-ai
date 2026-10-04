"""
Model Evaluation Script
Computes accuracy, precision, recall, F1-score and generates evaluation report.

Usage:
    python evaluate.py --model_path models/food_classifier.pth --dataset_path dataset/food-101/test
"""

import os
import json
import argparse
import logging
import numpy as np
from pathlib import Path

import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader
from torchvision.datasets import ImageFolder

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("evaluate")


def evaluate(args):
    """Run model evaluation on test set."""
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # Load checkpoint
    logger.info(f"Loading model from {args.model_path}")
    checkpoint = torch.load(args.model_path, map_location=device)

    architecture = checkpoint.get("architecture", "efficientnet_b0")
    class_names = checkpoint.get("class_names", [])

    # Build model
    import torchvision.models as models
    import torch.nn as nn

    if "efficientnet_b0" in architecture:
        model = models.efficientnet_b0(weights=None)
        in_features = model.classifier[1].in_features
        model.classifier = nn.Sequential(
            nn.Dropout(0.3), nn.Linear(in_features, 512),
            nn.ReLU(), nn.Dropout(0.2), nn.Linear(512, len(class_names))
        )
    elif "resnet50" in architecture:
        model = models.resnet50(weights=None)
        model.fc = nn.Sequential(
            nn.Dropout(0.3), nn.Linear(2048, 512),
            nn.ReLU(), nn.Dropout(0.2), nn.Linear(512, len(class_names))
        )
    else:
        raise ValueError(f"Unknown architecture: {architecture}")

    model.load_state_dict(checkpoint["model_state_dict"])
    model = model.to(device)
    model.eval()

    # Load test dataset
    import torchvision.transforms as transforms
    transform = transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])

    test_dataset = ImageFolder(args.dataset_path, transform=transform)
    test_loader = DataLoader(test_dataset, batch_size=args.batch_size, shuffle=False, num_workers=4)

    logger.info(f"Evaluating on {len(test_dataset)} images...")

    all_preds, all_labels, all_probs = [], [], []

    with torch.no_grad():
        for images, labels in test_loader:
            images = images.to(device)
            outputs = model(images)
            probs = F.softmax(outputs, dim=1)
            _, preds = outputs.max(1)

            all_preds.extend(preds.cpu().numpy())
            all_labels.extend(labels.numpy())
            all_probs.extend(probs.cpu().numpy())

    all_preds = np.array(all_preds)
    all_labels = np.array(all_labels)
    all_probs = np.array(all_probs)

    # Compute metrics
    from sklearn.metrics import (
        accuracy_score, precision_score, recall_score, f1_score,
        classification_report, top_k_accuracy_score
    )

    accuracy = accuracy_score(all_labels, all_preds) * 100
    precision = precision_score(all_labels, all_preds, average="weighted", zero_division=0) * 100
    recall = recall_score(all_labels, all_preds, average="weighted", zero_division=0) * 100
    f1 = f1_score(all_labels, all_preds, average="weighted", zero_division=0) * 100
    top5_acc = top_k_accuracy_score(all_labels, all_probs, k=5) * 100

    logger.info("\n" + "=" * 60)
    logger.info("EVALUATION RESULTS")
    logger.info("=" * 60)
    logger.info(f"Top-1 Accuracy:  {accuracy:.2f}%")
    logger.info(f"Top-5 Accuracy:  {top5_acc:.2f}%")
    logger.info(f"Precision:       {precision:.2f}%")
    logger.info(f"Recall:          {recall:.2f}%")
    logger.info(f"F1 Score:        {f1:.2f}%")
    logger.info("=" * 60)

    # Per-class report
    if args.verbose:
        report = classification_report(all_labels, all_preds, target_names=class_names, zero_division=0)
        logger.info("\nPer-Class Classification Report:")
        logger.info(report)

    # Save results
    results = {
        "top1_accuracy": accuracy,
        "top5_accuracy": top5_acc,
        "precision": precision,
        "recall": recall,
        "f1_score": f1,
        "num_test_samples": len(all_labels),
        "num_classes": len(class_names),
        "architecture": architecture
    }

    with open(os.path.join(args.output_dir, "evaluation_results.json"), "w") as f:
        json.dump(results, f, indent=2)

    logger.info(f"\nResults saved to {args.output_dir}/evaluation_results.json")
    return results


def parse_args():
    parser = argparse.ArgumentParser(description="Evaluate Food Classification Model")
    parser.add_argument("--model_path", type=str, default="models/food_classifier.pth")
    parser.add_argument("--dataset_path", type=str, default="dataset/food-101/test")
    parser.add_argument("--output_dir", type=str, default="models")
    parser.add_argument("--batch_size", type=int, default=64)
    parser.add_argument("--verbose", action="store_true", help="Print per-class report")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    os.makedirs(args.output_dir, exist_ok=True)
    evaluate(args)
