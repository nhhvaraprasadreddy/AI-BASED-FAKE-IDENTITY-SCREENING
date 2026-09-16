from __future__ import annotations

import logging
import cv2
import numpy as np
from typing import Any, Optional

from src.config import PREPROCESSING

logger = logging.getLogger(__name__)

class ImagePreprocessor:
    """Computer vision modules for image preprocessing and analysis."""

    def preprocess(self, image: np.ndarray) -> dict[str, Any]:
        """Runs the full pipeline."""
        steps = []
        try:
            if image is None or not isinstance(image, np.ndarray):
                logger.error("Invalid image provided for preprocessing")
                return {"original": image, "processed": image, "steps": steps}

            resized = self.resize_image(image)
            steps.append({"name": "resize", "description": "Resized to max 1024px", "image": resized})
            
            denoised = self.denoise(resized)
            steps.append({"name": "denoise", "description": "Applied non-local means denoising", "image": denoised})
            
            gray = self.to_grayscale(denoised)
            steps.append({"name": "grayscale", "description": "Converted to grayscale", "image": gray})
            
            thresh = self.adaptive_threshold(gray)
            steps.append({"name": "threshold", "description": "Applied adaptive thresholding", "image": thresh})
            
            return {
                "original": image,
                "processed": thresh,
                "grayscale": gray,
                "steps": steps
            }
        except Exception as e:
            logger.error(f"Error in preprocessing pipeline: {e}")
            return {"original": image, "processed": image, "steps": steps}

    def resize_image(self, image: np.ndarray, max_dim: Optional[int] = None) -> np.ndarray:
        """Resize maintaining aspect ratio."""
        try:
            if max_dim is None:
                max_dim = PREPROCESSING.get("max_dimension", 1024)
            h, w = image.shape[:2]
            if max(h, w) > max_dim:
                scale = max_dim / max(h, w)
                return cv2.resize(image, (int(w * scale), int(h * scale)))
            return image
        except Exception as e:
            logger.error(f"Error resizing image: {e}")
            return image

    def to_grayscale(self, image: np.ndarray) -> np.ndarray:
        """Convert BGR to grayscale."""
        try:
            if len(image.shape) == 2:
                return image
            if len(image.shape) == 3 and image.shape[2] == 3:
                return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            if len(image.shape) == 3 and image.shape[2] == 4:
                return cv2.cvtColor(image, cv2.COLOR_BGRA2GRAY)
            return image
        except Exception as e:
            logger.error(f"Error converting to grayscale: {e}")
            return image

    def denoise(self, image: np.ndarray) -> np.ndarray:
        """Use fastNlMeansDenoising."""
        try:
            h = PREPROCESSING.get("denoise_strength", 10)
            hColor = PREPROCESSING.get("denoise_color_strength", 10)
            if len(image.shape) == 3:
                return cv2.fastNlMeansDenoisingColored(image, None, h, hColor, 7, 21)
            else:
                return cv2.fastNlMeansDenoising(image, None, h, 7, 21)
        except Exception as e:
            logger.error(f"Error denoising image: {e}")
            return image

    def deskew(self, image: np.ndarray) -> np.ndarray:
        """Detect skew angle and rotate."""
        try:
            gray = self.to_grayscale(image)
            coords = np.column_stack(np.where(gray > 0))
            if len(coords) == 0:
                return image
            angle = cv2.minAreaRect(coords)[-1]
            if angle < -45:
                angle = -(90 + angle)
            else:
                angle = -angle
            if abs(angle) < 0.5:
                return image
            (h, w) = image.shape[:2]
            center = (w // 2, h // 2)
            M = cv2.getRotationMatrix2D(center, angle, 1.0)
            return cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        except Exception as e:
            logger.error(f"Error deskewing image: {e}")
            return image

    def adaptive_threshold(self, image: np.ndarray) -> np.ndarray:
        """Apply cv2.adaptiveThreshold."""
        try:
            gray = self.to_grayscale(image)
            block_size = PREPROCESSING.get("adaptive_threshold_block_size", 11)
            c = PREPROCESSING.get("adaptive_threshold_c", 2)
            return cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, block_size, c
            )
        except Exception as e:
            logger.error(f"Error applying adaptive threshold: {e}")
            return image
