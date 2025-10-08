# Music-to-MIDI API - Usage Examples

Complete examples for using the Music-to-MIDI API.

## Quick Start

### 1. Upload Audio File

```bash
curl -X POST "http://localhost:8000/api/v1/upload" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@song.mp3"
```

**Response**:
```json
{
  "job_id": "abc123def456",
  "message": "File uploaded successfully",
  "filename": "song.mp3",
  "file_size": 5242880,
  "created_at": "2025-10-08T12:00:00Z"
}
```

### 2. Start Transcription

```bash
curl -X POST "http://localhost:8000/api/v1/predict/abc123def456" \
  -H "Content-Type: application/json" \
  -d '{
    "confidence_threshold": 0.2,
    "use_stems": true
  }'
```

**Response**:
```json
{
  "job_id": "abc123def456",
  "message": "Analysis completed successfully",
  "duration": 180.5,
  "tempo": 120,
  "total_beats": 450,
  "stems_processed": 3,
  "total_segments": 45
}
```

### 3. Check Status

```bash
curl "http://localhost:8000/api/v1/status/abc123def456"
```

**Response**:
```json
{
  "job_id": "abc123def456",
  "status": "completed",
  "progress": 100,
  "message": "Analysis completed successfully"
}
```

### 4. Get Results

```bash
curl "http://localhost:8000/api/v1/results/abc123def456"
```

**Response**:
```json
{
  "job_id": "abc123def456",
  "song_info": {
    "duration": 180.5,
    "tempo": 120,
    "total_beats": 450,
    "beats": [0.0, 0.5, 1.0, ...]
  },
  "timeline": {
    "beat_1": [
      {"instrument": "Electric Bass", "confidence": 0.92, "stem": "bass", "program": 33}
    ],
    "beat_2": [
      {"instrument": "Electric Bass", "confidence": 0.88, "stem": "bass", "program": 33},
      {"instrument": "Synth Drum", "confidence": 0.95, "stem": "drums", "program": 118}
    ]
  },
  "processing_summary": {
    "stems_processed": 3,
    "total_segments": 45,
    "unique_instruments": ["Electric Bass", "Synth Drum", "Acoustic Grand Piano"]
  }
}
```

---

## Python Client Examples

### Basic Usage

```python
import requests

# API base URL
BASE_URL = "http://localhost:8000"

# 1. Upload audio file
with open("song.mp3", "rb") as f:
    response = requests.post(
        f"{BASE_URL}/api/v1/upload",
        files={"file": f}
    )
    job_id = response.json()["job_id"]
    print(f"Job ID: {job_id}")

# 2. Start transcription
response = requests.post(
    f"{BASE_URL}/api/v1/predict/{job_id}",
    json={
        "confidence_threshold": 0.2,
        "use_stems": True
    }
)
print(response.json())

# 3. Get results
response = requests.get(f"{BASE_URL}/api/v1/results/{job_id}")
results = response.json()
print(f"Duration: {results['song_info']['duration']:.1f}s")
print(f"Tempo: {results['song_info']['tempo']} BPM")
```

### Advanced: Poll Until Complete

```python
import requests
import time

def wait_for_completion(job_id, timeout=300):
    """Poll job status until completion"""
    start_time = time.time()

    while time.time() - start_time < timeout:
        response = requests.get(f"{BASE_URL}/api/v1/status/{job_id}")
        status = response.json()

        print(f"Progress: {status['progress']}% - {status['message']}")

        if status['status'] == 'completed':
            return True
        elif status['status'] == 'failed':
            raise Exception(f"Job failed: {status['message']}")

        time.sleep(2)  # Poll every 2 seconds

    raise TimeoutError("Job did not complete in time")

# Upload and process
with open("song.mp3", "rb") as f:
    response = requests.post(f"{BASE_URL}/api/v1/upload", files={"file": f})
    job_id = response.json()["job_id"]

# Start transcription
requests.post(f"{BASE_URL}/api/v1/predict/{job_id}")

# Wait for completion
wait_for_completion(job_id)

# Get results
response = requests.get(f"{BASE_URL}/api/v1/results/{job_id}")
print(response.json())
```

### Cleanup

```python
# Delete job when done
response = requests.delete(f"{BASE_URL}/api/v1/jobs/{job_id}")
print(response.json())  # {"message": "Job cleaned up successfully"}
```

---

## JavaScript/TypeScript Examples

### Using Fetch API

