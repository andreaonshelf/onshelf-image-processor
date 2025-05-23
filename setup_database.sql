-- OnShelf Image Processing Service Database Schema
-- Run this in your Supabase SQL Editor

-- Create the media_files table
CREATE TABLE IF NOT EXISTS public.media_files (
    media_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    storage_path text NOT NULL,              -- Original image path in storage
    processed_path text,                     -- Processed image path (populated by service)
    processing_status text DEFAULT 'pending', -- 'pending', 'processing', 'completed', 'failed'
    approval_status text DEFAULT 'pending',   -- 'pending', 'approved', 'rejected'
    processing_metadata jsonb,               -- Processing details and parameters
    file_name text,                         -- Original filename
    file_size bigint,                       -- File size in bytes
    mime_type text,                         -- Image MIME type
    uploaded_by uuid,                       -- User who uploaded (optional)
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_media_files_processing_status ON public.media_files(processing_status);
CREATE INDEX IF NOT EXISTS idx_media_files_approval_status ON public.media_files(approval_status);
CREATE INDEX IF NOT EXISTS idx_media_files_created_at ON public.media_files(created_at);
CREATE INDEX IF NOT EXISTS idx_media_files_pending_processing ON public.media_files(approval_status, processing_status, processed_path) 
WHERE approval_status = 'approved' AND processing_status = 'pending' AND processed_path IS NULL;

-- Create a function to update the updated_at column
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger to auto-update updated_at
DROP TRIGGER IF EXISTS update_media_files_updated_at ON public.media_files;
CREATE TRIGGER update_media_files_updated_at
    BEFORE UPDATE ON public.media_files
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Enable Row Level Security (optional, for production)
-- ALTER TABLE public.media_files ENABLE ROW LEVEL SECURITY;

-- Sample data for testing
INSERT INTO public.media_files (
    media_id,
    storage_path,
    processing_status,
    approval_status,
    file_name,
    file_size,
    mime_type,
    created_at
) VALUES 
(
    gen_random_uuid(),
    'test-images/sample-shelf-1.jpg',
    'pending',
    'approved',
    'sample-shelf-1.jpg',
    1024000,
    'image/jpeg',
    now()
),
(
    gen_random_uuid(),
    'test-images/sample-shelf-2.jpg',
    'pending',
    'approved',
    'sample-shelf-2.jpg',
    892000,
    'image/jpeg',
    now() - interval '5 minutes'
),
(
    gen_random_uuid(),
    'test-images/sample-shelf-3.jpg',
    'pending',
    'pending',  -- Not approved yet, won't be processed
    'sample-shelf-3.jpg',
    756000,
    'image/jpeg',
    now() - interval '10 minutes'
);

-- Verify the setup
SELECT 
    media_id,
    storage_path,
    processing_status,
    approval_status,
    file_name,
    created_at
FROM public.media_files
ORDER BY created_at DESC; 