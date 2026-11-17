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

## Cleanup (`cleanup.py`)
- `transcribe.py` cleans Basic Pitch events before rounding times and returning the note format. Amplitude is used internally and never added to the API response.
- A scoop is at most 150 ms, within two semitones of the following note, and at most a third of its length. It is absorbed into that note, including multi-step approaches.
- Same-pitch pieces touching, overlapping, or separated by at most 40 ms are rejoined. Longer breaks remain separate notes.
- Overlapping octave ghosts (one or two octaves away) are dropped only when they are less than half as strong as a note at least as long that covers at least 80% of them.
- An octave excursion at most 180 ms long is rejoined into a held note only when it touches the same pitch on both sides and each neighbor is at least three times longer. Sustained octave leaps remain intact.
- These are timing/pitch/amplitude heuristics for one hummed voice. Fast ornaments and same-pitch re-attacks with no clear gap can be merged; quiet genuine octave excursions can resemble tracking errors. Thresholds still need validation on representative humming recordings.
- Run the dependency-free regression tests from the repo root: `python -m unittest discover -s server -p 'test_*.py' -v`. They also check the Basic Pitch adapter with mocked model output; they do not measure transcription accuracy on audio.

## Notate step
- Snap notes to a beat grid using the tempo, guess the key, add barlines, write MusicXML with music21.

## Modal
- `modal serve` gives a temporary URL (for development).
- `modal deploy` gives a stable URL. That's the one that goes in `web/.env` as `VITE_API_URL`.
