// Turn a MediaRecorder recording (usually WebM/Opus or MP4/AAC) into a mono 16-bit WAV file.
// The WAV keeps the sample rate the mic recorded at. We never downsample in the browser:
// Basic Pitch resamples on the server, and our own model will want 44,100 Hz.
// If the browser didn't report the mic's rate, the context uses the device's default rate.
export async function toWav(recording: Blob, sampleRate?: number): Promise<Blob> {
  // Decode with a context at the mic's rate so decodeAudioData doesn't resample.
  const context = new AudioContext(sampleRate ? { sampleRate } : undefined)
  try {
    const audio = await context.decodeAudioData(await recording.arrayBuffer())
    return encodeWav(toMono(audio), audio.sampleRate)
  } finally {
    await context.close()
  }
}

// Average all channels into one. Humming is a single voice, so stereo adds nothing.
function toMono(audio: AudioBuffer): Float32Array {
  const mono = new Float32Array(audio.length)
  for (let ch = 0; ch < audio.numberOfChannels; ch++) {
    const data = audio.getChannelData(ch)
    for (let i = 0; i < data.length; i++) {
      mono[i] += data[i] / audio.numberOfChannels
    }
  }
  return mono
}

// Write a standard 44-byte WAV header followed by 16-bit PCM samples.
function encodeWav(samples: Float32Array, sampleRate: number): Blob {
  const bytesPerSample = 2
  const dataSize = samples.length * bytesPerSample
  const view = new DataView(new ArrayBuffer(44 + dataSize))

  writeText(view, 0, 'RIFF')
  view.setUint32(4, 36 + dataSize, true) // size of everything after this field
  writeText(view, 8, 'WAVE')
  writeText(view, 12, 'fmt ')
  view.setUint32(16, 16, true) // fmt chunk size
  view.setUint16(20, 1, true) // format 1 = PCM
  view.setUint16(22, 1, true) // 1 channel
  view.setUint32(24, sampleRate, true)
  view.setUint32(28, sampleRate * bytesPerSample, true) // bytes per second
  view.setUint16(32, bytesPerSample, true) // bytes per frame
  view.setUint16(34, 16, true) // bits per sample
  writeText(view, 36, 'data')
  view.setUint32(40, dataSize, true)

  for (let i = 0; i < samples.length; i++) {
    const s = Math.max(-1, Math.min(1, samples[i])) // clip to [-1, 1]
    view.setInt16(44 + i * bytesPerSample, s < 0 ? s * 0x8000 : s * 0x7fff, true)
  }
  return new Blob([view], { type: 'audio/wav' })
}

function writeText(view: DataView, offset: number, text: string) {
  for (let i = 0; i < text.length; i++) {
    view.setUint8(offset + i, text.charCodeAt(i))
  }
}
