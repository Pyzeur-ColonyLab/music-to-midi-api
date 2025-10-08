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
from app.services.model_loader import load_yourmt3_model, get_model_info, get_model_instance

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
    model_instance = get_model_instance()

    return HealthResponse(
        status="healthy" if model_instance is not None else "initializing",
        model_loaded=model_instance is not None,
        device=str(model_instance.device) if model_instance else "unknown",
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
    Initialize the 3-stem models on startup

    Loads YourMT3 with specialized bass, drums, and other stem classifiers
    """
    try:
        logger.info("=" * 60)
        logger.info("🚀 Starting Music-to-MIDI API Service")
        logger.info("=" * 60)

        # Path to the 3-stem models (relative to project root)
        models_dir = "app/models/3_stems_models"

        logger.info("📦 Initializing 3-stem specialized models...")

        # Initialize the model (auto-detects CPU/GPU)
        model = load_yourmt3_model(
            models_dir=models_dir,
            device=None,  # Auto-detect
            sample_rate=22050,
            segment_duration=4.0
        )

        logger.info("=" * 60)
        logger.info("✅ Music-to-MIDI API Ready!")
        logger.info("=" * 60)
        logger.info(f"   Device: {model.device}")
        logger.info(f"   Models loaded: bass (99%), drums (98%), other (84%)")
        logger.info(f"   Total classes: 24 instrument classes")
        logger.info(f"   Sample rate: {model.sample_rate}Hz")
        logger.info("=" * 60)
        logger.info("📖 API Documentation: http://localhost:8000/docs")
        logger.info("🏥 Health Check: http://localhost:8000/health")
        logger.info("=" * 60)

    except Exception as e:
        logger.error("=" * 60)
        logger.error(f"❌ Failed to initialize models: {e}")
        logger.error("=" * 60)
        logger.error("Service will start but model endpoints will return 503 errors")
        logger.error("Check that model files exist in app/models/3_stems_models/")
        logger.error("=" * 60)


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("🛑 Shutting down Music-to-MIDI API Service")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
