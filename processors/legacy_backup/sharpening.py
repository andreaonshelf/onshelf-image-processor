"""Text sharpening using unsharp mask for enhanced readability."""

import cv2
import numpy as np
from typing import Tuple


def sharpen_text(image: np.ndarray) -> Tuple[np.ndarray, dict]:
    """
    Apply unsharp mask filter to enhance text edges and readability.
    
    Creates a Gaussian blur and uses it to create an unsharp mask
    that enhances high-frequency details like text edges.
    
    Args:
        image: Input image in BGR format
        
    Returns:
        Tuple of (sharpened_image, metadata)
    """
    # Create Gaussian blur
    kernel_size = (9, 9)
    sigma = 10.0
    blurred = cv2.GaussianBlur(image, kernel_size, sigma)
    
    # Apply unsharp mask
    amount = 1.5
    sharpened = cv2.addWeighted(image, 1.0 + amount, blurred, -amount, 0)
    
    # Ensure values are in valid range
    sharpened = np.clip(sharpened, 0, 255).astype(np.uint8)
    
    # Calculate sharpness metrics
    gray_original = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray_sharpened = cv2.cvtColor(sharpened, cv2.COLOR_BGR2GRAY)
    
    # Use Laplacian variance as sharpness measure
    laplacian_original = cv2.Laplacian(gray_original, cv2.CV_64F).var()
    laplacian_sharpened = cv2.Laplacian(gray_sharpened, cv2.CV_64F).var()
    
    metadata = {
        "text_sharpening": {
            "kernel_size": kernel_size,
            "gaussian_sigma": sigma,
            "unsharp_amount": amount,
            "original_sharpness": float(laplacian_original),
            "enhanced_sharpness": float(laplacian_sharpened),
            "sharpness_increase_percent": float((laplacian_sharpened - laplacian_original) / laplacian_original * 100)
        }
    }
    
    return sharpened, metadata


def adaptive_sharpening(image: np.ndarray) -> np.ndarray:
    """
    Apply adaptive sharpening based on local image content.
    
    Stronger sharpening in text areas, less in smooth regions.
    
    Args:
        image: Input image
        
    Returns:
        Adaptively sharpened image
    """
    # Convert to grayscale for edge detection
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Detect edges (potential text areas)
    edges = cv2.Canny(gray, 50, 150)
    
    # Create edge mask with dilation
    kernel = np.ones((3, 3), np.uint8)
    edge_mask = cv2.dilate(edges, kernel, iterations=2)
    
    # Blur the mask for smooth transitions
    edge_mask = cv2.GaussianBlur(edge_mask.astype(np.float32), (15, 15), 0)
    edge_mask = edge_mask / 255.0
    
    # Apply different sharpening strengths
    # Strong sharpening for edges
    strong_sharp = apply_unsharp_mask(image, amount=2.0, sigma=5.0)
    # Mild sharpening for non-edges
    mild_sharp = apply_unsharp_mask(image, amount=0.5, sigma=10.0)
    
    # Blend based on edge mask
    result = np.zeros_like(image, dtype=np.float32)
    for i in range(3):
        result[:, :, i] = (strong_sharp[:, :, i] * edge_mask + 
                          mild_sharp[:, :, i] * (1 - edge_mask))
    
    return np.clip(result, 0, 255).astype(np.uint8)


def apply_unsharp_mask(image: np.ndarray, amount: float = 1.5, sigma: float = 10.0) -> np.ndarray:
    """
    Apply unsharp mask with specified parameters.
    
    Args:
        image: Input image
        amount: Strength of sharpening
        sigma: Gaussian blur sigma
        
    Returns:
        Sharpened image
    """
    blurred = cv2.GaussianBlur(image, (0, 0), sigma)
    sharpened = cv2.addWeighted(image, 1.0 + amount, blurred, -amount, 0)
    return np.clip(sharpened, 0, 255).astype(np.uint8)


def edge_enhancement(image: np.ndarray) -> np.ndarray:
    """
    Enhance edges specifically for better text definition.
    
    Args:
        image: Input image
        
    Returns:
        Edge-enhanced image
    """
    # Convert to LAB for better edge enhancement
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    l_channel, a_channel, b_channel = cv2.split(lab)
    
    # Apply edge enhancement to L channel
    # Use a sharpening kernel
    kernel = np.array([[-1, -1, -1],
                      [-1,  9, -1],
                      [-1, -1, -1]])
    
    l_enhanced = cv2.filter2D(l_channel, -1, kernel)
    
    # Blend with original for controlled enhancement
    l_final = cv2.addWeighted(l_channel, 0.7, l_enhanced, 0.3, 0)
    
    # Merge and convert back
    lab_enhanced = cv2.merge([l_final, a_channel, b_channel])
    return cv2.cvtColor(lab_enhanced, cv2.COLOR_LAB2BGR)


def process_text_sharpening(image: np.ndarray) -> Tuple[np.ndarray, dict]:
    """
    Complete text sharpening pipeline.
    
    Args:
        image: Input image
        
    Returns:
        Tuple of (processed_image, metadata)
    """
    # Apply main unsharp mask sharpening
    sharpened, metadata = sharpen_text(image)
    
    # Apply adaptive sharpening
    sharpened = adaptive_sharpening(sharpened)
    
    # Enhance edges for text
    sharpened = edge_enhancement(sharpened)
    
    # Update metadata
    metadata["text_sharpening"]["adaptive_sharpening"] = True
    metadata["text_sharpening"]["edge_enhancement"] = True
    
    return sharpened, metadata 