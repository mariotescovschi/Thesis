import { useState } from 'react';
import { cn } from '@/shared/lib/cn';
import { SemanticSummary } from './SemanticSummary';
import { ChatConversation } from './ChatConversation';

type ActiveFile = { kind: 'input' | 'output'; floorId: string } | null;
type Tab = 'overview' | 'chat';

interface ChatPanelProps {
  projectId: string | null;
  activeFile: ActiveFile;
}

// Wrapper: hooks must run unconditionally, so the working view is a child that only
// mounts when an analyzed floor is open (projectId + output floorId both defined).
export const ChatPanel = ({ projectId, activeFile }: ChatPanelProps) => {
  const output = projectId && activeFile?.kind === 'output' ? activeFile : null;
  if (!projectId || !output) {
    return (
      <p className="p-4 text-sm text-muted-foreground">
        Open an analyzed floor (under <span className="text-foreground">output/</span>) to see
        what the model understood and to ask questions.
      </p>
    );
  }
  return <TabbedPanel projectId={projectId} floorId={output.floorId} />;
};

interface TabbedPanelProps {
  projectId: string;
  floorId: string;
}

const TABS: { id: Tab; label: string }[] = [
  { id: 'overview', label: 'Overview' },
  { id: 'chat', label: 'Chat' },
];

const TabbedPanel = ({ projectId, floorId }: TabbedPanelProps) => {
  const [tab, setTab] = useState<Tab>('overview');

  return (
    <div className="flex h-full flex-col">
      <div className="flex shrink-0 border-b border-border">
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => setTab(t.id)}
            className={cn(
              'flex-1 border-b-2 px-3 py-2 text-sm font-medium transition-colors',
              tab === t.id
                ? 'border-primary text-foreground'
                : 'border-transparent text-muted-foreground hover:text-foreground',
            )}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div className="min-h-0 flex-1">
        {tab === 'overview' ? (
          <div className="h-full overflow-y-auto">
            <SemanticSummary projectId={projectId} floorId={floorId} />
          </div>
        ) : (
          <ChatConversation projectId={projectId} floorId={floorId} />
        )}
      </div>
    </div>
  );
};
