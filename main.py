"""OnShelf Image Processing Service - Main Application."""

import os
import asyncio
import time
from datetime import datetime
from typing import Dict, Any, Optional
from contextlib import asynccontextmanager
import signal
import sys

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
import uvicorn
from dotenv import load_dotenv

from database.supabase_client import SupabaseClient
from processors.rotation import process_rotation
from processors.brightness import process_brightness_enhancement
from processors.shadows import process_shadow_enhancement
from processors.glare import process_glare_reduction
from processors.sharpening import process_text_sharpening
from utils.logging import setup_logging, log_processing_start, log_processing_complete, log_processing_failed

# Load environment variables
load_dotenv()

# Initialize logger
logger = setup_logging(os.getenv("LOG_LEVEL", "INFO"))

# Global variables
db_client: Optional[SupabaseClient] = None
background_task_running = False
shutdown_event = asyncio.Event()


def process_image(media_id: str, storage_path: str) -> Dict[str, Any]:
    """
    Complete image processing pipeline.
    
    Args:
        media_id: UUID of the media file
        storage_path: Path to image in storage
        
    Returns:
        Processing results dictionary
    """
    start_time = time.time()
    current_stage = "initialization"
    
    try:
        # Log processing start
        log_processing_start(logger, media_id, storage_path)
        
        # Mark as processing
        current_stage = "marking_as_processing"
        db_client.mark_as_processing(media_id)
        
        # Download image
        current_stage = "downloading"
        image = db_client.download_image(storage_path)
        
        # Initialize metadata
        all_metadata = {
            "processor_version": "1.0.0",
            "original_size": f"{image.shape[1]}x{image.shape[0]}",
            "processing_stages": []
        }
        
        # 1. Rotation correction
        current_stage = "rotation_correction"
        image, rotation_metadata = process_rotation(image)
        all_metadata["processing_stages"].append("rotation")
        all_metadata.update(rotation_metadata)
        
        # 2. Brightness enhancement
        current_stage = "brightness_enhancement"
        image, brightness_metadata = process_brightness_enhancement(image)
        all_metadata["processing_stages"].append("brightness")
        all_metadata.update(brightness_metadata)
        
        # 3. Shadow enhancement
        current_stage = "shadow_enhancement"
        image, shadow_metadata = process_shadow_enhancement(image)
        all_metadata["processing_stages"].append("shadows")
        all_metadata.update(shadow_metadata)
        
        # 4. Glare reduction
        current_stage = "glare_reduction"
        image, glare_metadata = process_glare_reduction(image)
        all_metadata["processing_stages"].append("glare")
        all_metadata.update(glare_metadata)
        
        # 5. Text sharpening
        current_stage = "text_sharpening"
        image, sharpening_metadata = process_text_sharpening(image)
        all_metadata["processing_stages"].append("sharpening")
        all_metadata.update(sharpening_metadata)
        
        # Upload processed image
        current_stage = "uploading"
        processed_path = db_client.upload_processed_image(image, media_id)
        
        # Calculate processing time
        processing_time = time.time() - start_time
        all_metadata["processing_time_seconds"] = processing_time
        
        # Mark as completed
        current_stage = "marking_as_completed"
        db_client.mark_as_completed(media_id, processed_path, all_metadata)
        
        # Log completion
        log_processing_complete(logger, media_id, processing_time, all_metadata)
        
        return {
            "success": True,
            "media_id": media_id,
            "processed_path": processed_path,
            "processing_time": processing_time,
            "metadata": all_metadata
        }
        
    except Exception as e:
        # Log failure
        log_processing_failed(logger, media_id, e, current_stage)
        
        # Mark as failed in database
        try:
            error_message = f"Failed at stage '{current_stage}': {str(e)}"
            db_client.mark_as_failed(media_id, error_message)
        except Exception as db_error:
            logger.error(
                "failed_to_mark_as_failed",
                media_id=media_id,
                error=str(db_error)
            )
        
        return {
            "success": False,
            "media_id": media_id,
            "error": str(e),
            "stage": current_stage
        }


async def process_pending_images():
    """Process all pending images in the queue."""
    try:
        # Get pending images
        pending_images = db_client.get_pending_images(
            limit=int(os.getenv("MAX_CONCURRENT_PROCESSING", "5"))
        )
        
        if not pending_images:
            logger.debug("no_pending_images", timestamp=datetime.utcnow().isoformat())
            return
        
        logger.info(
            "processing_batch",
            count=len(pending_images),
            timestamp=datetime.utcnow().isoformat()
        )
        
        # Process each image
        for image_data in pending_images:
            if shutdown_event.is_set():
                break
                
            media_id = image_data["media_id"]
            storage_path = image_data["storage_path"]
            
            # Process image synchronously
            result = process_image(media_id, storage_path)
            
            # Small delay between processing to avoid overload
            await asyncio.sleep(1)
            
    except Exception as e:
        logger.error(
            "batch_processing_error",
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True
        )


