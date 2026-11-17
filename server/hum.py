"""The Detect step for humming: a WAV file in, notes out (our note format).

A hum is one note at a time, so instead of Basic Pitch (built for instruments playing many
notes at once) this tracks the single pitch of the voice with pYIN, then cuts that pitch
curve into notes. On 40 HumTrans test clips this got about 20% of notes wrong, against
about 60% for Basic Pitch. See server/CLAUDE.md for the numbers.

Steps:
1. Track the pitch of the voice, frame by frame (pYIN, from librosa).
2. Cut the pitch curve into pieces: where the voice stops, where the pitch jumps, and where
   the loudness dips (the same note hummed twice).
3. Merge slides between notes into the note they lead to, and drop blips.
4. Work out how sharp or flat the singer is overall, remove that, and round to notes.
5. Nudge notes that fall outside the melody's scale onto the nearest scale note.
"""

import librosa
import numpy as np
from scipy.ndimage import median_filter

SAMPLE_RATE = 22050
HOP = 256  # samples between pitch readings (about 12 ms)
FRAME_SECONDS = HOP / SAMPLE_RATE
LOWEST_HZ, HIGHEST_HZ = 65, 1047  # C2 to C6, wider than any human hum

# Tuned on HumTrans clips. Results change very little when these move, which is a good sign.
BRIDGE_FRAMES = 2  # a gap in the voice this short is a glitch, not a break between notes
SMOOTH_FRAMES = 5  # smooths out wobble in the pitch curve
JUMP_SEMITONES = 0.85  # this far from the current note...
JUMP_FRAMES = 5  # ...for this many frames in a row starts a new note
DIP = 0.45  # loudness falling below this fraction of its surroundings is a new note
DIP_SECONDS = 0.12  # how far each side to look for "its surroundings"
SLIDE_SECONDS = 0.14  # a piece shorter than this next to a longer one is a slide, not a note
SLIDE_SEMITONES = 2.5  # ...if it is within this distance of that neighbor
# Sliding up into the first note after a breath, or falling off the last one, can take much longer.
EDGE_SLIDE_SECONDS = 0.4  # a piece at the start or end of a breath, shorter than this...
EDGE_SLIDE_RATIO = 1.5  # ...and touching a neighbor at least this many times longer, is a slide
MIN_SECONDS = 0.11  # anything still shorter than this is dropped
# Breaths, clicks and room noise can look like very quiet, uncertain notes far from the melody.
QUIET = 0.2  # a note this much quieter than the typical note is noise
UNSURE = 0.1  # pitch tracker confidence (0 to 1) below this is "unsure"...
UNSURE_QUIET = 0.5  # ...and an unsure note that is also this quiet is noise
STRAY_SEMITONES = 15  # an unsure note this far from the middle of the melody is noise
SCALE_REACH = 1.0  # how far (semitones) a note may be moved to land on the scale
MAJOR_SCALE = [0, 2, 4, 5, 7, 9, 11]


def notes_from_wav(path):
    """Read a WAV file and return the hummed notes in our note format, sorted by onset."""
    audio, _ = librosa.load(path, sr=SAMPLE_RATE, mono=True)
    hz, voiced, confidence = librosa.pyin(
        audio, fmin=LOWEST_HZ, fmax=HIGHEST_HZ, sr=SAMPLE_RATE, frame_length=2048, hop_length=HOP
    )
    loudness = librosa.feature.rms(y=audio, frame_length=1024, hop_length=HOP)[0][: len(hz)]
    notes = notes_from_track(librosa.hz_to_midi(hz), voiced, loudness, FRAME_SECONDS, confidence)
    return [{"pitch": n["pitch"], "onset": n["onset"], "offset": n["offset"]} for n in notes]


