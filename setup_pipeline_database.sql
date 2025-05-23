-- OnShelf Multi-Step AI Processing Pipeline Database Schema
-- Foundation for enhancement → extraction → planogram analysis pipeline

-- Core media files table (keeps all assets)
CREATE TABLE IF NOT EXISTS public.media_files (
    media_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    storage_path text NOT NULL,              -- Path in storage bucket
    file_name text,                         -- Original filename
    file_size bigint,                       -- File size in bytes
    mime_type text,                         -- File MIME type
    media_type text DEFAULT 'image',        -- 'image', 'data', 'json', 'text'
    source_type text DEFAULT 'upload',      -- 'upload', 'processed', 'extracted'
    metadata jsonb,                         -- File-specific metadata
    uploaded_by uuid,                       -- User who uploaded (optional)
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);

-- Multi-step processing pipeline tracking
CREATE TABLE IF NOT EXISTS public.media_processing_pipeline (
    pipeline_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    source_media_id uuid REFERENCES media_files(media_id) ON DELETE CASCADE,
    output_media_id uuid REFERENCES media_files(media_id) ON DELETE CASCADE,
    process_type text NOT NULL,             -- 'enhancement', 'extraction', 'planogram', 'analysis'
    process_status text DEFAULT 'pending', -- 'pending', 'processing', 'completed', 'failed'
    process_config jsonb,                   -- Process-specific configuration
    process_results jsonb,                  -- Process output data/metadata
    error_details text,                     -- Error information if failed
    processing_time_ms integer,             -- Processing duration
    processor_version text,                 -- Version of processor used
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    
    UNIQUE(source_media_id, process_type)   -- Prevent duplicate processes
);

-- Legacy approval/status tracking for compatibility
CREATE TABLE IF NOT EXISTS public.media_approval_status (
    media_id uuid PRIMARY KEY REFERENCES media_files(media_id) ON DELETE CASCADE,
    approval_status text DEFAULT 'pending', -- 'pending', 'approved', 'rejected'
    approved_by uuid,                       -- Who approved
    approval_notes text,                    -- Approval/rejection notes
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);