```javascript
const BASE_URL = 'http://localhost:8000';

// Upload and process audio
async function transcribeAudio(audioFile) {
  // 1. Upload
  const formData = new FormData();
  formData.append('file', audioFile);

  const uploadResponse = await fetch(`${BASE_URL}/api/v1/upload`, {
    method: 'POST',
    body: formData
  });

  const { job_id } = await uploadResponse.json();
  console.log('Job ID:', job_id);

  // 2. Start transcription
  await fetch(`${BASE_URL}/api/v1/predict/${job_id}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      confidence_threshold: 0.2,
      use_stems: true
    })
  });

  // 3. Poll for completion
  let completed = false;
  while (!completed) {
    const statusResponse = await fetch(`${BASE_URL}/api/v1/status/${job_id}`);
    const status = await statusResponse.json();

    console.log(`Progress: ${status.progress}%`);

    if (status.status === 'completed') {
      completed = true;
    } else if (status.status === 'failed') {
      throw new Error(status.message);
    } else {
      await new Promise(resolve => setTimeout(resolve, 2000));
    }
  }

  // 4. Get results
  const resultsResponse = await fetch(`${BASE_URL}/api/v1/results/${job_id}`);
  return await resultsResponse.json();
}

// Usage
const fileInput = document.querySelector('#audio-file');
const results = await transcribeAudio(fileInput.files[0]);
console.log('Results:', results);
```

---

## Health Check & Model Info

### Check API Health

```bash
curl "http://localhost:8000/health"
```

```json
{
  "status": "healthy",
  "model_loaded": true,
  "device": "cuda",
  "gpu_available": true,
  "timestamp": "2025-10-08T12:00:00Z"
}
```

### Get Model Information

```bash
curl "http://localhost:8000/model/info"
```

```json
{
  "system_type": "3-Stem Specialized Models",
  "device": "cuda",
  "sample_rate": 22050,
  "segment_duration": 4.0,
  "models": {
    "bass": {
      "classes": 8,
      "accuracy": 0.99,
      "description": "Bass-specific instrument classifier"
    },
    "drums": {
      "classes": 8,
      "accuracy": 0.98,
      "description": "Drums-specific instrument classifier"
    },
    "other": {
      "classes": 8,
      "accuracy": 0.84,
      "description": "Other instruments classifier"
    }
  },
  "total_classes": 24
}
```

---

## Error Handling

### Handle Upload Errors

```python
try:
    with open("song.mp3", "rb") as f:
        response = requests.post(f"{BASE_URL}/api/v1/upload", files={"file": f})
        response.raise_for_status()
        job_id = response.json()["job_id"]
except requests.HTTPError as e:
    if e.response.status_code == 400:
        print("Invalid file format")
    elif e.response.status_code == 413:
        print("File too large (max 100MB)")
    else:
        print(f"Upload failed: {e}")
```

### Handle Processing Errors

```python
response = requests.post(f"{BASE_URL}/api/v1/predict/{job_id}")
if response.status_code == 404:
    print("Job not found")
elif response.status_code == 400:
    print("Job not in correct state for prediction")
elif response.status_code == 503:
    print("Model not loaded")
else:
    print(response.json())
```

---

## Common Workflows

### Batch Processing

```python
import os
import requests
from pathlib import Path

def batch_transcribe(audio_dir, output_dir):
    """Process all audio files in directory"""
    audio_files = list(Path(audio_dir).glob("*.mp3")) + \
                  list(Path(audio_dir).glob("*.wav"))

    results = {}

    for audio_file in audio_files:
        print(f"Processing: {audio_file.name}")

        # Upload
        with open(audio_file, "rb") as f:
            response = requests.post(f"{BASE_URL}/api/v1/upload", files={"file": f})
            job_id = response.json()["job_id"]

        # Process
        requests.post(f"{BASE_URL}/api/v1/predict/{job_id}")
        wait_for_completion(job_id)

        # Get results
        response = requests.get(f"{BASE_URL}/api/v1/results/{job_id}")
        results[audio_file.name] = response.json()

        # Cleanup
        requests.delete(f"{BASE_URL}/api/v1/jobs/{job_id}")

    return results

# Process all files
results = batch_transcribe("./audio", "./output")
print(f"Processed {len(results)} files")
```

---

## API Documentation

- **Interactive Docs**: http://localhost:8000/docs (Swagger UI)
- **Alternative Docs**: http://localhost:8000/redoc (ReDoc)
- **OpenAPI Schema**: http://localhost:8000/openapi.json
