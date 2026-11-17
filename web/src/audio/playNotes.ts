import * as Tone from 'tone'
import type { Note } from '../types/note'

// Play notes with a simple synth. Resolves when the last note has finished.
// Call this from a click handler: browsers block audio until the user clicks,
// and Tone.start() is what unlocks it.
export async function playNotes(notes: Note[]): Promise<void> {
  if (notes.length === 0) return
  await Tone.start()

  const synth = new Tone.Synth({ oscillator: { type: 'triangle' } }).toDestination()
  const startTime = Tone.now() + 0.1 // a short lead-in so the first note isn't clipped
  for (const note of notes) {
    const frequency = Tone.Frequency(note.pitch, 'midi').toFrequency()
    synth.triggerAttackRelease(frequency, note.offset - note.onset, startTime + note.onset)
  }

  const lastOffset = Math.max(...notes.map((n) => n.offset))
  await new Promise((resolve) => setTimeout(resolve, (lastOffset + 0.4) * 1000))
  synth.dispose()
}
