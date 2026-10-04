from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.modules.corrections.service import CorrectionService
from backend.app.schemas.correction import CorrectionRequest, CorrectionResponse

router = APIRouter(prefix="/food", tags=["corrections"])

@router.post("/correct", response_model=CorrectionResponse, status_code=status.HTTP_201_CREATED)
def submit_corrections(
    payload: CorrectionRequest,
    db: Session = Depends(get_db),
):
    service = CorrectionService(db)
    return service.apply_corrections(payload)
