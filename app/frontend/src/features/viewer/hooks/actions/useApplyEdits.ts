import { useMutation, useQueryClient } from '@tanstack/react-query';
import type { Floor } from '@/features/projects';
import { useEditorStore, type EditorSnapshot } from '../../store/editorStore';
import { editApi } from '../../api/edit.api';
import type { EditCommand } from '../../types/command';

// Atomic apply of a command set (chat-proposed edits): the backend applies all or
// none, so a later failing command never leaves a half-edited document. Same
// optimistic snapshot/rollback shape as useApplyEdit.
export const useApplyEdits = (projectId: string, floorId: string) => {
  const qc = useQueryClient();
  const snapshot = useEditorStore((s) => s.snapshot);
  const restore = useEditorStore((s) => s.restore);
  const setDirty = useEditorStore((s) => s.setDirty);
  const commit = useEditorStore((s) => s.commit);

  return useMutation<Floor, Error, EditCommand[], { snap: EditorSnapshot }>({
    mutationFn: (commands) => editApi.applyEdits(projectId, floorId, commands),
    onMutate: () => {
      const snap = snapshot();
      setDirty(true);
      return { snap };
    },
    onSuccess: (floor) => {
      commit(floor);
      qc.setQueryData(['output', projectId, floorId], floor);
    },
    onError: (_err, _commands, ctx) => {
      if (ctx) restore(ctx.snap);
    },
  });
};
