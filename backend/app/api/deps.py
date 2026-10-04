from datetime import datetime, timezone
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.security import decode_token
from app.models import User, Session as UserSession

bearer=HTTPBearer(auto_error=False)

def current_session(request: Request, creds=Depends(bearer), db:Session=Depends(get_db)):
    if not creds: raise HTTPException(401,"Autenticação obrigatória")
    try:
        payload=decode_token(creds.credentials)
        uid=int(payload["sub"]); sid=int(payload["sid"])
    except Exception:
        raise HTTPException(401,"Token inválido ou expirado")
    session=db.get(UserSession,sid)
    if not session or session.user_id!=uid or session.revoked_at is not None or session.expires_at <= datetime.utcnow():
        raise HTTPException(401,"Sessão inválida ou revogada")
    session.last_used_at=datetime.utcnow()
    return session

def current_user(session=Depends(current_session), db:Session=Depends(get_db)):
    user=db.get(User,session.user_id)
    if not user: raise HTTPException(401,"Usuário não encontrado")
    return user
