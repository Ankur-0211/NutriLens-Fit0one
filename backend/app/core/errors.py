import uuid
from typing import Any, Dict, Optional
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

class NutriLensException(HTTPException):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(status_code=status_code, detail=message)
        self.code = code
        self.message = message
        self.details = details or {}

def error_response(code: str, message: str, status_code: int = 400, details: Optional[Dict[str, Any]] = None, request_id: Optional[str] = None):
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "details": details or {},
                "request_id": request_id or f"req_{uuid.uuid4().hex[:12]}"
            }
        }
    )
