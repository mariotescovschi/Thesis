import { Circle, Line } from 'react-konva';
import type { Element } from '@/features/projects';
import type { EditCommand } from '../types/command';

const GHOST = '#fbbf24'; // amber: proposed, not yet applied
const CUT = '#f87171'; // red: removals / cuts

interface EditPreviewLayerProps {
  commands: EditCommand[];
  elements: Element[];
}

const flat = (poly: number[][]): number[] => poly.flatMap((p) => p);

/**
 * Non-destructive ghost rendering of chat-proposed commands. Resolves element ids
 * against the live document; commands with no geometric effect (label/type/scale…)
 * fall through silently. Must be mounted inside a Konva <Layer listening={false}>.
 */
export const EditPreviewLayer = ({ commands, elements }: EditPreviewLayerProps) => {
  const byId = new Map(elements.map((e) => [e.id, e]));

  return (
    <>
      {commands.map((cmd, i) => {
        switch (cmd.op) {
          case 'add_wall':
            return (
              <Line
                key={i}
                points={flat(cmd.segment)}
                stroke={GHOST}
                strokeWidth={(cmd.thickness ?? 6) + 2}
                opacity={0.6}
                lineCap="round"
                strokeScaleEnabled={false}
              />
            );
          case 'split_room':
            return (
              <Line
                key={i}
                points={flat(cmd.segment)}
                stroke={CUT}
                strokeWidth={2}
                dash={[8, 5]}
                strokeScaleEnabled={false}
              />
            );
          case 'move_element': {
            const el = byId.get(cmd.element_id);
            if (!el) return null;
            const poly = cmd.polygon ?? el.polygon;
            const dx = cmd.dx ?? 0;
            const dy = cmd.dy ?? 0;
            const pts = cmd.polygon ? flat(poly) : poly.flatMap(([x, y]) => [x + dx, y + dy]);
            return (
              <Line
                key={i}
                points={pts}
                closed
                stroke={GHOST}
                strokeWidth={2}
                dash={[8, 5]}
                fill={`${GHOST}22`}
                strokeScaleEnabled={false}
              />
            );
          }
          case 'delete_element': {
            const el = byId.get(cmd.element_id);
            if (!el) return null;
            return (
              <Line
                key={i}
                points={flat(el.polygon)}
                closed
                stroke={CUT}
                strokeWidth={2}
                fill={`${CUT}33`}
                strokeScaleEnabled={false}
              />
            );
          }
          case 'merge_rooms':
            return cmd.element_ids.map((id) => {
              const el = byId.get(id);
              return el ? (
                <Line
                  key={`${i}-${id}`}
                  points={flat(el.polygon)}
                  closed
                  stroke={GHOST}
                  strokeWidth={2}
                  fill={`${GHOST}22`}
                  strokeScaleEnabled={false}
                />
              ) : null;
            });
          case 'add_annotation':
            return (
              <Circle
                key={i}
                x={cmd.x}
                y={cmd.y}
                radius={6}
                fill={GHOST}
                opacity={0.7}
                strokeScaleEnabled={false}
              />
            );
          default:
            return null; // semantic-only ops have no canvas preview
        }
      })}
    </>
  );
};
