import { Fragment } from 'react';
import { Circle, Line } from 'react-konva';
import type Konva from 'konva';
import type { Element } from '@/features/projects';
import type { EditCommand } from '../types/command';
import type { EditorTool } from '../store/editorStore';
import { snapToGrid } from '../services/snap';

const GRID = 10;

interface EditableElementProps {
  element: Element;
  color: string;
  selected: boolean;
  tool: EditorTool;
  hoverText: string;
  onSelect: (e: Konva.KonvaEventObject<MouseEvent | TouchEvent>) => void;
  onApply: (command: EditCommand) => void;
  onHover: (h: { x: number; y: number; text: string } | null) => void;
}

/**
 * A floor element rendered as a polygon. Interaction depends on the active tool:
 * `move` makes the whole shape draggable (→ move_element dx/dy); `vertex` exposes
 * draggable per-vertex handles (→ move_element polygon). In `wall`/`split` the shape
 * is non-listening so clicks fall through to the stage for drawing.
 */
export const EditableElement = ({
  element,
  color,
  selected,
  tool,
  hoverText,
  onSelect,
  onApply,
  onHover,
}: EditableElementProps) => {
  const listening = tool === 'select' || tool === 'move' || tool === 'vertex';
  const draggable = tool === 'move';

  const onDragEnd = (e: Konva.KonvaEventObject<DragEvent>) => {
    const node = e.target;
    const dx = Math.round(node.x());
    const dy = Math.round(node.y());
    node.position({ x: 0, y: 0 }); // server returns the new polygon; avoid double-offset
    if (dx !== 0 || dy !== 0)
      onApply({ op: 'move_element', element_id: element.id, dx, dy });
  };

  const onVertexDragEnd = (idx: number, e: Konva.KonvaEventObject<DragEvent>) => {
    const node = e.target;
    const nx = snapToGrid(node.x(), GRID);
    const ny = snapToGrid(node.y(), GRID);
    const polygon = element.polygon.map((pt, i) => (i === idx ? [nx, ny] : pt));
    onApply({ op: 'move_element', element_id: element.id, polygon });
  };

  return (
    <Fragment>
      <Line
        points={element.polygon.flat()}
        closed
        listening={listening}
        draggable={draggable}
        stroke={selected ? '#f8fafc' : color}
        strokeWidth={selected ? 3 : 1.5}
        strokeScaleEnabled={false}
        fill={`${color}${selected ? '4d' : '22'}`}
        onClick={onSelect}
        onTap={onSelect}
        onDragStart={onSelect}
        onDragEnd={onDragEnd}
        onMouseMove={(e: Konva.KonvaEventObject<MouseEvent>) =>
          onHover({ x: e.evt.offsetX, y: e.evt.offsetY, text: hoverText })
        }
        onMouseLeave={() => onHover(null)}
      />
      {selected &&
        tool === 'vertex' &&
        element.polygon.map(([x, y], idx) => (
          <Circle
            key={idx}
            x={x}
            y={y}
            radius={5}
            fill="#f8fafc"
            stroke={color}
            strokeWidth={1}
            strokeScaleEnabled={false}
            draggable
            onDragEnd={(e) => onVertexDragEnd(idx, e)}
          />
        ))}
    </Fragment>
  );
};