async def background_worker():
    """Background worker that continuously polls for new images."""
    global background_task_running
    background_task_running = True
    
    poll_interval = int(os.getenv("POLL_INTERVAL_SECONDS", "30"))
    
    logger.info(
        "background_worker_started",
        poll_interval=poll_interval,
        timestamp=datetime.utcnow().isoformat()
    )
    
    while not shutdown_event.is_set():
        try:
            # Process pending images
            await process_pending_images()
            
            # Wait for next poll interval
            await asyncio.sleep(poll_interval)
            
        except Exception as e:
            logger.error(
                "background_worker_error",
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True
            )
            
            # Exponential backoff on errors
            await asyncio.sleep(min(poll_interval * 2, 300))
    
    background_task_running = False
    logger.info("background_worker_stopped", timestamp=datetime.utcnow().isoformat())


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    global db_client
    
    # Startup
    logger.info("service_starting", timestamp=datetime.utcnow().isoformat())
    
    # Initialize database client
    try:
        db_client = SupabaseClient()
        logger.info("database_client_initialized")
    except Exception as e:
        logger.error("database_client_initialization_failed", error=str(e))
        raise
    
    # Start background worker
    asyncio.create_task(background_worker())
    
    yield
    
    # Shutdown
    logger.info("service_shutting_down", timestamp=datetime.utcnow().isoformat())
    shutdown_event.set()
    
    # Wait for background worker to finish
    max_wait = 30
    waited = 0
    while background_task_running and waited < max_wait:
        await asyncio.sleep(1)
        waited += 1
    
    logger.info("service_shutdown_complete", timestamp=datetime.utcnow().isoformat())


# Create FastAPI app
app = FastAPI(
    title="OnShelf Image Processing Service",
    description="Automated image processing for retail shelf photos",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": "OnShelf Image Processing Service",
        "version": "1.0.0",
        "status": "running",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    try:
        # Check database connectivity
        db_health = db_client.health_check() if db_client else {"database": "not_initialized"}
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "background_worker": background_task_running,
            "database": db_health
        }
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e)
            }
        )


@app.post("/process/{media_id}")
async def manual_process(media_id: str, background_tasks: BackgroundTasks):
    """
    Manually trigger processing for a specific image.
    
    Args:
        media_id: UUID of the media file to process
        
    Returns:
        Processing status
    """
    try:
        # Verify image exists and needs processing
        response = db_client.client.table("media_files").select(
            "media_id", "storage_path", "processing_status"
        ).eq("media_id", media_id).execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Media file not found")
        
        image_data = response.data[0]
        
        if image_data["processing_status"] == "completed":
            return {
                "message": "Image already processed",
                "media_id": media_id,
                "status": "completed"
            }
        
        if image_data["processing_status"] == "processing":
            return {
                "message": "Image is currently being processed",
                "media_id": media_id,
                "status": "processing"
            }
        
        # Add to background tasks
        background_tasks.add_task(
            process_image,
            media_id,
            image_data["storage_path"]
        )
        
        return {
            "message": "Processing started",
            "media_id": media_id,
            "status": "queued"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "manual_process_error",
            media_id=media_id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats")
async def get_stats():
    """Get processing statistics."""
    try:
        # Get counts by status
        stats_response = db_client.client.table("media_files").select(
            "processing_status", "count"
        ).execute()
        
        # Count by status
        status_counts = {
            "pending": 0,
            "processing": 0,
            "completed": 0,
            "failed": 0
        }
        
        # This would need proper aggregation query
        # For now, return basic info
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "background_worker_active": background_task_running,
            "poll_interval_seconds": int(os.getenv("POLL_INTERVAL_SECONDS", "30")),
            "max_concurrent_processing": int(os.getenv("MAX_CONCURRENT_PROCESSING", "5"))
        }
        
    except Exception as e:
        logger.error("stats_error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


def handle_shutdown(signum, frame):
    """Handle shutdown signals gracefully."""
    logger.info("shutdown_signal_received", signal=signum)
    shutdown_event.set()
    sys.exit(0)


# Register signal handlers
signal.signal(signal.SIGINT, handle_shutdown)
signal.signal(signal.SIGTERM, handle_shutdown)


if __name__ == "__main__":
    # Run the application
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        log_level=os.getenv("LOG_LEVEL", "info").lower()
    ) 