interface CanvasStatusBarProps {
  scalePxPerM: number | null | undefined;
  zoom: number;
}

export const CanvasStatusBar = ({ scalePxPerM, zoom }: CanvasStatusBarProps) => (
  <div className="absolute bottom-3 left-3 z-10 flex items-center gap-3 rounded-md border border-border bg-card/90 px-2.5 py-1 text-xs text-muted-foreground backdrop-blur">
    <span>
      Scale: {scalePxPerM ? `${scalePxPerM.toFixed(2)} px/m` : 'not set'}
    </span>
    <span className="h-3 w-px bg-border" />
    <span>Zoom: {(zoom * 100).toFixed(0)}%</span>
  </div>
);
