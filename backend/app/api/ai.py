from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
import httpx
from app.api.deps import current_user
from app.db.session import get_db
from app.models import Transaction,Goal,Debt
from app.core.config import settings

router=APIRouter(prefix="/ai",tags=["ai"])
class AskIn(BaseModel): question:str

@router.post("/ask")
async def ask(x:AskIn,db:Session=Depends(get_db),u=Depends(current_user)):
    tx=db.query(Transaction).filter(Transaction.user_id==u.id).all()
    goals=db.query(Goal).filter(Goal.user_id==u.id).all()
    debts=db.query(Debt).filter(Debt.user_id==u.id).all()
    income=sum(float(t.amount) for t in tx if t.type=="income")
    expense=sum(float(t.amount) for t in tx if t.type=="expense")
    debt_monthly=sum(float(d.monthly_payment) for d in debts)
    context={"income":income,"expense":expense,"balance":income-expense,
             "debt_monthly":debt_monthly,"goals":[{"name":g.name,"target":float(g.target_amount),"current":float(g.current_amount)} for g in goals]}
    if not settings.ai_api_key or not settings.ai_base_url:
        return {"mode":"local","answer":f"Análise local: renda registrada {income:.2f}, despesas {expense:.2f}, saldo {income-expense:.2f} e parcelas mensais de dívidas {debt_monthly:.2f}. Considere esses compromissos e suas metas antes de assumir uma nova obrigação.","context":context}
    payload={"model":settings.ai_model,"messages":[{"role":"system","content":"Você é um planejador financeiro. Analise dados fornecidos, explicite incertezas e não execute operações financeiras."},{"role":"user","content":f"Dados: {context}\\nPergunta: {x.question}"}]}
    headers={"Authorization":f"Bearer {settings.ai_api_key}"}
    async with httpx.AsyncClient(timeout=30) as c:
        r=await c.post(settings.ai_base_url,json=payload,headers=headers);r.raise_for_status()
    data=r.json()
    return {"mode":"api","answer":data.get("choices",[{}])[0].get("message",{}).get("content",""),"context":context}
