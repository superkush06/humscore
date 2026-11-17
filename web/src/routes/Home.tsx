import { useEffect, useRef, useState } from 'react'
import type { Note } from '../types/note'
import { notate, notateMidi, transcribe, type Notation } from '../api'
import { playNotes } from '../audio/playNotes'
import { EXAMPLE_NOTES } from '../exampleNotes'
import SheetMusicDisplay from '../components/SheetMusicDisplay'
import Recorder from '../components/Recorder'
// Animations from React Bits (reactbits.dev), copied in unchanged
import AnimatedContent from '../components/reactbits/AnimatedContent'
import SplitText from '../components/reactbits/SplitText'
import Waves from '../components/reactbits/Waves'

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
  const [tempoText, setTempoText] = useState('') // what is typed in the tempo box
  const [take, setTake] = useState(0) // counts hums, so the score sheet animates in once per hum
  const [samples, setSamples] = useState<string[]>([]) // recorded hums in web/public/samples, if there are any
  const samplePlayer = useRef<HTMLAudioElement | null>(null)

  // Recorded hums are audio, so they are never in the repo. If this machine has some in
  // web/public/samples (with an index.json listing the file names), offer them; if not, show nothing.
  useEffect(() => {
    fetch('/samples/index.json')
      .then((response) => response.json())
      .then((names) => setSamples(names))
      .catch(() => setSamples([]))
  }, [])

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

  // Notate step. Leave bpm out to let the server pick the tempo from the timing of the notes.
  async function writeScore(notes: Note[], bpm?: number) {
    const result = await notate(notes, bpm)
    setNotation(result)
    setTempoText(String(result.bpm))
    // SheetMusicDisplay loads from a URL, so wrap the MusicXML text in one.
    // Free the previous score's URL before replacing it.
    setScoreUrl((oldUrl) => {
      if (oldUrl) URL.revokeObjectURL(oldUrl)
      return URL.createObjectURL(new Blob([result.musicxml], { type: 'application/xml' }))
    })
  }

  function handleRecording(wav: Blob) {
    setTake((t) => t + 1)
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

  // Play a recorded hum out loud and send the same audio through the app, exactly like a new recording.
  async function trySample(name: string) {
    samplePlayer.current?.pause()
    const wav = await (await fetch(`/samples/${name}`)).blob()
    samplePlayer.current = new Audio(URL.createObjectURL(wav))
    samplePlayer.current.play()
    handleRecording(wav)
  }

  function tryExample() {
    setTake((t) => t + 1)
    setDetected(EXAMPLE_NOTES)
    run('Writing the score…', () => writeScore(EXAMPLE_NOTES))
  }

  // The tempo is picked after you sing. Typing a different one redraws the same hum at that tempo.
  function applyTempo() {
    const bpm = Math.round(Number(tempoText))
    if (!detected || !notation || bpm === notation.bpm) return
    if (!(bpm >= 30 && bpm <= 240)) {
      setTempoText(String(notation.bpm)) // not a usable tempo: put the current one back
      return
    }
    run('Writing the score…', () => writeScore(detected, bpm))
  }

  function autoTempo() {
    if (!detected) return
    run('Writing the score…', () => writeScore(detected))
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

  const button =
    'rounded-full border border-gray-300 bg-white px-4 py-1.5 text-sm font-medium text-gray-900 hover:bg-gray-100 disabled:opacity-50'

  return (
    <>
      {/* Moving lines behind the whole page */}
      <div className="fixed inset-0 -z-10">
        <Waves lineColor="#343a8c" backgroundColor="#14173a" rotation={90} spacing={22} amplitude={26} clickRipple={false} />
      </div>

      <main className="mx-auto max-w-4xl px-4 py-16 text-center">
        <SplitText
          text="HumScore"
          tag="h1"
          trigger="load"
          className="font-display text-7xl leading-tight sm:text-9xl"
        />
        <p className="mt-2 font-display text-2xl text-mist sm:text-3xl">Hum a melody. Get sheet music.</p>
        <p className="mt-8 mb-6 text-mist">Press Record, hum a tune at a steady pace, then press Stop.</p>

        <Recorder onRecorded={handleRecording} />

        <button
          onClick={tryExample}
          disabled={busy !== null}
          className="mt-6 text-sm text-mist underline underline-offset-4 hover:text-white disabled:opacity-50"
        >
          No mic? Try an example melody
        </button>

        {samples.length > 0 && (
          <div className="mt-4 flex items-center justify-center gap-2 text-sm text-mist">
            Or hear a recorded hum
            {samples.map((name, i) => (
              <button
                key={name}
                onClick={() => trySample(name)}
                disabled={busy !== null}
                aria-label={`Recorded hum ${i + 1}`}
                className="h-8 w-8 rounded-full border border-white/30 tabular-nums hover:border-brass hover:text-brass disabled:opacity-50"
              >
                {i + 1}
              </button>
            ))}
          </div>
        )}

        {busy && <p className="mt-10 text-lg text-brass">{busy}</p>}

        {error && <p className="mt-10 text-red-300">Something went wrong: {error}. Is the server running?</p>}

        {detected && detected.length === 0 && !busy && (
          <p className="mt-10">No notes found. Try humming louder or closer to the mic.</p>
        )}

        {!detected && !busy && !error && (
          <p className="mt-10 rounded-lg border border-dashed border-white/25 px-6 py-14 text-mist">
            Your sheet music will appear here.
          </p>
        )}

        {scoreUrl && notation && (
          // key={take}: a new hum is a new sheet, so it animates in again.
          <AnimatedContent key={take} trigger="mount" distance={80} duration={0.9} className="mt-10">
            <section className="rounded-md bg-white p-6 text-left text-gray-900 shadow-2xl shadow-black/50">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <button
                  onClick={play}
                  disabled={playing}
                  className="rounded-full bg-brass px-6 py-2 font-semibold text-midnight hover:brightness-105 disabled:opacity-60"
                >
                  {playing ? 'Playing…' : '▶ Play'}
                </button>

                <div className="flex flex-wrap items-center gap-2">
                  <label className="flex items-center gap-2 text-sm text-gray-600">
                    Tempo
                    <input
                      type="number"
                      min={30}
                      max={240}
                      value={tempoText}
                      onChange={(e) => setTempoText(e.target.value)}
                      onBlur={applyTempo}
                      onKeyDown={(e) => e.key === 'Enter' && applyTempo()}
                      className="w-20 rounded-full border border-gray-300 px-3 py-1.5 text-center tabular-nums text-gray-900"
                    />
                    BPM
                  </label>
                  <button onClick={autoTempo} disabled={busy !== null} className={button}>
                    Auto
                  </button>
                  <a href={scoreUrl} download="humscore.musicxml" className={button}>
                    Download MusicXML
                  </a>
                  <button onClick={downloadMidi} disabled={busy !== null} className={button}>
                    Download MIDI
                  </button>
                </div>
              </div>

              <div className="mt-4">
                <SheetMusicDisplay xmlUrl={scoreUrl} />
              </div>
            </section>
          </AnimatedContent>
        )}

        {detected && detected.length > 0 && (
          <details className="mt-6 rounded-md border border-white/15 bg-white/5 p-6 text-left backdrop-blur-sm">
            <summary className="cursor-pointer font-medium text-mist">Detected notes ({detected.length})</summary>
            <p className="mt-3 text-sm text-mist">
              What the server heard, before the notes were snapped to the beat. This list is the note format the whole app is built around.
            </p>
            <table className="mt-3 w-full text-sm tabular-nums">
              <thead>
                <tr className="text-left text-mist">
                  <th className="font-medium">Note</th>
                  <th className="font-medium">MIDI</th>
                  <th className="font-medium">Start (s)</th>
                  <th className="font-medium">End (s)</th>
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
    </>
  )
}
