from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from backend.app.core.database import get_db
from backend.app.modules.identity_resolution.resolver import FoodIdentityResolver
from backend.app.schemas.analysis import FoodIdentityResult

router = APIRouter(prefix="/food/identity", tags=["identity_resolution"])

class ResolveRequest(BaseModel):
    visual_class_id: str
    visual_score: float = 0.90
    visual_top_k: Optional[List[Dict[str, Any]]] = None
    identity_map_version: Optional[str] = "idmap-2026.01"

@router.post("/resolve", response_model=FoodIdentityResult)
def resolve_identity(payload: ResolveRequest, db: Session = Depends(get_db)):
    resolver = FoodIdentityResolver(db, identity_map_version=payload.identity_map_version or "idmap-2026.01")
    return resolver.resolve(
        visual_class_id=payload.visual_class_id,
        visual_score=payload.visual_score,
        visual_top_k=payload.visual_top_k,
    )
