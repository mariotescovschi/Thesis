# Repo Map — Mappa (`app/`)

> Single source of truth for *where things live*. Read this first for any task.
> Grounded in the actual tree; update it when the structure changes.

The app is internally named **Mappa** (`FastAPI(title="Mappa")`). It is the interactive
viewer/editor half of the thesis: upload a floor-plan image → AI pipeline
(Mask2Former geometry + Qwen3-VL semantics) → CAD-like canvas with a chat panel.
The training/benchmark code lives elsewhere in the repo (`training/`, `benchmarks/`,
`experiments/`) and is **out of scope** for app tasks.

## Stack (pinned)

| Layer    | Tech |
|----------|------|
| Frontend | React 19, Vite 8, TypeScript ~6, TanStack Query 5, Zustand 5, Tailwind v4, shadcn/ui (Radix), react-konva, lucide-react, sonner. Package manager: **bun**. |
| Backend  | FastAPI, uvicorn, Python 3.10 (pyenv), Pydantic v2, torch + detectron2/Mask2Former (geometry), httpx, ezdxf (DXF export). |
| AI        | Geometry: detectron2/Mask2Former (local CPU). Semantics: Qwen3-VL via Modal endpoint. Chat: Ollama local model. |

Single-user, local, no auth — see `.kiro/steering/product.md` for excluded concerns.

## Top-Level Layout

```
app/
├── frontend/            # Vite SPA (port 5173)
│   └── src/
│       ├── app/         # App.tsx (just <AppShell/>), providers.tsx, theme.css
│       ├── shared/      # api/client.ts, components/ui (shadcn), lib/cn.ts
│       └── features/    # feature modules (see table)
├── backend/             # FastAPI app (port 8000)
│   ├── main.py          # app, CORS, router mounting, exception handlers, /projects + /health
│   ├── routes/          # thin HTTP layer (APIRouter per concern)
│   ├── services/        # business logic + orchestration (NO filesystem I/O)
│   ├── core/            # domain: document (models), commands (edit vocab), errors
│   ├── helpers/         # PURE functions: geometry, scene-building (no I/O, no LLM)
│   ├── infra/           # all external I/O: store (filesystem), geometry/qwen/ollama clients
│   └── tests/           # pytest
└── docs/                # ← these agent docs
```

## Frontend Features (`frontend/src/features/`)

Gold standard: **`viewer/`** — study it before building any canvas/editor feature.

| Feature      | Owns | Description |
|--------------|------|-------------|
| `viewer/`    | api, components, hooks/{queries,actions}, services, store, types, constants, index.ts | **Gold standard.** Konva canvas, output Document rendering, edit tools (move/vertex/wall/split/calibrate/annotate), optimistic edits, undo/redo, export menu. |
| `projects/`  | api, components, hooks/{queries,actions}, types, index.ts | Project CRUD, the canonical domain types (`project.ts` mirrors backend `document.py`), React Query keys (`projectKeys`). |
| `chat/`      | api, components, hooks, store | Chat panel; sends a floor + message, renders the answer and **proposed** (unapplied) edit commands, adjacency editor, semantic summary. |
| `analysis/`  | api, hooks, components | Trigger pipeline analysis, per-floor status chip. |
| `floorplans/`| api, components, hooks | Upload floors (multipart), floor rows. |
| `workspace/` | components, store | `AppShell` (3-pane CSS grid), `Sidebar`, `Explorer`, `RightPanel`, `workspaceStore` (active project/file). |

There is **no router** — `App.tsx` renders a single `AppShell` with a CSS-grid
3-pane layout: `Sidebar | CenterStage | RightPanel`.

## Backend Layers (`backend/`)

Request flow: **Route → Service → Store**. Pure helpers and core models sit beside them.

