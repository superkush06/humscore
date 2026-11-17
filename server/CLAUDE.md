# server/ (API)

Owners: Anna (the API on Modal), Valerie (the Notate step: rhythm, key, MusicXML).

## Stack
- Python 3.11. Basic Pitch supports up to 3.11 and music21 needs 3.11 or newer, so don't change it.
- FastAPI, deployed on Modal with `@modal.asgi_app()`.
- Supabase (login, Postgres, file storage) gets added later.

## /transcribe contract
- Receives a WAV upload from the browser (recorded at the browser's own sample rate).
- Returns a JSON list of notes: `[{"pitch": 60, "onset": 0.42, "offset": 0.79}]`
  - `pitch`: MIDI note number (60 = middle C)
  - `onset`, `offset`: seconds from the start of the recording
- Don't change this format without the whole team agreeing.

## FastAPI notes
- CORS must allow `http://localhost:5173` (Vite's dev server).
- File uploads need the `python-multipart` package.

## Basic Pitch (Detect step, fall)
- Package `basic-pitch` (Apache 2.0).
- `predict()` writes MIDI at 120 BPM unless you pass `midi_tempo`.
- Defaults: `onset_threshold` 0.5, `frame_threshold` 0.3, `minimum_note_length` 127.7 ms.
- It resamples audio to 22,050 Hz (our model uses 44,100 Hz), which is why the browser never downsamples.
- In spring it is swapped for our PyTorch model (`model/`). Both return the same note format.

## Notate step (`notate.py`, first version from demo day)
- Snaps notes to a beat grid using the tempo, guesses the key, adds barlines, writes MusicXML and MIDI with music21.
- `GRID` at the top of `notate.py` is the smallest rhythm written (0.5 = eighth notes).
- `POST /notate`: body `{"notes": [...], "bpm": 100}` (`bpm` optional; the server guesses a tempo from 70 to 140 if it's left out). Returns `{"musicxml": "...", "bpm": 100, "notes": [...]}`. The returned `notes` are the notes as the score shows them, in the note format, used for playback.
- `POST /notate/midi`: same body, returns a `.mid` file.
- Known limits: always 4/4, one voice, no triplets, and the key guess is unreliable on very short melodies.

## Run locally
- `.venv/bin/uvicorn app:app --port 8000` (see the README for first-time setup).

## Modal
- `modal serve` gives a temporary URL (for development).
- `modal deploy` gives a stable URL. That's the one that goes in `web/.env` as `VITE_API_URL`.
