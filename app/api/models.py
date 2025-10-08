"""
API Request/Response Models
Pydantic schemas for FastAPI
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any, List
from datetime import datetime


class JobStatus(BaseModel):
    """Job status response"""
    job_id: str
    status: str = Field(..., description="Job status: pending, processing, completed, failed")
    progress: Optional[int] = Field(default=0, ge=0, le=100, description="Progress percentage")
    message: Optional[str] = Field(default=None, description="Status message")

    model_config = {
        "json_schema_extra": {
            "example": {
                "job_id": "abc123def456",
                "status": "processing",
                "progress": 45,
                "message": "Processing stem: drums"
            }
        }
    }


class AnalysisResult(BaseModel):
    """Complete analysis result"""
    job_id: str
    song_info: Dict[str, Any] = Field(..., description="Song metadata (duration, tempo, beats)")
    timeline: Dict[str, Any] = Field(..., description="Beat-by-beat instrument timeline")
    processing_summary: Optional[Dict[str, Any]] = Field(default=None, description="Processing statistics")

    model_config = {
        "json_schema_extra": {
            "example": {
                "job_id": "abc123",
                "song_info": {
                    "duration": 180.5,
                    "tempo": 120,
                    "total_beats": 450
                },
                "timeline": {
                    "beat_1": [
                        {"instrument": "bass", "confidence": 0.92, "stem": "bass"}
                    ]
                },
                "processing_summary": {
                    "stems_processed": 3,
                    "total_segments": 45
                }
            }
        }
    }


class PredictionRequest(BaseModel):
    """Transcription parameters"""
    confidence_threshold: Optional[float] = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="Minimum confidence threshold for predictions"
    )
    use_stems: Optional[bool] = Field(
        default=True,
        description="Whether to use stem separation (recommended)"
    )
    output_format: Optional[str] = Field(
        default="both",
        description="Output format: midi, json, or both"
    )

    @field_validator('output_format')
    @classmethod
    def validate_output_format(cls, v: str) -> str:
        allowed = ['midi', 'json', 'both']
        if v not in allowed:
            raise ValueError(f"output_format must be one of {allowed}")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "confidence_threshold": 0.2,
                "use_stems": True,
                "output_format": "both"
            }
        }
    }


class ModelInfo(BaseModel):
    """Model information response"""
    system_type: str = Field(..., description="Model system type")
    device: str = Field(..., description="Device being used (cuda/cpu)")
    sample_rate: int = Field(..., description="Audio sample rate")
    segment_duration: float = Field(..., description="Segment duration in seconds")
    models: Dict[str, Any] = Field(..., description="Information about each stem model")
    total_classes: int = Field(..., description="Total instrument classes across all models")

    model_config = {
        "json_schema_extra": {
            "example": {
                "system_type": "3-Stem Specialized Models",
                "device": "cuda",
                "sample_rate": 22050,
                "segment_duration": 4.0,
                "models": {
                    "bass": {"classes": 8, "accuracy": 0.99},
                    "drums": {"classes": 8, "accuracy": 0.98},
                    "other": {"classes": 8, "accuracy": 0.84}
                },
                "total_classes": 24
            }
        }
    }


class TranscriptionResponse(BaseModel):
    """Transcription job response"""
    job_id: str
    message: str
    duration: Optional[float] = Field(default=None, description="Audio duration in seconds")
    tempo: Optional[float] = Field(default=None, description="Detected tempo in BPM")
    total_beats: Optional[int] = Field(default=None, description="Number of beats detected")
    stems_processed: Optional[int] = Field(default=None, description="Number of stems processed")
    total_segments: Optional[int] = Field(default=None, description="Total audio segments analyzed")

    model_config = {
        "json_schema_extra": {
            "example": {
                "job_id": "abc123",
                "message": "Analysis completed successfully",
                "duration": 180.5,
                "tempo": 120,
                "total_beats": 450,
                "stems_processed": 3,
                "total_segments": 45
            }
        }
    }


class UploadResponse(BaseModel):
    """File upload response"""
    job_id: str
    message: str
    filename: Optional[str] = Field(default=None, description="Original filename")
    file_size: Optional[int] = Field(default=None, description="File size in bytes")
    created_at: Optional[datetime] = Field(default=None, description="Upload timestamp")

    model_config = {
        "json_schema_extra": {
            "example": {
                "job_id": "abc123def456",
                "message": "File uploaded successfully",
                "filename": "song.mp3",
                "file_size": 5242880,
                "created_at": "2025-10-08T12:00:00Z"
            }
        }
    }


class HealthResponse(BaseModel):
    """Health check response"""
    status: str = Field(..., description="Service health status")
    model_loaded: bool = Field(..., description="Whether model is loaded")
    device: str = Field(..., description="Device being used")
    gpu_available: bool = Field(..., description="Whether GPU is available")
    timestamp: datetime = Field(..., description="Current server timestamp")

    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "healthy",
                "model_loaded": True,
                "device": "cuda",
                "gpu_available": True,
                "timestamp": "2025-10-08T12:00:00Z"
            }
        }
    }


class ErrorResponse(BaseModel):
    """Error response"""
    detail: str = Field(..., description="Error message")
    job_id: Optional[str] = Field(default=None, description="Associated job ID if applicable")
    timestamp: Optional[datetime] = Field(default=None, description="Error timestamp")

    model_config = {
        "json_schema_extra": {
            "example": {
                "detail": "File format not supported",
                "job_id": "abc123",
                "timestamp": "2025-10-08T12:00:00Z"
            }
        }
    }
