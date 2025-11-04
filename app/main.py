"""
Music-to-MIDI API Service
Production API for audio-to-MIDI transcription using YourMT3
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import torch
import logging

from app.api.routes import router
from app.api.models import ModelInfo, HealthResponse
from app.services.yourmt3_service import load_yourmt3, get_yourmt3_model, get_model_info

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI application
app = FastAPI(
    title="Music-to-MIDI API",
    description="AI-powered audio-to-MIDI transcription with stem-based processing",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router, prefix="/api/v1", tags=["Music-to-MIDI"])


@app.get("/", tags=["Health"])
async def root():
    """API root endpoint"""
    return {
        "service": "Music-to-MIDI API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """
    Service health check endpoint

    Returns system status, model state, and GPU availability
    """
    model_instance = get_yourmt3_model()

    return HealthResponse(
        status="healthy" if model_instance is not None else "initializing",
        model_loaded=model_instance is not None,
        device=str(model_instance.device) if model_instance and hasattr(model_instance, 'device') else "unknown",
        gpu_available=torch.cuda.is_available(),
        timestamp=datetime.now()
    )


@app.get("/model/info", response_model=ModelInfo, tags=["Model"])
async def get_model_information():
    """
    Get information about loaded models

    Returns details about the 3-stem specialized models and their capabilities
    """
    try:
        model_info = get_model_info()
        return ModelInfo(**model_info)
    except RuntimeError as e:
        logger.error(f"Error getting model info: {e}")
        raise HTTPException(status_code=503, detail=str(e))


@app.on_event("startup")
async def startup_event():
    """
    Initialize YourMT3 model on startup

    Loads YourMT3 for audio-to-MIDI transcription

    Set SKIP_MODEL_LOADING=1 to start API without loading models (for testing)
    """
    import os

    # Check if model loading should be skipped
    if os.getenv('SKIP_MODEL_LOADING') == '1':
        logger.info("=" * 60)
        logger.info("🚀 Starting Music-to-MIDI API Service (TESTING MODE)")
        logger.info("=" * 60)
        logger.warning("⚠️  Model loading SKIPPED (SKIP_MODEL_LOADING=1)")
        logger.warning("⚠️  API endpoints will return 503 errors")
        logger.info("=" * 60)
        logger.info("📖 API Documentation: http://localhost:8000/docs")
        logger.info("=" * 60)
        return

    try:
        logger.info("=" * 60)
        logger.info("🚀 Starting Music-to-MIDI API Service")
        logger.info("=" * 60)

        logger.info("📦 Initializing YourMT3 model...")

        # Load YourMT3 model (auto-detects CPU/GPU)
        model = load_yourmt3(device=None)

        # Check bypass mode
        bypass_demucs = os.getenv('BYPASS_DEMUCS', '0') == '1'
        processing_mode = "Direct (bypassing Demucs)" if bypass_demucs else "Stem-based (Demucs + YourMT3)"

        logger.info("=" * 60)
        logger.info("✅ Music-to-MIDI API Ready!")
        logger.info("=" * 60)
        logger.info(f"   Model: YourMT3 (YPTF.MoE+Multi, 536M params)")
        logger.info(f"   Device: {model.device if hasattr(model, 'device') else 'unknown'}")
        logger.info(f"   Processing Mode: {processing_mode}")
        logger.info(f"   Capabilities: Audio-to-MIDI transcription")
        logger.info(f"   Supported: Multi-instrument, polyphonic, percussion")
        logger.info("=" * 60)
        logger.info("📖 API Documentation: http://localhost:8000/docs")
        logger.info("🏥 Health Check: http://localhost:8000/health")
        logger.info("=" * 60)

    except Exception as e:
        logger.error("=" * 60)
        logger.error(f"❌ Failed to initialize YourMT3 model: {e}")
        logger.error("=" * 60)
        logger.error("Service will start but model endpoints will return 503 errors")
        logger.error("Check that YourMT3 checkpoint exists in MT3/yourmt3_space/")
        logger.error("=" * 60)


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("🛑 Shutting down Music-to-MIDI API Service")


if __name__ == "__main__":
    import uvicorn
    import os

    # Enable auto-reload only in development (set ENABLE_RELOAD=1 for development)
    enable_reload = os.getenv('ENABLE_RELOAD', '0') == '1'

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=enable_reload,
        log_level="info"
    )