| Dir / file | Layer | Responsibility |
|------------|-------|----------------|
| `main.py` | app | FastAPI app, CORS (vite `:5173`), `include_router` × 4, `@app.exception_handler`, inline `/health` + `/projects*` + `/analyze` + image/output GET. |
| `routes/routes_edit.py` | route | `PATCH/POST/DELETE` edit endpoints (apply/batch/revert/autoscale/adjacency). |
| `routes/routes_chat.py` | route | `POST .../chat` — hydrate floors, delegate to chat service, persist history. |
| `routes/routes_split.py` | route | `POST .../split` — multi-floor split. |
| `routes/routes_export.py` | route | `GET .../export` — DXF/SVG/JSON download. |
| `services/analysis.py` | service | Per-floor pipeline: geometry → semantics → merge → autoscale → adjacency; saves manifest after each floor for progress. |
| `services/editing.py` | service | **Pure** `apply(floor, command) -> new Floor` engine (dispatch table over the command vocab). |
| `services/chat.py` | service | Build scene text → Ollama → parse `{answer, commands}` → validate → **propose** (never applies). |
| `services/chat_building.py` | service | Building-level (multi-floor) chat scene. |
| `services/splitting.py` | service | Detect / apply multi-floor regions. |
| `services/export.py` | service | **Pure** `to_json` / `to_svg` / `to_dxf` (ezdxf). |
| `services/semantics.py` | service | Qwen3-VL semantics call wrapper. |
| `services/merge.py` | service | Merge geometry elements + semantics into a `Floor` Document (used by the pipeline). |
| `core/document.py` | core | Pydantic models: `Project`, `Floor`, `Element`, `Annotation`, `Link`, `ProjectSummary`, `new_id()`. |
| `core/commands.py` | core | `EditCommand` discriminated union (the edit vocabulary) + `EditCommandEnvelope`. |
| `core/errors.py` | core | `AppError`, `NotFoundError`, `ValidationError`, `ConflictError`. |
| `helpers/geom.py`, `editing_geom.py` | helper (pure) | Polygon area, centroid, union/split/wall buffering, rounding. |
| `helpers/scene.py`, `building_scene.py` | helper (pure) | Build the normalized 0..1000 scene text the LLM reasons over. |
| `helpers/adjacency.py`, `autoscale.py` | helper (pure) | Derive room adjacency; estimate `scale_px_per_m` from door/window widths. |
| `infra/store.py` | store | **Only** module that touches the filesystem. Manifest + base/overlay Documents. |
| `infra/geometry.py` | infra | detectron2/Mask2Former inference (heavy; imported lazily). |
| `infra/qwen_endpoint.py`, `ollama_client.py` | infra | External model endpoints. |

## Data Model (`core/document.py` ↔ frontend `projects/types/project.ts`)

```
Project                      # project.json manifest (the "database")
├── floors: Floor[]          # each Floor IS the editable "Document"
│   ├── elements: Element[]  # kind = room|wall|door|window|railing; polygon px; label/type/area_m2
│   ├── adjacency: {from,to}[]
│   └── annotations: Annotation[]   # named pins (x,y,name,note) — live in the overlay
├── links: Link[]            # cross-floor (e.g. vertical_circulation)
└── chat: {role,text}[]      # persisted conversation
```

Frontend types **mirror these exactly in snake_case** (`area_m2`, `scale_px_per_m`,
`from_floor`). There is **no mapper layer** — see `frontend-standards.md`.

### Storage model (per project folder, under `$FPS_ROOT` or `~/MappaProjects`)

```
<project-id>/
├── project.json                  # manifest: light floors (no polygons) + links + chat
├── input/<floor-id>.<ext>        # uploaded source images
└── output/
    ├── <floor-id>.json           # IMMUTABLE pipeline base (written by analysis)
    └── <floor-id>.edited.json    # editable OVERLAY (all user + chat edits land here)
```

`store.read_output` prefers the overlay and falls back to the base. Edits and
revert only ever touch the overlay; the pipeline base is never mutated.

## REST API (envelope: `{ data }` ok · `{ error: { message, code } }` fail)

