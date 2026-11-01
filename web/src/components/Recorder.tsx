import { useRef, useState } from 'react'

// Record from the mic and play the recording back.
function Recorder() {
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
      setError(err instanceof Error ? err.message : String(err))
      return
    }

    const recorder = new MediaRecorder(stream)
    const chunks: Blob[] = []
    recorder.ondataavailable = (e) => chunks.push(e.data)
    recorder.onstop = () => {
      const blob = new Blob(chunks, { type: recorder.mimeType })
      // Free the previous recording before replacing it.
      setAudioUrl((oldUrl) => {
        if (oldUrl) URL.revokeObjectURL(oldUrl)
        return URL.createObjectURL(blob)
      })
      stream.getTracks().forEach((t) => t.stop()) // turns the mic off
      setRecording(false)
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

      {error && <p className="mt-4 text-red-600">Could not use the mic: {error}</p>}

      {audioUrl && <audio controls src={audioUrl} className="mt-4 w-full" />}
    </section>
  )
}

export default Recorder
