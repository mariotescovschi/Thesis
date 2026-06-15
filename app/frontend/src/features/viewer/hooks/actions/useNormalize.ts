import { useCallback } from 'react';
import { useMutation } from '@tanstack/react-query';
import { useEditorStore } from '../../store/editorStore';
import { normalizeApi } from '../../api/normalize.api';

/**
 * On-demand polygon regularization. Fetches proposed commands at a chosen level
 * (1 light .. 3 hard) and loads them into the shared editor preview (amber ghost)
 * so the user sees the effect before accepting. Accept/Discard reuse the existing
 * preview pipeline (useApplyEdits -> batch -> overlay; clearPreview) — the
 * immutable pipeline base is never touched.
 */
export const useNormalize = (projectId: string, floorId: string) => {
  const setPreview = useEditorStore((s) => s.setPreview);

  const mutation = useMutation({
    mutationFn: (level: number) => normalizeApi.preview(projectId, floorId, level),
    onSuccess: (res) => setPreview(res.commands),
  });

  const preview = useCallback((level: number) => mutation.mutate(level), [mutation]);

  return {
    preview,
    level: mutation.variables ?? null,
    proposed: mutation.isSuccess,
    count: mutation.data?.commands.length ?? 0,
    isPending: mutation.isPending,
    error: mutation.error as Error | null,
  };
};