| Method | Path | Body / Query | Returns |
|--------|------|--------------|---------|
| GET | `/health` | — | `{ ok }` |
| GET | `/projects` | — | `ProjectSummary[]` |
| POST | `/projects` | `{ name, type?, location? }` | `Project` (201) |
| GET | `/projects/{pid}` | — | `Project` |
| POST | `/projects/{pid}/floors` | multipart `files[]` + `meta` (JSON) | `Project` (201) |
| GET | `/projects/{pid}/input/{floor_id}` | — | image file |
| POST | `/projects/{pid}/analyze` | `?force` | `Project` |
| GET | `/projects/{pid}/output/{floor_id}` | — | `Floor` (overlay-preferred) |
| PATCH | `/projects/{pid}/output/{floor_id}` | `{ command }` | `Floor` |
| POST | `/projects/{pid}/output/{floor_id}/batch` | `{ commands[] }` | `Floor` (all-or-nothing) |
| DELETE | `/projects/{pid}/output/{floor_id}/edits` | — | `Floor` (base, overlay discarded) |
| POST | `/projects/{pid}/output/{floor_id}/autoscale` | — | `Floor` |
| POST | `/projects/{pid}/output/{floor_id}/adjacency/derive` | — | `Floor` |
| POST | `/projects/{pid}/chat` | `{ floor_id, message, pin_ids?, element_ids?, history? }` | `{ answer, proposed_commands }` |
| POST | `/projects/{pid}/floors/{floor_id}/split` | `{ manual_rects? }` | `Project` |
| GET | `/projects/{pid}/export/{floor_id}` | `?fmt=json\|svg\|dxf` | file download |

## Read Order for Agents

**Tier 1 — always read first (any task)**
- `app/docs/repo-map.md` (this file)
- `.kiro/steering/product.md` (scope + what is deliberately excluded)
- `app/backend/core/document.py` + `app/frontend/src/features/projects/types/project.ts` (the shared contract)

**Tier 2 — backend task**
- `app/docs/backend-standards.md`
- `app/backend/main.py` (mounting, envelope, exception handlers)
- `app/backend/infra/store.py` (the only I/O point; base/overlay model)
- `app/backend/core/commands.py` + `app/backend/services/editing.py` (edit vocab + pure engine — the gold standard for a route→service→store flow)

**Tier 3 — frontend task**
- `app/docs/frontend-standards.md`
- `app/frontend/src/shared/api/client.ts` (envelope unwrap + `ApiError`)
- `app/frontend/src/features/viewer/**` (gold standard: store, `hooks/actions/useApplyEdit.ts`, `api/edit.api.ts`)
- `app/frontend/src/features/projects/hooks/**` (React Query keys + query/mutation pattern)

**Tier 4 — full-stack feature**
- Read Tiers 1–3, then compare the new field/endpoint across `document.py` ↔ `project.ts` ↔ the route.

**Never read:** `frontend/node_modules`, `frontend/dist`, `backend/__pycache__`,
`backend/.pytest_cache`, `backend/projects/` & `backend/data/` (runtime data),
`venv/`, `vendor/`, `model/*.pth`, `_old/`.

## Build & Verify (the Done Gate)

```bash
cd app/frontend && bun run lint && bun run build   # eslint + (tsc -b && vite build)
cd app/backend  && python3 -c "import main"        # pyenv 3.10; must import cleanly
```

A task is complete only when the relevant command(s) pass with zero errors.

## Known Issues (verify before relying on the done gate)

The backend was reorganized into `routes/services/core/helpers/infra/` recently. The
application modules are fully migrated to package-qualified imports, so
`python3 -c "import main"` imports cleanly. **The test suite was not migrated** — these
two files still use the old flat imports and will fail `pytest` collection until fixed:
- `tests/test_editing.py` → `import commands as cmds`, `import editing`, `from document import …`, `from errors import …`
- `tests/test_export.py` → `import export`, `from document import …`

Fix: change them to the qualified form (`import core.commands as cmds`,
`import services.editing as editing`, `from core.document import …`,
`from core.errors import …`, `import services.export as export`). Noted here so the map
stays honest.
