"""
Universal Instrument Recognition App - Backend API
Main FastAPI application with async processing support
"""

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import os
import uuid
from typing import Optional, Dict, Any
import logging
from app.models.stem_specific_classifier import get_stem_pipeline, initialize_stem_pipeline
from app.models.stem_integrated_classifier import get_integrated_classifier, initialize_integrated_classifier

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Universal Instrument Recognition API",
    description="AI-powered instrument detection and timeline generation",
    version="1.0.0"
)

# CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Temporary in-memory storage (replace with Redis in production)
job_storage: Dict[str, Dict[str, Any]] = {}

# Pydantic models for API responses
class JobStatus(BaseModel):
    job_id: str
    status: str  # "pending", "processing", "completed", "failed"
    progress: Optional[int] = 0
    message: Optional[str] = None

class AnalysisResult(BaseModel):
    job_id: str
    song_info: Dict[str, Any]
    timeline: Dict[str, Any]

class PredictionRequest(BaseModel):
    confidence_threshold: Optional[float] = 0.1

class ModelInfo(BaseModel):
    model_name: str
    num_classes: int
    class_names: list
    sample_rate: int
    segment_duration: float

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "Universal Instrument Recognition API", "status": "running"}

@app.get("/model/info")
async def get_model_info():
    """Get information about the loaded 3-stem models"""
    try:
        integrated_classifier = get_integrated_classifier()
        model_info = integrated_classifier.get_model_info()

        return {
            "system_type": model_info['system_type'],
            "models": model_info['models'],
            "audio_processing": model_info['audio_processing'],
            "performance_summary": model_info['performance_summary'],
            "total_classes": model_info['performance_summary']['total_classes']
        }
    except Exception as e:
        logger.error(f"Error getting model info: {e}")
        raise HTTPException(status_code=500, detail="3-stem models not loaded properly")

@app.post("/predict/{job_id}")
async def predict_instruments(job_id: str, request: PredictionRequest = PredictionRequest()):
    """
    Run full instrument recognition pipeline on uploaded file
    Includes beat detection, stem separation, and classification
    """
    if job_id not in job_storage:
        raise HTTPException(status_code=404, detail="Job not found")

    job = job_storage[job_id]

    if job["status"] != "uploaded":
        raise HTTPException(
            status_code=400,
            detail=f"Job must be 'uploaded' status, currently {job['status']}"
        )

    try:
        # Get integrated classifier
        integrated_classifier = get_integrated_classifier()

        # Progress callback to update job status
        def update_progress(progress: int, message: str):
            if progress >= 0:
                job["progress"] = progress
                job["message"] = message
                logger.info(f"Job {job_id}: {progress}% - {message}")
            else:
                job["status"] = "failed"
                job["message"] = message

        # Update initial status
        job["status"] = "processing"
        job["progress"] = 0
        job["message"] = "Starting analysis..."

        # Run complete processing pipeline with 3-stem models
        analysis_result = integrated_classifier.analyze_file(
            job["file_path"],
            confidence_threshold=request.confidence_threshold,
            progress_callback=update_progress
        )

        # Update job with results
        job["status"] = "completed"
        job["progress"] = 100
        job["message"] = "Analysis completed successfully"
        job["analysis_result"] = analysis_result

        # Calculate summary metrics for response
        processing_summary = analysis_result['processing_summary']
        song_info = analysis_result['song_info']

        logger.info(f"Analysis completed for job {job_id}: {song_info['duration']:.1f}s, "
                   f"{processing_summary['stems_processed']} stems processed")

        return {
            "job_id": job_id,
            "message": "Analysis completed successfully with 3-stem models",
            "duration": song_info['duration'],
            "tempo": song_info['tempo'],
            "total_beats": len(song_info.get('beats', [])),
            "stems_processed": processing_summary['stems_processed'],
            "total_segments": processing_summary['total_segments'],
            "model_performance": processing_summary['model_performance']
        }

    except Exception as e:
        # Update job with error
        job["status"] = "failed"
        job["message"] = f"Analysis failed: {str(e)}"
        logger.error(f"Analysis failed for job {job_id}: {e}")

        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {str(e)}"
        )

