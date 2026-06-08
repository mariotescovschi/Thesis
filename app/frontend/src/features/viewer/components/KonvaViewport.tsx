import { type ReactNode, useCallback, useEffect, useRef, useState } from 'react';
import { Stage } from 'react-konva';
import type Konva from 'konva';

interface KonvaViewportProps {
  contentWidth: number;
  contentHeight: number;
  children: ReactNode;
  overlay?: ReactNode;
  onCanvasClick?: (world: { x: number; y: number }, isBackground: boolean) => void;
  onCanvasMouseMove?: (world: { x: number; y: number }) => void;
  /** Called once with {fit, getZoom} so parent can wire recenter button / status bar. */
  onViewReady?: (api: { fit: () => void; getZoom: () => number }) => void;
  /** Called on every zoom/pan change with the current zoom level. */
  onViewChange?: (zoom: number) => void;
}

const MIN_SCALE = 0.05;
const MAX_SCALE = 24;

export const KonvaViewport = ({
  contentWidth,
  contentHeight,
  children,
  overlay,
  onCanvasClick,
  onCanvasMouseMove,
  onViewReady,
  onViewChange,
}: KonvaViewportProps) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const stageRef = useRef<Konva.Stage>(null);
  const [size, setSize] = useState({ w: 0, h: 0 });
  const [view, setView] = useState({ scale: 1, x: 0, y: 0 });

  const fitView = useCallback(
    (w: number, h: number) => {
      if (!w || !h || !contentWidth || !contentHeight) return null;
      const scale = Math.min(w / contentWidth, h / contentHeight) * 0.92;
      return { scale, x: (w - contentWidth * scale) / 2, y: (h - contentHeight * scale) / 2 };
    },
    [contentWidth, contentHeight],
  );

  const fitRef = useRef<() => void>(() => {});
  useEffect(() => {
    fitRef.current = () => {
      const fitted = fitView(size.w, size.h);
      if (fitted) {
        setView(fitted);
        onViewChange?.(fitted.scale);
      }
    };
  });

  // Expose API to parent once.
  const exposedRef = useRef(false);
  useEffect(() => {
    if (!exposedRef.current && onViewReady && size.w > 0) {
      exposedRef.current = true;
      onViewReady({ fit: () => fitRef.current(), getZoom: () => view.scale });
    }
  }, [onViewReady, size.w]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const ro = new ResizeObserver(() => {
      const w = el.clientWidth;
      const h = el.clientHeight;
      setSize({ w, h });
      const fitted = fitView(w, h);
      if (fitted) {
        setView(fitted);
        onViewChange?.(fitted.scale);
      }
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, [fitView, onViewChange]);

  const onWheel = (e: Konva.KonvaEventObject<WheelEvent>) => {
    e.evt.preventDefault();
    const stage = stageRef.current;
    const pointer = stage?.getPointerPosition();
    if (!pointer) return;
    const scaleBy = 1.06;
    const next = e.evt.deltaY > 0 ? view.scale / scaleBy : view.scale * scaleBy;
    const scale = Math.max(MIN_SCALE, Math.min(MAX_SCALE, next));
    const worldX = (pointer.x - view.x) / view.scale;
    const worldY = (pointer.y - view.y) / view.scale;
    const newView = { scale, x: pointer.x - worldX * scale, y: pointer.y - worldY * scale };
    setView(newView);
    onViewChange?.(scale);
  };

  const toWorld = (pointer: { x: number; y: number }) => ({
    x: (pointer.x - view.x) / view.scale,
    y: (pointer.y - view.y) / view.scale,
  });

  const onStageClick = (e: Konva.KonvaEventObject<MouseEvent | TouchEvent>) => {
    const stage = e.target.getStage();
    const pointer = stage?.getPointerPosition();
    if (!pointer) return;
    onCanvasClick?.(toWorld(pointer), e.target === stage);
  };

  const onStageMouseMove = (e: Konva.KonvaEventObject<MouseEvent>) => {
    if (!onCanvasMouseMove) return;
    const pointer = e.target.getStage()?.getPointerPosition();
    if (pointer) onCanvasMouseMove(toWorld(pointer));
  };

  return (
    <div ref={containerRef} className="relative h-full w-full overflow-hidden">
      <Stage
        ref={stageRef}
        width={size.w}
        height={size.h}
        scaleX={view.scale}
        scaleY={view.scale}
        x={view.x}
        y={view.y}
        draggable
        onWheel={onWheel}
        onClick={onStageClick}
        onTap={onStageClick}
        onMouseMove={onStageMouseMove}
        onDragEnd={(e) => {
          if (e.target !== stageRef.current) return;
          setView((v) => ({ ...v, x: e.target.x(), y: e.target.y() }));
        }}
      >
        {children}
      </Stage>
      {overlay}
    </div>
  );
};
