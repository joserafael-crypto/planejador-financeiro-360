from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models import User, Session as UserSession
from app.schemas.auth import RegisterIn, LoginIn, TokenOut, RefreshIn, MFAConfirmIn, MFAEnrollmentOut
from app.core.security import *
from app.core.audit import audit
from app.core.config import settings
from app.core.rate_limit import enforce_auth_rate_limit

router=APIRouter(prefix="/auth",tags=["auth"])

def _new_session(db,user,request):
    raw=new_refresh_token()
    session=UserSession(user_id=user.id,token_hash=hash_refresh_token(raw),expires_at=datetime.utcnow()+timedelta(days=settings.refresh_token_days),ip_address=request.client.host if request.client else None,user_agent=(request.headers.get("user-agent") or "")[:512])
    db.add(session); db.flush()
    return session,raw

def _tokens(db,user,request):
    session,refresh=_new_session(db,user,request)
    access=create_token(user.id,session.id)
    return {"access_token":access,"refresh_token":refresh,"token_type":"bearer","expires_in":settings.access_token_minutes*60}

@router.post("/register",response_model=TokenOut)
def register(x:RegisterIn,request:Request,db:Session=Depends(get_db)):
    enforce_auth_rate_limit(request)
    if db.query(User).filter(User.email==x.email.lower()).first(): raise HTTPException(409,"E-mail já cadastrado")
    u=User(name=x.name.strip(),email=x.email.lower(),password_hash=hash_password(x.password))
    db.add(u);db.flush(); result=_tokens(db,u,request); audit(db,request,"auth.register",u.id); db.commit(); return result

@router.post("/login",response_model=TokenOut)
def login(x:LoginIn,request:Request,db:Session=Depends(get_db)):
    enforce_auth_rate_limit(request)
    u=db.query(User).filter(User.email==x.email.lower()).first()
    if not u or not verify_password(x.password,u.password_hash):
        audit(db,request,"auth.login_failed",None,{"reason":"invalid_credentials"}); db.commit(); raise HTTPException(401,"Credenciais inválidas")
    if u.mfa_enabled and (not x.otp or not verify_otp(u.mfa_secret,x.otp)):
        audit(db,request,"auth.mfa_failed",u.id); db.commit(); raise HTTPException(401,"MFA obrigatório ou código inválido")
    result=_tokens(db,u,request); audit(db,request,"auth.login",u.id); db.commit(); return result

@router.post("/refresh",response_model=TokenOut)
def refresh(x:RefreshIn,request:Request,db:Session=Depends(get_db)):
    enforce_auth_rate_limit(request)
    session=db.query(UserSession).filter(UserSession.token_hash==hash_refresh_token(x.refresh_token)).first()
    if not session or session.revoked_at is not None or session.expires_at<=datetime.utcnow(): raise HTTPException(401,"Refresh token inválido, expirado ou revogado")
    user=db.get(User,session.user_id)
    if not user: raise HTTPException(401,"Usuário não encontrado")
    session.revoked_at=datetime.utcnow()
    result=_tokens(db,user,request); audit(db,request,"auth.refresh",user.id); db.commit(); return result

@router.post("/logout")
def logout(request:Request,session=Depends(__import__('app.api.deps',fromlist=['current_session']).current_session),db:Session=Depends(get_db)):
    session.revoked_at=datetime.utcnow(); audit(db,request,"auth.logout",session.user_id); db.commit(); return {"status":"ok"}

@router.post("/logout-all")
def logout_all(request:Request,session=Depends(__import__('app.api.deps',fromlist=['current_session']).current_session),db:Session=Depends(get_db)):
    now=datetime.utcnow(); db.query(UserSession).filter(UserSession.user_id==session.user_id,UserSession.revoked_at.is_(None)).update({"revoked_at":now},synchronize_session=False); audit(db,request,"auth.logout_all",session.user_id); db.commit(); return {"status":"ok"}

@router.get("/sessions")
def sessions(session=Depends(__import__('app.api.deps',fromlist=['current_session']).current_session),db:Session=Depends(get_db)):
    rows=db.query(UserSession).filter(UserSession.user_id==session.user_id).order_by(UserSession.created_at.desc()).all()
    return [{"id":s.id,"created_at":s.created_at,"expires_at":s.expires_at,"last_used_at":s.last_used_at,"revoked":s.revoked_at is not None,"current":s.id==session.id,"ip_address":s.ip_address} for s in rows]

@router.delete("/sessions/{session_id}")
def revoke_session(session_id:int,request:Request,session=Depends(__import__('app.api.deps',fromlist=['current_session']).current_session),db:Session=Depends(get_db)):
    target=db.query(UserSession).filter(UserSession.id==session_id,UserSession.user_id==session.user_id).first()
    if not target: raise HTTPException(404,"Sessão não encontrada")
    target.revoked_at=datetime.utcnow(); audit(db,request,"auth.session_revoked",session.user_id,{"session_id":session_id}); db.commit(); return {"status":"ok"}

@router.post("/mfa/enroll",response_model=MFAEnrollmentOut)
def mfa_enroll(user=Depends(__import__('app.api.deps',fromlist=['current_user']).current_user),db:Session=Depends(get_db)):
    secret=new_mfa_secret(); user.mfa_secret=secret; db.commit()
    uri=pyotp.TOTP(secret).provisioning_uri(name=user.email,issuer_name=settings.mfa_issuer)
    return {"secret":secret,"otpauth_uri":uri}

@router.post("/mfa/confirm")
def mfa_confirm(x:MFAConfirmIn,request:Request,user=Depends(__import__('app.api.deps',fromlist=['current_user']).current_user),db:Session=Depends(get_db)):
    if not user.mfa_secret or not verify_otp(user.mfa_secret,x.code): raise HTTPException(400,"Código MFA inválido")
    user.mfa_enabled=True; audit(db,request,"auth.mfa_enabled",user.id); db.commit(); return {"status":"enabled"}

@router.delete("/mfa")
def mfa_disable(x:MFAConfirmIn,request:Request,user=Depends(__import__('app.api.deps',fromlist=['current_user']).current_user),db:Session=Depends(get_db)):
    if not user.mfa_enabled or not verify_otp(user.mfa_secret,x.code): raise HTTPException(400,"Código MFA inválido")
    user.mfa_enabled=False; user.mfa_secret=None; audit(db,request,"auth.mfa_disabled",user.id); db.commit(); return {"status":"disabled"}
