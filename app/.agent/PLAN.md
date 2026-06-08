# FloorPlan Studio — Plan

**Created:** 2026-05-29
**Status:** Draft (ready for review)
**Methodology:** `doit` / describe-new-feature (feature spec + INVEST task breakdown)

A desktop-feel web app on top of the existing **hybrid floor-plan pipeline**
(Mask2Former geometry, local CPU + Qwen3-VL semantics on Modal). Codex-like
3-pane workspace: **projects on the left, focused file in the center, chat/semantics
on the right**.

---

## Vision

Upload one or more floor-plan images into a **local project**, run the hybrid
pipeline (detectron2 → polygons, then Qwen → semantics) **sequentially per image**,
and explore the result in an editable, CAD-like canvas with a chat panel that shows
what the model understood. Everything saved **locally** for now (server later).

### Aesthetic direction (committed)
- **Tone:** industrial / utilitarian IDE — near-black surfaces, sharp single accent.
- **Type:** display `Space Grotesk`, body `Outfit` (no system fonts).
- **Depth:** layered panels, subtle grain/gradient on empty states, one delightful
  reveal on project open. Premium, not MVP.

---

## Architecture

```
┌── Sidebar ──┐┌────────── Center (focused) ──────────┐┌── Right (chat) ──┐
│ Projects    ││  input/<img>  -> image viewer        ││ Qwen semantics   │
│  ▸ proj A   ││  output/<f>   -> Konva canvas + CAD   ││ "what the model  │
│  ▸ proj B   ││               export                 ││  said" + chat    │
│ Explorer    ││                                      ││ (collapsible)    │
│  input/     ││                                      ││                  │
│  output/    ││                                      ││                  │
└─────────────┘└──────────────────────────────────────┘└──────────────────┘
        React 19 + Vite 8 + TS 6 + react-konva (bun)            │
                              │ REST                            │
                    FastAPI (pyenv 3.10.15)                     │
          geometry.py (detectron2/Mask2Former, local CPU)       │
          semantics.py (Qwen3-VL-8B via Modal web endpoint) ────┘
                    local project store (folders + project.json)
```

### On-disk project format (local persistence)
A project is a **folder**. `project.json` is the manifest (source of truth).
```
<PROJECTS_ROOT>/<project_slug>/
  project.json          # {id,name,type,created,floors:[...],links:[...]}
  input/                # uploaded floor-plan images (verbatim)
    <floor>.png
  output/               # created after analysis
    <floor_id>.json     # merged Document: geometry (polygons) + semantics
    <floor_id>.svg      # optional vectorization
```
`PROJECTS_ROOT` default: `~/FloorPlanStudio` (overridable). "Save location" in the
New Project dialog selects/creates the folder. Server mode later = swap the store.

### Backend API (evolves the current P0 backend)
| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | liveness (exists) |
| GET | `/projects` | list local projects (scan ROOT) |
| POST | `/projects` | create folder + manifest `{name,type}` |
| GET | `/projects/{id}` | load manifest |
| POST | `/projects/{id}/floors` | multipart upload -> copy to `input/`, update manifest |
| POST | `/projects/{id}/analyze` | sequential geometry+semantics -> write `output/` |
| GET | `/projects/{id}/input/{floor_id}` | serve input image |
| GET | `/projects/{id}/output/{floor_id}` | return merged Document JSON |
| GET | `/projects/{id}/export/{floor_id}?fmt=dxf\|svg\|json` | CAD export |

> The P0 in-memory `/analyze` + `/project` are replaced by the project-folder store.
> `geometry.analyze_image()` and the `document.py` models are reused as-is.

