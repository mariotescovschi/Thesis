import { useMutation, useQueryClient } from '@tanstack/react-query';
import type { Floor } from '@/features/projects';
import { useEditorStore, type EditorSnapshot } from '../../store/editorStore';
import { editApi } from '../../api/edit.api';
import type { EditCommand } from '../../types/command';

// Optimistic flow: snapshot editor history -> mark dirty optimistically ->
// mutate -> onSuccess swap in server truth + invalidate output query ->
// onError rollback to the snapshot.
export const useApplyEdit = (projectId: string, floorId: string) => {
  const qc = useQueryClient();
  const snapshot = useEditorStore((s) => s.snapshot);
  const restore = useEditorStore((s) => s.restore);
  const setDirty = useEditorStore((s) => s.setDirty);
  const commit = useEditorStore((s) => s.commit);

  return useMutation<Floor, Error, EditCommand, { snap: EditorSnapshot }>({
    mutationFn: (command) => editApi.applyEdit(projectId, floorId, command),
    onMutate: () => {
      const snap = snapshot();
      setDirty(true);
      return { snap };
    },
    onSuccess: (floor) => {
      commit(floor);
      qc.setQueryData(['output', projectId, floorId], floor);
    },
    onError: (_err, _command, ctx) => {
      if (ctx) restore(ctx.snap);
    },
  });
};
