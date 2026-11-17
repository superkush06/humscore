import { useState } from 'react'
import type { Note } from '../types/note'
import { notate, notateMidi, transcribe, type Notation } from '../api'
import { playNotes } from '../audio/playNotes'
import { EXAMPLE_NOTES } from '../exampleNotes'
import SheetMusicDisplay from '../components/SheetMusicDisplay'
import Recorder from '../components/Recorder'

const NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

// MIDI number to a name like "C4" (60 = middle C = C4).
function noteName(pitch: number): string {
  return NOTE_NAMES[pitch % 12] + (Math.floor(pitch / 12) - 1)
}

// Hum in, sheet music out: record, detect the notes, write the score, then play or download it.
export default function Home() {
  const [detected, setDetected] = useState<Note[] | null>(null) // what /transcribe heard
  const [notation, setNotation] = useState<Notation | null>(null) // what /notate wrote
  const [scoreUrl, setScoreUrl] = useState<string | null>(null) // the MusicXML as a link
  const [busy, setBusy] = useState<string | null>(null) // message shown while waiting on the server
  const [error, setError] = useState<string | null>(null)
  const [playing, setPlaying] = useState(false)

  // Run a server step, showing a message while it runs and the error if it fails.
  async function run(message: string, step: () => Promise<void>) {
    setBusy(message)
    setError(null)
    try {
      await step()
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setBusy(null)
    }
  }

  // Notate step. Leave bpm out to let the server guess the tempo.
  async function writeScore(notes: Note[], bpm?: number) {
    const result = await notate(notes, bpm)
    setNotation(result)
    // SheetMusicDisplay loads from a URL, so wrap the MusicXML text in one.
    // Free the previous score's URL before replacing it.
    setScoreUrl((oldUrl) => {
      if (oldUrl) URL.revokeObjectURL(oldUrl)
      return URL.createObjectURL(new Blob([result.musicxml], { type: 'application/xml' }))
    })
  }

  function handleRecording(wav: Blob) {
    run('Listening for notes…', async () => {
      const notes = await transcribe(wav)
      setDetected(notes)
      if (notes.length === 0) {
        setNotation(null)
        return
      }
      setBusy('Writing the score…')
      await writeScore(notes)
    })
  }

  function tryExample() {
    setDetected(EXAMPLE_NOTES)
    run('Writing the score…', () => writeScore(EXAMPLE_NOTES))
  }

  // Redraw the same notes at a different tempo. No need to record again.
  function changeTempo(bpm: number) {
    if (!detected || bpm < 30 || bpm > 240) return
    run('Writing the score…', () => writeScore(detected, bpm))
  }

  async function play() {
    if (!notation) return
    setPlaying(true)
    try {
      await playNotes(notation.notes)
    } finally {
      setPlaying(false)
    }
  }

  function downloadMidi() {
    if (!detected || !notation) return
    run('Making the MIDI file…', async () => {
      const midi = await notateMidi(detected, notation.bpm)
      const url = URL.createObjectURL(midi)
      const link = document.createElement('a')
      link.href = url
      link.download = 'humscore.mid'
      link.click()
      URL.revokeObjectURL(url)
    })
  }

  const button = 'rounded border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium hover:bg-gray-50 disabled:opacity-50'

  return (
    <main className="mx-auto max-w-4xl px-4 py-10">
      <h1 className="font-serif text-5xl font-bold">HumScore</h1>
      <p className="mt-2 text-lg text-gray-600">Hum a melody. Get sheet music.</p>

      <section className="mt-8 rounded-lg border border-gray-200 bg-white p-6">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-500">1. Hum</h2>
        <p className="mt-1 mb-4 text-gray-600">
          Press Record, hum a tune at a steady pace, then press Stop.
        </p>
        <Recorder onRecorded={handleRecording} />
        <button onClick={tryExample} disabled={busy !== null} className="mt-4 text-sm text-indigo-600 underline disabled:opacity-50">
          No mic? Try an example melody
        </button>
      </section>

      <section className="mt-6 rounded-lg border border-gray-200 bg-white p-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-500">2. Your score</h2>

          {notation && scoreUrl && (
            <div className="flex flex-wrap items-center gap-2">
              <button onClick={play} disabled={playing} className="rounded bg-indigo-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50">
                {playing ? 'Playing…' : '▶ Play'}
              </button>

              <span className="flex items-center gap-1 text-sm">
                <button onClick={() => changeTempo(notation.bpm - 4)} disabled={busy !== null} className={button} aria-label="Slower">
                  −
                </button>
                <span className="w-20 text-center tabular-nums">{notation.bpm} BPM</span>
                <button onClick={() => changeTempo(notation.bpm + 4)} disabled={busy !== null} className={button} aria-label="Faster">
                  +
                </button>
              </span>

              <a href={scoreUrl} download="humscore.musicxml" className={button}>
                Download MusicXML
              </a>
              <button onClick={downloadMidi} disabled={busy !== null} className={button}>
                Download MIDI
              </button>
            </div>
          )}
        </div>

        {busy && <p className="mt-4 text-gray-600">{busy}</p>}

        {error && <p className="mt-4 text-red-600">Something went wrong: {error}. Is the server running?</p>}

        {detected && detected.length === 0 && !busy && (
          <p className="mt-4">No notes found. Try humming louder or closer to the mic.</p>
        )}

        {!detected && !busy && !error && (
          <p className="mt-4 text-gray-500">Your sheet music will appear here.</p>
        )}

        {scoreUrl && notation && (
          <div className="mt-4">
            <SheetMusicDisplay xmlUrl={scoreUrl} />
          </div>
        )}
      </section>

      {detected && detected.length > 0 && (
        <details className="mt-6 rounded-lg border border-gray-200 bg-white p-6">
          <summary className="cursor-pointer text-sm font-semibold uppercase tracking-wide text-gray-500">
            Detected notes ({detected.length})
          </summary>
          <p className="mt-3 text-sm text-gray-600">
            What the server heard, before it was snapped to the beat. This list is the note format the whole app is built around.
          </p>
          <table className="mt-3 w-full font-mono text-sm">
            <thead>
              <tr className="text-left">
                <th>Note</th>
                <th>MIDI</th>
                <th>Start (s)</th>
                <th>End (s)</th>
              </tr>
            </thead>
            <tbody>
              {detected.map((note, i) => (
                <tr key={i}>
                  <td>{noteName(note.pitch)}</td>
                  <td>{note.pitch}</td>
                  <td>{note.onset.toFixed(2)}</td>
                  <td>{note.offset.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </details>
      )}
    </main>
  )
}
