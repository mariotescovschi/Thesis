# Epic E1 — Workspace Shell & Navigation

**Status:** Draft · **Depends on:** — · **Estimate:** M (one focused session)

## Problem
There is no UI. We need a Codex-like desktop-feel shell so every later feature has a
home: projects on the left, the focused file in the center, chat/semantics on the right.

## Solution
A 3-pane application shell with a collapsible right panel, a left sidebar (projects +
per-project file explorer), and a center stage that swaps content by the active file.
Dark industrial IDE aesthetic, React Query + Zustand wired at the root.

## User Stories
- As a user, I see my projects in a left sidebar and can open one.
- As a user, when a project is open I see its `input/` and `output/` files in an explorer tree.
- As a user, I can collapse the right (chat) panel to focus on the canvas.

## Scope
**In:** app shell layout, sidebar, explorer tree, right panel collapse, theme tokens,
React Query provider, workspace Zustand store, empty states.
**Out:** actual project data wiring (E2), viewers (E5), chat content (E6).

## Technical Context
- New: `frontend/src/app/`, `frontend/src/features/workspace/`, `frontend/src/shared/`.
- Patterns: feature-based arch; named exports; components ≤200 lines; logic in hooks.
- Aesthetic: `Space Grotesk`/`Outfit`, CSS variables in `app/theme.css`.

---

## Tasks

### Task E1.1 — Scaffold frontend deps + providers + theme + tooling
**Type:** chore · **Priority:** P1 · **Estimate:** S
**Context:** Vite React-TS exists (confirm/create at `app/frontend`). Add libs, UI stack, tooling per `.agent/rules/rules.md`.
**Do:**
- `bun add zustand @tanstack/react-query lucide-react sonner clsx tailwind-merge`
- Tailwind v4 (`bun add -d tailwindcss @tailwindcss/vite`) + init shadcn/ui (Radix primitives added on demand).
- `app/providers.tsx` (QueryClientProvider + Toaster), `app/theme.css` (Tailwind import + CSS vars, `Space Grotesk`/`Outfit`), wire in `main.tsx`.
- Tooling: eslint flat config (`@eslint/js` + `typescript-eslint` + `react-hooks` + `react-refresh`); `tsconfig` `paths: {"@/*":["./src/*"]}`; Prettier defaults.
- `shared/api/client.ts` — typed fetch wrapper, `BASE=http://localhost:8000`, unwraps `{ data }` / throws on `{ error }`.
**Don't:** add routing libs (single-window app; state-driven panels). Don't hand-roll Dialog/Tooltip — use shadcn.
**Files:** `frontend/src/app/{providers.tsx,theme.css}`, `frontend/src/main.tsx`, `frontend/src/shared/api/client.ts`, `frontend/eslint.config.js`, `frontend/tsconfig*.json`.
**Acceptance:** `bun run dev` boots; `bun run lint && bun run build` pass; `@/` alias resolves; theme tokens applied.
**Dependencies:** Blocked by: confirm `app/frontend` exists.

### Task E1.2 — Workspace store (Zustand)
**Type:** feature · **Priority:** P1 · **Estimate:** S
**Context:** Single source for active selection + panel state.
**Do:** store `{activeProjectId, activeFile: {kind:'input'|'output', floorId}|null, rightPanelOpen, setters}`.
**Files:** `frontend/src/features/workspace/store/workspaceStore.ts` → create.
**Acceptance:** selectors/actions typed; toggling `rightPanelOpen` works in a test render.

### Task E1.3 — App shell layout (3-pane, resizable/collapsible)
**Type:** feature · **Priority:** P1 · **Estimate:** M
**Context:** The frame everything renders into.
**Do:** `AppShell` with grid: Sidebar | Center | RightPanel; right panel collapses via store;
min-widths; dark surfaces; subtle gradient on empty center.
**Files:**
- `frontend/src/features/workspace/components/AppShell.tsx` → create
- `frontend/src/features/workspace/components/RightPanel.tsx` → create (wraps E6 later)
- `frontend/src/App.tsx` → modify (render AppShell)
**Acceptance:** three panes; collapse toggle hides right panel; layout stable on resize.

### Task E1.4 — Sidebar (projects list region + actions)
**Type:** feature · **Priority:** P1 · **Estimate:** S
**Context:** Top-level nav like Codex (New project, Projects header, list, Settings footer).
**Do:** `Sidebar` with "New project" button (opens modal in E2), "Projects" section (list slot),
footer. Uses placeholder list until E2.
**Files:** `frontend/src/features/workspace/components/Sidebar.tsx` → create.
**Acceptance:** renders; "New project" fires a callback; active project highlighted.

### Task E1.5 — Explorer tree (input/ & output/)
**Type:** feature · **Priority:** P2 · **Estimate:** M
**Context:** When a project is active, show its files; clicking sets `activeFile`.
**Do:** `Explorer` renders two folders (`input`, `output`) with file rows; click → `setActiveFile`;
`output` shows "empty until analyzed" state.
**Files:**
- `frontend/src/features/workspace/components/Explorer.tsx` → create
- `frontend/src/features/workspace/components/FileRow.tsx` → create
**Acceptance:** clicking a file updates store + center reacts (placeholder ok); folders collapsible.

## Epic Acceptance Criteria
- [ ] 3-pane shell renders, right panel collapsible
- [ ] Sidebar + Explorer present with empty states
- [ ] Zustand store drives active selection + panel state
- [ ] React Query provider mounted; theme tokens applied; no TS errors
