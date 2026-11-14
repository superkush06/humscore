import { useRef, useEffect, useState } from 'react';
import { OpenSheetMusicDisplay } from 'opensheetmusicdisplay';

type Status = "loading" | "error" | "success";

export default function SheetMusicDisplay({ xmlUrl }: { xmlUrl: string }) {
  const sheetMusicDisplayRef = useRef<HTMLDivElement>(null);
  const [status, setStatus] = useState<Status>("loading");

  useEffect(() => {
    const container = sheetMusicDisplayRef.current;
    if (!container) return;

    const osmd = new OpenSheetMusicDisplay(container, { autoResize: true });
    // Set by the cleanup below, so a load that finishes late can't draw over a newer score
    let cancelled = false;

    async function render() {
      try {
        const response = await fetch(xmlUrl);
        if (!response.ok) throw new Error(`HTTP error! Status: ${response.status}`);
        const xml = await response.text();
        if (cancelled) return;

        await osmd.load(xml);
        if (cancelled) return;
        osmd.Zoom = 0.75;
        osmd.render();
        setStatus("success");
      } catch (error) {
        if (cancelled) return;
        setStatus("error");
        console.error("Could not load the score:", error);
      }
    }
    render();

    return () => {
      cancelled = true;
      osmd.clear();
      container.innerHTML = '';
    };
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