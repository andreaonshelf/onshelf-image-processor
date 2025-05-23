#!/usr/bin/env python3
"""Diagnostic script to check pending image processing status."""

import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from database.supabase_client import SupabaseClient

# Load environment variables
load_dotenv()

def diagnose_pending_images():
    """Diagnose why images might not be getting processed."""
    try:
        db_client = SupabaseClient()
        
        print("🔍 DIAGNOSTIC: Checking Image Processing Pipeline")
        print("=" * 60)
        
        # 1. Check recent media uploads
        print("\n📁 RECENT MEDIA UPLOADS (last 2 hours):")
        recent_cutoff = datetime.utcnow() - timedelta(hours=2)
        
        recent_media = db_client.client.table("media_files").select(
            "media_id", "file_path", "status", "approval_status", "created_at"
        ).gte("created_at", recent_cutoff.isoformat()).order("created_at", desc=True).execute()
        
        print(f"Found {len(recent_media.data)} recent uploads:")
        for media in recent_media.data[:10]:  # Show latest 10
            created = media.get('created_at', 'unknown')[:19] if media.get('created_at') else 'unknown'
            print(f"  📸 {media['media_id'][:8]}... | {media['status']} | {media['approval_status']} | {created}")
        
        # 2. Check what's approved and completed but not processed
        print(f"\n✅ APPROVED & COMPLETED (ready for processing):")
        approved_completed = db_client.client.table("media_files").select(
            "media_id", "file_path", "status", "approval_status", "created_at"
        ).eq("approval_status", "approved").eq("status", "completed").order("created_at", desc=True).limit(10).execute()
        
        print(f"Found {len(approved_completed.data)} approved & completed:")
        for media in approved_completed.data:
            # Check if has pipeline record
            pipeline_check = db_client.client.table("media_processing_pipeline").select(
                "pipeline_id", "process_status"
            ).eq("source_media_id", media["media_id"]).eq("process_type", "enhancement").execute()
            
            pipeline_status = "NO PIPELINE" if not pipeline_check.data else pipeline_check.data[0]["process_status"]
            created = media.get('created_at', 'unknown')[:19] if media.get('created_at') else 'unknown'
            
            print(f"  🔄 {media['media_id'][:8]}... | {pipeline_status} | {created}")
        
        # 3. Check current pipeline processing status
        print(f"\n⚙️  CURRENT PIPELINE STATUS:")
        pipeline_status = db_client.client.table("media_processing_pipeline").select(
            "pipeline_id", "source_media_id", "process_type", "process_status", "created_at"
        ).eq("process_type", "enhancement").order("created_at", desc=True).limit(10).execute()
        
        print(f"Found {len(pipeline_status.data)} enhancement pipelines:")
        for pipe in pipeline_status.data:
            created = pipe.get('created_at', 'unknown')[:19] if pipe.get('created_at') else 'unknown'
            print(f"  ⚡ {pipe['source_media_id'][:8]}... | {pipe['process_status']} | {created}")
        
        # 4. Find truly pending work (approved+completed but no pipeline)
        print(f"\n🚨 TRULY PENDING (should be processed):")
        pending_count = 0
        for media in approved_completed.data:
            pipeline_check = db_client.client.table("media_processing_pipeline").select(
                "pipeline_id"
            ).eq("source_media_id", media["media_id"]).eq("process_type", "enhancement").execute()
            
            if not pipeline_check.data:
                pending_count += 1
                created = media.get('created_at', 'unknown')[:19] if media.get('created_at') else 'unknown'
                print(f"  🎯 {media['media_id']} | NEEDS PROCESSING | {created}")
                
                if pending_count == 1:  # Show details for first pending
                    print(f"      📁 Path: {media['file_path']}")
                    print(f"      📊 Status: {media['status']} | Approval: {media['approval_status']}")
        
        if pending_count == 0:
            print("  ✅ No truly pending images found")
        else:
            print(f"  🚨 Found {pending_count} images that should be processed!")
        
        # 5. Check service polling behavior
        print(f"\n🔄 SERVICE POLLING INFO:")
        print(f"  📍 Service running on: http://localhost:8001")
        print(f"  ⏰ Poll interval: 30 seconds")
        print(f"  🎯 Looking for: approval_status='approved' AND status='completed'")
        print(f"  ❌ Excluding: Images with existing enhancement pipeline records")
        
        return pending_count > 0
        
    except Exception as e:
        print(f"❌ Diagnostic failed: {e}")
        return False

def force_process_image(media_id: str):
    """Force process a specific image by ID."""
    try:
        print(f"\n🚀 FORCE PROCESSING: {media_id}")
        
        # Make API call to the running service
        import httpx
        response = httpx.post(f"http://localhost:8001/process/{media_id}", timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Processing triggered: {result}")
        else:
            print(f"❌ Failed to trigger: {response.status_code} {response.text}")
            
    except Exception as e:
        print(f"❌ Force processing failed: {e}")

if __name__ == "__main__":
    has_pending = diagnose_pending_images()
    
    if has_pending:
        print(f"\n💡 RECOMMENDATION: Your service should pick these up within 30 seconds")
        print(f"   If not, there may be an issue with the background worker")
        
        media_id = input(f"\n🎯 Enter media_id to force process (or press Enter to skip): ").strip()
        if media_id:
            force_process_image(media_id)
    else:
        print(f"\n✅ All approved images are already processed or in progress")
        print(f"💭 Your '41-second pending' image might be:")
        print(f"   - Still uploading (status != 'completed')")
        print(f"   - Waiting for approval (approval_status != 'approved')")
        print(f"   - Already processed (has pipeline record)")
        
        check_specific = input(f"\n🔍 Enter specific media_id to check (or press Enter to skip): ").strip()
        if check_specific:
            try:
                db_client = SupabaseClient()
                
                # Check media_files
                media_result = db_client.client.table("media_files").select("*").eq("media_id", check_specific).execute()
                
                if media_result.data:
                    print(f"\n📋 MEDIA RECORD:")
                    media = media_result.data[0]
                    for key, value in media.items():
                        print(f"  {key}: {value}")
                    
                    # Check pipeline
                    pipeline_result = db_client.client.table("media_processing_pipeline").select("*").eq("source_media_id", check_specific).execute()
                    
                    if pipeline_result.data:
                        print(f"\n⚙️  PIPELINE RECORD:")
                        for key, value in pipeline_result.data[0].items():
                            print(f"  {key}: {value}")
                    else:
                        print(f"\n⚙️  NO PIPELINE RECORD FOUND")
                else:
                    print(f"\n❌ Media ID {check_specific} not found")
                    
            except Exception as e:
                print(f"❌ Check failed: {e}") 