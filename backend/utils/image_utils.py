"""
Image Utilities
Image validation and preprocessing for food classification.
"""

import os
import io
import logging
from typing import Tuple

logger = logging.getLogger("utils.image_utils")

ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB


def validate_image(file) -> Tuple[bool, str]:
    """
    Validate uploaded image file.
    Returns (is_valid, error_message)
    """
    # Check file size
    file.seek(0, 2)  # Seek to end
    size = file.tell()
    file.seek(0)  # Reset

    if size > MAX_IMAGE_SIZE:
        return False, f"Image too large ({size // (1024*1024)}MB). Max 10MB."

    if size == 0:
        return False, "Empty file uploaded"

    # Check magic bytes for image type
    header = file.read(12)
    file.seek(0)

    if header[:4] == b'\x89PNG':
        return True, ""
    elif header[:3] == b'\xff\xd8\xff':
        return True, ""
    elif header[:6] in (b'GIF87a', b'GIF89a'):
        return True, ""
    elif header[:4] == b'RIFF' and header[8:12] == b'WEBP':
        return True, ""

    return False, "Invalid image format. Only PNG, JPG, GIF, and WEBP supported."


def preprocess_image(image_path: str, target_size: Tuple[int, int] = (224, 224)) -> "np.ndarray":
    """
    Preprocess image for model inference.
    Returns normalized numpy array ready for model input.
    """
    try:
        from PIL import Image
        import numpy as np

        img = Image.open(image_path).convert("RGB")

        # Resize
        img = img.resize(target_size, Image.LANCZOS)

        # Convert to numpy
        arr = np.array(img, dtype=np.float32)

        # Normalize (ImageNet stats)
        mean = np.array([0.485, 0.456, 0.406])
        std = np.array([0.229, 0.224, 0.225])
        arr = arr / 255.0
        arr = (arr - mean) / std

        # HWC -> CHW
        arr = arr.transpose(2, 0, 1)

        return arr

    except ImportError:
        logger.warning("PIL not available — returning raw image path")
        return image_path
    except Exception as e:
        logger.error(f"Image preprocessing failed: {e}")
        raise


def get_image_info(image_path: str) -> dict:
    """Get basic image metadata."""
    try:
        from PIL import Image
        img = Image.open(image_path)
        return {
            "format": img.format,
            "mode": img.mode,
            "size": img.size,
            "width": img.size[0],
            "height": img.size[1]
        }
    except Exception:
        return {}
