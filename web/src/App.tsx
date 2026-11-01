import { useState } from 'react'
import type { Note } from './types/note'
import Recorder from './components/Recorder'

// Smoke test for the note format: POST to /transcribe and list what comes back.
function App() {
  const [notes, setNotes] = useState<Note[]>([])
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  async function transcribeTest() {
    setLoading(true)
    setError(null)
    setNotes([])
    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL}/transcribe`, {
        method: 'POST',
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

      <Recorder />

      <button
        onClick={transcribeTest}
        disabled={loading}
        className="mt-6 rounded bg-blue-600 px-4 py-2 text-white disabled:opacity-50"
      >
        {loading ? 'Transcribing…' : 'Transcribe test'}
      </button>

      {error && <p className="mt-4 text-red-600">Request failed: {error}</p>}

      <ul className="mt-4 space-y-1 font-mono text-sm">
        {notes.map((note, i) => (
          <li key={i}>
            pitch {note.pitch} · onset {note.onset}s · offset {note.offset}s
          </li>
        ))}
      </ul>
    </main>
  )
}

export default App
