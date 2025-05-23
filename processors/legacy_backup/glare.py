"""Glare and reflection reduction for refrigerated sections."""

import cv2
import numpy as np
from typing import Tuple


def reduce_glare(image: np.ndarray) -> Tuple[np.ndarray, dict]:
    """
    Reduce glare and reflections from glass doors and bright surfaces.
    
    Detects bright spots using threshold on L channel and applies
    median filtering while preserving edges and text details.
    
    Args:
        image: Input image in BGR format
        
    Returns:
        Tuple of (processed_image, metadata)
    """
    # Convert to LAB color space
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    l_channel, a_channel, b_channel = cv2.split(lab)
    
    # Detect glare areas (very bright spots)
    glare_threshold = 220
    glare_mask = (l_channel > glare_threshold).astype(np.uint8) * 255
    
    # Use morphological operations for precise glare detection
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    glare_mask = cv2.morphologyEx(glare_mask, cv2.MORPH_CLOSE, kernel)
    glare_mask = cv2.morphologyEx(glare_mask, cv2.MORPH_OPEN, kernel)
    
    # Dilate mask slightly to cover glare edges
    glare_mask = cv2.dilate(glare_mask, kernel, iterations=1)
    
    # Apply median filter to glare areas
    l_filtered = cv2.medianBlur(l_channel, 9)
    
    # Blend filtered and original based on mask
    glare_mask_norm = glare_mask.astype(np.float32) / 255.0
    l_result = (l_filtered * glare_mask_norm + l_channel * (1 - glare_mask_norm)).astype(np.uint8)
    
    # Merge channels back
    lab_result = cv2.merge([l_result, a_channel, b_channel])
    result = cv2.cvtColor(lab_result, cv2.COLOR_LAB2BGR)
    
    # Calculate glare metrics
    total_pixels = l_channel.shape[0] * l_channel.shape[1]
    glare_pixels = np.sum(glare_mask > 0)
    glare_percentage = (glare_pixels / total_pixels) * 100
    
    metadata = {
        "glare_reduction": {
            "glare_threshold": glare_threshold,
            "median_kernel_size": 9,
            "glare_percentage": float(glare_percentage),
            "morphology_kernel_size": 5
        }
    }
    
    return result, metadata


def reduce_specular_highlights(image: np.ndarray) -> np.ndarray:
    """
    Reduce specular highlights while preserving texture details.
    
    Args:
        image: Input image
        
    Returns:
        Processed image
    """
    # Convert to HSV for better highlight detection
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv)
    
    # Detect specular highlights (high value, low saturation)
    highlight_mask = ((v > 240) & (s < 30)).astype(np.uint8) * 255
    
    # Apply inpainting to remove highlights
    result = cv2.inpaint(image, highlight_mask, 3, cv2.INPAINT_TELEA)
    
    return result


def adaptive_glare_reduction(image: np.ndarray) -> np.ndarray:
    """
    Apply adaptive glare reduction based on local image statistics.
    
    Args:
        image: Input image
        
    Returns:
        Processed image
    """
    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Calculate local mean and standard deviation
    kernel_size = 31
    local_mean = cv2.blur(gray, (kernel_size, kernel_size))
    gray_squared = gray.astype(np.float32) ** 2
    local_mean_squared = cv2.blur(gray_squared, (kernel_size, kernel_size))
    local_std = np.sqrt(np.maximum(local_mean_squared - local_mean.astype(np.float32) ** 2, 0))
    
    # Detect glare as areas with high brightness and low local contrast
    glare_mask = ((gray > 200) & (local_std < 20)).astype(np.float32)
    
    # Smooth the mask
    glare_mask = cv2.GaussianBlur(glare_mask, (15, 15), 0)
    
    # Apply bilateral filter to reduce glare while preserving edges
    filtered = cv2.bilateralFilter(image, 9, 75, 75)
    
    # Blend based on mask
    result = np.zeros_like(image, dtype=np.float32)
    for i in range(3):
        result[:, :, i] = filtered[:, :, i] * glare_mask + image[:, :, i] * (1 - glare_mask)
    
    return np.clip(result, 0, 255).astype(np.uint8)


def remove_reflections(image: np.ndarray) -> np.ndarray:
    """
    Remove reflections from glass surfaces using edge-preserving filtering.
    
    Args:
        image: Input image
        
    Returns:
        Processed image
    """
    # Apply guided filter to remove reflections while preserving edges
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Use guided filter (approximated with edge-preserving filter)
    filtered = cv2.edgePreservingFilter(image, flags=2, sigma_s=60, sigma_r=0.4)
    
    # Detect reflection areas (bright with low texture)
    edges = cv2.Canny(gray, 50, 150)
    reflection_mask = ((gray > 180) & (edges == 0)).astype(np.float32)
    reflection_mask = cv2.GaussianBlur(reflection_mask, (21, 21), 0)
    
    # Blend filtered and original
    result = np.zeros_like(image, dtype=np.float32)
    for i in range(3):
        result[:, :, i] = filtered[:, :, i] * reflection_mask + image[:, :, i] * (1 - reflection_mask)
    
    return np.clip(result, 0, 255).astype(np.uint8)


def process_glare_reduction(image: np.ndarray) -> Tuple[np.ndarray, dict]:
    """
    Complete glare and reflection reduction pipeline.
    
    Args:
        image: Input image
        
    Returns:
        Tuple of (processed_image, metadata)
    """
    # Apply main glare reduction
    processed, metadata = reduce_glare(image)
    
    # Remove specular highlights
    processed = reduce_specular_highlights(processed)
    
    # Apply adaptive glare reduction
    processed = adaptive_glare_reduction(processed)
    
    # Remove reflections
    processed = remove_reflections(processed)
    
    # Update metadata
    metadata["glare_reduction"]["specular_removal"] = True
    metadata["glare_reduction"]["adaptive_reduction"] = True
    metadata["glare_reduction"]["reflection_removal"] = True
    
    return processed, metadata 