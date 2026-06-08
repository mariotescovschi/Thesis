// Mirrors pipeline CLASSES order: ["room", "wall", "door", "window", "railing"].
export const CLASS_ORDER = ['room', 'wall', 'door', 'window', 'railing'] as const;

export const CLASS_COLORS: Record<string, string> = {
  room: '#f59e0b', // amber
  wall: '#60a5fa', // blue
  door: '#34d399', // green
  window: '#a78bfa', // violet
  railing: '#f472b6', // pink
};

export const colorFor = (kind: string) => CLASS_COLORS[kind] ?? '#9ca3af';
