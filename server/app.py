import os
import tempfile

from fastapi import FastAPI, HTTPException, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from notate import build_score, pick_bpm, snapped_notes, to_midi, to_musicxml
from hum import notes_from_wav

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite's dev server
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/transcribe")
def transcribe(audio: UploadFile):
    # Plain def (not async) so FastAPI runs the slow pitch tracking in a worker thread
    data = audio.file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty upload")

    # The detector reads from a file path, so save the upload to a temp file first
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        f.write(data)
        path = f.name
    try:
        return notes_from_wav(path)
    except Exception:
        raise HTTPException(status_code=400, detail="Could not read the audio file")
    finally:
        os.remove(path)


# Limits on what /notate accepts, so a bad request can't make the server build a giant score
MAX_SECONDS = 600
MAX_NOTES = 5000


class Note(BaseModel):
    pitch: int = Field(ge=0, le=127)  # MIDI note number (60 = middle C)
    onset: float = Field(ge=0, le=MAX_SECONDS)  # seconds from the start of the recording
    offset: float = Field(ge=0, le=MAX_SECONDS)


class NotateRequest(BaseModel):
    notes: list[Note] = Field(max_length=MAX_NOTES)
    bpm: int | None = Field(default=None, ge=30, le=240)  # leave out to let the server guess


def notes_and_bpm(request: NotateRequest):
    """Shared by both notate endpoints: the notes as plain dicts, and the tempo to use."""
    notes = [n.model_dump() for n in request.notes]
    if not notes:
        raise HTTPException(status_code=400, detail="No notes to notate")
    return notes, request.bpm or pick_bpm(notes)


@app.post("/notate")
def notate(request: NotateRequest):
    """Notes in, sheet music out.

    Returns the MusicXML text, the tempo that was used, and the notes as the score
    shows them (snapped to the beat, in our note format) for playback.
    """
    notes, bpm = notes_and_bpm(request)
    return {
        "musicxml": to_musicxml(build_score(notes, bpm)),
        "bpm": bpm,
        "notes": snapped_notes(notes, bpm),
    }


@app.post("/notate/midi")
def notate_midi(request: NotateRequest):
    """Same input as /notate, returns a .mid file."""
    notes, bpm = notes_and_bpm(request)
    return Response(content=to_midi(build_score(notes, bpm)), media_type="audio/midi")
