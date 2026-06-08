// Mirrors app/backend/commands.py exactly: the deterministic edit vocabulary.
// Discriminant is `op`; field names are snake_case to match the JSON contract.
// Coordinates are image pixels. Segments are [[x1, y1], [x2, y2]].

export type Point = number[]; // [x, y]
export type Segment = Point[]; // [[x1, y1], [x2, y2]]

// --- Semantic edits ---------------------------------------------------------
export interface SetLabel {
  op: 'set_label';
  element_id: string;
  label: string;
}

export interface SetType {
  op: 'set_type';
  element_id: string;
  type: string;
}

export interface SetAreaM2 {
  op: 'set_area_m2';
  element_id: string;
  area_m2: number;
}

export interface AddAdjacency {
  op: 'add_adjacency';
  from: string; // room label
  to: string;
}

export interface RemoveAdjacency {
  op: 'remove_adjacency';
  from: string;
  to: string;
}

// --- Geometry edits ---------------------------------------------------------
export interface DeleteElement {
  op: 'delete_element';
  element_id: string;
}

export interface MergeRooms {
  op: 'merge_rooms';
  element_ids: string[]; // >= 2; merged into the first id
}

export interface SplitRoom {
  op: 'split_room';
  element_id: string;
  segment: Segment; // cut line crossing the room polygon
}

export interface AddWall {
  op: 'add_wall';
  segment: Segment;
  thickness?: number; // px; buffered to a thin polygon (default 6.0)
}

export interface MoveElement {
  op: 'move_element';
  element_id: string;
  dx?: number; // translate by (dx, dy) ...
  dy?: number;
  polygon?: number[][] | null; // ... or replace polygon outright (vertex edit)
}

export interface SetScale {
  op: 'set_scale';
  scale_px_per_m: number; // = pixel_length / meters from calibration
}

// --- Annotations (pins) -----------------------------------------------------
export interface AddAnnotation {
  op: 'add_annotation';
  x: number;
  y: number;
  name: string;
  note?: string | null;
}

export interface UpdateAnnotation {
  op: 'update_annotation';
  id: string;
  name?: string | null;
  note?: string | null;
  x?: number | null;
  y?: number | null;
}

export interface DeleteAnnotation {
  op: 'delete_annotation';
  id: string;
}

export type EditCommand =
  | SetLabel
  | SetType
  | SetAreaM2
  | AddAdjacency
  | RemoveAdjacency
  | DeleteElement
  | MergeRooms
  | SplitRoom
  | AddWall
  | MoveElement
  | SetScale
  | AddAnnotation
  | UpdateAnnotation
  | DeleteAnnotation;

export type EditOp = EditCommand['op'];
