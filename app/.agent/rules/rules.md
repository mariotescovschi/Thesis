# FloorPlan Studio — Coding Standards (Gold Standard)

Distilled from the Venuora `floorplan` reference (`docs/RULES.md`, `AGENTS.md`,
`floor-plan` feature) and adapted to THIS app: a **local, single-user** desktop-feel
tool (React 19 + Vite + TS + react-konva, FastAPI on pyenv 3.10.15). Senior-quality,
**nothing overcomplicated**.

> Reference implementation to imitate for structure: Venuora `frontend/src/features/floor-plan/`.

---

## 0. The "Done" Gate (non-negotiable)
A task is done only when these pass cleanly:
```bash
cd app/frontend && bun run lint && bun run build
cd app/backend  && python3 -c "import main"      # imports + app constructs
```
Write/adjust the relevant test when fixing a bug or adding logic.

---

## 1. Frontend Architecture — Feature-Based

Each feature is self-contained: `frontend/src/features/<feature>/`
```
api/          # HTTP calls only (fetch wrapper). No React here.
components/   # React components (grouped by sub-feature when it grows)
hooks/
  queries/    # React Query reads/mutations (useXxxQuery, useXxxMutation)
  actions/    # "controller" hooks that glue UI ↔ store ↔ services ↔ queries
services/     # PURE functions only (state in → new state out). No hooks, no I/O.
store/        # Zustand client state
mappers/      # API DTO ↔ domain model transforms (boundary)
types/        # TS types
constants/    # static config
index.ts      # barrel: export ONLY the public API
```

### State split (strict)
- **Server state** → React Query (`hooks/queries/`).
- **Client/UI state** → Zustand (`store/`).
- **Local state** → `useState`/`useReducer`.

### Action-hook + optimistic pattern (for editor mutations, E-later)
Component → action hook → read Zustand → **pure service** computes next state →
optimistic `set(next)` → React Query `mutate` → on success `invalidateQueries`; on
error **rollback** to snapshot. UI never calls services/queries/store mutations directly.

### Low coupling (hard rule)
If a component imports `fetch`/the API client/React Query directly, that's a bug —
move it into a hook. UI knows *how to render*, not *how to fetch*.

---

## 2. Components
- **≤200 lines** (flag >300 for decomposition). Logic lives in hooks.
- **Named exports only** — no default exports.
- Props `interface` directly above the component; destructure in the signature.
- Comments explain **why**, not **what**. Self-documenting code first.

```tsx
interface AddFloorPlanModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export const AddFloorPlanModal = ({ open, onOpenChange }: AddFloorPlanModalProps) => {
  const { rows, addFiles, submit, canSubmit } = useAddFloorPlans();
  return <Dialog open={open} onOpenChange={onOpenChange}>{/* UI only */}</Dialog>;
};
```

## 3. Naming
| Kind | Pattern | Example |
|------|---------|---------|
| Component | `PascalCase.tsx` | `OutputCanvas.tsx` |
| Hook | `useCamelCase.ts` | `useAnalyze.ts` |
| Service | `camelCaseService.ts` | `polygonService.ts` |
| Store | `camelCaseStore.ts` | `workspaceStore.ts` |
| Mapper | `camelCaseMapper.ts` | `documentMapper.ts` |
| Types/consts | `camelCase.ts` | `project.ts` |
| Folders | `kebab-case` | `floor-plans/` |

## 4. Imports & barrels
- `@/*` path alias (configured in `tsconfig`). No deep `../../../` chains across features.
- Import other features via their `index.ts` only. **Never** import from your own barrel inside the feature.

## 5. UI stack (proven, themed to our dark aesthetic)
- **Tailwind CSS v4** + **shadcn/ui** primitives (Radix) for chrome: `Dialog`, `Tooltip`,
  `DropdownMenu`, `ScrollArea`, `Resizable`, `Tabs`. Don't hand-roll these.
- **lucide-react** icons, **sonner** toasts (`useMutationHandler`-style wrapper for async + toast).
- **react-konva** for the canvas only (renders to `<canvas>`; Tailwind styles the surrounding UI).
- Distinctive theme via CSS variables + `Space Grotesk`/`Outfit` (no generic system fonts).

## 6. Don't (frontend)
- ❌ `useEffect` for data fetching → use React Query.
- ❌ `setState` business logic in components → use action hooks.
- ❌ business logic in components → services/hooks.
- ❌ `any` → real types; map DTOs via `mappers/`.
- ❌ importing the API client inside a component.

---

## 7. Backend Architecture — Route → Service → Store

FastAPI, pyenv 3.10.15. Light 3-layer (our "Store" = local project-folder access; no DB/ORM).
```
Request → Route (Pydantic validation) → Service (business logic) → Store (filesystem) → disk
```
- **Routes** (`main.py` / route modules): validate input (Pydantic models), call a service,
  shape the response. No business logic, no direct filesystem walking.
- **Services** (`*.py`, e.g. `analysis`, `merge`): orchestration + pure logic. Reusable, testable.
- **Store** (`store.py`): all project-folder reads/writes + manifest I/O. Only layer touching disk.
- Pure helpers (geometry polygonization, scale math) stay pure — no I/O.

### API conventions
- **Envelope:** success `{ "data": <T> }`; error `{ "error": { "message", "code" } }`
  via a single FastAPI exception handler. Routes never hand-build error JSON.
- **Error classes:** `NotFoundError`, `ValidationError`, `ConflictError` → mapped to 404/400/409.
- **Status codes:** 200 GET/PATCH, 201 POST-create, 202 async accepted (analysis), 400/404/409, 500 logged.
- **Endpoints** kebab-case plural (`/projects`, `/projects/{id}/floors`).
- **JSON fields:** `snake_case` (Python-native; pydantic models are the contract). Frontend
  `types/` mirror them exactly — no per-field renaming. (One language boundary, one convention.)
- Validate at the boundary with Pydantic; never read raw request bodies ad-hoc.
- Log errors with context (which project/floor) for traceability.

## 8. Don't (backend)
- ❌ business logic in routes.
- ❌ filesystem access outside `store.py`.
- ❌ returning bare errors/strings — raise an error class, let the handler format it.
- ❌ blocking the event loop on long CPU work without a status path (analysis writes
  per-floor status to the manifest so progress is observable).

---

## 9. Deliberately NOT doing (anti-overengineering)
This is a **local single-user thesis app**. The reference is a multi-tenant SaaS; we
intentionally **drop** its enterprise machinery — adopting it here would be "prost":
- ❌ Auth / Firebase / JWT / permission tiers / access grants (server is `127.0.0.1` only).
- ❌ DI container, factory-repo indirection — plain modules + functions are enough.
- ❌ ORM / Postgres / Drizzle / migrations / **soft delete** — the project folder + `project.json` is the store.
- ❌ Org/Team/Hotel hierarchy, billing, multi-user sync.
- ❌ Microservices / queues — sequential in-process analysis with status is fine for a few floors.
Keep abstractions only where they earn their place (the 3 layers, pure services, mappers).

## 10. Tooling (drop-in)
- **eslint flat config** (`@eslint/js` + `typescript-eslint` + `react-hooks` + `react-refresh`).
- **tsconfig** with `"paths": { "@/*": ["./src/*"] }`.
- **Prettier** defaults (2-space, single quotes, semicolons, trailing commas).
- **bun** for everything (`bun add`, `bun run`). Conventional commits (`feat:`, `fix:`, `refactor:`…).
- Do **not** push without explicit ask (commit freely).
