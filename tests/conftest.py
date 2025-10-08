"""
Pytest configuration and fixtures
"""

import pytest
import os
from pathlib import Path
from fastapi.testclient import TestClient


@pytest.fixture
def test_data_dir():
    """Path to test data directory"""
    return Path(__file__).parent / "test_data"


@pytest.fixture
def test_audio_dir(test_data_dir):
    """Path to test audio directory"""
    audio_dir = test_data_dir / "audio"
    audio_dir.mkdir(exist_ok=True)
    return audio_dir


@pytest.fixture
def test_midi_dir(test_data_dir):
    """Path to test MIDI directory"""
    midi_dir = test_data_dir / "midi"
    midi_dir.mkdir(exist_ok=True)
    return midi_dir


@pytest.fixture
def sample_audio_path(test_audio_dir):
    """
    Path to sample audio file

    Note: For actual testing, place a test audio file here
    """
    return test_audio_dir / "test_sample.wav"


@pytest.fixture
def sample_midi_path(test_midi_dir):
    """
    Path to sample MIDI file

    Note: For actual testing, place a test MIDI file here
    """
    return test_midi_dir / "test_sample.mid"


@pytest.fixture
def api_client():
    """FastAPI test client"""
    from app.main import app
    return TestClient(app)


@pytest.fixture
def mock_job_id():
    """Mock job ID for testing"""
    return "test-job-12345"


@pytest.fixture(autouse=True)
def cleanup_test_files(test_data_dir):
    """Cleanup generated test files after each test"""
    yield

    # Cleanup logic runs after test
    temp_files = [
        test_data_dir / "uploads",
        test_data_dir / "stems",
    ]

    for temp_dir in temp_files:
        if temp_dir.exists():
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
