"""Conservative cleanup of note events from a single hummed melody."""

MAX_GAP = 0.04  # seconds: bridge tracker dropouts, not breaths
MAX_SCOOP = 0.15  # seconds
MAX_OCTAVE_BLIP = 0.18  # seconds; Basic Pitch's default minimum note is about 128 ms
LONGER_RATIO = 3
OCTAVES = (12, 24)
TIME_EPSILON = 1e-9  # tolerate floating-point subtraction at threshold boundaries


def cleanup_notes(notes):
    """Merge scoops and split notes, and remove likely octave ghosts.

    Input notes may include Basic Pitch's amplitude (0 to 1), used only to reject
    overlapping octave harmonics. The result uses the public note format, without
    amplitude. Input dictionaries are never changed; times stay in seconds.
    """
    notes = sorted((dict(n) for n in notes), key=lambda n: (n["onset"], n["pitch"]))

    # An octave harmonic overlaps a stronger, longer note. A sequential octave
    # jump has no such overlap, so it survives this pass regardless of loudness.
    kept = []
    for note in notes:
        ghost = False
        if "amplitude" in note:
            for other in notes:
                if other["onset"] >= note["offset"]:
                    break
                overlap = min(note["offset"], other["offset"]) - max(note["onset"], other["onset"])
                if (
                    abs(note["pitch"] - other["pitch"]) in OCTAVES
                    and "amplitude" in other
                    and note["amplitude"] < other["amplitude"] * 0.5
                    and duration(other) + TIME_EPSILON >= duration(note)
                    and overlap + TIME_EPSILON >= duration(note) * 0.8
                ):
                    ghost = True
                    break
        if not ghost:
            kept.append(note)
    notes = _join_same_pitch(kept)

    # A brief octave error inside a held note belongs to that note. Require the
    # same pitch on both sides, so a real octave leap is not folded down.
    for i in range(1, len(notes) - 1):
        before, note, after = notes[i - 1 : i + 2]
        if (
            duration(note) <= MAX_OCTAVE_BLIP + TIME_EPSILON
            and before["pitch"] == after["pitch"]
            and abs(note["pitch"] - before["pitch"]) in OCTAVES
            and abs(note["onset"] - before["offset"]) <= MAX_GAP + TIME_EPSILON
            and abs(after["onset"] - note["offset"]) <= MAX_GAP + TIME_EPSILON
            and min(duration(before), duration(after)) + TIME_EPSILON >= LONGER_RATIO * duration(note)
        ):
            note["pitch"] = before["pitch"]

    # Absorb a short approach into the longer note it leads to. Work backwards
    # so a scoop detected as several small steps is absorbed in one pass.
    for i in range(len(notes) - 2, -1, -1):
        scoop, target = notes[i : i + 2]
        if (
            duration(scoop) <= MAX_SCOOP + TIME_EPSILON
            and 0 < abs(scoop["pitch"] - target["pitch"]) <= 2
            and abs(target["onset"] - scoop["offset"]) <= MAX_GAP + TIME_EPSILON
            and duration(target) + TIME_EPSILON >= LONGER_RATIO * duration(scoop)
        ):
            target["onset"] = min(scoop["onset"], target["onset"])
            notes.pop(i)

    return [
        {key: n[key] for key in ("pitch", "onset", "offset")}
        for n in _join_same_pitch(notes)
    ]


def _join_same_pitch(notes):
    joined = []
    for note in notes:
        if (
            joined
            and note["pitch"] == joined[-1]["pitch"]
            and note["onset"] - joined[-1]["offset"] <= MAX_GAP + TIME_EPSILON
        ):
            joined[-1]["offset"] = max(joined[-1]["offset"], note["offset"])
        else:
            joined.append(note)

    return joined


def duration(note):
    return note["offset"] - note["onset"]
