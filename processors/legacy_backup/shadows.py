"""Shadow and highlight enhancement for dark shelving units."""

import cv2
import numpy as np
from typing import Tuple


def enhance_shadows(image: np.ndarray) -> Tuple[np.ndarray, dict]:
    """
    Enhance shadow areas to reveal details in dark shelving units.
    
    Creates a shadow mask and selectively brightens dark areas while
    preserving highlights, using smooth blending for natural results.
    
    Args:
        image: Input image in BGR format
        
    Returns:
        Tuple of (enhanced_image, metadata)
    """
    # Convert to grayscale for shadow detection
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Create shadow mask (threshold at 30% of max brightness)
    shadow_threshold = 0.3 * 255
    shadow_mask = (gray < shadow_threshold).astype(np.float32)
    
    # Apply Gaussian blur to shadow mask for smooth transitions
    shadow_mask = cv2.GaussianBlur(shadow_mask, (21, 21), 0)
    
    # Enhancement factor for shadows
    shadow_factor = 1.8
    
    # Create enhancement map
    enhancement_map = 1.0 + (shadow_mask * (shadow_factor - 1.0))
    
    # Apply enhancement to each channel
    enhanced = np.zeros_like(image, dtype=np.float32)
    for i in range(3):
        enhanced[:, :, i] = image[:, :, i] * enhancement_map
    
    # Clip values to valid range
    enhanced = np.clip(enhanced, 0, 255).astype(np.uint8)
    
    # Calculate enhancement metrics
    shadow_pixels = np.sum(shadow_mask > 0.5)
    total_pixels = gray.shape[0] * gray.shape[1]
    shadow_percentage = (shadow_pixels / total_pixels) * 100
    
    metadata = {
        "shadow_enhancement": {
            "shadow_threshold": float(shadow_threshold),
            "shadow_factor": shadow_factor,
            "shadow_percentage": float(shadow_percentage),
            "blur_kernel_size": 21
        }
    }
    
    return enhanced, metadata


def adjust_highlights(image: np.ndarray, highlight_factor: float = 0.9) -> np.ndarray:
    """
    Reduce brightness of highlight areas to balance with enhanced shadows.
    
    Args:
        image: Input image
        highlight_factor: Factor to reduce highlights (< 1.0)
        
    Returns:
        Adjusted image
    """
    # Convert to grayscale for highlight detection
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Create highlight mask (threshold at 80% of max brightness)
    highlight_threshold = 0.8 * 255
    highlight_mask = (gray > highlight_threshold).astype(np.float32)
    
    # Blur mask for smooth transitions
    highlight_mask = cv2.GaussianBlur(highlight_mask, (15, 15), 0)
    
    # Create adjustment map
    adjustment_map = 1.0 - (highlight_mask * (1.0 - highlight_factor))
    
    # Apply adjustment
    adjusted = np.zeros_like(image, dtype=np.float32)
    for i in range(3):
        adjusted[:, :, i] = image[:, :, i] * adjustment_map
    
    return np.clip(adjusted, 0, 255).astype(np.uint8)


def adaptive_shadow_enhancement(image: np.ndarray) -> np.ndarray:
    """
    Apply adaptive shadow enhancement based on image histogram.
    
    Args:
        image: Input image
        
    Returns:
        Enhanced image
    """
    # Convert to LAB color space
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    l_channel, a_channel, b_channel = cv2.split(lab)
    
    # Calculate histogram of L channel
    hist = cv2.calcHist([l_channel], [0], None, [256], [0, 256])
    
    # Find the peak of the histogram (most common brightness)
    peak_brightness = np.argmax(hist)
    
    # If peak is in dark region, apply stronger enhancement
    if peak_brightness < 50:
        # Very dark image - aggressive shadow lifting
        enhanced_l = cv2.add(l_channel, 30)
        enhanced_l = cv2.multiply(enhanced_l, 1.3)
    elif peak_brightness < 100:
        # Moderately dark - moderate enhancement
        enhanced_l = cv2.add(l_channel, 20)
        enhanced_l = cv2.multiply(enhanced_l, 1.2)
    else:
        # Normal brightness - light enhancement
        enhanced_l = cv2.add(l_channel, 10)
        enhanced_l = cv2.multiply(enhanced_l, 1.1)
    
    # Ensure values are in valid range
    enhanced_l = np.clip(enhanced_l, 0, 255).astype(np.uint8)
    
    # Merge channels and convert back
    enhanced_lab = cv2.merge([enhanced_l, a_channel, b_channel])
    return cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2BGR)


def process_shadow_enhancement(image: np.ndarray) -> Tuple[np.ndarray, dict]:
    """
    Complete shadow and highlight enhancement pipeline.
    
    Args:
        image: Input image
        
    Returns:
        Tuple of (processed_image, metadata)
    """
    # Apply main shadow enhancement
    enhanced, metadata = enhance_shadows(image)
    
    # Balance highlights
    enhanced = adjust_highlights(enhanced)
    
    # Apply adaptive enhancement if needed
    enhanced = adaptive_shadow_enhancement(enhanced)
    
    # Update metadata
    metadata["shadow_enhancement"]["highlight_adjustment"] = True
    metadata["shadow_enhancement"]["adaptive_enhancement"] = True
    
    return enhanced, metadata 