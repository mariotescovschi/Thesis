import { useState } from 'react';
import { Download } from 'lucide-react';
import { BASE } from '@/shared/api/client';

interface ExportMenuProps {
  projectId: string;
  floorId: string;
}

const FORMATS: { fmt: string; label: string }[] = [
  { fmt: 'dxf', label: 'DXF — CAD' },
  { fmt: 'svg', label: 'SVG — vector' },
  { fmt: 'json', label: 'JSON — raw' },
];

/** Toolbar dropdown that downloads the current floor in a CAD/vector/raw format.
 *  The backend serves the file with a Content-Disposition attachment header. */
export const ExportMenu = ({ projectId, floorId }: ExportMenuProps) => {
  const [open, setOpen] = useState(false);

  const download = (fmt: string) => {
    const a = document.createElement('a');
    a.href = `${BASE}/projects/${projectId}/export/${floorId}?fmt=${fmt}`;
    a.download = `${floorId}.${fmt}`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setOpen(false);
  };

  return (
    <div className="relative">
      <button
        onClick={() => setOpen((o) => !o)}
        aria-haspopup="menu"
        aria-expanded={open}
        title="Export"
        className="flex items-center gap-1.5 rounded-md border border-border bg-card/90 px-2.5 py-1.5 text-xs text-foreground backdrop-blur transition-colors hover:bg-card"
      >
        <Download className="size-3.5" />
        Export
      </button>

      {open && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
          <div
            role="menu"
            className="absolute right-0 top-full z-20 mt-1 w-40 overflow-hidden rounded-md border border-border bg-popover py-1 shadow-lg"
          >
            {FORMATS.map((f) => (
              <button
                key={f.fmt}
                role="menuitem"
                onClick={() => download(f.fmt)}
                className="block w-full px-3 py-1.5 text-left text-xs text-popover-foreground transition-colors hover:bg-muted"
              >
                {f.label}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );
};
