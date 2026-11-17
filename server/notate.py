"""The Notate step: turn detected notes into a score (MusicXML and MIDI).

First version for demo day. Input is our note format:
[{"pitch": 60, "onset": 0.42, "offset": 0.79}]  (MIDI number, seconds)
"""

from music21 import clef, key, metadata, meter, midi, note, stream, tempo
from music21.musicxml.m21ToXml import GeneralObjectExporter

# The smallest rhythm we write, in beats. 0.5 = eighth notes.
GRID = 0.5
# Some hums have quicker notes that eighths can't show. Those are written in sixteenths instead,
# but only when sixteenths fit the hum clearly better: they make a messier score.
FINE_GRID = 0.25
FINE_MARGIN = 0.04  # how much better sixteenths must fit (0 = always, 0.1 = almost never)
ODD_LENGTH = 0.05  # counted against a tempo for each gap that is not a plain length


def note_gaps(notes):
    """Seconds from each note's start to the next note's start."""
    notes = sorted(notes, key=lambda n: n["onset"])
    gaps = [b["onset"] - a["onset"] for a, b in zip(notes, notes[1:])]
    return [g for g in gaps if g < 3.0]  # a long pause says nothing about the beat


def misfit(gaps, bpm, grid):
    """How badly the gaps fit whole grid steps at this tempo (0 = perfectly).

    Gaps that would be an odd length (like 3 or 5 eighths) count against it a little, so
    evenly hummed notes come out as plain notes rather than dotted ones.
    """
    step = 60 / bpm * grid  # seconds per grid step
    plain = [length / grid for length in (0.5, 1, 2, 4)]  # eighth, quarter, half, whole, in steps
    error = 0.0
    for gap in gaps:
        steps = max(1, round(gap / step))
        error += abs(gap / step - steps) / steps  # how far this gap is from a whole number of steps
        if steps not in plain:
            error += ODD_LENGTH
    return error / len(gaps)


def pick_grid(notes, bpm):
    """Eighths or sixteenths for this hum at this tempo? Sixteenths only if they fit clearly better."""
    gaps = note_gaps(notes)
    if len(gaps) < 2:
        return GRID
    if misfit(gaps, bpm, FINE_GRID) + FINE_MARGIN < misfit(gaps, bpm, GRID):
        return FINE_GRID
    return GRID


def pick_bpm(notes):
    """Guess the tempo from the gaps between note starts.

    Tries 60 to 130 BPM, in eighths and in sixteenths, and keeps the tempo where the gaps are
    closest to whole grid steps. The sixteenth reading wins only if it fits clearly better.
    """
    gaps = note_gaps(notes)
    if len(gaps) < 2:
        return 100

    tempos = range(60, 131)
    best = min(tempos, key=lambda bpm: misfit(gaps, bpm, GRID))
    best_fine = min(tempos, key=lambda bpm: misfit(gaps, bpm, FINE_GRID))
    if misfit(gaps, best_fine, FINE_GRID) + FINE_MARGIN < misfit(gaps, best, GRID):
        return best_fine
    return best


def quantize(notes, bpm, grid=GRID):
    """Snap notes to the grid and make them one voice.

    Returns a list of [start, length, pitch] with start and length counted in grid steps.

    Each note is placed by its distance from the note before it, not from the start of the
    recording. People speed up and slow down a little while humming; measured from the
    start, that drift adds up and later notes land on the wrong beats.
    """
    notes = sorted(notes, key=lambda n: n["onset"])
    step = 60 / bpm * grid  # seconds per grid step

    quantized = []
    start = 0
    for i, n in enumerate(notes):
        if i > 0:
            gap = n["onset"] - notes[i - 1]["onset"]
            start += max(1, round(gap / step))  # every note gets its own step
        length = max(1, round((n["offset"] - n["onset"]) / step))

        if quantized:
            previous = quantized[-1]
            space = (start - (previous[0] + previous[1])) * grid  # beats of silence before this note
            held = previous[1] * grid  # beats the earlier note lasts
            # Overlap: the earlier note ends where this one begins.
            # A short space after a note at least as long is a breath, not a rest: hold the note through it.
            if space < 0 or 0 < space <= 0.5 or (space == 1 and held >= 1):
                previous[1] = start - previous[0]
        quantized.append([start, length, n["pitch"]])
    return quantized


def snapped_notes(notes, bpm):
    """The notes as the score shows them, back in our note format, so playback matches the score."""
    grid = pick_grid(notes, bpm)
    step = 60 / bpm * grid
    return [
        {"pitch": pitch, "onset": round(start * step, 3), "offset": round((start + length) * step, 3)}
        for start, length, pitch in quantize(notes, bpm, grid)
    ]


def build_score(notes, bpm):
    """Build a music21 score in 4/4 from notes in our note format."""
    if not notes:
        raise ValueError("No notes to notate")

    grid = pick_grid(notes, bpm)
    part = stream.Part()
    position = 0  # where the next note or rest goes, in grid steps
    for start, length, pitch in quantize(notes, bpm, grid):
        if start > position:
            part.append(note.Rest(quarterLength=(start - position) * grid))
        new_note = note.Note(pitch, quarterLength=length * grid)
        # A note made from a MIDI number is marked "natural" on white keys, which would print
        # a natural sign on nearly every note. Clear it; music21 adds back the ones really needed.
        if new_note.pitch.accidental is not None and new_note.pitch.accidental.alter == 0:
            new_note.pitch.accidental = None
        part.append(new_note)
        position = start + length

    # Finish the last bar with a rest so every bar has 4 beats
    beats = position * grid
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
