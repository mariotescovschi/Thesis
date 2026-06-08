import { useState } from 'react';
import { Plus } from 'lucide-react';
import type { Adjacency } from '@/features/projects';
import type { EditCommand } from '@/features/viewer';

interface AdjacencyEditorProps {
  adjacency: Adjacency[];
  roomNames: string[];
  onApply: (command: EditCommand) => void;
}

const selectCls =
  'flex-1 rounded-md border border-border bg-background px-2 py-1 text-xs text-foreground ' +
  'outline-none focus:border-primary';

/** Minimal add control for adjacencies. The graph visualization is separate. */
export const AdjacencyEditor = ({ adjacency, roomNames, onApply }: AdjacencyEditorProps) => {
  const [from, setFrom] = useState('');
  const [to, setTo] = useState('');

  const add = () => {
    if (from && to && from !== to) {
      onApply({ op: 'add_adjacency', from, to });
      setFrom('');
      setTo('');
    }
  };

  if (adjacency.length === 0 && roomNames.length === 0) {
    return <p className="text-muted-foreground">No relations.</p>;
  }

  return (
    <div className="flex items-center gap-1.5">
      <select className={selectCls} value={from} onChange={(e) => setFrom(e.target.value)}>
        <option value="">from…</option>
        {roomNames.map((n) => (
          <option key={n} value={n}>
            {n}
          </option>
        ))}
      </select>
      <select className={selectCls} value={to} onChange={(e) => setTo(e.target.value)}>
        <option value="">to…</option>
        {roomNames.map((n) => (
          <option key={n} value={n}>
            {n}
          </option>
        ))}
      </select>
      <button
        aria-label="Add adjacency"
        disabled={!from || !to || from === to}
        onClick={add}
        className="rounded-md border border-border p-1.5 text-muted-foreground transition-colors hover:text-foreground disabled:opacity-40"
      >
        <Plus className="size-3.5" />
      </button>
    </div>
  );
};
