"""
API Routes
FastAPI endpoint definitions
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, status
from fastapi.responses import FileResponse
from typing import Dict, Any
import os
import uuid
from datetime import datetime
import logging

from app.api.models import (
    JobStatus,
    AnalysisResult,
    PredictionRequest,
    TranscriptionResponse,
    UploadResponse,
    ErrorResponse
)
from app.services.transcription import transcribe_audio, get_transcription_stats
from app.services.yourmt3_service import get_yourmt3_model

logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory job storage (replace with Redis in production)
job_storage: Dict[str, Dict[str, Any]] = {}


@router.post("/upload", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(file: UploadFile = File(...)):
    """
    Upload audio file for processing

    Supported formats: .mp3, .wav, .flac, .m4a, .ogg

    Returns job ID for tracking the transcription job
    """
    # Validate file format
    allowed_extensions = {".mp3", ".wav", ".flac", ".m4a", ".ogg"}
    file_ext = os.path.splitext(file.filename)[1].lower()

    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '{file_ext}'. Allowed: {', '.join(allowed_extensions)}"
        )

    # Validate file size (configurable via env, default 500MB for music production)
    max_size = int(os.getenv("MAX_UPLOAD_SIZE_MB", "500")) * 1024 * 1024
    file_content = await file.read()
    file_size = len(file_content)

    if file_size > max_size:
        max_size_mb = max_size / 1024 / 1024
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size ({file_size / 1024 / 1024:.1f}MB) exceeds {max_size_mb:.0f}MB limit"
        )

    # Generate job ID and save file
    job_id = str(uuid.uuid4())
    upload_dir = "uploads"
    os.makedirs(upload_dir, exist_ok=True)

    file_path = os.path.join(upload_dir, f"{job_id}_{file.filename}")

    # Save uploaded file
    with open(file_path, "wb") as buffer:
        buffer.write(file_content)

    # Initialize job status
    job_storage[job_id] = {
        "status": "uploaded",
        "filename": file.filename,
        "file_path": file_path,
        "file_size": file_size,
        "progress": 0,
        "message": "File uploaded successfully",
        "created_at": datetime.now()
    }

    logger.info(f"File uploaded: {file.filename} ({file_size / 1024 / 1024:.1f}MB) -> Job ID: {job_id}")

    return UploadResponse(
        job_id=job_id,
        message="File uploaded successfully",
        filename=file.filename,
        file_size=file_size,
        created_at=datetime.now()
    )


@router.post("/predict/{job_id}", response_model=TranscriptionResponse)
async def predict_instruments(job_id: str, request: PredictionRequest = PredictionRequest()):
    """
    Run instrument recognition pipeline on uploaded file

    Includes beat detection, stem separation, and classification

    Returns transcription results with processing statistics
    """
    if job_id not in job_storage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job not found: {job_id}"
        )

    job = job_storage[job_id]

    if job["status"] != "uploaded":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job must be 'uploaded' status, currently '{job['status']}'"
        )

    # Verify model is loaded
    model = get_yourmt3_model()
    if model is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="YourMT3 model not loaded. Service is initializing."
        )

    # Progress callback to update job status
    def update_progress(progress: int, message: str):
        if progress >= 0:
            job["progress"] = progress
            job["message"] = message
            logger.info(f"Job {job_id}: {progress}% - {message}")
        else:
            job["status"] = "failed"
            job["message"] = message

    try:
        # Update initial status
        job["status"] = "processing"
        job["progress"] = 0
        job["message"] = "Starting analysis..."

        # Run transcription
        logger.info(f"Starting transcription for job {job_id}")
        analysis_result = transcribe_audio(
            audio_path=job["file_path"],
            job_id=job_id,
            confidence_threshold=request.confidence_threshold,
            progress_callback=update_progress
        )

        # Update job with results
        job["status"] = "completed"
        job["progress"] = 100
        job["message"] = "Analysis completed successfully"
        job["analysis_result"] = analysis_result

        # Extract statistics for response
        stats = get_transcription_stats(analysis_result)

        logger.info(
            f"Transcription completed for job {job_id}: "
            f"{stats['total_duration']:.1f}s, {stats['tempo']} BPM, "
            f"{stats['stems_processed']} stems"
        )

        return TranscriptionResponse(
            job_id=job_id,
            message="Analysis completed successfully with 3-stem models",
            duration=stats['total_duration'],
            tempo=stats['tempo'],
            total_beats=stats['total_beats'],
            stems_processed=stats['stems_processed'],
            total_segments=stats['total_segments']
        )

    except Exception as e:
        # Update job with error
        job["status"] = "failed"
        job["message"] = f"Analysis failed: {str(e)}"
        logger.error(f"Transcription failed for job {job_id}: {e}")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Transcription failed: {str(e)}"
        )


@router.get("/status/{job_id}", response_model=JobStatus)
async def get_job_status(job_id: str):
    """Get current status of processing job"""
    if job_id not in job_storage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job not found: {job_id}"
        )

    job = job_storage[job_id]

    return JobStatus(
        job_id=job_id,
        status=job["status"],
        progress=job.get("progress", 0),
        message=job.get("message", "")
    )


@router.get("/results/{job_id}", response_model=AnalysisResult)
async def get_results(job_id: str):
    """Get analysis results for completed job"""
    if job_id not in job_storage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job not found: {job_id}"
        )

    job = job_storage[job_id]

    if job["status"] != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job is '{job['status']}', results not available. Check /status/{job_id}"
        )

    if "analysis_result" not in job:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Analysis result not found in completed job"
        )

    result = job["analysis_result"]

    return AnalysisResult(
        job_id=job_id,
        song_info=result.get("song_info", {}),
        timeline=result.get("timeline", {}),
        processing_summary=result.get("processing_summary", {})
    )


@router.get("/files/{filename}")
async def download_file(filename: str):
    """
    Download generated MIDI or audio stem file

    Args:
        filename: Name of the file to download (e.g., {job_id}_bass.mid or {job_id}_bass.wav)

    Returns:
        MIDI or WAV file for download

    Raises:
        404: If file not found
        400: If file type not allowed
    """
    # Security: Only allow downloading from uploads directory
    # Prevent path traversal attacks
    safe_filename = os.path.basename(filename)

    # Search in uploads directory for files
    uploads_dir = "uploads"

    # Check all subdirectories for the file
    file_path = None
    for root, dirs, files in os.walk(uploads_dir):
        if safe_filename in files:
            file_path = os.path.join(root, safe_filename)
            break

    if not file_path or not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File not found: {filename}"
        )

    # Verify it's an allowed file type (MIDI or WAV)
    file_ext = os.path.splitext(file_path)[1].lower()
    allowed_extensions = ['.mid', '.wav']

    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Only MIDI (.mid) and WAV (.wav) files can be downloaded"
        )

    # Determine media type based on extension
    if file_ext == '.wav':
        media_type = "audio/wav"
    elif file_ext == '.mid':
        media_type = "audio/midi"
    else:
        media_type = "application/octet-stream"

    logger.info(f"Serving file: {file_path} ({media_type})")

    return FileResponse(
        path=file_path,
        media_type=media_type,
        filename=safe_filename,
        headers={
            "Content-Disposition": f"attachment; filename={safe_filename}"
        }
    )


@router.delete("/jobs/{job_id}")
async def cleanup_job(job_id: str):
    """Clean up job files and data"""
    if job_id not in job_storage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job not found: {job_id}"
        )

    job = job_storage[job_id]

    # Remove uploaded file
    if os.path.exists(job["file_path"]):
        os.remove(job["file_path"])
        logger.info(f"Deleted file: {job['file_path']}")

    # Remove MIDI directory if it exists
    job_id_clean = job_id.split('_')[0] if '_' in job_id else job_id
    midi_dir = f"uploads/{job_id_clean}/midi"
    if os.path.exists(midi_dir):
        import shutil
        shutil.rmtree(midi_dir)
        logger.info(f"Deleted MIDI directory: {midi_dir}")

    # Remove job from storage
    del job_storage[job_id]

    logger.info(f"Cleaned up job {job_id}")

    return {"message": f"Job {job_id} cleaned up successfully"}
