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

## Detect step (`hum.py`)
- `/transcribe` uses `hum.py`, not Basic Pitch. It tracks the single pitch of the voice with pYIN (from `librosa`), cuts the pitch curve into notes, removes how sharp or flat the singer is overall, and nudges off-scale notes onto the melody's scale. The steps are listed at the top of the file.
- Why: Basic Pitch is built for instruments playing several notes at once. On humming it chops one note into pieces and reports slides as extra notes.
- Backtest on 40 HumTrans test clips (10 singers, 4 clips each), counting the edits needed to turn the detected pitches into the true ones, per true note, after the best constant key shift (people hum in their own key):
  - Basic Pitch: 61% of notes wrong, 0 of 40 clips under 20% wrong.
  - `hum.py`: 21% wrong on average, 16% for the middle clip, 26 of 40 clips under 20% wrong. Female singers 11%, male singers 30%.
  - CREPE (a neural pitch tracker) in place of pYIN: 18%. Not used: it needs PyTorch and is about 3 times slower.
- Most of what is left is singers being off-key, not tracking mistakes.
- The settings at the top of `hum.py` were tuned on those clips. Results barely move when they change.
- About 1 to 2 seconds for a 10-second recording.

## Basic Pitch (`transcribe.py`, not used by the app right now)
- Kept for comparison and for instrument audio. Package `basic-pitch` (Apache 2.0).
- `predict()` writes MIDI at 120 BPM unless you pass `midi_tempo`.
- Defaults: `onset_threshold` 0.5, `frame_threshold` 0.3, `minimum_note_length` 127.7 ms.
- It resamples audio to 22,050 Hz (our model uses 44,100 Hz), which is why the browser never downsamples.
- In spring the Detect step is swapped for our PyTorch model (`model/`). It must return the same note format.

## Notate step (`notate.py`, first version from demo day)
- Snaps notes to a beat grid using the tempo, guesses the key, adds barlines, writes MusicXML and MIDI with music21.
- `GRID` at the top of `notate.py` is the smallest rhythm written (0.5 = eighth notes).
- Each note is placed by its distance from the note before it, not from the start of the recording, so small speed-ups and slow-downs don't add up. On the same 40 clips: rhythm right for 79% of note pairs (75% with a fixed grid), tempo right on 37 of 40 (30 before).
- `POST /notate`: body `{"notes": [...], "bpm": 100}` (`bpm` optional; the server guesses a tempo from 60 to 130 if it's left out). Returns `{"musicxml": "...", "bpm": 100, "notes": [...]}`. The returned `notes` are the notes as the score shows them, in the note format, used for playback.
- `POST /notate/midi`: same body, returns a `.mid` file.
- Known limits: always 4/4, one voice, no triplets, and the key guess is unreliable on very short melodies.

## Run locally
- `.venv/bin/uvicorn app:app --port 8000` (see the README for first-time setup).

## Modal
- `modal serve` gives a temporary URL (for development).
- `modal deploy` gives a stable URL. That's the one that goes in `web/.env` as `VITE_API_URL`.
