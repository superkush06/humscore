# HumScore

HumScore is a web app built by a Georgia Tech WebDev club team over Fall 2026 and Spring 2027. Hum a melody into your laptop or phone mic, and HumScore turns it into sheet music you can see, play back, and download as MusicXML, MIDI or PDF.

## How it works

1. **Record**: the browser records your humming as WAV and sends it to the server.
2. **Detect**: the server finds each note's pitch, start and end (Basic Pitch now, our own model in spring).
3. **Notate**: the server snaps notes to a beat grid, guesses the key, adds barlines and writes MusicXML.
4. **Use it**: the browser draws the score, plays it back and exports it.

## The note format

The server's `/transcribe` endpoint returns a JSON list of notes:

```json
[{"pitch": 60, "onset": 0.42, "offset": 0.79}]
```

`pitch` is a MIDI note number (60 is middle C). `onset` and `offset` are seconds from the start of the recording.

## Repo layout

- `web/`: React + TypeScript frontend
- `server/`: Python FastAPI server on Modal
- `model/`: PyTorch humming-transcription model

## Frontend setup

Requires Node 22.22+.

```bash
cd web
npm install
cp .env.example .env   # then set VITE_API_URL
npm run dev
```

## Contributing

`main` is protected. Every change goes through a pull request whose description says `Closes #<issue number>`, linking it to its ticket on the project board.
