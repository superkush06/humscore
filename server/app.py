from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite's dev server
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/transcribe")
def transcribe():
    # Fake notes in our note format: MIDI pitch, onset and offset in seconds
    return [
        {"pitch": 60, "onset": 0.0, "offset": 0.5},
        {"pitch": 62, "onset": 0.5, "offset": 1.0},
        {"pitch": 64, "onset": 1.0, "offset": 1.5},
    ]