from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.core.audit import audit
from app.core.config import settings
from app.db.session import get_db
from app.schemas.agent import AgentRequest, AgentResponse, DeterministicAgentRequest
from app.services.agent import run_ai_agent, run_deterministic_agent

router = APIRouter(prefix="/agent", tags=["financial-agent"])


def _audit_event(db: Session, request: Request, user_id: int):
    def emit(action: str, detail: dict):
        audit(db, request, action, user_id, detail)
    return emit


@router.post("/ask", response_model=AgentResponse)
def ask(payload: AgentRequest, request: Request, db: Session = Depends(get_db), user=Depends(current_user)):
    if not settings.agent_enabled:
        raise HTTPException(503, detail="Agente financeiro desabilitado")
    if not settings.ai_api_key or not settings.ai_model:
        raise HTTPException(503, detail="Agente de IA não configurado")
    try:
        event = _audit_event(db, request, user.id)
        event("agent.request", {"mode": "ai"})
        result = run_ai_agent(db, user.id, payload.question, event)
        event("agent.completed", {"tools_used": result["tools_used"], "provider": result["provider"]})
        db.commit()
        return result
    except RuntimeError as exc:
        db.rollback()
        audit(db, request, "agent.error", user.id, {"reason": str(exc)[:160]})
        db.commit()
        raise HTTPException(502, detail=str(exc))


@router.post("/ask/deterministic", response_model=AgentResponse)
def ask_deterministic(payload: DeterministicAgentRequest, request: Request, db: Session = Depends(get_db), user=Depends(current_user)):
    """Compatibilidade/testes: executa diretamente uma ferramenta allowlisted e auditável."""
    if not settings.agent_enabled:
        raise HTTPException(503, detail="Agente financeiro desabilitado")
    try:
        result = run_deterministic_agent(db, user.id, payload.question, payload.tool, payload.args)
        audit(db, request, "agent.deterministic", user.id, {"tool": result["tool"]})
        db.commit()
        result["tools_used"] = [result["tool"]]
        result["model"] = None
        return result
    except ValueError as exc:
        db.rollback()
        raise HTTPException(400, detail=str(exc))
