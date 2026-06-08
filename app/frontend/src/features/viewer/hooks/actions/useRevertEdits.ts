import { useMutation, useQueryClient } from '@tanstack/react-query';
import type { Floor } from '@/features/projects';
import { useEditorStore, type EditorSnapshot } from '../../store/editorStore';
import { editApi } from '../../api/edit.api';

// Revert all overlay edits back to the pipeline base. Snapshot the editor
// history first so a failed revert restores the prior client state.
export const useRevertEdits = (projectId: string, floorId: string) => {
  const qc = useQueryClient();
  const snapshot = useEditorStore((s) => s.snapshot);
  const restore = useEditorStore((s) => s.restore);
  const reset = useEditorStore((s) => s.reset);
  const setDoc = useEditorStore((s) => s.setDoc);

  return useMutation<Floor, Error, void, { snap: EditorSnapshot }>({
    mutationFn: () => editApi.revertEdits(projectId, floorId),
    onMutate: () => {
      const snap = snapshot();
      return { snap };
    },
    onSuccess: (floor) => {
      reset();
      setDoc(floor);
      qc.setQueryData(['output', projectId, floorId], floor);
      qc.invalidateQueries({ queryKey: ['output', projectId, floorId] });
    },
    onError: (_err, _vars, ctx) => {
      if (ctx) restore(ctx.snap);
    },
  });
};
