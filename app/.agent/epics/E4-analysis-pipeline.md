# Epic E4 — Analysis Pipeline (sequential detectron + Qwen)

**Status:** Draft · **Depends on:** E3 · **Estimate:** L

## Problem
Uploaded floor plans must be turned into structured output: pixel-precise geometry
(detectron2/Mask2Former) plus semantics (Qwen3-VL). This must run **sequentially per
image** and write results into the project's `output/` folder.

## Solution
An analyze endpoint that, for each floor in order: runs local geometry → polygons
(reuse `geometry.analyze_image`), then calls Qwen on Modal for semantics, **merges** them
into one Document per floor, derives a metric scale from Qwen areas, and writes
`output/<floor_id>.json`. Per-image status surfaces in the UI.

## User Stories
- As a user, I press "Analyze" and watch each floor processed one by one.
- As a user, after analysis an `output/` folder appears with a result per floor.
- As a user, geometry and room semantics are combined in a single structured result.

## Scope
**In:** Modal Qwen web endpoint (from `compare_qwen.py`), `semantics.py`, merge logic,
scale derivation, `POST /projects/{id}/analyze` (sequential), status in manifest, output files.
**Out:** canvas rendering (E5), chat (E6), prompt-edit (later).
**M0 fallback:** analyze runs **geometry only** (semantics stubbed) so the shell works
before the Modal endpoint is deployed.

## Technical Context
- Reuse `geometry.analyze_image(path) -> (w,h,elements)`.
- Qwen: deploy `compare_qwen.py` logic as a Modal `@app.function` + `fastapi_endpoint`
  (`modal deploy`), returning the semantic JSON schema (rooms/types/areas/adjacency/floors).
- Merge: assign Qwen room labels/types/areas onto geometry `room` elements (by order/area
  heuristic for now); store unmatched semantics at floor level.
- Scale: `px_per_m` from median(room polygon area_px / Qwen area_m2).

---

## Tasks

### Task E4.1 — Modal: Qwen semantic web endpoint
**Type:** feature · **Priority:** P1 · **Estimate:** M
**Context:** Backend needs HTTP access to Qwen (today it's `modal run` batch).
**Do:** `app/backend/qwen_endpoint.py` — Modal app reusing the PROMPT + model load from
`compare_qwen.py`; `@modal.fastapi_endpoint(method="POST")` taking image bytes (base64/multipart),
returning parsed semantic JSON. `modal deploy`.
**Files:** `app/backend/qwen_endpoint.py` → create.
**Acceptance:** `modal deploy` prints a URL; POSTing one plan returns valid semantic JSON.
**Notes:** mind cold start + $17 credits; test on 1 image first.

### Task E4.2 — Backend: semantics client
**Type:** feature · **Priority:** P1 · **Estimate:** S
**Do:** `semantics.py`: `analyze_semantics(image_path) -> dict` calling the Modal endpoint
via `httpx` (URL from env `QWEN_ENDPOINT`); timeout + graceful failure → `{}`.
**Files:** `app/backend/semantics.py` → create.
**Acceptance:** returns parsed dict for a real plan; returns `{}` (not crash) on timeout/error.

### Task E4.3 — Backend: merge + scale into Document
**Type:** feature · **Priority:** P1 · **Estimate:** M
**Do:** `merge.py`: given geometry elements + semantic dict → fill `room` elements'
`label/type/area_m2`; compute `scale_px_per_m`; attach `adjacency`, floor-level `notes`,
`floor_count`. Return a `Floor` Document.
**Files:** `app/backend/merge.py` → create.
**Acceptance:** rooms get labels/types when counts align; `scale_px_per_m` computed; deterministic.

### Task E4.4 — Backend: sequential analyze endpoint
**Type:** feature · **Priority:** P1 · **Estimate:** M
**Context:** "detectron sequential; after each image, Qwen; output to the right."
**Do:** `POST /projects/{id}/analyze`: for each `pending` floor in order → geometry →
semantics (E4.2) → merge (E4.3) → write `output/<floor_id>.json`, set `status="done"`,
save manifest after each (so progress is observable). Return updated project.
**Files:** `app/backend/main.py` → modify; `app/backend/store.py` → modify (`write_output`).
**Acceptance:** TestClient on 1 CubiCasa image (geometry path real, semantics may be `{}` if
endpoint absent) → `output/<id>.json` written, floor `done`, elements present.

### Task E4.5 — Backend: read output Document
**Type:** feature · **Priority:** P2 · **Estimate:** XS
**Do:** `GET /projects/{id}/output/{floor_id}` → the merged Document JSON.
**Files:** `app/backend/main.py` → modify.
**Acceptance:** 200 + Document for analyzed floor; 404 if not yet analyzed.

### Task E4.6 — Frontend: analyze trigger + status
**Type:** feature · **Priority:** P1 · **Estimate:** S
**Do:** "Analyze" action (project toolbar); `useAnalyze` mutation; per-floor status chips
(pending/running/done) from manifest; on done, reveal `output/` in explorer.
**Files:**
- `frontend/src/features/analysis/api/analysis.api.ts` → create
- `frontend/src/features/analysis/hooks/useAnalyze.ts` → create
- `frontend/src/features/analysis/components/AnalyzeButton.tsx` → create
**Acceptance:** clicking Analyze runs backend; statuses update; `output/` files appear.

## Epic Acceptance Criteria
- [ ] Sequential geometry+semantics per floor; manifest status progresses
- [ ] `output/<floor_id>.json` written with merged geometry + semantics + scale
- [ ] Modal Qwen endpoint deployed and callable (M1); geometry-only fallback works (M0)
- [ ] Explorer reveals `output/` after analysis