### Frontend structure (feature-based — see `.agent/rules/rules.md`)
```
frontend/src/
  app/                  # shell entry, providers (React Query), theme tokens
  features/
    workspace/          # E1: 3-pane layout, explorer, panels
    projects/           # E2: create/list/open, New Project + Type modals
    floor-plans/        # E3: Add Floor Plan dialog + upload
    analysis/           # E4: trigger + per-image status
    viewer/             # E5: image viewer, Konva output canvas, export
    chat/               # E6: semantics panel + chat
  shared/               # api client, ui primitives (shadcn), utils, types
```
Each feature owns: `api/ components/ hooks/{queries,actions}/ services/ store/ mappers/ types/ constants/ index.ts`
(only create the folders a feature actually needs). Public API via `index.ts` only.
- **Server state:** React Query (`hooks/queries/`); **client state:** Zustand (`store/`:
  `activeProjectId`, `activeFile`, panel state); **local:** `useState`.
- Mutations use the **action-hook + optimistic + rollback** pattern; **services are pure**.
- Named exports only, components ≤200 lines, no `any`, no `useEffect`-fetch.

### Stack (verified current/compatible)
React 19.2.6 · react-dom 19.2.6 · Vite 8.0.14 · TS 6.0.3 · react-konva 19.2.4 ·
konva 10.3.0 · **zustand · @tanstack/react-query** · **tailwindcss v4 + shadcn/ui (Radix)
· lucide-react · sonner** · bun 1.3.0.
Backend in pyenv 3.10.15 (torch 2.12, detectron2 0.6, cv2 4.10). Qwen on Modal ($17 credits).

### Coding standards (gold standard) — **read `.agent/rules/rules.md` before coding**
Distilled from the Venuora `floorplan` reference (`docs/RULES.md`, gold-standard `floor-plan`
feature) and adapted to a local single-user app. Enterprise machinery (auth tiers, DI
container, ORM/soft-delete, multi-tenant) is **deliberately excluded** — see rules §9.
Backend follows **Route → Service → Store** with a `{ data } / { error }` envelope and
Pydantic validation. **Done gate:** `bun run lint && bun run build` (frontend) +
`python3 -c "import main"` (backend) pass cleanly.

---

## Epics

| ID | Epic | Depends on | Est. |
|----|------|-----------|------|
| [E1](epics/E1-workspace-shell.md) | Workspace shell & navigation (Codex 3-pane) | — | M |
| [E2](epics/E2-project-lifecycle.md) | Project lifecycle (create/save local, list, open) | E1 | L |
| [E3](epics/E3-floorplan-upload.md) | Floor-plan upload (Add Floor Plan dialog + input/) | E2 | M |
| [E4](epics/E4-analysis-pipeline.md) | Analysis pipeline (sequential detectron + Qwen) | E3 | L |
| [E5](epics/E5-viewers-export.md) | Viewers (image + output canvas) + CAD export | E4 | L |
| [E6](epics/E6-chat-semantics.md) | Chat & semantics panel (right) | E4 | M |

Dependency chain: **E1 → E2 → E3 → E4 → {E5, E6}**.

---

## Milestones

- **M0 — Skeleton (today):** E1 shell + E2 New Project/Type modals + local create,
  E3 Add Floor Plan dialog writing to `input/`, explorer shows files, E5 image viewer
  + read-only output canvas (geometry only), E6 right panel placeholder. E4 analyze
  button runs **geometry only** (semantics stubbed). Goal: clickable end-to-end shell.
- **M1 — Real analysis:** E4 sequential geometry + Qwen (Modal endpoint), output/ written,
  per-image progress, semantics merged into Document.
- **M2 — Canvas + export:** E5 layers/toggles/pan-zoom polished, DXF/SVG/JSON export.
- **M3 — Chat:** E6 grounded Q&A; later prompt-edit (NL → command DSL → deterministic apply).

---

## Risks / notes
- **Qwen geometry is off** (Phase-1 finding): VLM never emits coordinates; geometry is
  detectron-only, semantics-only from Qwen. Edits (later) = NL → structured command → applied deterministically.
- **CPU geometry** ~seconds/image; sequential is fine for a few floors. Show progress.
- **Modal cold start** ~30–60s; budget the $17 credits (test on 1–3 plans).
- **Security:** local-only server (`127.0.0.1`), no auth — fine locally; add token before any remote exposure.
- **CubiCasa caveat:** F1/F2/F3 can be the same sheet (floors side-by-side) — relevant to multi-floor links.
```
