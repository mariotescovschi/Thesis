import { useState, type FormEvent } from 'react';
import { Send, Plus, Box } from 'lucide-react';
import { Button } from '@/shared/components/ui/button';
import { Input } from '@/shared/components/ui/input';
import { useOutputDocument } from '@/features/viewer';
import { cn } from '@/shared/lib/cn';
import { PinContextBar } from './PinContextBar';
import { ProposedEdits } from './ProposedEdits';
import { RejectedEdits } from './RejectedEdits';
import { useChat } from '../hooks/useChat';
import { useChatStore } from '../store/chatStore';

interface ChatConversationProps {
  projectId: string;
  floorId: string;
}

/** The live conversation: transcript + proposed-edit Apply/Discard + pin context +
 *  composer. The transcript persists in the chat store across tab switches. */
export const ChatConversation = ({ projectId, floorId }: ChatConversationProps) => {
  const { data: doc } = useOutputDocument(projectId, floorId);
  const { messages, send, newChat, isPending, error } = useChat(projectId, floorId);
  const [text, setText] = useState('');
  const [pins, setPins] = useState<string[]>([]);
  const contextElementIds = useChatStore((s) => s.contextElementIds);
  const toggleContextElement = useChatStore((s) => s.toggleContextElement);

  const togglePin = (id: string) =>
    setPins((prev) => (prev.includes(id) ? prev.filter((p) => p !== id) : [...prev, id]));

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (!text.trim() || isPending) return;
    send(text, pins, contextElementIds);
    setText('');
  };

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between border-b border-border px-3 py-1.5">
        <span className="text-xs text-muted-foreground">
          {messages.length > 0 ? `${messages.length} messages` : 'New conversation'}
        </span>
        <Button
          variant="ghost"
          size="sm"
          className="h-7 gap-1 text-xs"
          onClick={newChat}
          disabled={messages.length === 0 && !isPending}
        >
          <Plus className="size-3.5" /> New chat
        </Button>
      </div>

      <div className="flex-1 space-y-3 overflow-y-auto p-4">
        {messages.length === 0 && (
          <p className="text-sm text-muted-foreground">
            Ask about this floor plan, or request an edit (e.g. “split the kitchen with a
            wall”). Proposed changes preview on the canvas before you apply them.
          </p>
        )}
        {messages.map((m, i) => (
          <div
            key={i}
            className={cn(
              'max-w-[85%] rounded-lg px-3 py-2 text-sm',
              m.role === 'user'
                ? 'ml-auto bg-primary/15 text-foreground'
                : 'bg-muted text-foreground',
            )}
          >
            {m.text}
          </div>
        ))}
        {isPending && <p className="text-xs text-muted-foreground">Thinking…</p>}
        {error && <p className="text-xs text-destructive">{error.message}</p>}
      </div>

      <div className="border-t border-border">
        <ProposedEdits projectId={projectId} floorId={floorId} />
        <RejectedEdits />
        <PinContextBar pins={doc?.annotations ?? []} selected={pins} onToggle={togglePin} />
        {contextElementIds.length > 0 && doc && (
          <div className="flex flex-wrap items-center gap-1.5 px-3 pt-1">
            <span className="text-xs text-muted-foreground">Elements:</span>
            {contextElementIds.map((id) => {
              const el = doc.elements.find((e) => e.id === id);
              const name = el?.label || el?.type || el?.kind || id;
              return (
                <button
                  key={id}
                  onClick={() => toggleContextElement(id)}
                  className="flex items-center gap-1 rounded-full border border-primary bg-primary/15 px-2 py-0.5 text-xs text-primary transition-colors"
                >
                  <Box className="size-3" />
                  {name}
                </button>
              );
            })}
          </div>
        )}
        <form onSubmit={onSubmit} className="flex items-center gap-2 p-3">
          <Input
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Ask about this floor plan…"
            disabled={isPending}
          />
          <Button
            type="submit"
            size="icon"
            variant="secondary"
            disabled={isPending}
            aria-label="Send"
          >
            <Send />
          </Button>
        </form>
      </div>
    </div>
  );
};
