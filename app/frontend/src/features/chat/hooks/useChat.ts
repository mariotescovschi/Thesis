import { useCallback } from 'react';
import { useMutation } from '@tanstack/react-query';
import { useEditorStore } from '@/features/viewer';
import { chatApi } from '../api/chat.api';
import { useChatStore } from '../store/chatStore';

/**
 * Session chat for a floor. The transcript lives in the chat store (survives tab
 * switches); the latest proposed (unapplied) edit commands are pushed into the
 * shared editor store so the canvas renders a ghost preview and the chat panel can
 * offer Apply/Discard (see EditPreviewLayer + ProposedEdits).
 */
export const useChat = (projectId: string, floorId: string) => {
  const messages = useChatStore((s) => s.messages);
  const pushTurn = useChatStore((s) => s.pushTurn);
  const resetChat = useChatStore((s) => s.newChat);
  const setPreview = useEditorStore((s) => s.setPreview);
  const clearPreview = useEditorStore((s) => s.clearPreview);

  const mutation = useMutation({
    mutationFn: (vars: { message: string; pinIds: string[]; elementIds: string[] }) =>
      chatApi.send(projectId, {
        floor_id: floorId,
        message: vars.message,
        pin_ids: vars.pinIds,
        element_ids: vars.elementIds,
        history: useChatStore.getState().messages,
      }),
    onSuccess: (res) => {
      pushTurn({ role: 'assistant', text: res.answer });
      setPreview(res.proposed_commands ?? []);
    },
  });

  const send = useCallback(
    (message: string, pinIds: string[], elementIds: string[] = []) => {
      const text = message.trim();
      if (!text || mutation.isPending) return;
      pushTurn({ role: 'user', text });
      mutation.mutate({ message: text, pinIds, elementIds });
    },
    [mutation, pushTurn],
  );

  const newChat = useCallback(() => {
    resetChat();
    clearPreview();
  }, [resetChat, clearPreview]);

  return {
    messages,
    send,
    newChat,
    isPending: mutation.isPending,
    error: mutation.error as Error | null,
  };
};
