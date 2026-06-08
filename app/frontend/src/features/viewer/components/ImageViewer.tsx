import { Image as KonvaImage, Layer } from 'react-konva';
import { BASE } from '@/shared/api/client';
import { useImage } from '../hooks/useImage';
import { KonvaViewport } from './KonvaViewport';

const Centered = ({ children }: { children: string }) => (
  <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
    {children}
  </div>
);

export const ImageViewer = ({ projectId, floorId }: { projectId: string; floorId: string }) => {
  const [img, status] = useImage(`${BASE}/projects/${projectId}/input/${floorId}`);

  if (status === 'failed') return <Centered>Could not load image</Centered>;
  if (!img) return <Centered>Loading image…</Centered>;

  return (
    <KonvaViewport contentWidth={img.width} contentHeight={img.height}>
      <Layer>
        <KonvaImage image={img} />
      </Layer>
    </KonvaViewport>
  );
};
