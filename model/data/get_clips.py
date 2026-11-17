"""Download a small, reproducible HumTrans dataset subset."""

import argparse
import json
import random
import urllib.request
import zipfile
from pathlib import Path
from typing import Iterable

from remotezip import RemoteZip


HF_URL = "https://huggingface.co/datasets/dadinghh2/HumTrans/resolve/main"
SEED = 0
SPLITS = ("train", "valid", "test")
KEY_NAMES = {"train": "TRAIN", "valid": "VALID", "test": "TEST"}
TIMING_ZIPS = {
    "train": "filtered_train.zip",
    "valid": "filtered_valid.zip",
    "test": "filtered_test.zip",
}
TIMING_DIRS = {
    "train": "filtered",
    "valid": "filtered_valid",
    "test": "filtered_test",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download a reproducible HumTrans clip subset."
    )
    parser.add_argument("--split", choices=SPLITS, required=True)
    parser.add_argument("--n", type=int, required=True, help="Number of clips to select.")
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("mini_ds"),
        help="Output dataset directory (default: mini_ds).",
    )
    parser.add_argument(
        "--paper-repo",
        type=Path,
        default=Path("..") / "humming_transcription",
        help=(
            "Cloned Dynamic HumTrans repository. Its corrected timing zips must be "
            "under heurestic_filtered_onsets_offsets/."
        ),
    )
    parser.add_argument(
        "--held-out",
        nargs=2,
        metavar=("FEMALE", "MALE"),
        help=(
            "Also write held_out_singer_train_valid_test_keys.json, holding out "
            "one female and one male singer (for example: F01 M01)."
        ),
    )
    return parser.parse_args()


def read_keys() -> dict[str, list[str]]:
    with urllib.request.urlopen(f"{HF_URL}/train_valid_test_keys.json") as response:
        return json.load(response)


def corrected_keys(timing_zip: Path) -> set[str]:
    with zipfile.ZipFile(timing_zip) as archive:
        return {
            Path(name).stem.removesuffix("_onsets_offsets")
            for name in archive.namelist()
            if name.endswith("_onsets_offsets.txt")
        }


def choose_clips(
    keys: dict[str, list[str]], split: str, n: int, timing_zip: Path
) -> list[str]:
    available = sorted(set(keys[KEY_NAMES[split]]) & corrected_keys(timing_zip))
    if n > len(available):
        raise ValueError(
            f"{split} has {len(available)} clips with corrected timings; cannot select {n}."
        )
    return random.Random(SEED).sample(available, n)


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def write_timing_files(
    output_dir: Path, split: str, clip_names: Iterable[str], timing_zip: Path
) -> None:
    destination = output_dir / TIMING_DIRS[split]
    destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(timing_zip) as archive:
        for clip_name in clip_names:
            member = f"{clip_name}_onsets_offsets.txt"
            try:
                data = archive.read(member)
            except KeyError as error:
                raise RuntimeError(
                    f"Corrected timing archive is missing {member}."
                ) from error
            (destination / member).write_bytes(data)


def write_remote_files(output_dir: Path, clip_names: Iterable[str]) -> None:
    clip_names = list(clip_names)
    midi_dir = output_dir / "all_midi_unzipped" / "midi_data"
    wav_dir = output_dir / "all_wav_unzipped" / "wav_data_sync_with_midi"
    midi_dir.mkdir(parents=True, exist_ok=True)
    wav_dir.mkdir(parents=True, exist_ok=True)

    with RemoteZip(f"{HF_URL}/all_midi.zip") as archive:
        for clip_name in clip_names:
            member = f"midi_data/{clip_name}.mid"
            (midi_dir / f"{clip_name}.mid").write_bytes(archive.read(member))

    with RemoteZip(f"{HF_URL}/all_wav.zip") as archive:
        for clip_name in clip_names:
            member = f"wav_data_sync_with_midi/{clip_name}.wav"
            (wav_dir / f"{clip_name}.wav").write_bytes(archive.read(member))


def held_out_keys(
    keys: dict[str, list[str]], female: str, male: str
) -> dict[str, list[str]]:
    singers = (female, male)
    if any(
        singer not in {f"F0{i}" for i in range(1, 6)}
        | {f"M0{i}" for i in range(1, 6)}
        for singer in singers
    ):
        raise ValueError("Held-out singers must be F01-F05 or M01-M05.")
    if not female.startswith("F") or not male.startswith("M"):
        raise ValueError("Pass one female singer (F01-F05) and one male singer (M01-M05).")

    return {
        "TRAIN": sorted(
            clip
            for clip in keys["TRAIN"]
            if not clip.startswith(singers)
        ),
        "VALID": sorted(
            clip
            for clip in keys["VALID"]
            if not clip.startswith(singers)
        ),
        "TEST": sorted(
            clip
            for source_split in SPLITS
            for clip in keys[KEY_NAMES[source_split]]
            if clip.startswith(singers)
        ),
    }


def main() -> None:
    args = parse_args()
    if args.n < 0:
        raise ValueError("--n must be non-negative.")

    timings_dir = args.paper_repo / "heurestic_filtered_onsets_offsets"
    timing_zip = timings_dir / TIMING_ZIPS[args.split]
    if not timing_zip.is_file():
        raise FileNotFoundError(
            f"Corrected timings not found: {timing_zip}. "
            "Clone humming_transcription next to this repository or pass --paper-repo."
        )

    keys = read_keys()
    selected = choose_clips(keys, args.split, args.n, timing_zip)
    selected_by_split = {name.upper(): [] for name in SPLITS}
    selected_by_split[KEY_NAMES[args.split]] = selected

    args.out.mkdir(parents=True, exist_ok=True)
    write_timing_files(args.out, args.split, selected, timing_zip)
    write_remote_files(args.out, selected)
    write_json(args.out / "train_valid_test_keys.json", selected_by_split)

    if args.held_out:
        held_out = held_out_keys(keys, args.held_out[0], args.held_out[1])
        write_json(args.out / "held_out_singer_train_valid_test_keys.json", held_out)
        print(
            "held-out singers:",
            args.held_out[0],
            args.held_out[1],
            "->",
            ", ".join(
                f"{split.lower()} {len(held_out[split.upper()])}"
                for split in SPLITS
            ),
        )

    print(f"dataset ready: {len(selected)} {args.split} clips in {args.out}")


if __name__ == "__main__":
    main()
