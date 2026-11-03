import { useRef, useEffect, useState } from 'react';
import { OpenSheetMusicDisplay } from 'opensheetmusicdisplay';

type Status = "loading" | "error" | "success";

export default function SheetMusicDisplay({ xmlUrl }: { xmlUrl: string }) {
  const sheetMusicDisplayRef = useRef<HTMLDivElement>(null);
  const osmd = useRef<OpenSheetMusicDisplay | null>(null);
  const [status, setStatus] = useState<Status>("loading");

  useEffect(() => {
    async function render() {
      if (!sheetMusicDisplayRef.current) return;

      osmd.current = new OpenSheetMusicDisplay(sheetMusicDisplayRef.current, {
        autoResize: true,
      });
      
      try {
        const response = await fetch(xmlUrl);
        if (!response.ok) {
          // status error
          setStatus("error");
          throw new Error(`HTTP error! Status: ${response.status}`);
        }
        setStatus("success");

        const xml = await response.text();
        await osmd.current.load(xml);
        osmd.current.Zoom = 0.75;
        osmd.current.render();

      } catch (error) {
        setStatus("error");
        console.error("Network error: " + error);
      }
    }
    render();

    // Clean up bc React dev mode may render the element twice
    return () => {
      if (osmd.current) {
        osmd.current.clear();
      }

      // Wipe the container to prevent duplicate SVGs/Canvases on hot-reloads or re-renders
      // happens if you get into error state and then the reload causes it to go to a success state
      if (sheetMusicDisplayRef.current) {
        sheetMusicDisplayRef.current.innerHTML = '';
      }
    }
  }, [xmlUrl]);

  return (
    <>
      {
        status == "error" ? <div className="text-red-700">Oops... it looks like the score could not be loaded :&#40;</div> :
          (status == "loading" && <div>Loading...</div>)
      }

      <div ref={sheetMusicDisplayRef}></div>
    </>
  )
}