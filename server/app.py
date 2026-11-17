import os
import tempfile

from fastapi import FastAPI, HTTPException, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from notate import build_score, pick_bpm, to_midi, to_musicxml
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


class Note(BaseModel):
    pitch: int  # MIDI note number (60 = middle C)
    onset: float  # seconds from the start of the recording
    offset: float


class NotateRequest(BaseModel):
    notes: list[Note]
    bpm: int | None = Field(default=None, ge=30, le=240)  # leave out to let the server guess


def score_from(request: NotateRequest):
    """Shared by both notate endpoints: returns (score, bpm)."""
    notes = [n.model_dump() for n in request.notes]
    if not notes:
        raise HTTPException(status_code=400, detail="No notes to notate")
    bpm = request.bpm or pick_bpm(notes)
    return build_score(notes, bpm), bpm


@app.post("/notate")
def notate(request: NotateRequest):
    """Notes in, sheet music out: returns MusicXML text and the tempo that was used."""
    score, bpm = score_from(request)
    return {"musicxml": to_musicxml(score), "bpm": bpm}


@app.post("/notate/midi")
def notate_midi(request: NotateRequest):
    """Same input as /notate, returns a .mid file."""
    score, _ = score_from(request)
    return Response(content=to_midi(score), media_type="audio/midi")
