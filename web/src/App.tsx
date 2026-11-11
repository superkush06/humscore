import { useState } from 'react'
import type { Note } from './types/note'
import Recorder from './components/Recorder'

const NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

// MIDI number to a name like "C4" (60 = middle C = C4).
function noteName(pitch: number): string {
  return NOTE_NAMES[pitch % 12] + (Math.floor(pitch / 12) - 1)
}

// Hum in, notes out: record, upload the WAV to /transcribe, list the notes that come back.
function App() {
  const [wav, setWav] = useState<Blob | null>(null)
  const [notes, setNotes] = useState<Note[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  async function transcribe(recording: Blob) {
    setWav(recording)
    setLoading(true)
    setError(null)
    setNotes(null)
    try {
      const form = new FormData()
      form.append('audio', recording, 'recording.wav') // 'audio' matches the server's parameter name
      const response = await fetch(`${import.meta.env.VITE_API_URL}/transcribe`, {
        method: 'POST',
        body: form,
      })
      if (!response.ok) {
        throw new Error(`Server returned ${response.status}`)
      }
      setNotes(await response.json())
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="mx-auto max-w-xl p-8">
      <h1 className="text-3xl font-bold">HumScore</h1>
      <p className="mt-2 text-gray-600">Hum a melody, press Stop, and see the notes.</p>

      <Recorder onRecorded={transcribe} />

      {loading && <p className="mt-6">Transcribing…</p>}

      {error && (
        <div className="mt-6 text-red-600">
          <p>Transcription failed: {error}</p>
          {wav && (
            <button
              onClick={() => transcribe(wav)}
              className="mt-2 rounded bg-blue-600 px-4 py-2 text-white"
            >
              Try again
            </button>
          )}
        </div>
      )}

      {notes && notes.length === 0 && (
        <p className="mt-6">No notes found. Try humming louder or closer to the mic.</p>
      )}

      {notes && notes.length > 0 && (
        <table className="mt-6 w-full font-mono text-sm">
          <thead>
            <tr className="text-left">
              <th>Note</th>
              <th>MIDI</th>
              <th>Start (s)</th>
              <th>End (s)</th>
            </tr>
          </thead>
          <tbody>
            {notes.map((note, i) => (
              <tr key={i}>
                <td>{noteName(note.pitch)}</td>
                <td>{note.pitch}</td>
                <td>{note.onset.toFixed(2)}</td>
                <td>{note.offset.toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </main>
  )
}

export default App
