"""Mappa backend: Route -> Service -> Store, { data } / { error } envelope.

Run (from app/backend, in pyenv 3.10.15):
    uvicorn main:app --reload --port 8000
"""
import json
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

import infra.store as store
import services.analysis as analysis
from routes import routes_edit, routes_chat, routes_split, routes_export, routes_pricing, routes_search
from core.errors import AppError, ValidationError

app = FastAPI(title="Mappa")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes_edit.router)
app.include_router(routes_chat.router)
app.include_router(routes_split.router)
app.include_router(routes_export.router)
app.include_router(routes_pricing.router)
app.include_router(routes_search.router)


@app.on_event("startup")
def _reset_stale_running():
    """Reset floors stuck in 'running' from a previous crash back to 'pending'."""
    for d in store.projects_root().iterdir():
        manifest = d / "project.json"
        if not manifest.is_file():
            continue
        from core.document import Project as P
        proj = P.model_validate_json(manifest.read_text())
        dirty = False
        for f in proj.floors:
            if f.status == "running":
                f.status = "pending"
                dirty = True
        if dirty:
            store.save_manifest(proj)


@app.exception_handler(AppError)
async def _app_error(_: Request, exc: AppError):
    return JSONResponse(
        status_code=exc.status, content={"error": {"message": exc.message, "code": exc.code}}
    )


@app.exception_handler(RequestValidationError)
async def _validation_error(_: Request, exc: RequestValidationError):
    detail = exc.errors()
    msg = detail[0]["msg"] if detail else "Invalid request"
    return JSONResponse(
        status_code=400, content={"error": {"message": msg, "code": "validation_error"}}
    )


class CreateProjectBody(BaseModel):
    name: str
    type: str = "analysis"
    location: str | None = None


@app.get("/health")
def health():
    return {"data": {"ok": True}}


@app.get("/projects")
def list_projects():
    return {"data": [s.model_dump() for s in store.list_projects()]}


@app.post("/projects", status_code=201)
def create_project(body: CreateProjectBody):
    return {"data": store.create_project(body.name, body.type, body.location)}


@app.get("/projects/{pid}")
def get_project(pid: str):
    return {"data": store.load_project(pid)}


@app.post("/projects/{pid}/floors", status_code=201)
async def add_floors(
    pid: str, files: list[UploadFile] = File(...), meta: str = Form("[]")
):
    try:
        metas = json.loads(meta)
    except json.JSONDecodeError:
        raise ValidationError("meta must be valid JSON")
    if not isinstance(metas, list) or len(metas) != len(files):
        raise ValidationError("meta must be a list matching the number of files")
    items = []
    for f, m in zip(files, metas):
        name = (m.get("name") or "").strip() or (f.filename or "Floor")
        items.append(
            {
                "bytes": await f.read(),
                "orig": f.filename or "floor.png",
                "name": name,
                "description": m.get("description") or None,
            }
        )
    return {"data": store.add_floors(pid, items)}


@app.get("/projects/{pid}/input/{floor_id}")
def get_input_image(pid: str, floor_id: str):
    return FileResponse(store.input_path(pid, floor_id))


@app.post("/projects/{pid}/analyze")
def analyze_project(pid: str, force: bool = False):
    if force:
        proj = store.load_project(pid)
        for f in proj.floors:
            f.status = "pending"
        store.save_manifest(proj)
    return {"data": analysis.analyze_project(pid)}


@app.get("/projects/{pid}/output/{floor_id}")
def get_output(pid: str, floor_id: str):
    return {"data": store.read_output(pid, floor_id)}
