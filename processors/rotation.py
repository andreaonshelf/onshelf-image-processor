"""Rotation detection and correction using Hough Line Transform."""

import cv2
import numpy as np
from typing import Tuple, Optional
import math


def detect_shelf_rotation(image: np.ndarray) -> float:
    """
    Detect rotation angle using shelf edge lines.
    
    Uses Hough Line Transform to detect predominant horizontal lines
    which represent shelf edges, then calculates the median rotation angle.
    
    Args:
        image: Input image in BGR format
        
    Returns:
        Rotation angle in degrees (positive = clockwise, negative = counter-clockwise)
        Limited to range [-10, 10] degrees
    """
    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Apply Gaussian blur to reduce noise
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    
    # Edge detection using Canny
    edges = cv2.Canny(blurred, 50, 150)
    
    # Detect lines using Hough Transform
    lines = cv2.HoughLines(edges, rho=1, theta=np.pi/180, threshold=100)
    
    if lines is None:
        return 0.0
    
    # Extract angles of detected lines
    angles = []
    
    for line in lines:
        rho, theta = line[0]
        
        # Convert theta to degrees
        angle_deg = theta * 180 / np.pi
        
        # Filter for approximately horizontal lines (80-100 degrees or 260-280 degrees)
        if (80 <= angle_deg <= 100) or (260 <= angle_deg <= 280):
            # Normalize angle to deviation from horizontal
            if angle_deg > 180:
                deviation = angle_deg - 270
            else:
                deviation = angle_deg - 90
            
            angles.append(deviation)
    
    if not angles:
        return 0.0
    
    # Calculate median angle for robustness against outliers
    median_angle = np.median(angles)
    
    # Limit rotation to ±10 degrees to prevent excessive data loss
    return np.clip(median_angle, -10, 10)


def apply_rotation(image: np.ndarray, angle: float) -> np.ndarray:
    """
    Apply rotation correction to image.
    
    Rotates the image by the specified angle, using border reflection
    to minimize data loss at edges.
    
    Args:
        image: Input image
        angle: Rotation angle in degrees (limited to ±10 degrees)
        
    Returns:
        Rotated image
    """
    # Ensure angle is within limits
    angle = np.clip(angle, -10, 10)
    
    # Get image dimensions
    height, width = image.shape[:2]
    center = (width // 2, height // 2)
    
    # Get rotation matrix
    rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
    
    # Calculate new image bounds to prevent cropping
    cos = np.abs(rotation_matrix[0, 0])
    sin = np.abs(rotation_matrix[0, 1])
    
    new_width = int((height * sin) + (width * cos))
    new_height = int((height * cos) + (width * sin))
    
    # Adjust rotation matrix for translation
    rotation_matrix[0, 2] += (new_width / 2) - center[0]
    rotation_matrix[1, 2] += (new_height / 2) - center[1]
    
    # Apply rotation with border reflection
    rotated = cv2.warpAffine(
        image, 
        rotation_matrix, 
        (new_width, new_height),
        borderMode=cv2.BORDER_REFLECT
    )
    
    return rotated


def auto_crop_borders(image: np.ndarray, threshold: int = 10) -> np.ndarray:
    """
    Remove black or reflected borders after rotation.
    
    Args:
        image: Rotated image
        threshold: Pixel value threshold for border detection
        
    Returns:
        Cropped image
    """
    # Convert to grayscale for border detection
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Find non-border pixels
    _, thresh = cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY)
    
    # Find contours
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if not contours:
        return image
    
    # Find largest contour (main image area)
    largest_contour = max(contours, key=cv2.contourArea)
    
    # Get bounding rectangle
    x, y, w, h = cv2.boundingRect(largest_contour)
    
    # Crop image
    cropped = image[y:y+h, x:x+w]
    
    return cropped


def process_rotation(image: np.ndarray) -> Tuple[np.ndarray, dict]:
    """
    Complete rotation processing pipeline.
    
    Args:
        image: Input image
        
    Returns:
        Tuple of (processed_image, metadata)
    """
    # Detect rotation angle
    angle = detect_shelf_rotation(image)
    
    # Apply rotation if needed
    if abs(angle) > 0.5:  # Only rotate if angle is significant
        rotated = apply_rotation(image, angle)
        # Auto-crop borders
        processed = auto_crop_borders(rotated)
    else:
        processed = image
        angle = 0.0
    
    metadata = {
        "rotation": {
            "detected_angle": float(angle),
            "rotation_applied": abs(angle) > 0.5,
            "final_size": f"{processed.shape[1]}x{processed.shape[0]}"
        }
    }
    
    return processed, metadata 