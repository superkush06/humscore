import { useEffect, useRef } from 'react'
import WaveSurfer from 'wavesurfer.js'
import RecordPlugin from 'wavesurfer.js/dist/plugins/record.esm.js'

// A waveform that moves with the mic while recording, drawn by wavesurfer.js.
// It only draws: the recording itself is still done by Recorder.
export default function LiveWaveform({ stream }: { stream: MediaStream }) {
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    const wavesurfer = WaveSurfer.create({
      container,
      height: 72,
      waveColor: '#f5c451',
      barWidth: 4,
      barGap: 3,
      barRadius: 2,
      cursorWidth: 0,
      interact: false,
    })
    const record = wavesurfer.registerPlugin(RecordPlugin.create({ scrollingWaveform: true }))
    const micWaveform = record.renderMicStream(stream)

    return () => {
      micWaveform.onDestroy()
      wavesurfer.destroy()
    }
  }, [stream])

  return <div ref={containerRef} className="w-full max-w-md" />
}