def notes_from_track(pitch, voiced, loudness, frame_seconds, confidence=None):
    """Turn a pitch curve into notes.

    pitch: MIDI pitch per frame, with decimals (60.4 = a bit sharp of middle C). NaN where unknown.
    voiced: True for frames where the voice is sounding.
    loudness: loudness per frame.
    confidence: how sure the pitch tracker is, 0 to 1 per frame (optional; used to drop noise).
    Returns a list of dicts with onset, offset (seconds), pitch (whole MIDI number) and
    exact (the pitch before rounding).
    """
    pitch = np.array(pitch, dtype=float)
    voiced = np.array(voiced, dtype=bool) & ~np.isnan(pitch)
    bridge_short_gaps(pitch, voiced)
    loudness = np.convolve(loudness, np.ones(3) / 3, mode="same")
    dip_frames = max(1, int(DIP_SECONDS / frame_seconds))

    pieces = []
    for start, end in voiced_runs(voiced):
        smooth = median_filter(pitch[start:end], size=SMOOTH_FRAMES, mode="nearest")
        cuts = {0, end - start}
        cuts.update(pitch_jumps(smooth))
        cuts.update(k - start for k in loudness_dips(loudness, start, end, dip_frames))
        cuts = sorted(cuts)
        for a, b in zip(cuts, cuts[1:]):
            pieces.append({"start": start + a, "end": start + b, "exact": middle_pitch(smooth[a:b])})

    absorb_slides_and_drop_blips(pieces, frame_seconds)
    pieces = drop_noise(pieces, loudness, confidence)
    if not pieces:
        return []

    remove_tuning_offset(pieces)
    for p in pieces:
        p["pitch"] = int(round(p["exact"]))
    join_same_pitch(pieces, loudness, dip_frames)
    snap_to_scale(pieces)
    join_same_pitch(pieces, loudness, dip_frames)  # snapping can make two touching pieces the same note

    return [
        {
            "onset": round(p["start"] * frame_seconds, 3),
            "offset": round(p["end"] * frame_seconds, 3),
            "pitch": p["pitch"],
            "exact": p["exact"],
        }
        for p in pieces
    ]


def voiced_runs(voiced):
    """(start, end) frame ranges where the voice sounds without a break."""
    runs, start = [], None
    for i, on in enumerate(voiced):
        if on and start is None:
            start = i
        elif not on and start is not None:
            runs.append((start, i))
            start = None
    if start is not None:
        runs.append((start, len(voiced)))
    return runs


def bridge_short_gaps(pitch, voiced):
    """Fill very short breaks in the voice by drawing a straight line across them. Edits in place."""
    runs = voiced_runs(voiced)
    for (_, gap_start), (gap_end, _) in zip(runs, runs[1:]):
        if gap_end - gap_start <= BRIDGE_FRAMES:
            pitch[gap_start:gap_end] = np.interp(
                np.arange(gap_start, gap_end), [gap_start - 1, gap_end], [pitch[gap_start - 1], pitch[gap_end]]
            )
            voiced[gap_start:gap_end] = True


def pitch_jumps(smooth):
    """Frames (within one run) where the pitch moves away from the current note and stays away."""
    cuts = []
    current = [smooth[0]]  # pitch readings of the note we are in
    k = 1
    while k < len(smooth):
        center = np.median(current)
        ahead = smooth[k : k + JUMP_FRAMES]
        if len(ahead) == JUMP_FRAMES and np.all(np.abs(ahead - center) > JUMP_SEMITONES):
            cuts.append(k)
            current = [smooth[k]]
        else:
            current.append(smooth[k])
        k += 1
    return cuts


def is_dip(loudness, k, start, end, dip_frames, fraction):
    """True if the loudness at frame k is well below the loudest moments just before and after."""
    before = loudness[max(start, k - dip_frames) : k]
    after = loudness[k + 1 : min(end, k + dip_frames + 1)]
    if len(before) == 0 or len(after) == 0:
        return False
    return loudness[max(start, k - 2) : k + 3].min() < fraction * min(before.max(), after.max())


def loudness_dips(loudness, start, end, dip_frames):
    """Frames where the loudness briefly drops: the same note being hummed again."""
    dips = []
    for k in range(start + dip_frames, end - dip_frames):
        is_local_low = loudness[k] == loudness[max(start, k - 2) : k + 3].min()
        if is_local_low and is_dip(loudness, k, start, end, dip_frames, DIP):
            dips.append(k)
    return dips


def middle_pitch(smooth):
    """The pitch of a piece, ignoring its first and last fifth (the slide in and out)."""
    if len(smooth) >= 6:
        edge = len(smooth) // 5
        smooth = smooth[edge : len(smooth) - edge]
    return float(np.median(smooth))


