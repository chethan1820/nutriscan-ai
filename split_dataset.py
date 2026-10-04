import os
import shutil
import random

random.seed(42)

# YOUR REAL DATASET PATH
images_path = "dataset/images"

# OUTPUT PATH
food101_path = "dataset/food-101"

train_path = os.path.join(food101_path, "train")
val_path = os.path.join(food101_path, "val")
test_path = os.path.join(food101_path, "test")

os.makedirs(train_path, exist_ok=True)
os.makedirs(val_path, exist_ok=True)
os.makedirs(test_path, exist_ok=True)

classes = os.listdir(images_path)

for cls in classes:

    cls_dir = os.path.join(images_path, cls)

    if not os.path.isdir(cls_dir):
        continue

    images = os.listdir(cls_dir)

    random.shuffle(images)

    total = len(images)

    train_split = int(0.7 * total)
    val_split = int(0.85 * total)

    train_imgs = images[:train_split]
    val_imgs = images[train_split:val_split]
    test_imgs = images[val_split:]

    os.makedirs(os.path.join(train_path, cls), exist_ok=True)
    os.makedirs(os.path.join(val_path, cls), exist_ok=True)
    os.makedirs(os.path.join(test_path, cls), exist_ok=True)

    for img in train_imgs:
        shutil.copy(
            os.path.join(cls_dir, img),
            os.path.join(train_path, cls, img)
        )

    for img in val_imgs:
        shutil.copy(
            os.path.join(cls_dir, img),
            os.path.join(val_path, cls, img)
        )

    for img in test_imgs:
        shutil.copy(
            os.path.join(cls_dir, img),
            os.path.join(test_path, cls, img)
        )

print("Dataset split complete!")