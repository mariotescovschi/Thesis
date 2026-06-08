# Epic E2 — Project Lifecycle (create / save local / list / open)

**Status:** Draft · **Depends on:** E1 · **Estimate:** L

## Problem
Users need to create a project, choose where it's saved locally, pick its type, and
re-open it later. Today the backend only holds an in-memory `Project`.

## Solution
A local **project-folder store** in the backend (`project.json` manifest), plus a
two-step creation flow in the UI: **New Project** (name + save location) → **Project
Type** (Analysis only, for now). Sidebar lists projects from disk; opening loads the manifest.

## User Stories
- As a user, I click "New project", name it, and choose a local folder to save it.
- As a user, I pick the project type (Analysis) in a nice modal.
- As a user, I see all my local projects in the sidebar and can re-open them.

## Scope
**In:** backend project store + endpoints (`GET/POST /projects`, `GET /projects/{id}`),
New Project modal, Project Type modal, projects query/list, open → set active.
**Out:** floor upload (E3), analysis (E4). Server persistence (later).

## Technical Context
- New backend: `app/backend/store.py` (folder + manifest CRUD), evolve `main.py`.
- Reuse `document.py` `Project` (+ add `type`, `created`, per-floor `status`).
- Frontend: `features/projects/` (api, hooks/queries, components modals, store optional).
- Modals pattern: lightweight `shared/components/Modal.tsx`.

---

## Tasks

### Task E2.1 — Backend: local project store + manifest
**Type:** feature · **Priority:** P1 · **Estimate:** M
**Context:** Source of truth = a folder per project with `project.json`.
**Do:** `store.py`: `PROJECTS_ROOT` (env `FPS_ROOT`, default `~/FloorPlanStudio`);
`create_project(name,type,location?)` → slug folder + `input/` + manifest; `list_projects()`;
`load_project(id)`; `save_manifest(project)`. Extend `Project` with `type`, `created`, `root` (server-side only).
**Files:**
- `app/backend/store.py` → create
- `app/backend/document.py` → modify (add `type`, `created`; `Floor.status`, `description`)
**Acceptance:** unit check: create → folder + `input/` + valid `project.json`; list/load round-trip.
**Dependencies:** Blocks E2.2.

### Task E2.2 — Backend: project endpoints
**Type:** feature · **Priority:** P1 · **Estimate:** S
**Context:** Expose the store over REST; replace P0 in-memory `/analyze`+`/project`.
**Do:** `GET /projects`, `POST /projects {name,type,location?}`, `GET /projects/{id}`.
Keep `/health`. Remove/relocate old `/analyze` (moves to E4 as `/projects/{id}/analyze`).
**Files:** `app/backend/main.py` → modify.
**Acceptance:** `TestClient`: create → 200 + manifest; list contains it; load by id works; 404 on missing.

### Task E2.3 — Frontend: projects API + queries
**Type:** feature · **Priority:** P1 · **Estimate:** S
**Do:** `listProjects`, `createProject`, `getProject`; React Query `useProjects`,
`useProject(id)`, `useCreateProject` (invalidates list).
**Files:**
- `frontend/src/features/projects/api/projects.api.ts` → create
- `frontend/src/features/projects/hooks/queries/useProjects.ts` → create
- `frontend/src/features/projects/types/project.ts` → create (mirror backend models)
**Acceptance:** list renders from backend; create refetches.

### Task E2.4 — New Project modal (name + save location)
**Type:** feature · **Priority:** P1 · **Estimate:** M
**Context:** First step of creation; "save locally for now".
**Do:** modal with name input + location field (text path; default `~/FloorPlanStudio`,
prefilled, editable). Next → opens Project Type modal (E2.5) carrying the name/location.
**Files:**
- `frontend/src/shared/components/Modal.tsx` → create
- `frontend/src/features/projects/components/NewProjectModal.tsx` → create
**Acceptance:** validates non-empty name; "Next" advances; Esc/Cancel closes.
**Notes:** native folder picker isn't available from browser; use a text path now,
real picker when we move to a desktop/server shell.

### Task E2.5 — Project Type modal (Analysis only)
**Type:** feature · **Priority:** P1 · **Estimate:** S
**Context:** "nice pop-up to select the project type"; only Analysis for now.
**Do:** card grid of types; only **Analysis (semantic / sequential)** enabled, others
shown disabled/"coming soon". Confirm → `useCreateProject` → set active → open Add Floor Plan (E3).
**Files:** `frontend/src/features/projects/components/ProjectTypeModal.tsx` → create.
**Acceptance:** selecting Analysis + confirm creates project, sets it active, chains to E3.

### Task E2.6 — Wire sidebar list + open
**Type:** feature · **Priority:** P2 · **Estimate:** S
**Do:** feed `useProjects` into `Sidebar`; click → `setActiveProjectId` + load; highlight active.
**Files:** `frontend/src/features/workspace/components/Sidebar.tsx` → modify.
**Acceptance:** real projects listed; opening one loads manifest + explorer reflects it.

## Epic Acceptance Criteria
- [ ] Create flow: New Project → Type → project folder on disk with manifest
- [ ] Sidebar lists local projects; opening loads it
- [ ] Backend store round-trips manifests; endpoints covered by TestClient checks
- [ ] No TS errors; modals keyboard-accessible (Esc/Enter)
