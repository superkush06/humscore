from basic_pitch import ICASSP_2022_MODEL_PATH
from basic_pitch.inference import Model, predict

# Load the model once when the server starts, not on every request
model = Model(ICASSP_2022_MODEL_PATH)


def notes_from_wav(path):
    """Run Basic Pitch on a WAV file and return notes in our note format, sorted by onset."""
    _, _, note_events = predict(path, model)
    # Each event is (onset seconds, offset seconds, MIDI pitch, amplitude, pitch bends)
    notes = [
        {"pitch": int(pitch), "onset": round(float(onset), 3), "offset": round(float(offset), 3)}
        for onset, offset, pitch, *_ in note_events
    ]
    return sorted(notes, key=lambda n: n["onset"])
