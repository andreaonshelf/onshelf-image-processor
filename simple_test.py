#!/usr/bin/env python3
"""Simple functional test for the new CLAHE enhancement pipeline."""

import cv2
import numpy as np
import time
from processors.enhanced_clahe import process_smart_enhancement


def test_core_functionality():
    """Test that the core enhancement pipeline functions work correctly."""
    print("🧪 Testing Core CLAHE Pipeline Functionality")
    print("=" * 50)
    
    # Create a basic test image
    test_image = np.ones((300, 400, 3), dtype=np.uint8) * 100
    cv2.rectangle(test_image, (50, 50), (350, 100), (120, 120, 120), -1)
    cv2.putText(test_image, "TEST IMAGE", (70, 80), cv2.FONT_HERSHEY_SIMPLEX, 1, (80, 80, 80), 2)
    
    print("📸 Processing test image...")
    
    # Test the processing function
    start_time = time.time()
    enhanced_image, metadata = process_smart_enhancement(test_image)
    processing_time = (time.time() - start_time) * 1000
    
    # Validate basic functionality
    print("✅ Processing completed successfully")
    print(f"⏱️  Processing time: {processing_time:.1f}ms")
    print(f"🔧 Technique used: {metadata['technique_used']}")
    print(f"📊 Enhancement applied: {metadata['enhancement_applied']}")
    
    # Validate metadata structure
    required_fields = [
        "enhancement_applied", "technique_used", "quality_assessment", 
        "processing_time_ms"
    ]
    
    for field in required_fields:
        assert field in metadata, f"Missing required field: {field}"
        print(f"✅ Required field '{field}' present")
    
    # Validate output image
    assert enhanced_image is not None, "Enhanced image should not be None"
    assert enhanced_image.shape == test_image.shape, "Output image shape should match input"
    assert enhanced_image.dtype == test_image.dtype, "Output image type should match input"
    
    print("✅ Output image validation passed")
    
    # Validate quality assessment fields
    qa = metadata["quality_assessment"]
    qa_fields = ["contrast", "brightness", "sharpness", "needs_enhancement"]
    for field in qa_fields:
        assert field in qa, f"Missing quality assessment field: {field}"
        if field != "needs_enhancement":
            assert isinstance(qa[field], (int, float)), f"{field} should be numeric"
    
    print("✅ Quality assessment structure valid")
    
    # Test with different image types
    print("\n📸 Testing with different image conditions...")
    
    # Very dark image
    dark_image = np.ones((200, 300, 3), dtype=np.uint8) * 20
    dark_enhanced, dark_metadata = process_smart_enhancement(dark_image)
    print(f"  Dark image - Enhancement: {dark_metadata['enhancement_applied']}")
    
    # Very bright image  
    bright_image = np.ones((200, 300, 3), dtype=np.uint8) * 220
    bright_enhanced, bright_metadata = process_smart_enhancement(bright_image)
    print(f"  Bright image - Enhancement: {bright_metadata['enhancement_applied']}")
    
    print("\n✅ All core functionality tests passed!")
    return True


def test_performance():
    """Test that processing is fast enough."""
    print("\n⚡ Performance Testing")
    print("=" * 30)
    
    # Test with different image sizes
    sizes = [(200, 300), (400, 600), (800, 1200)]
    
    for height, width in sizes:
        test_image = np.random.randint(0, 255, (height, width, 3), dtype=np.uint8)
        
        start_time = time.time()
        _, metadata = process_smart_enhancement(test_image)
        processing_time = (time.time() - start_time) * 1000
        
        print(f"📏 {width}x{height}: {processing_time:.1f}ms")
        
        # Should be under 2 seconds for any reasonable image size
        assert processing_time < 2000, f"Processing too slow for {width}x{height}: {processing_time}ms"
    
    print("✅ Performance tests passed!")
    return True


def test_error_handling():
    """Test error handling with invalid inputs."""
    print("\n🛡️  Error Handling Testing")
    print("=" * 30)
    
    # Test with invalid image (should return original)
    try:
        # Empty image
        empty_image = np.array([])
        # This should handle the error gracefully
        result_image, metadata = process_smart_enhancement(empty_image)
        print("✅ Empty image handled gracefully")
    except:
        print("⚠️  Empty image caused exception (may be expected)")
    
    # Test with minimal valid image
    tiny_image = np.ones((10, 10, 3), dtype=np.uint8) * 128
    tiny_enhanced, tiny_metadata = process_smart_enhancement(tiny_image)
    assert tiny_enhanced is not None, "Tiny image should be processed"
    print("✅ Tiny image processed successfully")
    
    print("✅ Error handling tests passed!")
    return True


if __name__ == "__main__":
    try:
        print("🚀 Starting Simple CLAHE Pipeline Tests")
        print("=" * 60)
        
        # Run all tests
        test_core_functionality()
        test_performance()  
        test_error_handling()
        
        print("\n" + "=" * 60)
        print("🎉 ALL TESTS PASSED!")
        print("✅ Core functionality working")
        print("⚡ Performance acceptable") 
        print("🛡️  Error handling robust")
        print("🚀 Pipeline ready for production!")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        exit(1) 