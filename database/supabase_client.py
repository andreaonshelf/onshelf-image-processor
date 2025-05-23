"""Supabase database client for managing image processing workflow."""

import os
from typing import List, Dict, Any, Optional
from datetime import datetime
import time
from supabase import create_client, Client
import httpx
import numpy as np
import cv2
from utils.logging import setup_logging, log_database_operation


class SupabaseClient:
    """Handle all Supabase database and storage operations."""
    
    def __init__(self, supabase_url: str = None, service_key: str = None):
        """Initialize Supabase client with credentials."""
        self.logger = setup_logging(os.getenv("LOG_LEVEL", "INFO"))
        
        self.supabase_url = supabase_url or os.getenv("SUPABASE_URL")
        self.service_key = service_key or os.getenv("SUPABASE_SERVICE_KEY")
        
        if not self.supabase_url or not self.service_key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be provided")
        
        self.client: Client = create_client(self.supabase_url, self.service_key)
        self.storage_bucket = "retail-captures"
        
        self.logger.info("supabase_client_initialized", url=self.supabase_url)
    
    def get_pending_images(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get approved images that need processing.
        
        Returns:
            List of image records ready for processing (mapped to expected format)
        """
        try:
            # First get all approved, completed uploads
            response = self.client.table("media_files").select(
                "media_id", "file_path", "status", "approval_status", "metadata", "created_at"
            ).eq(
                "approval_status", "approved"
            ).eq(
                "status", "completed"  # Only process completed uploads
            ).order(
                "created_at"
            ).limit(limit * 2).execute()  # Get more to account for filtering
            
            # Filter out images that already have completed pipeline records
            # BUT INCLUDE images with pending/failed pipeline records that should be retried
            unprocessed_images = []
            for record in response.data:
                # Check if this image already has an enhancement pipeline record
                pipeline_check = self.client.table("media_processing_pipeline").select(
                    "pipeline_id", "process_status"
                ).eq("source_media_id", record["media_id"]).eq(
                    "process_type", "enhancement"
                ).execute()
                
                # Include if:
                # 1. No pipeline record exists (new image)
                # 2. Pipeline exists but status is 'pending' or 'failed' (retry needed)
                should_process = False
                if not pipeline_check.data:
                    should_process = True  # New image, no pipeline record
                else:
                    pipeline_status = pipeline_check.data[0]["process_status"]
                    if pipeline_status in ["pending", "failed"]:
                        should_process = True  # Retry pending or failed
                    # Skip if status is "completed" or "processing"
                
                if should_process:
                    unprocessed_images.append(record)
                    
                    # Stop when we have enough
                    if len(unprocessed_images) >= limit:
                        break
            
            # Map to expected format for the enhancement service
            mapped_results = []
            for record in unprocessed_images:
                mapped_record = {
                    "media_id": record["media_id"],
                    "storage_path": record["file_path"],  # Map file_path → storage_path
                    "created_at": record["created_at"]
                }
                mapped_results.append(mapped_record)
            
            log_database_operation(
                self.logger, 
                "get_pending_images", 
                True,
                {"count": len(mapped_results), "limit": limit, "filtered_count": len(response.data)}
            )
            
            return mapped_results
            
        except Exception as e:
            log_database_operation(
                self.logger,
                "get_pending_images",
                False,
                {"error": str(e)}
            )
            raise
    
    def mark_as_processing(self, media_id: str) -> bool:
        """
        Update image status to 'processing' before starting work.
        
        Args:
            media_id: UUID of the media file
            
        Returns:
            Success status
        """
        try:
            # For now, we'll add a pipeline record to track processing
            # First check if processing record already exists
            existing = self.client.table("media_processing_pipeline").select("pipeline_id").eq(
                "source_media_id", media_id
            ).eq("process_type", "enhancement").execute()
            
            if not existing.data:
                # Create new pipeline record
                response = self.client.table("media_processing_pipeline").insert({
                    "source_media_id": media_id,
                    "process_type": "enhancement",
                    "process_status": "processing",
                    "process_config": {
                        "processor_version": "1.0.0",
                        "started_at": datetime.utcnow().isoformat()
                    }
                }).execute()
            else:
                # Update existing record
                response = self.client.table("media_processing_pipeline").update({
                    "process_status": "processing",
                    "process_config": {
                        "processor_version": "1.0.0", 
                        "started_at": datetime.utcnow().isoformat()
                    }
                }).eq("source_media_id", media_id).eq("process_type", "enhancement").execute()
            
            log_database_operation(
                self.logger,
                "mark_as_processing",
                True,
                {"media_id": media_id}
            )
            
            return True
            
        except Exception as e:
            log_database_operation(
                self.logger,
                "mark_as_processing", 
                False,
                {"media_id": media_id, "error": str(e)}
            )
            raise
    
    def mark_as_completed(
        self, 
        media_id: str, 
        processed_path: str, 
        metadata: Dict[str, Any]
    ) -> bool:
        """
        Update image with successful processing results.
        
        Args:
            media_id: UUID of the media file
            processed_path: Path to processed image in storage
            metadata: Processing details and parameters
            
        Returns:
            Success status
        """
        try:
            # Get the original image details to inherit upload_id and other metadata
            original_image = self.client.table("media_files").select(
                "metadata", "file_path", "file_type"  # ✅ These exist in actual schema
            ).eq("media_id", media_id).execute()
            
            if not original_image.data:
                raise ValueError(f"Source image {media_id} not found")
            
            original_data = original_image.data[0]
            original_metadata = original_data.get("metadata", {})
            original_file_path = original_data.get("file_path", "")
            
            # Extract original filename from file_path
            original_filename = original_file_path.split("/")[-1] if original_file_path else "unknown.jpg"
            
            # Create processed image metadata inheriting upload_id
            processed_metadata = {
                "processed_from": media_id,
                "processing_metadata": metadata,
                "processor_version": "1.0.0",
                "original_filename": original_filename,
                "original_file_path": original_file_path
            }
            
            # Inherit upload_id if it exists for consistency
            if "upload_id" in original_metadata:
                processed_metadata["upload_id"] = original_metadata["upload_id"]
            
            # Inherit other important metadata
            if "public_url" in original_metadata:
                processed_metadata["source_public_url"] = original_metadata["public_url"]
            
            if "size" in original_metadata:
                processed_metadata["original_size"] = original_metadata["size"]
                
            if "mime_type" in original_metadata:
                processed_metadata["original_mime_type"] = original_metadata["mime_type"]
            
            # Create a new media_files record for the processed image
            processed_media_data = {
                "upload_id": f"processed-{media_id[:8]}",  # Always provide required upload_id
                "file_path": processed_path,
                "file_type": "image", 
                "status": "completed",
                "metadata": processed_metadata
            }
            
            # Override with original upload_id if it exists (for consistency)
            if "upload_id" in original_metadata:
                processed_media_data["upload_id"] = original_metadata["upload_id"]
            
            processed_media_response = self.client.table("media_files").insert(processed_media_data).execute()
            
            processed_media_id = processed_media_response.data[0]["media_id"]
            
            # Update the pipeline record
            response = self.client.table("media_processing_pipeline").update({
                "process_status": "completed",
                "output_media_id": processed_media_id,
                "process_results": metadata,
                "processing_time_ms": int(metadata.get("processing_time_seconds", 0) * 1000)
            }).eq("source_media_id", media_id).eq("process_type", "enhancement").execute()
            
            log_database_operation(
                self.logger,
                "mark_as_completed",
                True,
                {
                    "media_id": media_id, 
                    "processed_path": processed_path,
                    "processed_media_id": processed_media_id,
                    "inherited_upload_id": processed_metadata.get("upload_id", "none")
                }
            )
            
            return True
            
        except Exception as e:
            log_database_operation(
                self.logger,
                "mark_as_completed",
                False,
                {"media_id": media_id, "error": str(e)}
            )
            raise
    
    def mark_as_failed(self, media_id: str, error_message: str) -> bool:
        """
        Update image status to 'failed' with error details.
        
        Args:
            media_id: UUID of the media file
            error_message: Description of the failure
            
        Returns:
            Success status
        """
        try:
            response = self.client.table("media_processing_pipeline").update({
                "process_status": "failed",
                "error_details": error_message,
                "process_results": {
                    "failed_at": datetime.utcnow().isoformat(),
                    "error": error_message,
                    "processor_version": "1.0.0"
                }
            }).eq("source_media_id", media_id).eq("process_type", "enhancement").execute()
            
            log_database_operation(
                self.logger,
                "mark_as_failed",
                True,
                {"media_id": media_id, "error": error_message}
            )
            
            return True
            
        except Exception as e:
            log_database_operation(
                self.logger,
                "mark_as_failed",
                False,
                {"media_id": media_id, "error": str(e)}
            )
            raise
    
    def download_image(self, storage_path: str, max_retries: int = 3) -> np.ndarray:
        """
        Download image from Supabase storage and convert to OpenCV format.
        
        Args:
            storage_path: Path to image in storage bucket (from file_path field)
            max_retries: Maximum number of download attempts
            
        Returns:
            OpenCV image array
        """
        # Construct the public URL
        image_url = f"{self.supabase_url}/storage/v1/object/public/{self.storage_bucket}/{storage_path}"
        
        for attempt in range(max_retries):
            try:
                # Download image data
                response = httpx.get(image_url, timeout=30.0)
                response.raise_for_status()
                
                # Convert to OpenCV format
                image_array = np.frombuffer(response.content, np.uint8)
                image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
                
                if image is None:
                    raise ValueError("Failed to decode image")
                
                self.logger.info(
                    "image_downloaded",
                    storage_path=storage_path,
                    size=f"{image.shape[1]}x{image.shape[0]}",
                    attempt=attempt + 1
                )
                
                return image
                
            except Exception as e:
                if attempt == max_retries - 1:
                    self.logger.error(
                        "image_download_failed",
                        storage_path=storage_path,
                        error=str(e),
                        attempts=max_retries
                    )
                    raise
                
                # Exponential backoff
                time.sleep(2 ** attempt)
    
    def upload_processed_image(
        self, 
        image: np.ndarray, 
        media_id: str,
        max_retries: int = 3
    ) -> str:
        """
        Upload processed image to Supabase storage.
        
        Args:
            image: OpenCV image array
            media_id: UUID for naming the processed file
            max_retries: Maximum number of upload attempts
            
        Returns:
            Storage path of the uploaded file
        """
        # Encode image as JPEG with high quality
        success, buffer = cv2.imencode('.jpg', image, [cv2.IMWRITE_JPEG_QUALITY, 95])
        
        if not success:
            raise ValueError("Failed to encode image as JPEG")
        
        # Convert to bytes
        image_bytes = buffer.tobytes()
        
        # Generate filename
        file_path = f"processed/processed_{media_id}.jpg"
        
        for attempt in range(max_retries):
            try:
                # Upload to storage
                response = self.client.storage.from_(self.storage_bucket).upload(
                    file_path,
                    image_bytes,
                    {
                        "content-type": "image/jpeg",
                        "cache-control": "3600",
                        "upsert": "true"
                    }
                )
                
                self.logger.info(
                    "image_uploaded",
                    media_id=media_id,
                    file_path=file_path,
                    size_kb=len(image_bytes) / 1024,
                    attempt=attempt + 1
                )
                
                return file_path
                
            except Exception as e:
                if attempt == max_retries - 1:
                    self.logger.error(
                        "image_upload_failed",
                        media_id=media_id,
                        error=str(e),
                        attempts=max_retries
                    )
                    raise
                
                # Exponential backoff
                time.sleep(2 ** attempt)
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check database connectivity and return health status.
        
        Returns:
            Health check results
        """
        try:
            # Try a simple query on the actual table
            response = self.client.table("media_files").select("media_id").limit(1).execute()
            
            return {
                "database": "healthy",
                "storage": "healthy",
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {
                "database": "unhealthy",
                "storage": "unknown",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            } 