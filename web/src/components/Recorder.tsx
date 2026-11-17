import { useRef, useState } from 'react'
import { toWav } from '../audio/toWav'

type Props = {
  // Called with the finished recording as a WAV file.
  onRecorded: (wav: Blob) => void
}

// Record from the mic, convert the recording to WAV, and play it back.
function Recorder({ onRecorded }: Props) {
  const recorderRef = useRef<MediaRecorder | null>(null)
  const [recording, setRecording] = useState(false)
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
  }

  function stopRecording() {
    recorderRef.current?.stop()
    recorderRef.current = null
  }

  return (
    <section className="mt-6">
      <div className="flex gap-2">
        <button
          onClick={startRecording}
          disabled={recording}
          className="rounded bg-red-600 px-4 py-2 text-white disabled:opacity-50"
        >
          {recording ? 'Recording…' : 'Record'}
        </button>
        <button
          onClick={stopRecording}
          disabled={!recording}
          className="rounded bg-gray-700 px-4 py-2 text-white disabled:opacity-50"
        >
          Stop
        </button>
      </div>

      {error && <p className="mt-4 text-red-600">{error}</p>}

      {audioUrl && <audio controls src={audioUrl} className="mt-4 w-full" />}
    </section>
  )
}

export default Recorder
