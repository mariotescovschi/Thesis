# Epic E3 — Floor-Plan Upload ("Add Floor Plan" dialog → input/)

**Status:** Draft · **Depends on:** E2 · **Estimate:** M

## Problem
After creating a project, users must add one or more floor-plan images, name them, and
optionally describe them — then have them stored in the project's `input/` folder.

## Solution
An **Add Floor Plan** dialog (mirrors the reference screenshot): multi-file upload with
per-file thumbnail, required name, optional description, "Add more", remove, and a
"Create N Floor Plans" action that uploads to the backend, which copies them into `input/`.

## User Stories
- As a user, I upload several images at once and rename each before committing.
- As a user, I add a description per floor (optional).
- As a user, after confirming, the files appear under `input/` in the explorer.

## Scope
**In:** Add Floor Plan modal (thumbnails, name*, description, add more, remove, counter,
Create N), upload endpoint copying to `input/`, manifest update, explorer refresh.
**Out:** running analysis (E4), "attach capacity chart" (reference-only, not needed here).

## Technical Context
- Frontend: `features/floorplans/` (modal, upload hook). Object URLs for thumbnails.
- Backend: `POST /projects/{id}/floors` multipart (files + JSON sidecar of names/descriptions).
- Reuse `store.py` to write files + update `Floor` entries (`status="pending"`).

---

## Tasks

### Task E3.1 — Backend: upload floors to input/
**Type:** feature · **Priority:** P1 · **Estimate:** M
**Context:** Persist uploaded images verbatim and register them in the manifest.
**Do:** `POST /projects/{id}/floors` accepts `files[]` + `meta` (JSON: `[{name,description}]`);
copy each to `<root>/input/`, append `Floor{id,name,description,image:input path,status:"pending"}`
to manifest, save. Return updated project.
**Files:**
- `app/backend/main.py` → modify (endpoint)
- `app/backend/store.py` → modify (`add_floors(project, files, meta)`)
**Acceptance:** TestClient: upload 2 files → 200; `input/` has 2 images; manifest has 2 floors `pending`.

### Task E3.2 — Backend: serve input images
**Type:** feature · **Priority:** P1 · **Estimate:** XS
**Do:** `GET /projects/{id}/input/{floor_id}` returns the image (FileResponse).
**Files:** `app/backend/main.py` → modify.
**Acceptance:** returns 200 image/png for an uploaded floor; 404 otherwise.

### Task E3.3 — Frontend: upload API + hook
**Type:** feature · **Priority:** P1 · **Estimate:** S
**Do:** `uploadFloors(projectId, items)` building `FormData`; `useUploadFloors` mutation
(invalidates `useProject`).
**Files:**
- `frontend/src/features/floorplans/api/floorplans.api.ts` → create
- `frontend/src/features/floorplans/hooks/useUploadFloors.ts` → create
**Acceptance:** mutation posts multipart; project refetches with new floors.

### Task E3.4 — Add Floor Plan modal
**Type:** feature · **Priority:** P1 · **Estimate:** M
**Context:** Mirror the reference: header "Add Floor Plan", subtitle, "N floor plans"
counter, "Add more", per-row thumbnail + name* + description + remove, Cancel / "Create N".
**Do:** local list of `{file, previewUrl, name, description}`; file input (multiple);
validate every row has a name; submit via `useUploadFloors`; on success close + refresh explorer.
**Files:**
- `frontend/src/features/floorplans/components/AddFloorPlanModal.tsx` → create
- `frontend/src/features/floorplans/components/FloorPlanRow.tsx` → create
**Acceptance:** matches reference layout; "Create N" disabled until ≥1 row with a name;
revokes object URLs on close; files land in `input/`.

### Task E3.5 — Explorer reflects input/ files
**Type:** feature · **Priority:** P2 · **Estimate:** XS
**Do:** map `project.floors` into the Explorer `input/` folder; clicking a row sets
`activeFile={kind:'input',floorId}`.
**Files:** `frontend/src/features/workspace/components/Explorer.tsx` → modify.
**Acceptance:** uploaded floors appear under `input/`; selecting one focuses it (viewer in E5).

## Epic Acceptance Criteria
- [ ] Add Floor Plan dialog matches the reference (multi-upload, rename, description, add more, remove)
- [ ] Confirm creates `input/` files + manifest floors (`pending`)
- [ ] Explorer lists `input/` files and selection drives `activeFile`
- [ ] Object URLs revoked; no TS errors
