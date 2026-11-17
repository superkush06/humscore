import copy
import importlib
import sys
import unittest
from types import ModuleType
from unittest.mock import Mock, patch

from cleanup import cleanup_notes


def note(pitch, onset, offset, amplitude=None):
    result = {"pitch": pitch, "onset": onset, "offset": offset}
    if amplitude is not None:
        result["amplitude"] = amplitude
    return result


class CleanupTests(unittest.TestCase):
    def test_merge_scoops(self):
        cases = [
            ([note(59, 0, 0.1), note(60, 0.1, 0.8)], [note(60, 0, 0.8)]),
            ([note(62, 0, 0.1), note(60, 0.1, 0.8)], [note(60, 0, 0.8)]),
            ([note(58, 0, 0.05), note(59, 0.05, 0.1), note(60, 0.1, 0.8)], [note(60, 0, 0.8)]),
            ([note(59, 0.5, 0.65), note(60, 0.69, 1.5)], [note(60, 0.5, 1.5)]),
            ([note(59, 0, 0.14), note(60, 0.14, 0.8)], [note(60, 0, 0.8)]),
        ]
        for original, expected in cases:
            with self.subTest(notes=original):
                self.assertEqual(cleanup_notes(original), expected)

    def test_preserve_distinct_notes(self):
        cases = [
            [note(59, 0, 0.2), note(60, 0.2, 1)],  # long enough to be a real note
            [note(59, 0, 0.1), note(60, 0.1, 0.3)],  # neither note dominates
            [note(59, 0, 0.1), note(60, 0.2, 0.8)],  # separated by a breath
            [note(55, 0, 0.1), note(60, 0.1, 0.8)],  # a leap, not a scoop
            [note(60, 0, 0.8), note(59, 0.8, 0.9)],  # do not swallow the next short note
            [note(60, 0, 0.5), note(60, 0.6, 1)],  # repeated note with a break
            [note(60, 0, 0.5), note(60, 0.5401, 1)],  # just beyond the bridge threshold
            [note(60, 0, 0.5), note(72, 0.5, 1), note(60, 1, 1.5)],  # sustained octave leap
            [note(60, 0, 0.5), note(72, 0.5, 0.6)],  # no return to the earlier pitch
            [note(60, 0, 0.5), note(72, 0.6, 0.7), note(60, 0.8, 1.3)],  # breaks around an octave
        ]
        for original in cases:
            with self.subTest(notes=original):
                self.assertEqual(cleanup_notes(original), original)

    def test_rejoin_split_notes(self):
        cases = [
            [note(60, 0, 0.5), note(60, 0.5, 1)],
            [note(60, 0, 0.5), note(60, 0.54, 1)],
            [note(60, 0, 0.5), note(60, 0.45, 1)],
            [note(60, 0, 1), note(60, 0.2, 0.5)],
            [note(60, 0, 0.3), note(60, 0.32, 0.6), note(60, 0.63, 1)],
        ]
        for original in cases:
            with self.subTest(notes=original):
                self.assertEqual(cleanup_notes(original), [note(60, 0, 1)])

    def test_drop_overlapping_octave_ghosts(self):
        for ghost_pitch in (48, 72, 84):
            with self.subTest(pitch=ghost_pitch):
                self.assertEqual(
                    cleanup_notes([note(60, 0, 1, 0.8), note(ghost_pitch, 0, 1, 0.2)]),
                    [note(60, 0, 1)],
                )
        self.assertEqual(
            cleanup_notes([note(72, 0, 0.4, 0.2), note(60, 0.08, 1, 0.8)]),
            [note(60, 0.08, 1)],
        )

    def test_keep_octaves_without_strong_evidence(self):
        cases = [
            [note(60, 0, 1), note(72, 0, 1)],  # no amplitude evidence
            [note(60, 0, 1, 0.8), note(72, 0, 1, 0.5)],  # similar strength
            [note(60, 0, 0.5, 0.8), note(72, 0.4, 1, 0.2)],  # only a small overlap
            [note(60, 0, 0.5, 0.8), note(72, 0.5, 1, 0.2)],  # sequential, even if quiet
            [note(60, 0, 1, 0.8), note(67, 0, 1, 0.2)],  # not an octave
        ]
        for original in cases:
            with self.subTest(notes=original):
                expected = [{k: n[k] for k in ("pitch", "onset", "offset")} for n in original]
                self.assertEqual(cleanup_notes(original), expected)

    def test_rejoin_around_brief_octave_errors(self):
        for ghost_pitch in (48, 72, 84):
            with self.subTest(pitch=ghost_pitch):
                self.assertEqual(
                    cleanup_notes([note(60, 0, 0.5), note(ghost_pitch, 0.5, 0.6), note(60, 0.6, 1)]),
                    [note(60, 0, 1)],
                )
        self.assertEqual(
            cleanup_notes([note(60, 0, 0.6), note(72, 0.6, 0.74), note(60, 0.74, 1.4)]),
            [note(60, 0, 1.4)],
        )

    def test_combined_cleanup_sorted_without_mutating_input(self):
        original = [
            note(60, 0.54, 1, 0.8), note(72, 0.1, 0.5, 0.2),
            note(59, 0, 0.1, 0.7), note(60, 0.1, 0.5, 0.8),
        ]
        unchanged = copy.deepcopy(original)
        cleaned = cleanup_notes(original)
        self.assertEqual(cleaned, [note(60, 0, 1)])
        self.assertEqual(original, unchanged)
        self.assertEqual(cleanup_notes(cleaned), cleaned)

    def test_scoop_into_a_note_split_into_short_pieces(self):
        self.assertEqual(
            cleanup_notes([
                note(59, 0, 0.14), note(60, 0.14, 0.28),
                note(60, 0.3, 0.44), note(60, 0.46, 0.66),
            ]),
            [note(60, 0, 0.66)],
        )

    def test_empty_and_single_note(self):
        self.assertEqual(cleanup_notes([]), [])
        self.assertEqual(cleanup_notes([note(60, 0.5, 1, 0.7)]), [note(60, 0.5, 1)])

    def test_transcription_uses_amplitude_and_cleans_before_rounding(self):
        # Exercise the real adapter without downloading/loading the ML model in unit tests.
        basic_pitch = ModuleType("basic_pitch")
        basic_pitch.ICASSP_2022_MODEL_PATH = "model-path"
        inference = ModuleType("basic_pitch.inference")
        inference.Model = Mock()
        inference.predict = Mock(return_value=(None, None, [
            (0.5, 1.0, 60, 0.8, None),
            (0.1, 0.4596, 60, 0.8, None),
            (0.1, 0.4596, 72, 0.2, None),
            (0, 0.1, 59, 0.7, None),
        ]))
        with patch.dict(sys.modules, {"basic_pitch": basic_pitch, "basic_pitch.inference": inference}):
            sys.modules.pop("transcribe", None)
            transcribe = importlib.import_module("transcribe")
            result = transcribe.notes_from_wav("recording.wav")
        self.assertEqual(result, [note(60, 0, 0.46), note(60, 0.5, 1)])
        inference.Model.assert_called_once_with("model-path")
        inference.predict.assert_called_once_with("recording.wav", inference.Model.return_value)


if __name__ == "__main__":
    unittest.main()
