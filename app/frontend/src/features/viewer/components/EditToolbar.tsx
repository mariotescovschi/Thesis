import { MousePointer2, Move, Spline, Minus, Scissors, MapPin, Ruler, Maximize } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { cn } from '@/shared/lib/cn';
import { Tooltip, TooltipTrigger, TooltipContent } from '@/shared/components/ui/tooltip';
import { useEditorStore, type EditorTool } from '../store/editorStore';

interface ToolDef {
  tool: EditorTool;
  icon: LucideIcon;
  title: string;
}

const TOOLS: ToolDef[] = [
  { tool: 'select', icon: MousePointer2, title: 'Select (Esc)' },
  { tool: 'move', icon: Move, title: 'Drag element' },
  { tool: 'vertex', icon: Spline, title: 'Edit vertices' },
  { tool: 'wall', icon: Minus, title: 'Draw wall (2 clicks)' },
  { tool: 'split', icon: Scissors, title: 'Split room (2 clicks)' },
  { tool: 'annotate', icon: MapPin, title: 'Drop pin' },
  { tool: 'calibrate', icon: Ruler, title: 'Calibrate scale' },
];

interface EditToolbarProps {
  onRecenter?: () => void;
}

export const EditToolbar = ({ onRecenter }: EditToolbarProps) => {
  const tool = useEditorStore((s) => s.tool);
  const setTool = useEditorStore((s) => s.setTool);

  return (
    <div className="flex items-center gap-0.5 rounded-lg border border-border bg-card/90 p-1 backdrop-blur">
      {TOOLS.map(({ tool: t, icon: Icon, title }) => (
        <Tooltip key={t}>
          <TooltipTrigger asChild>
            <button
              aria-label={title}
              aria-pressed={tool === t}
              onClick={() => setTool(t)}
              className={cn(
                'rounded-md p-2 text-muted-foreground transition-colors hover:bg-accent hover:text-foreground',
                tool === t && 'bg-primary/15 text-primary',
              )}
            >
              <Icon className="size-4" />
            </button>
          </TooltipTrigger>
          <TooltipContent side="bottom">{title}</TooltipContent>
        </Tooltip>
      ))}
      {onRecenter && (
        <>
          <div className="mx-0.5 h-5 w-px bg-border" />
          <Tooltip>
            <TooltipTrigger asChild>
              <button
                aria-label="Fit to screen"
                onClick={onRecenter}
                className="rounded-md p-2 text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
              >
                <Maximize className="size-4" />
              </button>
            </TooltipTrigger>
            <TooltipContent side="bottom">Fit to screen</TooltipContent>
          </Tooltip>
        </>
      )}
    </div>
  );
};
