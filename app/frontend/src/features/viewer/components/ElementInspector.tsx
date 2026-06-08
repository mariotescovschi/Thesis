import { useState } from 'react';
import { Trash2, X } from 'lucide-react';
import type { Element } from '@/features/projects';
import type { EditCommand } from '../types/command';
import { ConfirmDialog } from './ConfirmDialog';

interface ElementInspectorProps {
  element: Element;
  scaleKnown: boolean;
  scalePxPerM?: number | null;
  onApply: (command: EditCommand) => void;
  onClose: () => void;
}

const Field = ({ label, children }: { label: string; children: React.ReactNode }) => (
  <label className="flex flex-col gap-1 text-xs">
    <span className="text-muted-foreground">{label}</span>
    {children}
  </label>
);

const inputCls =
  'rounded-md border border-border bg-background px-2 py-1 text-sm text-foreground ' +
  'outline-none focus:border-primary';

export const ElementInspector = ({
  element,
  scaleKnown,
  scalePxPerM,
  onApply,
  onClose,
}: ElementInspectorProps) => {
  const [label, setLabel] = useState(element.label ?? '');
  const [type, setType] = useState(element.type ?? '');
  const [area, setArea] = useState(element.area_m2 != null ? String(element.area_m2) : '');
  const [confirmDelete, setConfirmDelete] = useState(false);

  const commitLabel = () => {
    const v = label.trim();
    if (v !== (element.label ?? '')) onApply({ op: 'set_label', element_id: element.id, label: v });
  };
  const commitType = () => {
    const v = type.trim();
    if (v !== (element.type ?? '')) onApply({ op: 'set_type', element_id: element.id, type: v });
  };
  const commitArea = () => {
    const n = parseFloat(area);
    if (!Number.isNaN(n) && n !== element.area_m2)
      onApply({ op: 'set_area_m2', element_id: element.id, area_m2: n });
  };

  const blurOnEnter = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') (e.target as HTMLInputElement).blur();
  };

  // Wall/door/window metric dimensions (length & thickness in meters)
  const isSegment = ['wall', 'door', 'window', 'railing'].includes(element.kind);
  const wallMetrics = (() => {
    if (!isSegment || !scalePxPerM || scalePxPerM <= 0) return null;
    const poly = element.polygon;
    if (poly.length < 2) return null;
    // Approximate: longest diagonal = length, use bbox short side for thickness
    let maxD = 0;
    for (let i = 0; i < poly.length; i++) {
      for (let j = i + 1; j < poly.length; j++) {
        const d = Math.hypot(poly[i][0] - poly[j][0], poly[i][1] - poly[j][1]);
        if (d > maxD) maxD = d;
      }
    }
    const lengthM = maxD / scalePxPerM;
    // Thickness: area / length (approximation from oriented rect)
    const area = Math.abs(poly.reduce((a, [x1, y1], i) => {
      const [x2, y2] = poly[(i + 1) % poly.length];
      return a + (x1 * y2 - x2 * y1);
    }, 0)) / 2;
    const thicknessM = maxD > 0 ? (area / maxD) / scalePxPerM : 0;
    return { length: lengthM, thickness: thicknessM };
  })();

  const friendlyName = element.label || element.type || element.kind;

  return (
    <>
      <div className="w-64 rounded-lg border border-border bg-card/95 p-3 shadow-lg backdrop-blur">
        <div className="mb-2 flex items-center justify-between">
          <span className="text-xs font-medium capitalize text-foreground">{element.kind}</span>
          <button
            onClick={onClose}
            aria-label="Close inspector"
            className="text-muted-foreground transition-colors hover:text-foreground"
          >
            <X className="size-4" />
          </button>
        </div>

        <div className="flex flex-col gap-2">
          <Field label="Label">
            <input
              className={inputCls}
              value={label}
              onChange={(e) => setLabel(e.target.value)}
              onBlur={commitLabel}
              onKeyDown={blurOnEnter}
              placeholder="e.g. Master bedroom"
            />
          </Field>
          <Field label="Type">
            <input
              className={inputCls}
              value={type}
              onChange={(e) => setType(e.target.value)}
              onBlur={commitType}
              onKeyDown={blurOnEnter}
              placeholder="e.g. bedroom"
            />
          </Field>
          <Field label={`Area (m²)${scaleKnown ? '' : ' · scale not set'}`}>
            <input
              className={inputCls}
              type="number"
              step="0.1"
              value={area}
              onChange={(e) => setArea(e.target.value)}
              onBlur={commitArea}
              onKeyDown={blurOnEnter}
              placeholder="0.0"
            />
          </Field>
          {wallMetrics && (
            <div className="flex gap-3 text-xs text-muted-foreground">
              <span>Length: {wallMetrics.length.toFixed(2)} m</span>
              <span>Thickness: {wallMetrics.thickness.toFixed(2)} m</span>
            </div>
          )}
          <button
            onClick={() => setConfirmDelete(true)}
            className="flex items-center justify-center gap-1.5 rounded-md border border-destructive/40 px-2 py-1 text-xs text-destructive transition-colors hover:bg-destructive/10"
          >
            <Trash2 className="size-3.5" />
            Delete
          </button>
        </div>
      </div>

      <ConfirmDialog
        open={confirmDelete}
        title={`Delete ${friendlyName}?`}
        description="This action cannot be undone."
        onConfirm={() => {
          onApply({ op: 'delete_element', element_id: element.id });
          setConfirmDelete(false);
          onClose();
        }}
        onCancel={() => setConfirmDelete(false)}
      />
    </>
  );
};