def absorb_slides_and_drop_blips(pieces, frame_seconds):
    """Merge short slides into the longer note next to them, and drop pieces too short to be notes."""
    def frames(p):
        return p["end"] - p["start"]

    changed = True
    while changed:
        changed = False
        for i, piece in enumerate(pieces):
            seconds = frames(piece) * frame_seconds
            neighbors = []
            if i > 0 and pieces[i - 1]["end"] == piece["start"]:
                neighbors.append(pieces[i - 1])
            if i + 1 < len(pieces) and pieces[i + 1]["start"] == piece["end"]:
                neighbors.append(pieces[i + 1])
            at_edge_of_breath = len(neighbors) == 1
            neighbors = [n for n in neighbors if abs(n["exact"] - piece["exact"]) <= SLIDE_SEMITONES]

            if seconds < SLIDE_SECONDS:
                neighbors = [n for n in neighbors if frames(n) > frames(piece)]
            elif at_edge_of_breath and seconds < EDGE_SLIDE_SECONDS:
                neighbors = [n for n in neighbors if frames(n) >= EDGE_SLIDE_RATIO * frames(piece)]
            else:
                neighbors = []

            if neighbors:
                target = max(neighbors, key=frames)
                target["start"] = min(target["start"], piece["start"])
                target["end"] = max(target["end"], piece["end"])
                pieces.pop(i)
                changed = True
                break
            if seconds < MIN_SECONDS:
                pieces.pop(i)
                changed = True
                break


def drop_noise(pieces, loudness, confidence):
    """Remove pieces that are a breath, a click or room noise rather than a hummed note."""
    if len(pieces) < 3:
        return pieces  # too few notes to know what "typical" is

    def average(values, p):
        return float(np.nanmean(values[p["start"] : p["end"]]))

    typical_loudness = np.median([average(loudness, p) for p in pieces])
    middle_pitch_of_melody = np.median([p["exact"] for p in pieces])

    kept = []
    for p in pieces:
        how_loud = average(loudness, p) / typical_loudness
        unsure = confidence is not None and average(confidence, p) < UNSURE
        stray = abs(p["exact"] - middle_pitch_of_melody) > STRAY_SEMITONES
        is_noise = how_loud < QUIET or (unsure and (how_loud < UNSURE_QUIET or stray))
        if not is_noise:
            kept.append(p)
    return kept


def remove_tuning_offset(pieces):
    """People hum a little sharp or flat of the piano. Find the shift (up to half a semitone)
    that puts their notes closest to whole pitches, and remove it."""
    exact = np.array([p["exact"] for p in pieces])
    frames = np.array([p["end"] - p["start"] for p in pieces])
    shifts = np.arange(-0.5, 0.5, 0.05)
    misfit = [np.sum(frames * np.abs((exact - s) - np.round(exact - s))) for s in shifts]
    best = float(shifts[int(np.argmin(misfit))])
    for p in pieces:
        p["exact"] -= best


def join_same_pitch(pieces, loudness, dip_frames):
    """Two touching pieces that rounded to the same note are one note, unless the loudness dips between them."""
    i = 0
    while i < len(pieces) - 1:
        a, b = pieces[i], pieces[i + 1]
        touching = a["end"] == b["start"]
        if a["pitch"] == b["pitch"] and touching and not is_dip(loudness, b["start"], 0, len(loudness), dip_frames, DIP * 1.5):
            a["end"] = b["end"]
            pieces.pop(i + 1)
        else:
            i += 1


def snap_to_scale(pieces):
    """Find the major scale the melody fits best (this also covers minor keys, which share
    their notes with a major scale), then move off-scale notes to a neighboring scale note."""
    if len(pieces) < 5:
        return

    def misfit(tonic):
        scale = np.array([(tonic + step) % 12 for step in MAJOR_SCALE])
        total = 0.0
        for p in pieces:
            distance = np.abs(p["exact"] % 12 - scale)
            total += np.min(np.minimum(distance, 12 - distance)) * (p["end"] - p["start"])
        return total

    tonic = min(range(12), key=misfit)
    scale = {(tonic + step) % 12 for step in MAJOR_SCALE}
    for p in pieces:
        if p["pitch"] % 12 in scale:
            continue
        options = [q for q in (p["pitch"] - 1, p["pitch"] + 1) if q % 12 in scale and abs(p["exact"] - q) <= SCALE_REACH]
        if options:
            p["pitch"] = min(options, key=lambda q: abs(p["exact"] - q))
