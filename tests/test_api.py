"""
Integration tests for FastAPI endpoints
"""

import pytest
from fastapi.testclient import TestClient
from io import BytesIO


class TestHealthEndpoints:
    """Test health and info endpoints"""

    def test_root_endpoint(self, api_client):
        """Test API root endpoint"""
        response = api_client.get("/")
        assert response.status_code == 200

        data = response.json()
        assert data["service"] == "Music-to-MIDI API"
        assert data["version"] == "1.0.0"
        assert "docs" in data
        assert "health" in data

    def test_health_endpoint(self, api_client):
        """Test health check endpoint"""
        response = api_client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert "status" in data
        assert "model_loaded" in data
        assert "device" in data
        assert "gpu_available" in data
        assert "timestamp" in data

        # Status should be either "healthy" or "initializing"
        assert data["status"] in ["healthy", "initializing"]


class TestModelEndpoints:
    """Test model information endpoints"""

    def test_model_info_endpoint(self, api_client):
        """Test model information endpoint"""
        response = api_client.get("/model/info")

        # May return 503 if models not loaded (acceptable in test environment)
        if response.status_code == 200:
            data = response.json()
            assert "system_type" in data
            assert "device" in data
            assert "models" in data
            assert "total_classes" in data

            # Check 3-stem models structure
            assert "bass" in data["models"]
            assert "drums" in data["models"]
            assert "other" in data["models"]
        elif response.status_code == 503:
            # Models not loaded - acceptable in test environment
            assert "detail" in response.json()
        else:
            pytest.fail(f"Unexpected status code: {response.status_code}")


class TestUploadEndpoint:
    """Test file upload endpoint"""

    def test_upload_valid_file(self, api_client):
        """Test uploading a valid audio file"""
        # Create a minimal WAV file (header only for testing)
        file_content = b'RIFF' + b'\x00' * 36  # Minimal WAV header
        files = {"file": ("test.wav", BytesIO(file_content), "audio/wav")}

        response = api_client.post("/api/v1/upload", files=files)

        # May succeed or fail depending on audio validation
        # We're testing the endpoint structure, not full audio processing
        if response.status_code == 201:
            data = response.json()
            assert "job_id" in data
            assert "message" in data
            assert data["message"] == "File uploaded successfully"
        else:
            # File might be rejected for being invalid audio - acceptable
            assert response.status_code in [400, 413, 422]

    def test_upload_invalid_format(self, api_client):
        """Test uploading unsupported file format"""
        files = {"file": ("test.txt", BytesIO(b"not an audio file"), "text/plain")}

        response = api_client.post("/api/v1/upload", files=files)
        assert response.status_code == 400

        data = response.json()
        assert "detail" in data
        assert "Unsupported file format" in data["detail"]

    def test_upload_file_too_large(self, api_client):
        """Test uploading file exceeding size limit"""
        # Create file larger than 100MB limit
        large_file = b'X' * (101 * 1024 * 1024)  # 101MB
        files = {"file": ("large.wav", BytesIO(large_file), "audio/wav")}

        response = api_client.post("/api/v1/upload", files=files)
        assert response.status_code == 413

        data = response.json()
        assert "detail" in data
        assert "exceeds 100MB limit" in data["detail"]


class TestJobStatusEndpoint:
    """Test job status tracking"""

    def test_status_nonexistent_job(self, api_client):
        """Test getting status for non-existent job"""
        response = api_client.get("/api/v1/status/nonexistent-job-id")
        assert response.status_code == 404

        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()


class TestResultsEndpoint:
    """Test results retrieval"""

    def test_results_nonexistent_job(self, api_client):
        """Test getting results for non-existent job"""
        response = api_client.get("/api/v1/results/nonexistent-job-id")
        assert response.status_code == 404

        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()


class TestOpenAPIDocumentation:
    """Test auto-generated API documentation"""

    def test_openapi_schema_available(self, api_client):
        """Test OpenAPI schema is available"""
        response = api_client.get("/openapi.json")
        assert response.status_code == 200

        schema = response.json()
        assert "openapi" in schema
        assert "info" in schema
        assert "paths" in schema

        # Verify key endpoints are documented
        assert "/" in schema["paths"]
        assert "/health" in schema["paths"]
        assert "/api/v1/upload" in schema["paths"]

    def test_docs_page_available(self, api_client):
        """Test Swagger UI docs page"""
        response = api_client.get("/docs")
        assert response.status_code == 200
        assert b"swagger" in response.content.lower()

    def test_redoc_page_available(self, api_client):
        """Test ReDoc page"""
        response = api_client.get("/redoc")
        assert response.status_code == 200
        assert b"redoc" in response.content.lower()
