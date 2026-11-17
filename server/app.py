import os
import tempfile

from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from transcribe import notes_from_wav

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite's dev server
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/transcribe")
def transcribe(audio: UploadFile):
    # Plain def (not async) so FastAPI runs the slow Basic Pitch call in a worker thread
    data = audio.file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty upload")

    # Basic Pitch reads from a file path, so save the upload to a temp file first
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        f.write(data)
        path = f.name
    try:
        return notes_from_wav(path)
    except Exception:
        raise HTTPException(status_code=400, detail="Could not read the audio file")
    finally:
        os.remove(path)
