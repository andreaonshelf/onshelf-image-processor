#!/usr/bin/env python3
from database.supabase_client import SupabaseClient
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

load_dotenv()
db = SupabaseClient()

print('🔍 RECENT UPLOADS (last 1 hour):')
recent = datetime.utcnow() - timedelta(hours=1)
result = db.client.table('media_files').select('media_id,status,approval_status,created_at').gte('created_at', recent.isoformat()).order('created_at', desc=True).execute()

for r in result.data:
    print(f'  {r["media_id"][:8]}... | {r["status"]} | {r["approval_status"]} | {r["created_at"][:19]}')

print(f'\n📊 TOTAL RECENT: {len(result.data)}')

if len(result.data) == 0:
    print('\n💡 No recent uploads found.')
    print('   Your pending image might be older or have a different status.')
    print('\n🎯 Try checking a specific media_id:')
    print('   python3 -c "from database.supabase_client import SupabaseClient; db=SupabaseClient(); print(db.client.table(\'media_files\').select(\'*\').eq(\'media_id\', \'YOUR_MEDIA_ID\').execute())"') 