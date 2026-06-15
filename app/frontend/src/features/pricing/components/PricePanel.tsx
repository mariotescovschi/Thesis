import { useRef, type FormEvent } from 'react';
import { TrendingUp, TrendingDown, Minus, HelpCircle } from 'lucide-react';
import { Input } from '@/shared/components/ui/input';
import { Button } from '@/shared/components/ui/button';
import { cn } from '@/shared/lib/cn';
import { usePriceEstimate } from '../hooks/queries/usePriceEstimate';
import { useSetFloorPrice } from '../hooks/actions/useSetFloorPrice';
import type { PriceEstimate, PriceVerdict } from '../types/pricing';

interface PricePanelProps {
  projectId: string;
  floorId: string;
}

const money = (value: number | null | undefined, currency: string): string => {
  if (value == null) return '—';
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

// Turn a feature key (e.g. "area_frac_kitchen") into a readable label.
const prettyFeature = (key: string): string =>
  key
    .replace(/^area_frac_/, 'area: ')
    .replace(/^building_/, 'type: ')
    .replace(/_/g, ' ');

const VERDICT: Record<PriceVerdict, { label: string; cls: string; Icon: typeof Minus }> = {
  overpriced: { label: 'Overpriced', cls: 'text-destructive', Icon: TrendingUp },
  underpriced: { label: 'Underpriced', cls: 'text-blue-400', Icon: TrendingDown },
  fair: { label: 'Fair price', cls: 'text-emerald-400', Icon: Minus },
  insufficient_data: { label: 'Not enough data', cls: 'text-muted-foreground', Icon: HelpCircle },
};

const VerdictBadge = ({ verdict, deltaPct }: { verdict: PriceVerdict; deltaPct?: number | null }) => {
  const { label, cls, Icon } = VERDICT[verdict];
  return (
    <span className={cn('inline-flex items-center gap-1 text-xs font-medium', cls)}>
      <Icon className="size-3.5" />
      {label}
      {deltaPct != null && verdict !== 'fair' && verdict !== 'insufficient_data' && (
        <span>({deltaPct > 0 ? '+' : ''}{deltaPct}% vs similar)</span>
      )}
    </span>
  );
};

const ContributionBars = ({ data }: { data: PriceEstimate }) => {
  const items = data.contributions ?? [];
  if (items.length === 0) return null;
  const max = Math.max(...items.map((c) => Math.abs(c.pct)), 1);
  return (
    <div className="space-y-1">
      <p className="text-xs text-muted-foreground">What drives the estimate</p>
      {items.map((c) => (
        <div key={c.feature} className="flex items-center gap-2 text-xs">
          <span className="w-28 shrink-0 truncate text-muted-foreground" title={prettyFeature(c.feature)}>
            {prettyFeature(c.feature)}
          </span>
          <div className="h-2 flex-1 rounded bg-muted">
            <div
              className={cn('h-2 rounded', c.pct >= 0 ? 'bg-primary' : 'bg-destructive')}
              style={{ width: `${(Math.abs(c.pct) / max) * 100}%` }}
            />
          </div>
          <span className="w-10 shrink-0 text-right tabular-nums">{c.pct}%</span>
        </div>
      ))}
    </div>
  );
};

const Comparables = ({ data }: { data: PriceEstimate }) => {
  const comps = data.comparables ?? [];
  if (comps.length === 0) return null;
  return (
    <div className="space-y-1">
      <p className="text-xs text-muted-foreground">Similar plans</p>
      <ul className="space-y-0.5 text-xs">
        {comps.map((c) => (
          <li key={`${c.project_id}/${c.floor_id}`} className="flex justify-between gap-2">
            <span className="truncate text-muted-foreground">
              {c.project_name} · {c.floor_name}
            </span>
            <span className="tabular-nums">{money(c.price, data.currency)}</span>
          </li>
        ))}
      </ul>
    </div>
  );
};

export const PricePanel = ({ projectId, floorId }: PricePanelProps) => {
  const { data, isLoading } = usePriceEstimate(projectId, floorId);
  const setPrice = useSetFloorPrice(projectId, floorId);
  const inputRef = useRef<HTMLInputElement>(null);

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    const raw = inputRef.current?.value.trim() ?? '';
    const value = raw === '' ? null : Number(raw);
    if (value != null && (Number.isNaN(value) || value < 0)) return;
    setPrice.mutate(value);
  };

  const currency = data?.currency ?? 'EUR';
  // Re-key the form so the uncontrolled input re-initialises when the server price
  // changes (after a save → refetch), without setState-in-effect.
  const formKey = data?.price != null ? String(data.price) : 'empty';

  return (
    <section className="space-y-2">
      <h3 className="font-display text-xs font-semibold uppercase tracking-wider text-muted-foreground">
        Price
      </h3>

      <form key={formKey} onSubmit={onSubmit} className="flex items-center gap-2">
        <Input
          ref={inputRef}
          type="number"
          min={0}
          defaultValue={data?.price != null ? data.price : ''}
          placeholder={`Asking price (${currency})`}
          className="h-8"
        />
        <Button type="submit" size="sm" variant="secondary" disabled={setPrice.isPending}>
          Save
        </Button>
      </form>

      {isLoading && <p className="text-xs text-muted-foreground">Estimating…</p>}

      {data && !data.available && (
        <p className="text-xs text-muted-foreground">{data.reason ?? 'No estimate yet.'}</p>
      )}

      {data && data.available && (
        <div className="space-y-3 rounded-lg border border-border bg-muted/30 p-3">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs text-muted-foreground">Estimated</p>
              <p className="text-lg font-semibold tabular-nums">{money(data.estimate, currency)}</p>
            </div>
            {data.verdict && <VerdictBadge verdict={data.verdict} deltaPct={data.delta_pct} />}
          </div>
          <ContributionBars data={data} />
          <Comparables data={data} />
          <p className="text-[11px] text-muted-foreground">
            Based on {data.sample_size} priced plan{data.sample_size === 1 ? '' : 's'}.
          </p>
        </div>
      )}
    </section>
  );
};
