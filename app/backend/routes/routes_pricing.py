"""Pricing routes: set asking prices (project / floor) and get a floor estimate.

Prices are manifest truth (like chat history), set via PATCH and then mirrored into
the derived index by the pricing service. The estimate is computed read-only over
the whole index (ridge + kNN). Local-only, no auth — consistent with the rest.
"""
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

import services.pricing as pricing

router = APIRouter()


class ProjectPriceBody(BaseModel):
    price: Optional[float] = Field(default=None, ge=0)
    currency: Optional[str] = None


class FloorPriceBody(BaseModel):
    price: Optional[float] = Field(default=None, ge=0)


@router.patch("/projects/{pid}/price")
def patch_project_price(pid: str, body: ProjectPriceBody) -> dict:
    """Set the project's total asking price / currency."""
    return {"data": pricing.set_project_price(pid, body.price, body.currency)}


@router.patch("/projects/{pid}/floors/{floor_id}/price")
def patch_floor_price(pid: str, floor_id: str, body: FloorPriceBody) -> dict:
    """Set a single floor's asking price."""
    return {"data": pricing.set_floor_price(pid, floor_id, body.price)}


@router.get("/projects/{pid}/floors/{floor_id}/price/estimate")
def get_price_estimate(pid: str, floor_id: str) -> dict:
    """Estimated price + contributions + comparables + verdict for a floor."""
    return {"data": pricing.estimate_floor(pid, floor_id)}
