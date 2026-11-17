import type { Note } from './types/note'

// All calls to our server live here. The server's address comes from web/.env.
const API_URL = import.meta.env.VITE_API_URL

// What /notate sends back.
export type Notation = {
  musicxml: string // the score, as MusicXML text
  bpm: number // the tempo the server used
  notes: Note[] // the notes as the score shows them (snapped to the beat), for playback
}

async function post(path: string, body: FormData | object): Promise<Response> {
  const isForm = body instanceof FormData
  const response = await fetch(`${API_URL}${path}`, {
    method: 'POST',
    headers: isForm ? undefined : { 'Content-Type': 'application/json' },
    body: isForm ? body : JSON.stringify(body),
  })
  if (!response.ok) {
    throw new Error(`Server returned ${response.status}`)
  }
  return response
}

// Detect step: a WAV recording in, notes out.
export async function transcribe(wav: Blob): Promise<Note[]> {
  const form = new FormData()
  form.append('audio', wav, 'recording.wav') // 'audio' matches the server's parameter name
  return (await post('/transcribe', form)).json()
}

// Notate step: notes in, sheet music out. Leave bpm out to let the server guess the tempo.
export async function notate(notes: Note[], bpm?: number): Promise<Notation> {
  return (await post('/notate', { notes, bpm })).json()
}

// The same score as a MIDI file.
export async function notateMidi(notes: Note[], bpm: number): Promise<Blob> {
  return (await post('/notate/midi', { notes, bpm })).blob()
}
