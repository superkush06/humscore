from basic_pitch import ICASSP_2022_MODEL_PATH
from basic_pitch.inference import Model, predict

from cleanup import cleanup_notes

# Load the model once when the server starts, not on every request
model = Model(ICASSP_2022_MODEL_PATH)


def notes_from_wav(path):
    """Run Basic Pitch, clean up humming artifacts, and return our note format."""
    _, _, note_events = predict(path, model)
    # Each event is (onset seconds, offset seconds, MIDI pitch, amplitude, pitch bends)
    notes = [
        {
            "pitch": int(pitch),
            "onset": float(onset),
            "offset": float(offset),
            "amplitude": float(amplitude),
        }
        for onset, offset, pitch, amplitude, *_ in note_events
    ]
    return [
        {"pitch": n["pitch"], "onset": round(n["onset"], 3), "offset": round(n["offset"], 3)}
        for n in cleanup_notes(notes)
    ]
