import { useRef, useState } from 'react'
import { toWav } from '../audio/toWav'

type Props = {
  // Called with the finished recording as a WAV file.
  onRecorded: (wav: Blob) => void
}

// Record from the mic, convert the recording to WAV, and play it back.
function Recorder({ onRecorded }: Props) {
  const recorderRef = useRef<MediaRecorder | null>(null)
  const timerRef = useRef<number | undefined>(undefined)
  const [recording, setRecording] = useState(false)
  const [seconds, setSeconds] = useState(0) // how long the current recording has been running
  const [audioUrl, setAudioUrl] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function startRecording() {
    setError(null)
    let stream: MediaStream
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    } catch (err) {
      setError(`Could not use the mic: ${err instanceof Error ? err.message : String(err)}`)
      return
    }

    // The mic's own sample rate. Some browsers (Firefox) don't report it; toWav handles that.
    const micRate = stream.getAudioTracks()[0].getSettings().sampleRate

    const recorder = new MediaRecorder(stream)
    const chunks: Blob[] = []
    recorder.ondataavailable = (e) => chunks.push(e.data)
    recorder.onstop = async () => {
      stream.getTracks().forEach((t) => t.stop()) // turns the mic off
      window.clearInterval(timerRef.current)
      setRecording(false)

      const recordedBlob = new Blob(chunks, { type: recorder.mimeType })
      let wav: Blob
      try {
        wav = await toWav(recordedBlob, micRate)
      } catch (err) {
        setError(`Could not convert the recording: ${err instanceof Error ? err.message : String(err)}`)
        return
      }

      // Play back the WAV itself, so what you hear is exactly what gets uploaded.
      // Free the previous recording before replacing it.
      setAudioUrl((oldUrl) => {
        if (oldUrl) URL.revokeObjectURL(oldUrl)
        return URL.createObjectURL(wav)
      })
      onRecorded(wav)
    }

    recorderRef.current = recorder
    recorder.start()
    setRecording(true)
    setSeconds(0)
    timerRef.current = window.setInterval(() => setSeconds((s) => s + 1), 1000)
  }

  function stopRecording() {
    recorderRef.current?.stop()
    recorderRef.current = null
  }

  return (
    <section>
      <div className="flex items-center gap-2">
        <button
          onClick={startRecording}
          disabled={recording}
          className="rounded bg-red-600 px-4 py-2 font-medium text-white hover:bg-red-700 disabled:opacity-50"
        >
          Record
        </button>
        <button
          onClick={stopRecording}
          disabled={!recording}
          className="rounded bg-gray-700 px-4 py-2 font-medium text-white hover:bg-gray-800 disabled:opacity-50"
        >
          Stop
        </button>
        {recording && (
          <span className="ml-2 flex items-center gap-2 text-red-600">
            <span className="h-3 w-3 animate-pulse rounded-full bg-red-600" />
            Recording {Math.floor(seconds / 60)}:{String(seconds % 60).padStart(2, '0')}
          </span>
        )}
      </div>

      {error && <p className="mt-4 text-red-600">{error}</p>}

      {audioUrl && <audio controls src={audioUrl} className="mt-4 w-full" />}
    </section>
  )
}

export default Recorder