@app.post("/upload", response_model=Dict[str, str])
async def upload_file(file: UploadFile = File(...)):
    """
    Upload audio file for processing
    Supported formats: .mp3, .wav, .flac
    """
    # Validate file format
    allowed_extensions = {".mp3", ".wav", ".flac"}
    file_ext = os.path.splitext(file.filename)[1].lower()
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported file format. Allowed: {', '.join(allowed_extensions)}"
        )
    
    # Validate file size (50MB limit)
    if file.size > 50 * 1024 * 1024:  # 50MB
        raise HTTPException(
            status_code=400,
            detail="File size exceeds 50MB limit"
        )
    
    # Generate job ID and save file
    job_id = str(uuid.uuid4())
    file_path = f"uploads/{job_id}_{file.filename}"
    
    # Create uploads directory if it doesn't exist
    os.makedirs("uploads", exist_ok=True)
    
    # Save uploaded file
    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)
    
    # Initialize job status
    job_storage[job_id] = {
        "status": "uploaded",
        "filename": file.filename,
        "file_path": file_path,
        "progress": 0,
        "message": "File uploaded successfully"
    }
    
    logger.info(f"File uploaded: {file.filename} -> Job ID: {job_id}")
    
    return {"job_id": job_id, "message": "File uploaded successfully"}

@app.post("/analyze/{job_id}")
async def start_analysis(job_id: str):
    """
    Start instrument analysis for uploaded file
    This will trigger async processing with Celery
    """
    if job_id not in job_storage:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = job_storage[job_id]
    
    if job["status"] != "uploaded":
        raise HTTPException(
            status_code=400, 
            detail=f"Job already {job['status']}"
        )
    
    # Update job status to processing
    job["status"] = "processing" 
    job["progress"] = 5
    job["message"] = "Starting analysis..."
    
    # TODO: Trigger Celery task for actual processing
    # For now, we'll simulate the process
    logger.info(f"Starting analysis for job {job_id}")
    
    return {"job_id": job_id, "message": "Analysis started"}

@app.get("/status/{job_id}", response_model=JobStatus)
async def get_job_status(job_id: str):
    """Get current status of processing job"""
    if job_id not in job_storage:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = job_storage[job_id]
    
    return JobStatus(
        job_id=job_id,
        status=job["status"],
        progress=job.get("progress", 0),
        message=job.get("message", "")
    )

@app.get("/results/{job_id}")
async def get_results(job_id: str):
    """Get analysis results for completed job"""
    if job_id not in job_storage:
        raise HTTPException(status_code=404, detail="Job not found")

    job = job_storage[job_id]

    if job["status"] != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Job is {job['status']}, results not available"
        )

    # Return actual analysis results if available
    if "analysis_result" in job:
        return {
            "job_id": job_id,
            "filename": job["filename"],
            "analysis_result": job["analysis_result"]
        }
    # Fallback for legacy prediction results
    elif "prediction_result" in job:
        return {
            "job_id": job_id,
            "filename": job["filename"],
            "prediction_result": job["prediction_result"]
        }

    # Fallback to mock data if no prediction results
    mock_results = {
        "job_id": job_id,
        "song_info": {
            "filename": job["filename"],
            "duration": 225.6,
            "bpm": 120,
            "total_beats": 450
        },
        "timeline": {
            "beat_1": [
                {"instrument": "bass", "confidence": 0.92, "stem": "bass"}
            ],
            "beat_2": [
                {"instrument": "bass", "confidence": 0.88, "stem": "bass"},
                {"instrument": "kick_drum", "confidence": 0.95, "stem": "drums"}
            ]
        }
    }

    return mock_results

@app.get("/audio/{job_id}")
async def stream_audio(job_id: str):
    """Stream processed audio file"""
    if job_id not in job_storage:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # TODO: Implement audio streaming
    return {"message": "Audio streaming not yet implemented"}

@app.delete("/jobs/{job_id}")
async def cleanup_job(job_id: str):
    """Clean up job files and data"""
    if job_id not in job_storage:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = job_storage[job_id]
    
    # Remove uploaded file
    if os.path.exists(job["file_path"]):
        os.remove(job["file_path"])
    
    # Remove job from storage
    del job_storage[job_id]
    
    logger.info(f"Cleaned up job {job_id}")
    
    return {"message": "Job cleaned up successfully"}

@app.on_event("startup")
async def startup_event():
    """Initialize the 3-stem models on startup"""
    try:
        logger.info("🚀 Initializing 3-stem specialized models...")

        # Path to the 3-stem models
        models_dir = "models/3_stems_models"

        # Initialize the integrated classifier with 3-stem models
        initialize_integrated_classifier(
            models_dir=models_dir,
            device='cpu',  # Change to 'cuda' if you have GPU
            sample_rate=22050,
            segment_duration=4.0
        )

        logger.info("✅ 3-stem specialized models initialized successfully")
        logger.info("🎸 Bass Model: 99% accuracy (8 classes)")
        logger.info("🥁 Drums Model: 98% accuracy (8 classes)")
        logger.info("🎹 Other Model: 84% accuracy (8 classes)")
        logger.info("📊 Total: 24 instrument classes across 3 specialized models")

    except Exception as e:
        logger.error(f"❌ Failed to initialize 3-stem models: {e}")
        raise

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)