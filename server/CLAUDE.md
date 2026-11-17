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
  - `hum.py`: 18% wrong on average.
  - CREPE (a neural pitch tracker) in place of pYIN: 18%. Not used: it needs PyTorch and is about 3 times slower.
- Most of what is left is singers being off-key, not tracking mistakes.
- Held-out check: 100 more HumTrans test clips that were never used for tuning gave 15.6% wrong (female singers 9%, male 22%), rhythm right 82%, tempo right 87 of 100.
- Final check: 200 more test clips, touched only once, gave 17.8% wrong (middle clip 13%), rhythm right 79%, tempo right 173 of 200. Across all 340 clips, 8 of the 10 singers are between 6% and 19% wrong. Two male singers (M02, M03) are at 24% to 49% because they sing a narrower range than the written tune; the detector reports what they sang.
- What the errors are (tuning set): female singers 2.8% wrong pitch, 1.2% extra notes, 7.2% missed notes; male singers 14.5% wrong pitch, 3.4% extra, 7.9% missed. Missed notes are mostly a step from a neighbor or the same note hummed twice with no break.
- What the browser sends makes no real difference (40 clips, 18.2% on the original files): Opus 128k 18.2%, Opus 32k 19.1%, AAC 18.2%, 1% volume 18.3%, clipped 19.4%, 16 kHz 18.1%, 8 kHz 17.8%.
- Tried and rejected, because none beat the current code on both the tuning and validation sets: a tuning shift that follows the singer's drift, folding octave jumps back, changing any single threshold in `hum.py`, and extra note boundaries from re-attacks (onset strength). For rhythm: a beat length that adapts during the hum, other tempo ranges, and a sixteenth-note grid.
- Short hums (the first 5 to 8 notes of 122 clips, cut at a breath): notes are 1 to 3 points worse than the same notes heard with the whole clip, because there is less to judge the tuning and scale from. The tempo guess is the weak part: right on 69% of short hums against 87% of full clips, and rhythm drops from 91% to 58% when it is wrong. Eleven variants of `pick_bpm` (penalty size, which lengths count as plain, note lengths, tempo range) did not fix it; a few notes fit several tempos equally well. The tempo box on the page is the fix.
- Also rejected: stretching the singer's intervals before rounding (for singers who squeeze the tune into a narrow range). It made both sets worse or left them unchanged.
- YouTube spot check (5 solo-voice clips of known tunes, sung with words): 30% wrong, mostly the same note sung twice in a row heard as one.
- Vocadito (40 solo singing recordings with hand-annotated notes): 70% of notes found within 100 ms and a semitone, where a second human annotator scores 81%. It misses very short ornament notes sung without a break. Singing with words is harder than humming and is not what this is tuned for.
- Noise: the same clips with room noise, a click and a breath added before and after the humming gave 40 junk notes across 26 clips. `drop_noise` in `hum.py` removes very quiet notes, and notes the tracker is unsure about that are also quiet or far from the melody. After it: 0 junk notes, and 20% wrong on the noisy clips.
- Real rooms: two laptop recordings of a quiet room (fan rumble and electrical hum, nobody humming) used to produce 17 and 29 junk notes. Sound below 70 Hz is now filtered out first, and a note barely louder than the quietest moments of the recording with low tracker confidence is dropped. Both recordings now give no notes. With that room noise mixed under the 40 clips: 19% wrong when the hum is 25 dB louder than the room, 22% at 12 dB, no junk notes.
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
