"""The Notate step: turn detected notes into a score (MusicXML and MIDI).

First version for demo day. Input is our note format:
[{"pitch": 60, "onset": 0.42, "offset": 0.79}]  (MIDI number, seconds)
"""

from music21 import clef, key, metadata, meter, midi, note, stream, tempo
from music21.musicxml.m21ToXml import GeneralObjectExporter

# The smallest rhythm we write, in beats. 0.5 = eighth notes, 0.25 = sixteenth notes.
# Smaller follows the humming more closely but makes a messier score.
GRID = 0.5


def pick_bpm(notes):
    """Guess the tempo: try 70 to 140 BPM and keep the one whose grid fits the note starts best."""
    if len(notes) < 3:
        return 100
    first = min(n["onset"] for n in notes)
    starts = [n["onset"] - first for n in notes]

    best_bpm, best_error = 100, None
    for bpm in range(70, 141, 2):
        step = 60 / bpm * GRID  # seconds per grid step
        # How far each note start is from its nearest grid line, as a fraction of a step
        error = sum(abs(s / step - round(s / step)) for s in starts) / len(starts)
        if best_error is None or error < best_error:
            best_bpm, best_error = bpm, error
    return best_bpm


def quantize(notes, bpm):
    """Snap notes to the grid and make them one voice.

    Returns a list of [start, length, pitch] with start and length counted in grid steps.
    """
    notes = sorted(notes, key=lambda n: n["onset"])
    first = notes[0]["onset"]  # drop the silence before the first note
    step = 60 / bpm * GRID  # seconds per grid step

    # If two notes land on the same step, keep the longer one
    by_start = {}
    for n in notes:
        start = round((n["onset"] - first) / step)
        end = max(start + 1, round((n["offset"] - first) / step))  # at least one step long
        length = end - start
        if start not in by_start or length > by_start[start][0]:
            by_start[start] = (length, n["pitch"])

    quantized = []
    for start in sorted(by_start):
        length, pitch = by_start[start]
        if quantized:
            previous = quantized[-1]
            gap = start - (previous[0] + previous[1])
            # Overlap: the earlier note ends where this one begins.
            # One-step gap: usually a breath, so hold the earlier note instead of writing a tiny rest.
            if gap < 0 or gap == 1:
                previous[1] = start - previous[0]
        quantized.append([start, length, pitch])
    return quantized


def snapped_notes(notes, bpm):
    """The notes as the score shows them, back in our note format, so playback matches the score."""
    step = 60 / bpm * GRID
    return [
        {"pitch": pitch, "onset": round(start * step, 3), "offset": round((start + length) * step, 3)}
        for start, length, pitch in quantize(notes, bpm)
    ]


def build_score(notes, bpm):
    """Build a music21 score in 4/4 from notes in our note format."""
    if not notes:
        raise ValueError("No notes to notate")

    part = stream.Part()
    position = 0  # where the next note or rest goes, in grid steps
    for start, length, pitch in quantize(notes, bpm):
        if start > position:
            part.append(note.Rest(quarterLength=(start - position) * GRID))
        new_note = note.Note(pitch, quarterLength=length * GRID)
        # A note made from a MIDI number is marked "natural" on white keys, which would print
        # a natural sign on nearly every note. Clear it; music21 adds back the ones really needed.
        if new_note.pitch.accidental is not None and new_note.pitch.accidental.alter == 0:
            new_note.pitch.accidental = None
        part.append(new_note)
        position = start + length

    # Finish the last bar with a rest so every bar has 4 beats
    beats = position * GRID
    if beats % 4 != 0:
        part.append(note.Rest(quarterLength=4 - beats % 4))

    # Guess the key from the notes, and spell black keys as flats in flat keys (B-flat, not A-sharp)
    guessed_key = part.analyze("key")
    if guessed_key.sharps < 0:
        for n in part.notes:
            if n.pitch.accidental is not None and n.pitch.accidental.alter > 0:
                n.pitch = n.pitch.getEnharmonic()

    part.insert(0, clef.bestClef(part))  # bass clef for low voices
    part.insert(0, key.KeySignature(guessed_key.sharps))
    part.insert(0, meter.TimeSignature("4/4"))
    part.insert(0, tempo.MetronomeMark(number=bpm))

    score = stream.Score()
    # movementName prints once as the title; composer replaces music21's default "Music21" credit
    score.insert(0, metadata.Metadata(movementName="Your hum", composer="HumScore"))
    score.insert(0, part)
    return score


def to_musicxml(score):
    """MusicXML text. music21 adds the barlines and ties while exporting."""
    return GeneralObjectExporter(score).parse().decode("utf-8")


def to_midi(score):
    """The bytes of a .mid file."""
    return midi.translate.streamToMidiFile(score).writestr()
