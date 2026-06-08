# Epic E6 — Chat & Semantics Panel (right)

**Status:** Draft · **Depends on:** E4 · **Estimate:** M

## Problem
When viewing an analyzed plan, the user wants to see — on the right — what the model
understood about the image, and (later) ask questions about it.

## Solution
A collapsible right panel that, when an `output/` file is open, shows Qwen's semantic
summary ("what the model said": building type, floor count, rooms with types/areas,
adjacencies, notes). A chat input is scaffolded now; grounded Q&A is wired in a later milestone.

## User Stories
- As a user, opening an output shows a readable summary of the model's understanding.
- As a user, I can collapse the panel to focus on the canvas.
- As a user (later), I can ask "how many bedrooms?" and get an answer grounded in the Document.

## Scope
**In:** right panel content, semantic summary view (from the Document), chat input scaffold
(disabled/placeholder until wired), collapse (E1 store).
**Out:** live Q&A inference, prompt-edit DSL (later milestones).

## Technical Context
- Frontend: `features/chat/`. Reads the same output Document query as E5.
- Panel mount point: `RightPanel` from E1.
- Later Q&A: backend `POST /projects/{id}/chat` (Document + question → Qwen/LLM); out of scope now.

---

## Tasks

### Task E6.1 — Semantic summary view
**Type:** feature · **Priority:** P1 · **Estimate:** S
**Context:** "when you open the output, on the right you're pasted what the model said."
**Do:** `SemanticSummary` renders from the output Document: building type, floor count,
room list (label · type · area_m2), adjacency count, notes. Empty state when no output open.
**Files:** `frontend/src/features/chat/components/SemanticSummary.tsx` → create.
**Acceptance:** opening an analyzed floor shows its semantics; switching floors updates it.

### Task E6.2 — Chat panel shell + input scaffold
**Type:** feature · **Priority:** P2 · **Estimate:** S
**Do:** `ChatPanel` = `SemanticSummary` (top) + message list (empty) + input box with send
(disabled, tooltip "coming soon"); mounts in `RightPanel`.
**Files:**
- `frontend/src/features/chat/components/ChatPanel.tsx` → create
- `frontend/src/features/workspace/components/RightPanel.tsx` → modify (mount ChatPanel)
**Acceptance:** panel shows summary + disabled composer; collapse via E1 toggle works.

### Task E6.3 — (Later) Grounded Q&A
**Type:** feature · **Priority:** P3 · **Estimate:** M · **Milestone:** M3
**Do:** backend `POST /projects/{id}/chat` (Document + question → Qwen) ; frontend enables
composer, streams/append answer; persist to manifest `chat[]`.
**Files:** `app/backend/main.py` (+chat) , `frontend/src/features/chat/hooks/useChat.ts`.
**Acceptance:** asking a question returns a Document-grounded answer; history persists.

## Epic Acceptance Criteria
- [ ] Right panel shows the model's semantic understanding for the open output
- [ ] Collapsible; empty state when nothing analyzed is open
- [ ] Chat composer scaffolded (Q&A enabled in M3)
