# Backend Standards — Mappa

Python 3.10 (pyenv), FastAPI, Pydantic v2. Gold-standard flow: **`core/commands.py` + `services/editing.py` + `routes/routes_edit.py`**.

## Route → Service → Store

| Layer | Lives in | Does | Never |
|-------|----------|------|-------|
| Route | `routes/`, `main.py` | Pydantic-validate, call service/store, return `{"data": …}` | logic, disk I/O |
| Service | `services/` | logic + orchestration; compose helpers; call infra | HTTP; raw filesystem |
| Store | `infra/store.py` | all project-folder + manifest + base/overlay I/O | HTTP, logic |
| Core | `core/` | models (`document.py`), edit vocab (`commands.py`), errors | I/O |
| Helpers | `helpers/` | pure geometry / scene / scale / adjacency | I/O, LLM, mutating inputs |
| Infra | `infra/` | filesystem store, detectron2, Qwen, Ollama | business decisions |

`helpers/` and the editing/export services are pure (same input → same output).

## Imports

Package-qualified, always: `from core.document import Floor`, `import infra.store as store`, `import services.editing as editing`, `from helpers.geom import poly_area_px`.

## Envelope & errors

- Success: every handler returns `{"data": <T>}` (file responses excepted). Errors: `{"error": {"message", "code"}}` from the single `AppError` handler in `main.py`.
- Raise error classes — never `HTTPException` or bare strings: `AppError` (500), `NotFoundError` (404), `ValidationError` (400), `ConflictError` (409). Add new subclasses in `core/errors.py`.
- Validate bodies with Pydantic at the boundary; never read the raw request body.
- Status: 200 GET/PATCH/DELETE, 201 create.

## Models (`core/document.py`)

`Floor` **is** the editable Document. `Project → floors[Floor] + links + chat`; `Floor → elements[Element] + adjacency + annotations` (+ `width/height/scale_px_per_m/status`); `Element → kind (room|wall|door|window|railing) + polygon (px) + label/type/area_m2`. snake_case; `new_id(prefix)` for ids. **Any change here mirrors to `frontend/src/features/projects/types/project.ts`.**

## Edits

`core/commands.py` is one discriminated union (`EditCommand`, `op` discriminator, 14 ops) used by both canvas and chat. The engine is pure:

```python
def apply(floor: Floor, command) -> Floor:
    result = floor.model_copy(deep=True)   # never mutate the input
    _DISPATCH[command.op](result, command)
    return result
```

The route reads overlay-preferred, applies, and writes the overlay only — the base stays immutable. Batch = all-or-nothing.

**Add an edit:** command class + `Literal` op + union entry in `commands.py` → pure `_handler` + `_DISPATCH` entry in `editing.py`. No route change.

## Store (`infra/store.py`)

The project folder + `project.json` is the database; only this module touches disk.

- Base (immutable): `write_output` / `read_base_output` → `output/<floor>.json`.
- Overlay (editable): `write_overlay` / `delete_overlay` / `has_overlay` → `output/<floor>.edited.json`.
- `read_output` is the read path (overlay else base). Edits write the overlay; revert deletes it; never write the base from an edit.
- Root: `$FPS_ROOT` (default `~/MappaProjects`).

## Services

- Receive plain args; call `store` for I/O and `helpers` for pure logic; raise error classes.
- Heavy imports are lazy: `import` torch/detectron2 inside the function (keeps `import main` light).
- Long work writes progress: `analyze_project` sets each floor's `status` and saves the manifest after every floor; a per-floor `except Exception` records `status="error"` and continues.
- Type-hint everything; functions ~≤40 lines.

## Naming

Route `routes_<concern>.py` · service/helper/infra `<concern>.py` · core `document.py` / `commands.py` / `errors.py`.

## Never

- ❌ logic in routes · ❌ filesystem outside `store.py` · ❌ mutating the input `Floor` (copy first) · ❌ writing the base from an edit · ❌ `HTTPException` / bare error strings · ❌ raw request body · ❌ top-level torch import · ❌ bare `except:` (the per-floor pipeline `except Exception` is the one exception) · ❌ bare imports (`from document import …`)

## Done gate

`cd app/backend && python3 -c "import main"` (run: `uvicorn main:app --reload --port 8000`; tests: `pytest`).
