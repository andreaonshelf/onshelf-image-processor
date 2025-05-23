#!/usr/bin/env python3
from database.supabase_client import SupabaseClient
from dotenv import load_dotenv

load_dotenv()
db = SupabaseClient()

print('🔍 FINDING YOUR PENDING RECORD')
print('=' * 40)

# 1. Find pending pipeline records
print('\n📋 PENDING PIPELINE RECORDS:')
pending_pipelines = db.client.table('media_processing_pipeline').select(
    'pipeline_id,source_media_id,process_type,process_status,created_at,error_details'
).eq('process_status', 'pending').order('created_at', desc=True).execute()

if pending_pipelines.data:
    for record in pending_pipelines.data:
        print(f"  🔄 Pipeline: {record['pipeline_id']}")
        print(f"     Source: {record['source_media_id']}")
        print(f"     Type: {record['process_type']}")
        print(f"     Status: {record['process_status']}")
        print(f"     Created: {record['created_at']}")
        
        # Check the source media for this pending record
        print(f"\n  📸 SOURCE MEDIA STATUS:")
        source_media = db.client.table('media_files').select(
            'media_id,status,approval_status,created_at,file_path'
        ).eq('media_id', record['source_media_id']).execute()
        
        if source_media.data:
            media = source_media.data[0]
            print(f"     ✅ Found: {media['media_id']}")
            print(f"     📊 Status: {media['status']}")
            print(f"     ✋ Approval: {media['approval_status']}")
            print(f"     📁 Path: {media['file_path']}")
            print(f"     📅 Created: {media['created_at']}")
            
            # Check if this meets service criteria
            meets_criteria = (media['approval_status'] == 'approved' and 
                            media['status'] == 'completed')
            
            print(f"     🎯 Meets Service Criteria: {'✅ YES' if meets_criteria else '❌ NO'}")
            
            if not meets_criteria:
                print(f"     💡 ISSUE: Service needs approval_status='approved' AND status='completed'")
                print(f"        Current: approval_status='{media['approval_status']}', status='{media['status']}'")
            else:
                print(f"     ❓ MYSTERY: Media meets criteria but service skips it")
                print(f"        This suggests a service logic issue")
        else:
            print(f"     ❌ SOURCE MEDIA NOT FOUND!")
            
        print()
        
else:
    print("  ❌ No pending pipeline records found")
    
    # Check for recent pipeline records
    print(f"\n🔍 RECENT PIPELINE RECORDS (any status):")
    recent_pipelines = db.client.table('media_processing_pipeline').select(
        'pipeline_id,source_media_id,process_type,process_status,created_at'
    ).order('created_at', desc=True).limit(5).execute()
    
    for record in recent_pipelines.data:
        print(f"  📋 {record['source_media_id'][:8]}... | {record['process_type']} | {record['process_status']} | {record['created_at'][:19]}")

print(f"\n🛠️ IMMEDIATE FIXES:")
print(f"   1. If approval_status != 'approved': Approve the image")
print(f"   2. If status != 'completed': Wait for upload to complete")
print(f"   3. If both are correct: Force process via API")
print(f"      curl -X POST http://localhost:8001/process/YOUR_MEDIA_ID") 