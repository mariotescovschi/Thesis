import { Loader2, Play } from 'lucide-react';
import { toast } from 'sonner';
import { useProject } from '@/features/projects';
import { Button } from '@/shared/components/ui/button';
import { useAnalyze } from '../hooks/useAnalyze';

export const AnalyzeButton = ({ projectId }: { projectId: string }) => {
  const { data: project } = useProject(projectId);
  const analyze = useAnalyze(projectId);
  const floors = project?.floors ?? [];
  const pending = floors.filter((f) => f.status === 'pending' || f.status === 'error').length;
  const running = analyze.isPending || floors.some((f) => f.status === 'running');

  return (
    <Button
      size="sm"
      variant="secondary"
      className="w-full"
      disabled={running || floors.length === 0}
      onClick={() =>
        analyze.mutate(pending === 0, {
          onSuccess: () => toast.success('Analysis complete'),
          onError: (err) => toast.error(err instanceof Error ? err.message : 'Analysis failed'),
        })
      }
    >
      {running ? (
        <>
          <Loader2 className="animate-spin" /> Analyzing…
        </>
      ) : pending > 0 ? (
        <>
          <Play /> Analyze ({pending})
        </>
      ) : (
        <>
          <Play /> Re-analyze
        </>
      )}
    </Button>
  );
};
