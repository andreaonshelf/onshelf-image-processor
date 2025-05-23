#!/usr/bin/env python3
"""Check for recently processed images and show detailed records."""

from database.supabase_client import SupabaseClient
from datetime import datetime, timedelta
from dotenv import load_dotenv
import json

load_dotenv()

def check_recent_processing():
    """Check for images processed in the last few minutes."""
    print("🔍 CHECKING RECENT PROCESSING ACTIVITY")
    print("=" * 60)
    
    try:
        db_client = SupabaseClient()
        
        # Check for recently completed pipeline records
        recent_cutoff = datetime.utcnow() - timedelta(minutes=5)
        
        print(f"\n📋 RECENT PIPELINE COMPLETIONS (last 5 minutes):")
        recent_pipelines = db_client.client.table("media_processing_pipeline").select(
            "pipeline_id", "source_media_id", "process_status", "output_media_id", 
            "process_results", "processing_time_ms", "updated_at", "created_at"
        ).eq("process_type", "enhancement").eq(
            "process_status", "completed"
        ).gte("updated_at", recent_cutoff.isoformat()).order("updated_at", desc=True).execute()
        
        if recent_pipelines.data:
            print(f"✅ Found {len(recent_pipelines.data)} recently completed processing jobs:")
            
            for pipeline in recent_pipelines.data:
                print(f"\n🎯 PIPELINE RECORD:")
                print(f"   Pipeline ID: {pipeline['pipeline_id']}")
                print(f"   Source Media ID: {pipeline['source_media_id']}")
                print(f"   Output Media ID: {pipeline['output_media_id']}")
                print(f"   Processing Time: {pipeline['processing_time_ms']}ms")
                print(f"   Completed At: {pipeline['updated_at']}")
                
                # Get the source media details
                source_media = db_client.client.table("media_files").select(
                    "media_id", "file_path", "status", "approval_status", "created_at", "metadata"
                ).eq("media_id", pipeline['source_media_id']).execute()
                
                if source_media.data:
                    source = source_media.data[0]
                    print(f"\n📸 SOURCE IMAGE:")
                    print(f"   Media ID: {source['media_id']}")
                    print(f"   File Path: {source['file_path']}")
                    print(f"   Status: {source['status']}")
                    print(f"   Approval: {source['approval_status']}")
                    print(f"   Uploaded: {source['created_at']}")
                
                # Get the processed image details
                if pipeline['output_media_id']:
                    processed_media = db_client.client.table("media_files").select(
                        "media_id", "file_path", "status", "metadata"
                    ).eq("media_id", pipeline['output_media_id']).execute()
                    
                    if processed_media.data:
                        processed = processed_media.data[0]
                        print(f"\n✅ PROCESSED IMAGE:")
                        print(f"   Media ID: {processed['media_id']}")
                        print(f"   File Path: {processed['file_path']}")
                        print(f"   Status: {processed['status']}")
                
                # Show processing results
                if pipeline['process_results']:
                    results = pipeline['process_results']
                    print(f"\n🎨 PROCESSING DETAILS:")
                    print(f"   Processor Version: {results.get('processor_version', 'unknown')}")
                    print(f"   Processing Approach: {results.get('processing_approach', 'unknown')}")
                    print(f"   Enhancement Applied: {results.get('enhancement_applied', 'unknown')}")
                    print(f"   Technique Used: {results.get('technique_used', 'unknown')}")
                    
                    if 'quality_assessment' in results:
                        qa = results['quality_assessment']
                        print(f"   Image Quality:")
                        print(f"     - Contrast: {qa.get('contrast', 'unknown'):.1f}")
                        print(f"     - Brightness: {qa.get('brightness', 'unknown'):.1f}")
                        print(f"     - Sharpness: {qa.get('sharpness', 'unknown'):.1f}")
                        print(f"     - Needed Enhancement: {qa.get('needs_enhancement', 'unknown')}")
                
                print(f"\n📋 FULL RECORD FOR SUPABASE VERIFICATION:")
                print(f"   Table: media_processing_pipeline")
                print(f"   Pipeline ID: {pipeline['pipeline_id']}")
                print(f"   Source Media ID: {pipeline['source_media_id']}")
                print(f"   Output Media ID: {pipeline['output_media_id']}")
                
                return pipeline  # Return the first recent record
                
        else:
            print("  ❌ No recent processing completions found")
            
            # Check for any recent pipeline activity (any status)
            print(f"\n🔍 ANY RECENT PIPELINE ACTIVITY:")
            any_recent = db_client.client.table("media_processing_pipeline").select(
                "pipeline_id", "source_media_id", "process_status", "updated_at"
            ).eq("process_type", "enhancement").gte(
                "updated_at", recent_cutoff.isoformat()
            ).order("updated_at", desc=True).limit(3).execute()
            
            if any_recent.data:
                for record in any_recent.data:
                    print(f"  📋 {record['source_media_id'][:8]}... | {record['process_status']} | {record['updated_at'][:19]}")
            else:
                print("  ❌ No recent pipeline activity at all")
                
            return None
            
    except Exception as e:
        print(f"❌ Check failed: {e}")
        return None

def get_specific_image_status(media_id: str):
    """Get detailed status for a specific image."""
    print(f"\n🔍 DETAILED STATUS FOR: {media_id}")
    print("=" * 50)
    
    try:
        db_client = SupabaseClient()
        
        # Get media file record
        media_record = db_client.client.table("media_files").select("*").eq("media_id", media_id).execute()
        
        if media_record.data:
            print(f"📸 MEDIA FILE RECORD:")
            media = media_record.data[0]
            for key, value in media.items():
                if key == 'metadata' and value:
                    print(f"   {key}: {json.dumps(value, indent=6)}")
                else:
                    print(f"   {key}: {value}")
        
        # Get pipeline record
        pipeline_record = db_client.client.table("media_processing_pipeline").select("*").eq(
            "source_media_id", media_id
        ).eq("process_type", "enhancement").execute()
        
        if pipeline_record.data:
            print(f"\n⚙️  PIPELINE RECORD:")
            pipeline = pipeline_record.data[0]
            for key, value in pipeline.items():
                if key == 'process_results' and value:
                    print(f"   {key}: {json.dumps(value, indent=6)}")
                else:
                    print(f"   {key}: {value}")
        else:
            print(f"\n❌ No pipeline record found")
            
    except Exception as e:
        print(f"❌ Status check failed: {e}")

if __name__ == "__main__":
    # Check for recent processing
    recent_record = check_recent_processing()
    
    if recent_record:
        print(f"\n🎉 SUCCESS! Found recent processing activity")
        print(f"📋 You can verify this in Supabase:")
        print(f"   1. Go to media_processing_pipeline table")
        print(f"   2. Look for pipeline_id: {recent_record['pipeline_id']}")
        print(f"   3. Check source_media_id: {recent_record['source_media_id']}")
        print(f"   4. Verify output_media_id: {recent_record['output_media_id']}")
        
        # Also show the source image details
        if recent_record['source_media_id']:
            get_specific_image_status(recent_record['source_media_id'])
    else:
        print(f"\n💡 No recent processing found")
        print(f"   This could mean:")
        print(f"   - Service is polling but finding no work")
        print(f"   - All recent images were already good quality")
        print(f"   - No new images have been approved recently") 