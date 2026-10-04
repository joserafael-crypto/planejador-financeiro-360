from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models import User, Account, Card, Invoice, Transaction, Recurring, InstallmentPlan, Installment, Transfer, Budget, Alert, Goal, Debt, Consent
from app.api.deps import current_user
from app.schemas.privacy import ConsentIn
from app.core.audit import audit
from app.core.config import settings

router=APIRouter(prefix="/privacy",tags=["privacy/LGPD"])

@router.get("/consents")
def list_consents(user=Depends(current_user),db:Session=Depends(get_db)):
    rows=db.query(Consent).filter(Consent.user_id==user.id).order_by(Consent.created_at.desc()).all()
    return [{"id":x.id,"purpose":x.purpose,"granted":x.granted,"version":x.version,"granted_at":x.granted_at,"revoked_at":x.revoked_at} for x in rows]

@router.post("/consents")
def set_consent(x:ConsentIn,request:Request,user=Depends(current_user),db:Session=Depends(get_db)):
    now=datetime.utcnow(); row=db.query(Consent).filter(Consent.user_id==user.id,Consent.purpose==x.purpose).order_by(Consent.created_at.desc()).first()
    if row and row.granted==x.granted and row.revoked_at is None: return {"status":"unchanged","id":row.id}
    row=Consent(user_id=user.id,purpose=x.purpose,granted=x.granted,version=settings.privacy_policy_version,granted_at=now if x.granted else None,revoked_at=None if x.granted else now)
    db.add(row); audit(db,request,"privacy.consent_updated",user.id,{"purpose":x.purpose,"granted":x.granted,"version":settings.privacy_policy_version}); db.commit(); return {"status":"ok","id":row.id}

@router.get("/export")
def export_data(user=Depends(current_user),db:Session=Depends(get_db)):
    def rows(model):
        return db.query(model).filter(model.user_id==user.id).all()
    def dump(items, fields): return [{f:getattr(x,f) for f in fields} for x in items]
    return {
      "privacy_policy_version":settings.privacy_policy_version,
      "user":{"id":user.id,"name":user.name,"email":user.email,"mfa_enabled":user.mfa_enabled,"created_at":user.created_at},
      "accounts":dump(rows(Account),["id","name","kind","balance","credit_limit","created_at"]),
      "cards":dump(rows(Card),["id","name","brand","last4","credit_limit","closing_day","due_day","active","created_at"]),
      "transactions":dump(rows(Transaction),["id","description","category","type","amount","occurred_at","status","created_at"]),
      "recurrings":dump(rows(Recurring),["id","description","category","amount","type","frequency","next_date","active"]),
      "budgets":dump(rows(Budget),["id","category","month","limit_amount","alert_percent"]),
      "goals":dump(rows(Goal),["id","name","target_amount","current_amount","target_date"]),
      "debts":dump(rows(Debt),["id","creditor","balance","monthly_payment","interest_rate"]),
      "consents":dump(rows(Consent),["id","purpose","granted","version","granted_at","revoked_at","created_at"]),
    }

@router.get("/profile")
def profile(user=Depends(current_user)):
    return {"id":user.id,"name":user.name,"email":user.email,"mfa_enabled":user.mfa_enabled,"created_at":user.created_at}

@router.patch("/profile")
def update_profile(name:str|None=None,email:str|None=None,request:Request=None,user=Depends(current_user),db:Session=Depends(get_db)):
    if name is not None:
        name=name.strip()
        if not name: raise HTTPException(400,"Nome inválido")
        user.name=name[:120]
    if email is not None:
        email=email.strip().lower()
        if not email or "@" not in email: raise HTTPException(400,"E-mail inválido")
        exists=db.query(User).filter(User.email==email,User.id!=user.id).first()
        if exists: raise HTTPException(409,"E-mail já cadastrado")
        user.email=email
    audit(db,request,"privacy.profile_updated",user.id); db.commit(); return profile(user)

@router.delete("/account")
def delete_account(request:Request,user=Depends(current_user),db:Session=Depends(get_db)):
    audit(db,request,"privacy.account_deletion_requested",user.id); db.delete(user); db.commit(); return {"status":"deleted"}
