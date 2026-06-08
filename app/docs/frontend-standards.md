# Frontend Standards — Mappa

Gold standard: **`app/frontend/src/features/viewer/`**. Match the existing code.

## Feature structure

```
features/<name>/
├── api/          # HTTP calls (reuse the shared client)
├── components/   # rendering only
├── hooks/
│   ├── queries/  # React Query hooks + the query-key object
│   └── actions/  # controller hooks: store ↔ api ↔ React Query (optimistic updates)
├── services/     # PURE functions, no hooks/IO (e.g. snap.ts)
├── store/        # Zustand
├── types/        # TS interfaces
└── index.ts      # barrel: public API only
```

Create only the folders a feature needs (`analysis/`, `floorplans/` = api+hooks+components; `viewer/` = full set).

## Types

`features/projects/types/project.ts` owns the domain types (`Project`, `Floor`, `Element`, `Annotation`, `Adjacency`, `Link`) and **mirrors `app/backend/core/document.py` 1:1 in snake_case** (`area_m2`, `scale_px_per_m`, `from_floor`). No DTO mapping, no `mappers/` folder. Import from the barrel: `import type { Floor } from '@/features/projects'`.

## State

| What | Where | Tool |
|------|-------|------|
| Server data | `hooks/queries/` | React Query |
| Shared client state | `store/` | Zustand (`editorStore`, `workspaceStore`, `chatStore`) |
| Transient UI | component | `useState` |

- Query keys: an exported object per feature (`projectKeys = { all, detail(id) }`). A floor's Document is cached at `['output', projectId, floorId]` — use that exact key from mutations.
- One `QueryClient`, configured in `app/providers.tsx`. Don't create another.
- `editorStore` holds the working `Floor` + undo/redo (`snapshot/restore/commit/undo/redo`). History lives in the store, not components.

## Optimistic edits (the core interaction)

Mutate only through an action hook (`viewer/hooks/actions/`): snapshot the store → mutate → `onSuccess` swap in server truth + `qc.setQueryData(['output', …])` → `onError` restore the snapshot. Components never call `editApi` or store setters directly. Reference: `useApplyEdit.ts`, `useRevertEdits.ts`.

## API

Shared client `@/shared/api/client.ts` (`api.get/post/postForm`) unwraps the `{ data }` envelope and throws `ApiError` on `{ error }`. For `PATCH`/`DELETE`, add a feature-local `request` that reuses `BASE` + `ApiError` (see `viewer/api/edit.api.ts`). No second `BASE` or error class. Feature API files are plain function objects (`projectsApi`).

## Components & UI

- Named exports only; props interface above the component; logic in hooks, render in component; `useCallback` for handlers. Target ≤200 lines (max 300 → split).
- `react-konva` for the canvas only; everything else is Tailwind v4 + shadcn/ui (Radix) in `shared/components/ui/`. Icons: `lucide-react`. Toasts: `sonner`.
- No router: a single `AppShell` (3-pane grid) switches content via `workspaceStore`.

## Imports

Alias `@/*` → `./src/*`. Cross-feature: barrel only (`@/features/projects`). Within a feature: relative paths. Never import your own barrel.

## Naming

| Component | Hook | Service | Store | Types | Folder |
|-----------|------|---------|-------|-------|--------|
| `PascalCase.tsx` | `useCamelCase.ts` | `camelCase.ts` | `<name>Store.ts` | `camelCase.ts` | `kebab-case` |

## Never

- ❌ `mappers/` / camelCase renaming — types mirror backend snake_case
- ❌ `useEffect` for fetching — React Query
- ❌ `editApi` / store setters in components — use action hooks
- ❌ logic in components — `services/`
- ❌ `any`, default exports, a second `QueryClient`/`BASE`/error class, `react-router`, importing your own barrel

## Done gate

`cd app/frontend && bun run lint && bun run build` — zero errors.
