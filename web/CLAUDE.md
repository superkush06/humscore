# web/ (frontend)

Owners: Aadi (app structure, recording, integration), Ben (score view).

## Stack
- React, TypeScript, Vite, Tailwind CSS v4 (via `@tailwindcss/vite`; `src/index.css` starts with `@import "tailwindcss";`)
- Linting is oxlint (`.oxlintrc.json`), not ESLint.

## Facts
- **Recording**: record the mic as WAV at the browser's own sample rate. Never downsample in the browser: Basic Pitch resamples to 22,050 Hz itself and our model uses 44,100 Hz.
- **API**: the server URL comes from `VITE_API_URL` in `web/.env` (copy `.env.example`). Call `${import.meta.env.VITE_API_URL}/transcribe`. `.env` is gitignored.
- **Note format**: `src/types/note.ts`. `pitch` = MIDI number, `onset`/`offset` = seconds. Don't change it without the team agreeing.
- **Score view**: OpenSheetMusicDisplay only renders scores. It is not an editor, and its audio player is only for its GitHub sponsors.
- **Server calls**: all in `src/api.ts` (`transcribe`, `notate`, `notateMidi`). Add new calls there, not in components.
- **Page flow** (`src/routes/Home.tsx`): record → `transcribe` → `notate` → `SheetMusicDisplay` shows the MusicXML (passed as a blob URL) → play or download. The server picks the tempo after the recording; the tempo box shows it, typing a new tempo redraws the same hum, and Auto goes back to the server's pick.
- **Look**: colors and fonts are defined once in `src/index.css` (`bg-midnight`, `text-mist`, `bg-brass`, `bg-signal`, `font-display`). The page is always dark; the score sits on a white sheet.
- **Animations**: `src/components/reactbits/` holds components copied unchanged from React Bits (reactbits.dev): `Waves` (background), `SplitText` (headline), `AnimatedContent` (score reveal). Don't edit them; that folder is skipped by lint. They need `gsap` and `@gsap/react`.
- **Live waveform**: `src/components/LiveWaveform.tsx` draws the mic level while recording with `wavesurfer.js`. It only draws; `Recorder` still does the recording.
- **Playback**: use Tone.js. Browsers block audio until a user click, so playback starts from a button whose handler calls `await Tone.start()`. The helper is `src/audio/playNotes.ts`.

## Commands (run in `web/`)
- `npm run dev`: dev server at http://localhost:5173
- `npm run lint`
- `npm run build`

CI runs `npm ci`, `npm run lint` and `npm run build` on every PR. Commit `package-lock.json` changes.
