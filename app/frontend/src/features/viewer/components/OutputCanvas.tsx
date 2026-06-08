import { useCallback, useEffect, useRef, useState } from 'react';
import { Circle, Image as KonvaImage, Layer, Line } from 'react-konva';
import type Konva from 'konva';
import { BASE } from '@/shared/api/client';
import type { Element } from '@/features/projects';
import { colorFor } from '../constants';
import { useImage } from '../hooks/useImage';
import { useOutputDocument } from '../hooks/useOutputDocument';
import { useApplyEdit } from '../hooks/actions/useApplyEdit';
import { useCanvasEditing } from '../hooks/useCanvasEditing';
import { useEditorStore } from '../store/editorStore';
import { useChatStore } from '@/features/chat/store/chatStore';
import type { EditCommand } from '../types/command';
import { KonvaViewport } from './KonvaViewport';
import { LayerToggles } from './LayerToggles';
import { EditToolbar } from './EditToolbar';
import { EditableElement } from './EditableElement';
import { ElementInspector } from './ElementInspector';
import { GridOverlay } from './GridOverlay';
import { PinsLayer } from './PinsLayer';
import { PinInspector } from './PinInspector';
import { CalibrateTool } from './CalibrateTool';
import { EditPreviewLayer } from './EditPreviewLayer';
import { ExportMenu } from './ExportMenu';
import { CanvasStatusBar } from './CanvasStatusBar';
import { ConfirmDialog } from './ConfirmDialog';

const Centered = ({ children }: { children: string }) => (
  <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
    {children}
  </div>
);

const describe = (el: Element) => {
  const parts = [el.kind];
  if (el.type) parts.push(el.type);
  if (el.label) parts.push(`(${el.label})`);
  if (el.area_m2) parts.push(`· ${el.area_m2.toFixed(2)} m²`);
  return parts.join(' ');
};

interface OutputCanvasProps {
  projectId: string;
  floorId: string;
}

