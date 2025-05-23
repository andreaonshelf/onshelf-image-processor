# OnShelf Image Processing Service

An automated image processing microservice designed specifically for retail shelf photos. This service continuously monitors a Supabase database for approved images and applies advanced computer vision techniques to enhance image quality for optimal text extraction by LLMs.

## 🚀 Features

- **Automatic Rotation Correction**: Uses Hough Line Transform to detect shelf edges and correct image rotation (±10 degrees)
- **Brightness & Contrast Enhancement**: CLAHE algorithm in LAB color space for optimal text visibility
- **Shadow Enhancement**: Reveals details in dark shelving units with adaptive shadow lifting
- **Glare Reduction**: Removes reflections and glare from refrigerated sections with glass doors
- **Text Sharpening**: Unsharp mask filter for enhanced text edge definition
- **Continuous Processing**: Background worker polls database every 30 seconds for new images
- **Production-Ready**: Comprehensive error handling, structured logging, and health monitoring

## 🛠️ Technology Stack

- **FastAPI**: High-performance web framework
- **OpenCV**: Advanced computer vision processing
- **Supabase**: Database and file storage
- **Docker**: Containerized deployment
- **Structlog**: Structured JSON logging

## 📋 Prerequisites

- Python 3.11+
- Supabase account with:
  - Access to `media_files` table
  - Storage bucket named `retail-captures`
  - Service role key with read/write permissions

## 🔧 Installation

### Local Development

1. Clone the repository:
```bash
git clone https://github.com/yourusername/onshelf-image-processor.git
cd onshelf-image-processor
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp env.example .env
# Edit .env with your Supabase credentials
```

5. Run the service:
```bash
python main.py
```

### Docker Deployment

1. Build the Docker image:
```bash
docker build -t onshelf-processor .
```

2. Run the container:
```bash
docker run -d \
  --name onshelf-processor \
  -p 8000:8000 \
  --env-file .env \
  onshelf-processor
```

## ⚙️ Configuration

Environment variables (set in `.env` file):

| Variable | Description | Default |
|----------|-------------|---------|
| `SUPABASE_URL` | Your Supabase project URL | Required |
| `SUPABASE_SERVICE_KEY` | Service role key for database access | Required |
| `LOG_LEVEL` | Logging level (DEBUG, INFO, WARNING, ERROR) | INFO |
| `POLL_INTERVAL_SECONDS` | How often to check for new images | 30 |
| `MAX_CONCURRENT_PROCESSING` | Maximum images to process per batch | 5 |
| `PORT` | Service port | 8000 |

## 📊 Database Schema

The service expects the following table structure:

```sql
CREATE TABLE public.media_files (
    media_id uuid PRIMARY KEY,
    storage_path text,              -- Original image path
    processed_path text,            -- Processed image path (populated by service)
    processing_status text,         -- 'pending', 'processing', 'completed', 'failed'
    approval_status text,           -- Must be 'approved' for processing
    processing_metadata jsonb,      -- Processing details and parameters
    created_at timestamp
);
```

## 🔄 Processing Pipeline

1. **Monitoring**: Service polls for images where:
   - `approval_status = 'approved'`
   - `processing_status = 'pending'`
   - `processed_path IS NULL`

2. **Processing Stages**:
   - Mark as `processing`
   - Download original image
   - Apply rotation correction
   - Enhance brightness/contrast
   - Lift shadows
   - Reduce glare
   - Sharpen text
   - Upload processed image
   - Mark as `completed` with metadata

3. **Error Handling**: Failed images marked with error details

## 🌐 API Endpoints

### Health Check
```bash
GET /health
```
Returns service health status and database connectivity

### Manual Processing
```bash
POST /process/{media_id}
```
Manually trigger processing for a specific image

### Statistics
```bash
GET /stats
```
Get processing statistics and configuration

### Root
```bash
GET /
```
Service information and version

## 📈 Processing Metadata

Each processed image includes detailed metadata:

```json
{
  "processor_version": "1.0.0",
  "processing_time_seconds": 8.5,
  "original_size": "1920x1080",
  "processing_stages": ["rotation", "brightness", "shadows", "glare", "sharpening"],
  "rotation": {
    "detected_angle": -2.3,
    "rotation_applied": true,
    "final_size": "1918x1078"
  },
  "brightness_enhancement": {
    "clahe_clip_limit": 2.0,
    "gamma_correction": 1.2,
    "brightness_increase_percent": 15.3
  },
  "shadow_enhancement": {
    "shadow_factor": 1.8,
    "shadow_percentage": 23.5
  },
  "glare_reduction": {
    "glare_percentage": 5.2,
    "reflection_removal": true
  },
  "text_sharpening": {
    "unsharp_amount": 1.5,
    "sharpness_increase_percent": 42.1
  }
}
```

## 🚀 Deployment

### Render.com

1. Create a new Web Service
2. Connect your GitHub repository
3. Set environment variables
4. Deploy using Dockerfile

### Railway

1. Create new project from GitHub
2. Add environment variables
3. Deploy automatically

### Manual VPS

1. Install Docker
2. Clone repository
3. Set up environment variables
4. Run Docker container with restart policy

## 📊 Monitoring

The service provides structured JSON logs for monitoring:

```json
{
  "event": "image_processing_completed",
  "media_id": "123e4567-e89b-12d3-a456-426614174000",
  "duration_seconds": 8.5,
  "timestamp": "2024-01-20T15:30:45.123Z"
}
```

Monitor key events:
- `image_processing_started`
- `image_processing_completed`
- `image_processing_failed`
- `database_operation_success/failed`

## 🧪 Testing

Run manual test with curl:

```bash
# Check health
curl http://localhost:8000/health

# Trigger manual processing
curl -X POST http://localhost:8000/process/YOUR_MEDIA_ID
```

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is proprietary software for OnShelf.

## 🆘 Support

For issues or questions:
- Check logs for error details
- Ensure Supabase credentials are correct
- Verify database schema matches requirements
- Check image storage bucket permissions

## 🔍 Troubleshooting

### Common Issues

1. **Images not processing**:
   - Check `approval_status` is 'approved'
   - Verify storage path exists
   - Check Supabase connection

2. **Processing failures**:
   - Check logs for specific error
   - Verify image format (JPEG/PNG)
   - Ensure sufficient memory

3. **Slow processing**:
   - Adjust `MAX_CONCURRENT_PROCESSING`
   - Check image sizes
   - Monitor CPU usage 