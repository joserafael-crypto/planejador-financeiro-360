import json
from fastapi import Request
from sqlalchemy.orm import Session
from app.models import AuditLog

def audit(db: Session, request: Request, action: str, user_id: int|None=None, detail: dict|None=None):
    db.add(AuditLog(
        user_id=user_id, action=action,
        detail=json.dumps(detail or {}, ensure_ascii=False, default=str),
        ip_address=request.client.host if request.client else None,
        user_agent=(request.headers.get("user-agent") or "")[:512],
    ))