export const OutputCanvas = ({ projectId, floorId }: OutputCanvasProps) => {
  const { data: doc, isLoading, isError } = useOutputDocument(projectId, floorId);
  const [img] = useImage(`${BASE}/projects/${projectId}/input/${floorId}`);
  const [hidden, setHidden] = useState<Set<string>>(new Set());
  const [hover, setHover] = useState<{ x: number; y: number; text: string } | null>(null);
  const [gridVisible, setGridVisible] = useState(true);
  const [imageVisible, setImageVisible] = useState(true);
  const [pinSelection, setPinSelection] = useState<string | null>(null);
  const [zoom, setZoom] = useState(1);
  const [deleteConfirm, setDeleteConfirm] = useState<{ type: 'element' | 'pin'; id: string; name: string } | null>(null);

  const fitFnRef = useRef<(() => void) | null>(null);

  const tool = useEditorStore((s) => s.tool);
  const selection = useEditorStore((s) => s.selection);
  const setSelection = useEditorStore((s) => s.setSelection);
  const setTool = useEditorStore((s) => s.setTool);
  const preview = useEditorStore((s) => s.preview);
  const clearPreview = useEditorStore((s) => s.clearPreview);
  const toggleContextElement = useChatStore((s) => s.toggleContextElement);
  const apply = useApplyEdit(projectId, floorId);
  const onApply = (command: EditCommand) => apply.mutate(command);
  const editing = useCanvasEditing(tool, selection, doc ?? null, onApply);

  useEffect(() => {
    setSelection(null);
    setTool('select');
    clearPreview();
  }, [floorId, setSelection, setTool, clearPreview]);

  // Keyboard: Escape deselects; Delete/Backspace triggers confirmation.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement).tagName;
      if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;

      if (e.key === 'Escape') {
        setSelection(null);
        setPinSelection(null);
      }
      if (e.key === 'Delete' || e.key === 'Backspace') {
        if (pinSelection && doc) {
          const pin = doc.annotations.find((a) => a.id === pinSelection);
          if (pin) setDeleteConfirm({ type: 'pin', id: pin.id, name: pin.name });
        } else if (selection && doc) {
          const el = doc.elements.find((e) => e.id === selection);
          if (el) setDeleteConfirm({ type: 'element', id: el.id, name: el.label || el.type || el.kind });
        }
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [setSelection, selection, pinSelection, doc]);

  const handleViewReady = useCallback((api: { fit: () => void }) => {
    fitFnRef.current = api.fit;
  }, []);

  if (isLoading) return <Centered>Loading output…</Centered>;
  if (isError || !doc) return <Centered>Could not load output</Centered>;

  const width = doc.width || img?.width || 1000;
  const height = doc.height || img?.height || 1000;
  const counts = doc.elements.reduce<Record<string, number>>((acc, el) => {
    acc[el.kind] = (acc[el.kind] ?? 0) + 1;
    return acc;
  }, {});
  const selected = doc.elements.find((el) => el.id === selection) ?? null;
  const selectedPin = doc.annotations.find((a) => a.id === pinSelection) ?? null;
  const drawing = tool === 'wall' || tool === 'split' || tool === 'calibrate';

  const toggle = (cls: string) =>
    setHidden((prev) => {
      const next = new Set(prev);
      if (next.has(cls)) next.delete(cls);
      else next.add(cls);
      return next;
    });

  const selectElement = (id: string, e?: Konva.KonvaEventObject<MouseEvent | TouchEvent>) => {
    const shiftKey = e && 'evt' in e && 'shiftKey' in e.evt && (e.evt as MouseEvent).shiftKey;
    if (shiftKey) {
      toggleContextElement(id);
      return;
    }
    setSelection(id);
    setPinSelection(null);
  };
  const selectPin = (id: string) => {
    setPinSelection(id);
    setSelection(null);
  };

  const handleCanvasClick = (world: { x: number; y: number }, isBackground: boolean) => {
    if (drawing) {
      editing.onCanvasClick(world);
      return;
    }
    if (tool === 'annotate') {
      onApply({
        op: 'add_annotation',
        x: Math.round(world.x),
        y: Math.round(world.y),
        name: `Pin ${doc.annotations.length + 1}`,
      });
      return;
    }
    if (isBackground) {
      setSelection(null);
      setPinSelection(null);
    }
  };

  const executeDelete = () => {
    if (!deleteConfirm) return;
    if (deleteConfirm.type === 'element') {
      onApply({ op: 'delete_element', element_id: deleteConfirm.id });
      setSelection(null);
    } else {
      onApply({ op: 'delete_annotation', id: deleteConfirm.id });
      setPinSelection(null);
    }
    setDeleteConfirm(null);
  };

  return (
    <>
      <KonvaViewport
        contentWidth={width}
        contentHeight={height}
        onCanvasClick={handleCanvasClick}
        onCanvasMouseMove={editing.onCanvasMouseMove}
        onViewReady={handleViewReady}
        onViewChange={setZoom}
        overlay={
          <>
            {/* Top-center: toolbar */}
            <div className="absolute left-1/2 top-3 z-10 -translate-x-1/2">
              <EditToolbar onRecenter={() => fitFnRef.current?.()} />
            </div>
            {/* Top-left: legend */}
            <div className="absolute left-3 top-3 z-10">
              <LayerToggles
                counts={counts}
                hidden={hidden}
                onToggle={toggle}
                gridVisible={gridVisible}
                onToggleGrid={() => setGridVisible((v) => !v)}
                imageVisible={imageVisible}
                onToggleImage={() => setImageVisible((v) => !v)}
              />
            </div>
            {/* Top-right: export */}
            <div className="absolute right-3 top-3 z-10">
              <ExportMenu projectId={projectId} floorId={floorId} />
            </div>
            {/* Bottom-left: status bar */}
            <CanvasStatusBar scalePxPerM={doc.scale_px_per_m} zoom={zoom} />
            {/* Hints */}
            {tool === 'split' && !selection && (
              <div className="absolute left-1/2 top-14 z-10 -translate-x-1/2 rounded-md border border-border bg-card/90 px-3 py-1 text-xs text-muted-foreground backdrop-blur">
                Select a room first, then draw the split line.
              </div>
            )}
            {tool === 'calibrate' && (
              <div className="absolute left-1/2 top-14 z-10 -translate-x-1/2">
                <CalibrateTool
                  pixelLength={editing.calibration?.pixelLength ?? null}
                  currentScale={doc.scale_px_per_m}
                  onConfirm={(meters) => {
                    const px = editing.calibration?.pixelLength;
                    if (px) onApply({ op: 'set_scale', scale_px_per_m: px / meters });
                    editing.clearCalibration();
                    setTool('select');
                  }}
                  onCancel={editing.clearCalibration}
                />
              </div>
            )}
            {/* Inspectors */}
            {selectedPin ? (
              <div className="absolute bottom-3 right-3 z-10">
                <PinInspector
                  key={selectedPin.id}
                  pin={selectedPin}
                  onApply={onApply}
                  onClose={() => setPinSelection(null)}
                />
              </div>
            ) : selected ? (
              <div className="absolute bottom-3 right-3 z-10">
                <ElementInspector
                  key={selected.id}
                  element={selected}
                  scaleKnown={doc.scale_px_per_m != null}
                  scalePxPerM={doc.scale_px_per_m}
                  onApply={onApply}
                  onClose={() => setSelection(null)}
                />
              </div>
            ) : null}
            {/* Hover tooltip */}
            {hover && (
              <div
                className="pointer-events-none absolute z-20 rounded-md border border-border bg-popover px-2 py-1 text-xs capitalize text-popover-foreground shadow-md"
                style={{ left: hover.x + 12, top: hover.y + 12 }}
              >
                {hover.text}
              </div>
            )}
          </>
        }
      >
        {/* Layer 1: Background (image + grid) */}
        <Layer listening={false}>
          {img && imageVisible && <KonvaImage image={img} opacity={0.45} />}
          {gridVisible && (
            <GridOverlay width={width} height={height} scalePxPerM={doc.scale_px_per_m} />
          )}
        </Layer>
        {/* Layer 2: Interactive content (elements + pins) */}
        <Layer>
          {doc.elements
            .filter((el) => !hidden.has(el.kind))
            .map((el) => (
              <EditableElement
                key={el.id}
                element={el}
                color={colorFor(el.kind)}
                selected={el.id === selection}
                tool={tool}
                hoverText={describe(el)}
                onSelect={(e) => selectElement(el.id, e)}
                onApply={onApply}
                onHover={setHover}
              />
            ))}
          <PinsLayer
            annotations={doc.annotations}
            selectedId={selectedPin?.id ?? null}
            onSelect={selectPin}
            onApply={onApply}
          />
        </Layer>
        {/* Layer 3: Overlays (editing guides + preview) */}
        <Layer listening={false}>
          {editing.previewPoints && (
            <Line points={editing.previewPoints} stroke="#f8fafc" strokeWidth={1.5} dash={[6, 4]} strokeScaleEnabled={false} />
          )}
          {editing.calibration && (
            <Line
              points={[
                editing.calibration.a.x,
                editing.calibration.a.y,
                editing.calibration.b.x,
                editing.calibration.b.y,
              ]}
              stroke="#22d3ee"
              strokeWidth={2}
              strokeScaleEnabled={false}
            />
          )}
          {editing.pending && (
            <Circle x={editing.pending.x} y={editing.pending.y} radius={4} fill="#f8fafc" strokeScaleEnabled={false} />
          )}
          {preview.length > 0 && (
            <EditPreviewLayer commands={preview} elements={doc.elements} />
          )}
        </Layer>
      </KonvaViewport>

      <ConfirmDialog
        open={deleteConfirm !== null}
        title={`Delete ${deleteConfirm?.name ?? ''}?`}
        description="This action cannot be undone."
        onConfirm={executeDelete}
        onCancel={() => setDeleteConfirm(null)}
      />
    </>
  );
};
