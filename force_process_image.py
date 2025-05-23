#!/usr/bin/env python3
"""Force process a specific image directly, bypassing service logic."""

import os
import time
from dotenv import load_dotenv
from database.supabase_client import SupabaseClient
from processors.enhanced_clahe import process_smart_enhancement

# Load environment variables
load_dotenv()

def force_process_specific_image(media_id: str):
    """Process a specific image directly."""
    print(f"🚀 FORCE PROCESSING IMAGE: {media_id}")
    print("=" * 60)
    
    try:
        db_client = SupabaseClient()
        start_time = time.time()
        
        # 1. Get image details
        print("📋 1. GETTING IMAGE DETAILS...")
        media_response = db_client.client.table("media_files").select(
            "media_id", "file_path", "status", "approval_status"
        ).eq("media_id", media_id).execute()
        
        if not media_response.data:
            print(f"❌ Image {media_id} not found!")
            return False
            
        image_data = media_response.data[0]
        print(f"   ✅ Found: {image_data['file_path']}")
        print(f"   📊 Status: {image_data['status']} | Approval: {image_data['approval_status']}")
        
        # 2. Update pipeline to processing
        print("\n⚙️  2. MARKING AS PROCESSING...")
        db_client.mark_as_processing(media_id)
        print("   ✅ Pipeline status updated to 'processing'")
        
        # 3. Download image
        print("\n📥 3. DOWNLOADING IMAGE...")
        image = db_client.download_image(image_data["file_path"])
        print(f"   ✅ Downloaded: {image.shape[1]}x{image.shape[0]} pixels")
        
        # 4. Process with new CLAHE pipeline
        print("\n🎨 4. APPLYING CLAHE ENHANCEMENT...")
        enhanced_image, enhancement_metadata = process_smart_enhancement(image)
        print(f"   ✅ Enhancement applied: {enhancement_metadata['enhancement_applied']}")
        print(f"   🔧 Technique used: {enhancement_metadata['technique_used']}")
        print(f"   ⏱️  Processing time: {enhancement_metadata['processing_time_ms']:.1f}ms")
        
        # 5. Upload processed image
        print("\n📤 5. UPLOADING PROCESSED IMAGE...")
        processed_path = db_client.upload_processed_image(enhanced_image, media_id)
        print(f"   ✅ Uploaded to: {processed_path}")
        
        # 6. Complete metadata
        total_time = time.time() - start_time
        full_metadata = {
            "processor_version": "2.0.0",
            "original_size": f"{image.shape[1]}x{image.shape[0]}",
            "processing_approach": "research_proven_clahe",
            "processing_time_seconds": total_time,
            **enhancement_metadata
        }
        
        # 7. Mark as completed
        print("\n✅ 6. MARKING AS COMPLETED...")
        db_client.mark_as_completed(media_id, processed_path, full_metadata)
        print(f"   ✅ Total processing time: {total_time:.2f} seconds")
        
        print(f"\n🎉 SUCCESS! Image processed successfully!")
        print(f"📁 Processed image path: {processed_path}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ PROCESSING FAILED: {e}")
        
        # Try to mark as failed
        try:
            db_client.mark_as_failed(media_id, str(e))
            print("   📝 Marked as failed in database")
        except:
            print("   ⚠️  Could not update database with failure")
            
        return False

if __name__ == "__main__":
    # Your specific pending image
    PENDING_IMAGE_ID = "fdb7840e-369a-4729-a777-0dee0e730913"
    
    print("🎯 DIRECT IMAGE PROCESSING")
    print("This bypasses the service polling logic entirely")
    print()
    
    success = force_process_specific_image(PENDING_IMAGE_ID)
    
    if success:
        print("\n🚀 NEXT: Your image is now processed!")
        print("   Check your database - pipeline status should be 'completed'")
        print("   The processed image should be available in storage")
    else:
        print("\n💡 If this failed, check:")
        print("   - Network connectivity to Supabase")
        print("   - Storage permissions")
        print("   - Image file accessibility") 