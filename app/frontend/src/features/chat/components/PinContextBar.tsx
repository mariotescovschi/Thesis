import { MapPin } from 'lucide-react';
import type { Annotation } from '@/features/projects';
import { cn } from '@/shared/lib/cn';

interface PinContextBarProps {
  pins: Annotation[];
  selected: string[];
  onToggle: (id: string) => void;
}

/** Toggleable chips for attaching floor pins as chat context (sent as pin_ids). */
export const PinContextBar = ({ pins, selected, onToggle }: PinContextBarProps) => {
  if (pins.length === 0) return null;
  return (
    <div className="flex flex-wrap items-center gap-1.5 px-3 pt-2">
      <span className="text-xs text-muted-foreground">Context:</span>
      {pins.map((p) => {
        const on = selected.includes(p.id);
        return (
          <button
            key={p.id}
            onClick={() => onToggle(p.id)}
            aria-pressed={on}
            className={cn(
              'flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs transition-colors',
              on
                ? 'border-primary bg-primary/15 text-primary'
                : 'border-border text-muted-foreground hover:text-foreground',
            )}
          >
            <MapPin className="size-3" />
            {p.name}
          </button>
        );
      })}
    </div>
  );
};
