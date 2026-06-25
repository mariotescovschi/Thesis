import { useState, type FormEvent } from 'react';
import { Search as SearchIcon } from 'lucide-react';
import { Input } from '@/shared/components/ui/input';
import { Button } from '@/shared/components/ui/button';
import { cn } from '@/shared/lib/cn';
import { useSearch } from '../hooks/useSearch';
import type { SearchResult } from '../types/search';

interface SearchViewProps {
  // Opening a result focuses that floor in the workspace (wired by AppShell to
  // avoid a search ↔ workspace import cycle).
  onOpenResult: (projectId: string, floorId: string) => void;
}

const money = (value: number | null, currency: string): string => {
  if (value == null) return 'No price';
  try {
    return new Intl.NumberFormat(undefined, {
      style: 'currency',
      currency,
      maximumFractionDigits: 0,
    }).format(value);
  } catch {
    return `${Math.round(value).toLocaleString()} ${currency}`;
  }
};

const ResultRow = ({ r, onOpen }: { r: SearchResult; onOpen: () => void }) => (
  <button
    onClick={onOpen}
    className={cn(
      'flex w-full items-start justify-between gap-3 rounded-lg border px-3 py-2.5 text-left transition-colors hover:bg-accent/60',
      r.match === 'exact'
        ? 'border-primary/40 bg-primary/5'
        : 'border-border bg-card/40',
    )}
  >
    <div className="min-w-0 flex-1">
      <div className="flex items-center gap-2">
        <p className="text-sm font-medium">
          {r.project_name} · {r.floor_name}
        </p>
        {r.match === 'exact' && (
          <span className="shrink-0 rounded-full bg-primary/15 px-1.5 py-0.5 text-[10px] font-medium text-primary">
            match
          </span>
        )}
      </div>
      {r.description && (
        <p className="mt-0.5 text-xs leading-relaxed text-muted-foreground">{r.description}</p>
      )}
    </div>
    <span className="shrink-0 pt-0.5 text-sm font-medium tabular-nums">{money(r.price, r.currency)}</span>
  </button>
);

export const SearchView = ({ onOpenResult }: SearchViewProps) => {
  const [query, setQuery] = useState('');
  const search = useSearch();
  const data = search.data;

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    const q = query.trim();
    if (!q || search.isPending) return;
    search.mutate(q);
  };

  const filterEntries = data ? Object.entries(data.filters) : [];

  return (
    <div className="mx-auto flex h-full w-full max-w-4xl flex-col gap-4 overflow-y-auto p-6">
      <div>
        <h2 className="font-display text-lg font-semibold">Search plans</h2>
        <p className="text-sm text-muted-foreground">
          Describe what you're looking for — e.g. “3-bedroom apartment under 200k, over 80 m²”.
        </p>
      </div>

      <form onSubmit={onSubmit} className="flex items-center gap-2">
        <Input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Natural-language query…"
          autoFocus
        />
        <Button type="submit" disabled={search.isPending}>
          <SearchIcon className="size-4" /> Search
        </Button>
      </form>

      {search.isPending && <p className="text-sm text-muted-foreground">Searching…</p>}
      {search.error && (
        <p className="text-sm text-destructive">{(search.error as Error).message}</p>
      )}

      {data && (
        <>
          {(filterEntries.length > 0 || (data.keywords?.length ?? 0) > 0) && (
            <div className="flex flex-wrap items-center gap-1.5">
              <span className="text-xs text-muted-foreground">Filters:</span>
              {filterEntries.map(([k, v]) => (
                <span key={k} className="rounded-full bg-primary/15 px-2 py-0.5 text-xs text-primary">
                  {k.replace(/_/g, ' ')}: {String(v)}
                </span>
              ))}
              {data.keywords?.map((kw) => (
                <span key={kw} className="rounded-full bg-emerald-500/15 px-2 py-0.5 text-xs text-emerald-400">
                  {kw}
                </span>
              ))}
              {!data.semantic && (
                <span className="text-xs text-muted-foreground">(filter-only — embeddings offline)</span>
              )}
            </div>
          )}

          {data.results.length === 0 ? (
            <p className="text-sm text-muted-foreground">No matching plans.</p>
          ) : (
            <ul className="space-y-2">
              {data.results.map((r) => (
                <li key={`${r.project_id}/${r.floor_id}`}>
                  <ResultRow r={r} onOpen={() => onOpenResult(r.project_id, r.floor_id)} />
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </div>
  );
};