-- Processing queue for orchestration
CREATE TABLE IF NOT EXISTS public.processing_queue (
    queue_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    media_id uuid REFERENCES media_files(media_id) ON DELETE CASCADE,
    process_type text NOT NULL,
    priority integer DEFAULT 5,            -- 1 (highest) to 10 (lowest)
    scheduled_for timestamp with time zone DEFAULT now(),
    retry_count integer DEFAULT 0,
    max_retries integer DEFAULT 3,
    queue_status text DEFAULT 'queued',    -- 'queued', 'processing', 'completed', 'failed'
    assigned_worker text,                   -- Worker ID processing this
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_media_files_media_type ON public.media_files(media_type);
CREATE INDEX IF NOT EXISTS idx_media_files_source_type ON public.media_files(source_type);
CREATE INDEX IF NOT EXISTS idx_media_files_created_at ON public.media_files(created_at);

CREATE INDEX IF NOT EXISTS idx_pipeline_source_media ON public.media_processing_pipeline(source_media_id);
CREATE INDEX IF NOT EXISTS idx_pipeline_output_media ON public.media_processing_pipeline(output_media_id);
CREATE INDEX IF NOT EXISTS idx_pipeline_process_type ON public.media_processing_pipeline(process_type);
CREATE INDEX IF NOT EXISTS idx_pipeline_status ON public.media_processing_pipeline(process_status);
CREATE INDEX IF NOT EXISTS idx_pipeline_pending ON public.media_processing_pipeline(process_type, process_status) 
WHERE process_status = 'pending';

CREATE INDEX IF NOT EXISTS idx_approval_status ON public.media_approval_status(approval_status);
CREATE INDEX IF NOT EXISTS idx_queue_status ON public.processing_queue(queue_status);
CREATE INDEX IF NOT EXISTS idx_queue_process_type ON public.processing_queue(process_type);
CREATE INDEX IF NOT EXISTS idx_queue_priority ON public.processing_queue(priority, scheduled_for);

-- Update timestamp triggers
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply triggers to all tables
DROP TRIGGER IF EXISTS update_media_files_updated_at ON public.media_files;
CREATE TRIGGER update_media_files_updated_at
    BEFORE UPDATE ON public.media_files
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_pipeline_updated_at ON public.media_processing_pipeline;
CREATE TRIGGER update_pipeline_updated_at
    BEFORE UPDATE ON public.media_processing_pipeline
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_approval_updated_at ON public.media_approval_status;
CREATE TRIGGER update_approval_updated_at
    BEFORE UPDATE ON public.media_approval_status
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_queue_updated_at ON public.processing_queue;
CREATE TRIGGER update_queue_updated_at
    BEFORE UPDATE ON public.processing_queue
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Helper view for backward compatibility with existing service
CREATE OR REPLACE VIEW media_files_legacy AS
SELECT 
    mf.media_id,
    mf.storage_path,
    -- Map pipeline status to legacy fields
    COALESCE(
        (SELECT output_media_id::text FROM media_processing_pipeline 
         WHERE source_media_id = mf.media_id AND process_type = 'enhancement' AND process_status = 'completed'
         LIMIT 1), 
        null
    ) as processed_path,
    COALESCE(
        (SELECT process_status FROM media_processing_pipeline 
         WHERE source_media_id = mf.media_id AND process_type = 'enhancement'
         ORDER BY created_at DESC LIMIT 1), 
        'pending'
    ) as processing_status,
    COALESCE(mas.approval_status, 'pending') as approval_status,
    COALESCE(
        (SELECT process_results FROM media_processing_pipeline 
         WHERE source_media_id = mf.media_id AND process_type = 'enhancement' AND process_status = 'completed'
         LIMIT 1), 
        '{}'::jsonb
    ) as processing_metadata,
    mf.created_at
FROM media_files mf
LEFT JOIN media_approval_status mas ON mf.media_id = mas.media_id
WHERE mf.media_type = 'image' AND mf.source_type = 'upload';

-- Sample data for testing the pipeline
INSERT INTO public.media_files (
    media_id,
    storage_path,
    file_name,
    file_size,
    mime_type,
    media_type,
    source_type,
    metadata
) VALUES 
(
    gen_random_uuid(),
    'test-images/sample-shelf-1.jpg',
    'sample-shelf-1.jpg',
    1024000,
    'image/jpeg',
    'image',
    'upload',
    '{"original": true, "test_data": true}'::jsonb
),
(
    gen_random_uuid(),
    'test-images/sample-shelf-2.jpg',
    'sample-shelf-2.jpg',
    892000,
    'image/jpeg',
    'image',
    'upload',
    '{"original": true, "test_data": true}'::jsonb
);

-- Add approval status for test images
INSERT INTO public.media_approval_status (media_id, approval_status)
SELECT media_id, 'approved'
FROM public.media_files 
WHERE source_type = 'upload' AND metadata->>'test_data' = 'true';

-- Add to processing queue for enhancement
INSERT INTO public.processing_queue (media_id, process_type, priority)
SELECT media_id, 'enhancement', 1
FROM public.media_files 
WHERE source_type = 'upload' AND metadata->>'test_data' = 'true';

-- Verify the setup
SELECT 
    'Media Files' as table_name,
    COUNT(*) as count
FROM public.media_files
UNION ALL
SELECT 
    'Approval Status' as table_name,
    COUNT(*) as count
FROM public.media_approval_status
UNION ALL
SELECT 
    'Processing Queue' as table_name,
    COUNT(*) as count
FROM public.processing_queue
UNION ALL
SELECT 
    'Legacy View' as table_name,
    COUNT(*) as count
FROM media_files_legacy; 