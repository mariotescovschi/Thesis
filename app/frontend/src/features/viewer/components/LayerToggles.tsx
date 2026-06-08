import { useState } from 'react';
import { ChevronDown, ChevronRight, Grid3x3, Image } from 'lucide-react';
import { CLASS_ORDER, colorFor } from '../constants';
import { cn } from '@/shared/lib/cn';

interface LayerTogglesProps {
  counts: Record<string, number>;
  hidden: Set<string>;
  onToggle: (cls: string) => void;
  gridVisible?: boolean;
  onToggleGrid?: () => void;
  imageVisible?: boolean;
  onToggleImage?: () => void;
}

export const LayerToggles = ({
  counts,
  hidden,
  onToggle,
  gridVisible,
  onToggleGrid,
  imageVisible = true,
  onToggleImage,
}: LayerTogglesProps) => {
  const [collapsed, setCollapsed] = useState(false);
  const classes = CLASS_ORDER.filter((c) => counts[c]);
  if (classes.length === 0 && !onToggleGrid) return null;

  return (
    <div className="flex flex-col gap-0.5 rounded-lg border border-border bg-card/90 p-2 backdrop-blur">
      <button
        onClick={() => setCollapsed((c) => !c)}
        className="flex items-center gap-1 text-xs font-medium text-muted-foreground transition-colors hover:text-foreground"
      >
        {collapsed ? <ChevronRight className="size-3" /> : <ChevronDown className="size-3" />}
        Legend
      </button>

      {!collapsed && (
        <>
          {classes.map((cls) => {
            const off = hidden.has(cls);
            return (
              <button
                key={cls}
                onClick={() => onToggle(cls)}
                className="flex items-center gap-2 rounded px-1.5 py-1 text-xs transition-colors hover:bg-accent"
              >
                <span
                  className="size-3 rounded-sm"
                  style={{ background: colorFor(cls), opacity: off ? 0.25 : 1 }}
                />
                <span className={cn('capitalize', off && 'text-muted-foreground line-through')}>
                  {cls}
                </span>
                <span className="ml-auto pl-2 text-muted-foreground">{counts[cls]}</span>
              </button>
            );
          })}

          <div className="mt-0.5 border-t border-border pt-1">
            {onToggleGrid && (
              <button
                onClick={onToggleGrid}
                className={cn(
                  'flex w-full items-center gap-2 rounded px-1.5 py-1 text-xs transition-colors hover:bg-accent',
                  !gridVisible && 'text-muted-foreground',
                )}
              >
                <Grid3x3 className="size-3" style={{ opacity: gridVisible ? 1 : 0.4 }} />
                <span className={cn(!gridVisible && 'line-through')}>Grid</span>
              </button>
            )}
            {onToggleImage && (
              <button
                onClick={onToggleImage}
                className={cn(
                  'flex w-full items-center gap-2 rounded px-1.5 py-1 text-xs transition-colors hover:bg-accent',
                  !imageVisible && 'text-muted-foreground',
                )}
              >
                <Image className="size-3" style={{ opacity: imageVisible ? 1 : 0.4 }} />
                <span className={cn(!imageVisible && 'line-through')}>Image</span>
              </button>
            )}
          </div>
        </>
      )}
    </div>
  );
};
