import { useRef, useState } from 'react'
import { toWav } from '../audio/toWav'
import LiveWaveform from './LiveWaveform'

type Props = {
  // Called with the finished recording as a WAV file.
  onRecorded: (wav: Blob) => void
  // A recorded hum to play in place of the mic recording (a link to the audio), if one was picked.
  sampleUrl?: string | null
  // Called when that recorded hum has played to the end.
  onSampleEnded?: () => void
}

// Record from the mic, convert the recording to WAV, and play it back.
function Recorder({ onRecorded, sampleUrl, onSampleEnded }: Props) {
  const recorderRef = useRef<MediaRecorder | null>(null)
  const timerRef = useRef<number | undefined>(undefined)
  const [recording, setRecording] = useState(false)
  // The recorder while it's running, so the live waveform can listen to the same mic
  const [liveRecorder, setLiveRecorder] = useState<MediaRecorder | null>(null)
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
      setLiveRecorder(null)

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
    setLiveRecorder(recorder)
    setSeconds(0)
    timerRef.current = window.setInterval(() => setSeconds((s) => s + 1), 1000)
  }

  function stopRecording() {
    recorderRef.current?.stop()
    recorderRef.current = null
  }

  return (
    <section className="flex flex-col items-center">
      {/* One button: Record while idle, Stop while recording */}
      <button
        onClick={recording ? stopRecording : startRecording}
        className={`flex items-center gap-3 rounded-full px-8 py-4 text-lg font-semibold transition-colors focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-brass ${
          recording ? 'bg-white text-midnight' : 'bg-signal text-white hover:brightness-110'
        }`}
      >
        <span className={recording ? 'h-3.5 w-3.5 rounded-sm bg-signal' : 'h-3.5 w-3.5 rounded-full bg-white'} />
        {recording ? 'Stop' : 'Record'}
      </button>

      {recording && liveRecorder && (
        <div className="mt-6 flex w-full flex-col items-center gap-2">
          <LiveWaveform stream={liveRecorder.stream} />
          <p className="text-mist tabular-nums">
            Recording {Math.floor(seconds / 60)}:{String(seconds % 60).padStart(2, '0')}
          </p>
        </div>
      )}

      {error && <p className="mt-4 text-red-300">{error}</p>}

      {/* The player shows the recorded hum if one was picked (and plays it right away), otherwise your own recording */}
      {sampleUrl && !recording ? (
        <audio key={sampleUrl} controls autoPlay src={sampleUrl} onEnded={onSampleEnded} className="mt-6 w-full max-w-md" />
      ) : (
        audioUrl && !recording && <audio controls src={audioUrl} className="mt-6 w-full max-w-md" />
      )}
    </section>
  )
}

export default Recorder
