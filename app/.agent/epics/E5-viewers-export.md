# Epic E5 — Viewers (image + output canvas) + CAD export

**Status:** Draft · **Depends on:** E4 · **Estimate:** L

## Problem
The center stage must show the right thing for the selected file: the raw image for an
`input/` file, and a structured, CAD-like canvas for an `output/` file — with the ability
to export to a CAD format.

## Solution
An `input` image viewer (pan/zoom) and an `output` Konva canvas that draws the image as
background with polygon layers per class (room/wall/door/window/railing), layer toggles,
and pan/zoom. An export menu produces DXF/SVG/JSON from the Document. Read-only first;
editing is a later milestone.

## User Stories
- As a user, clicking an `input/` file shows the original plan, zoomable.
- As a user, clicking an `output/` file shows detected rooms/walls as colored vector layers.
- As a user, I can toggle layers and export the result to CAD (DXF), SVG, or JSON.

## Scope
**In:** image viewer, Konva output canvas (image bg + polygon layers + toggles + pan/zoom),
export (DXF via `ezdxf`, SVG, JSON), center stage router by `activeFile`.
**Out:** editing geometry/labels (later P1), multi-floor stacked view (later).

## Technical Context
- Frontend: `features/viewer/`. Konva `Stage/Layer/Image/Line`; class colors mirror pipeline.
- Image URL: `http://localhost:8000/projects/{id}/input/{floorId}`.
- Output Document: `GET /projects/{id}/output/{floorId}`.
- Backend export: `ezdxf` (add to requirements when starting).

---

## Tasks

### Task E5.1 — Center stage router
**Type:** feature · **Priority:** P1 · **Estimate:** XS
**Do:** `CenterStage` reads `activeFile`; renders `ImageViewer` (input) / `OutputCanvas`
(output) / empty state.
**Files:** `frontend/src/features/viewer/components/CenterStage.tsx` → create.
**Acceptance:** switching files swaps the correct viewer.

### Task E5.2 — Image viewer (pan/zoom)
**Type:** feature · **Priority:** P1 · **Estimate:** S
**Do:** `ImageViewer` shows input image, wheel-zoom + drag-pan, fit-to-screen.
**Files:** `frontend/src/features/viewer/components/ImageViewer.tsx` → create.
**Acceptance:** large plan loads, zoom/pan smooth, fit button works.

### Task E5.3 — Output Konva canvas (layers + toggles)
**Type:** feature · **Priority:** P1 · **Estimate:** M
**Context:** The CAD-like view of the structured result.
**Do:** `OutputCanvas` (Konva): image background + one `Layer` per class with closed `Line`
polygons (class colors), legend + visibility toggles, pan/zoom; tooltip shows label/type/area on hover.
**Files:**
- `frontend/src/features/viewer/components/OutputCanvas.tsx` → create
- `frontend/src/features/viewer/components/LayerToggles.tsx` → create
- `frontend/src/features/viewer/hooks/useOutputDocument.ts` → create (query)
**Acceptance:** polygons align to image; toggles show/hide classes; hover shows room info.

### Task E5.4 — Backend: export DXF/SVG/JSON
**Type:** feature · **Priority:** P2 · **Estimate:** M
**Do:** `export.py`: Document → SVG (reuse `compare_m2f.render_svg` style), JSON (raw),
DXF (`ezdxf`: rooms as closed LWPOLYLINE on per-class layers, scaled by `px_per_m` if present).
`GET /projects/{id}/export/{floor_id}?fmt=` returns file.
**Files:**
- `app/backend/export.py` → create
- `app/backend/main.py` → modify (route)
- `app/backend/requirements.txt` → modify (uncomment `ezdxf`)
**Acceptance:** each format downloads; DXF opens in a CAD viewer with separated layers.

### Task E5.5 — Frontend: export menu
**Type:** feature · **Priority:** P2 · **Estimate:** XS
**Do:** export dropdown on the OutputCanvas toolbar → triggers download from backend.
**Files:** `frontend/src/features/viewer/components/ExportMenu.tsx` → create.
**Acceptance:** selecting a format downloads the file.

## Epic Acceptance Criteria
- [ ] Input files render in a pan/zoom image viewer
- [ ] Output files render on a Konva canvas with per-class layers + toggles
- [ ] Export to DXF, SVG, JSON works from the canvas
- [ ] Polygons align with the source image; no TS errors
