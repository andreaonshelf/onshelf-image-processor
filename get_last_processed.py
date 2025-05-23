#!/usr/bin/env python3
"""Script to find the path of the last processed image."""

import os
from dotenv import load_dotenv
from database.supabase_client import SupabaseClient

# Load environment variables
load_dotenv()

def get_last_processed_image():
    """Get the path and metadata of the most recently processed image."""
    try:
        # Initialize database client
        db_client = SupabaseClient()
        
        # Query for the most recent completed image
        response = db_client.client.table("media_files").select(
            "media_id", "storage_path", "processed_path", "processing_metadata", "created_at", "completed_at"
        ).eq("processing_status", "completed").order("completed_at", desc=True).limit(1).execute()
        
        if not response.data:
            print("❌ No processed images found in database")
            return None
        
        latest_image = response.data[0]
        
        print("📸 Last Processed Image:")
        print("=" * 40)
        print(f"🆔 Media ID: {latest_image['media_id']}")
        print(f"📁 Original Path: {latest_image['storage_path']}")
        print(f"✅ Processed Path: {latest_image['processed_path']}")
        print(f"⏰ Completed At: {latest_image['completed_at']}")
        
        # Show processing metadata if available
        if latest_image.get('processing_metadata'):
            metadata = latest_image['processing_metadata']
            print(f"\n📊 Processing Details:")
            if 'enhancement_applied' in metadata:
                print(f"  Enhancement Applied: {metadata['enhancement_applied']}")
            if 'technique_used' in metadata:
                print(f"  Technique Used: {metadata['technique_used']}")
            if 'processing_time_ms' in metadata:
                print(f"  Processing Time: {metadata['processing_time_ms']:.1f}ms")
        
        return latest_image['processed_path']
        
    except Exception as e:
        print(f"❌ Error querying database: {e}")
        return None

def download_last_processed_image(save_path: str = "last_processed_image.jpg"):
    """Download the last processed image to a local file."""
    try:
        db_client = SupabaseClient()
        
        # Get the last processed image path
        processed_path = get_last_processed_image()
        if not processed_path:
            return None
        
        print(f"\n📥 Downloading to: {save_path}")
        
        # Download the image
        image = db_client.download_image(processed_path)
        
        # Save locally
        import cv2
        cv2.imwrite(save_path, image)
        
        print(f"✅ Downloaded to: {os.path.abspath(save_path)}")
        return os.path.abspath(save_path)
        
    except Exception as e:
        print(f"❌ Error downloading image: {e}")
        return None

if __name__ == "__main__":
    print("🔍 Finding Last Processed Image")
    print("=" * 50)
    
    # Get the path
    processed_path = get_last_processed_image()
    
    if processed_path:
        print(f"\n🎯 Processed Image Path: {processed_path}")
        
        # Ask if user wants to download it locally
        download = input("\n📥 Download image locally? (y/n): ").lower().strip()
        if download == 'y':
            local_path = download_last_processed_image()
            if local_path:
                print(f"\n🎉 Image saved to: {local_path}")
    else:
        print("\n💡 Tip: Make sure you have processed images in your database")
        print("   You can process an image using: POST /process/{media_id}") 