# Using the HumTrans clip downloader

## Setup

Use Python 3.11 and install the downloader dependency:

```bash
pip install remotezip
```

Clone the Dynamic HumTrans repository next to `humscore`. The downloader needs
its corrected timing archives in
`humming_transcription/heurestic_filtered_onsets_offsets/`.

## Download clips

From the root of this repository, run:

```bash
python model/data/get_clips.py --split train --n 20 --out mini_ds
```

`--split` can be `train`, `valid`, or `test`. `--n` is the number of clips to
download, and `--out` is the output directory. The script uses a fixed random
seed, selects only clips with corrected timings, and downloads only the
requested WAV and MIDI files.

The output contains:

- Corrected timings in `filtered/`, `filtered_valid/`, or `filtered_test/`
- WAV files in `all_wav_unzipped/wav_data_sync_with_midi/`
- MIDI files in `all_midi_unzipped/midi_data/`
- Selected clip names in `train_valid_test_keys.json`

`mini_ds/` is ignored by Git, so downloaded clips will not be committed.

## Held-out singers

To create a held-out-singer key split, provide one female and one male singer:

```bash
python model/data/get_clips.py --split train --n 20 --out mini_ds --held-out F01 M01
```

Singer IDs must be `F01`-`F05` and `M01`-`M05`. This writes
`held_out_singer_train_valid_test_keys.json`: `TRAIN` and `VALID` contain the
other singers, while `TEST` contains the two held-out singers.
