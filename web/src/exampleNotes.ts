import type { Note } from './types/note'

// "Twinkle Twinkle Little Star" in our note format, for the "Try an example" button.
// Each entry is [MIDI pitch, length in beats], at 100 beats per minute.
const MELODY: [number, number][] = [
  [60, 1], [60, 1], [67, 1], [67, 1], [69, 1], [69, 1], [67, 2],
  [65, 1], [65, 1], [64, 1], [64, 1], [62, 1], [62, 1], [60, 2],
]
const SECONDS_PER_BEAT = 60 / 100

function buildNotes(): Note[] {
  const notes: Note[] = []
  let time = 0
  for (const [pitch, beats] of MELODY) {
    const length = beats * SECONDS_PER_BEAT
    notes.push({ pitch, onset: time, offset: time + length - 0.05 }) // small gap between notes
    time += length
  }
  return notes
}

export const EXAMPLE_NOTES = buildNotes()
