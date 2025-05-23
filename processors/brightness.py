"""Brightness and contrast enhancement for optimal text reading."""

import cv2
import numpy as np
from typing import Tuple


def enhance_for_text_reading(image: np.ndarray) -> Tuple[np.ndarray, dict]:
    """
    Enhance image brightness and contrast for optimal text visibility.
    
    Uses CLAHE (Contrast Limited Adaptive Histogram Equalization) in LAB color space
    combined with gamma correction to maximize text readability for LLM processing.
    
    Args:
        image: Input image in BGR format
        
    Returns:
        Tuple of (enhanced_image, metadata)
    """
    # Convert BGR to LAB color space
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    
    # Split LAB channels
    l_channel, a_channel, b_channel = cv2.split(lab)
    
    # Apply CLAHE to L channel
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l_enhanced = clahe.apply(l_channel)
    
    # Merge channels back
    lab_enhanced = cv2.merge([l_enhanced, a_channel, b_channel])
    
    # Convert back to BGR
    enhanced = cv2.cvtColor(lab_enhanced, cv2.COLOR_LAB2BGR)
    
    # Apply gamma correction for additional brightness adjustment
    gamma = 1.2
    enhanced = apply_gamma_correction(enhanced, gamma)
    
    # Calculate enhancement metrics
    original_brightness = np.mean(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY))
    enhanced_brightness = np.mean(cv2.cvtColor(enhanced, cv2.COLOR_BGR2GRAY))
    
    metadata = {
        "brightness_enhancement": {
            "clahe_clip_limit": 2.0,
            "clahe_grid_size": "8x8",
            "gamma_correction": gamma,
            "original_mean_brightness": float(original_brightness),
            "enhanced_mean_brightness": float(enhanced_brightness),
            "brightness_increase_percent": float((enhanced_brightness - original_brightness) / original_brightness * 100)
        }
    }
    
    return enhanced, metadata


def apply_gamma_correction(image: np.ndarray, gamma: float = 1.0) -> np.ndarray:
    """
    Apply gamma correction to adjust image brightness.
    
    Args:
        image: Input image
        gamma: Gamma value (>1 brightens, <1 darkens)
        
    Returns:
        Gamma-corrected image
    """
    # Build lookup table
    inv_gamma = 1.0 / gamma
    table = np.array([((i / 255.0) ** inv_gamma) * 255 for i in range(256)]).astype("uint8")
    
    # Apply gamma correction using lookup table
    return cv2.LUT(image, table)


def adaptive_brightness_adjustment(image: np.ndarray) -> np.ndarray:
    """
    Apply adaptive brightness adjustment based on image histogram.
    
    Args:
        image: Input image
        
    Returns:
        Brightness-adjusted image
    """
    # Convert to grayscale for analysis
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Calculate histogram
    hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
    
    # Determine if image is dark or bright
    total_pixels = gray.shape[0] * gray.shape[1]
    dark_pixels = np.sum(hist[:85])  # Pixels with value < 85
    dark_ratio = dark_pixels / total_pixels
    
    if dark_ratio > 0.5:
        # Image is predominantly dark, apply stronger brightening
        return apply_gamma_correction(image, 1.5)
    elif dark_ratio > 0.3:
        # Moderately dark
        return apply_gamma_correction(image, 1.2)
    else:
        # Image is already bright enough
        return image


def enhance_local_contrast(image: np.ndarray) -> np.ndarray:
    """
    Enhance local contrast for better text definition.
    
    Args:
        image: Input image
        
    Returns:
        Contrast-enhanced image
    """
    # Convert to LAB
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    l_channel, a_channel, b_channel = cv2.split(lab)
    
    # Apply bilateral filter to reduce noise while preserving edges
    l_filtered = cv2.bilateralFilter(l_channel, 9, 75, 75)
    
    # Enhance contrast
    l_enhanced = cv2.normalize(l_filtered, None, 0, 255, cv2.NORM_MINMAX)
    
    # Merge and convert back
    lab_enhanced = cv2.merge([l_enhanced, a_channel, b_channel])
    return cv2.cvtColor(lab_enhanced, cv2.COLOR_LAB2BGR)


def process_brightness_enhancement(image: np.ndarray) -> Tuple[np.ndarray, dict]:
    """
    Complete brightness and contrast enhancement pipeline.
    
    Args:
        image: Input image
        
    Returns:
        Tuple of (processed_image, metadata)
    """
    # First apply CLAHE and gamma correction
    enhanced, metadata = enhance_for_text_reading(image)
    
    # Apply adaptive brightness if needed
    enhanced = adaptive_brightness_adjustment(enhanced)
    
    # Finally enhance local contrast
    enhanced = enhance_local_contrast(enhanced)
    
    return enhanced, metadata 