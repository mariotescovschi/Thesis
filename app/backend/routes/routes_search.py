"""Search route: natural-language query over the indexed plans.

POST /search with a free-text query. The search service extracts filters, embeds
the query and ranks the index. Local-only, no auth — consistent with the rest.
"""
from fastapi import APIRouter
from pydantic import BaseModel, Field

import services.search as search

router = APIRouter()


class SearchBody(BaseModel):
    query: str = ""
    top_k: int = Field(default=20, ge=1, le=100)


@router.post("/search")
def post_search(body: SearchBody) -> dict:
    """Return plans ranked for the query (filters + semantic score + price/verdict data)."""
    return {"data": search.search(body.query, body.top_k)}


@router.post("/rebuild-index")
def rebuild_index() -> dict:
    """Rebuild the search index from all output documents, re-embedding descriptions."""
    import infra.index_store as index_store
    import infra.embeddings as embeddings
    try:
        count = index_store.rebuild(embed=embeddings.embed)
    except Exception:  # noqa: BLE001 degrade to no-vector rebuild
        count = index_store.rebuild()
    return {"data": {"records": count}}
