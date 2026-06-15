import { AlertTriangle, X } from 'lucide-react';
import { useChatStore } from '../store/chatStore';

/**
 * Lists edit commands the backend could not apply, with the reason. Replaces the
 * old silent-drop so the user knows why a requested change did not appear.
 */
export const RejectedEdits = () => {
  const rejected = useChatStore((s) => s.rejected);
  const setRejected = useChatStore((s) => s.setRejected);

  if (rejected.length === 0) return null;

  return (
    <div className="m-3 rounded-lg border border-destructive/40 bg-destructive/5 p-3 text-sm">
      <div className="mb-2 flex items-center justify-between text-destructive">
        <div className="flex items-center gap-2">
          <AlertTriangle className="size-4" />
          <span className="font-medium">Rejected edits ({rejected.length})</span>
        </div>
        <button
          onClick={() => setRejected([])}
          aria-label="Dismiss rejected edits"
          className="text-muted-foreground transition-colors hover:text-foreground"
        >
          <X className="size-3.5" />
        </button>
      </div>
      <ul className="space-y-1 text-xs text-foreground">
        {rejected.map((r, i) => (
          <li key={i} className="break-words">
            • <span className="font-medium">{r.command.op ?? 'command'}</span>: {r.reason}
          </li>
        ))}
      </ul>
    </div>
  );
};
