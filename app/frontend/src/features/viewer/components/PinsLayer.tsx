import { Circle, Group, Text } from 'react-konva';
import type Konva from 'konva';
import type { Annotation } from '@/features/projects';
import type { EditCommand } from '../types/command';

const PIN = '#f472b6';

interface PinsLayerProps {
  annotations: Annotation[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  onApply: (command: EditCommand) => void;
}

/** Named pins (checkpoints). Draggable → update_annotation; click → select for editing. */
export const PinsLayer = ({ annotations, selectedId, onSelect, onApply }: PinsLayerProps) => (
  <>
    {annotations.map((a) => {
      const onDragEnd = (e: Konva.KonvaEventObject<DragEvent>) =>
        onApply({
          op: 'update_annotation',
          id: a.id,
          x: Math.round(e.target.x()),
          y: Math.round(e.target.y()),
        });
      return (
        <Group
          key={a.id}
          x={a.x}
          y={a.y}
          draggable
          onClick={() => onSelect(a.id)}
          onTap={() => onSelect(a.id)}
          onDragEnd={onDragEnd}
        >
          <Circle
            radius={6}
            fill={selectedId === a.id ? '#f8fafc' : PIN}
            stroke="#0a0a0a"
            strokeWidth={1}
            strokeScaleEnabled={false}
          />
          <Text
            text={a.name}
            x={9}
            y={-6}
            fontSize={12}
            fill="#f8fafc"
            listening={false}
          />
        </Group>
      );
    })}
  </>
);
