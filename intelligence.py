
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from collections import defaultdict
from dateutil.relativedelta import relativedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.models import User, Account, Transaction, Recurring, Invoice, Budget, Goal, Debt, Alert
from app.schemas.finance import SimulationIn

router = APIRouter(prefix="/api/intelligence", tags=["intelligence"])

def month_start(d): return d.replace(day=1)
def next_month(d): return d.replace(day=1) + relativedelta(months=1)

def money(v):
    return float(Decimal(str(v or 0)).quantize(Decimal("0.01")))

def posted_transactions(db, uid):
    return db.scalars(select(Transaction).where(
        Transaction.user_id == uid, Transaction.status == "posted"
    )).all()

def monthly_history(db, uid, months=6):
    today = date.today()
    start = month_start(today) - relativedelta(months=months-1)
    rows = posted_transactions(db, uid)
    result = []
    for i in range(months):
        m = start + relativedelta(months=i)
        end = next_month(m)
        income = sum((r.amount for r in rows if r.type=="income" and m <= r.occurred_at < end), Decimal("0"))
        expense = sum((r.amount for r in rows if r.type=="expense" and m <= r.occurred_at < end), Decimal("0"))
        result.append({"month": m.isoformat(), "income": money(income), "expense": money(expense), "net": money(income-expense)})
    return result

def category_spend(db, uid, start, end):
    rows = db.execute(select(Transaction.category, func.sum(Transaction.amount)).where(
        Transaction.user_id == uid, Transaction.type == "expense",
        Transaction.status == "posted",
        Transaction.occurred_at >= start, Transaction.occurred_at < end
    ).group_by(Transaction.category)).all()
    return {str(cat): Decimal(str(total or 0)) for cat, total in rows}

def build_alerts(db, uid):
    today = date.today()
    # Budget alerts
    budgets = db.scalars(select(Budget).where(Budget.user_id == uid)).all()
    for b in budgets:
        start = month_start(b.month)
        if start.year != today.year or start.month != today.month:
            continue
        end = next_month(start)
        spent = db.scalar(select(func.coalesce(func.sum(Transaction.amount),0)).where(
            Transaction.user_id==uid, Transaction.type=="expense",
            Transaction.status=="posted", Transaction.category==b.category,
            Transaction.occurred_at>=start, Transaction.occurred_at<end
        )) or Decimal("0")
        pct = float(spent / b.limit_amount * 100) if b.limit_amount else 0
        if pct >= b.alert_percent:
            title = f"Orçamento: {b.category}"
            exists = db.scalar(select(Alert).where(
                Alert.user_id==uid, Alert.kind=="budget", Alert.title==title,
                func.date(Alert.created_at)==today
            ))
            if not exists:
                db.add(Alert(user_id=uid, kind="budget", title=title,
                             message=f"Uso de {pct:.0f}% do orçamento de {b.category}.",
                             severity="danger" if pct>=100 else "warning"))
    # Invoice alerts
    invoices = db.scalars(select(Invoice).where(
        Invoice.user_id==uid, Invoice.status!="paid"
    )).all()
    for inv in invoices:
        if inv.due_date < today and inv.total > inv.paid_amount:
            title = f"Fatura vencida #{inv.id}"
            exists = db.scalar(select(Alert).where(
                Alert.user_id==uid, Alert.kind=="invoice", Alert.title==title,
                func.date(Alert.created_at)==today
            ))
            if not exists:
                db.add(Alert(user_id=uid, kind="invoice", title=title,
                             message=f"Fatura vencida desde {inv.due_date.strftime('%d/%m/%Y')}.",
                             severity="danger"))
    # Negative projected cash alert
    history = monthly_history(db, uid, 3)
    avg_net = sum(x["net"] for x in history)/max(len(history),1)
    accounts = db.scalars(select(Account).where(Account.user_id==uid)).all()
    balance = sum((a.balance for a in accounts), Decimal("0"))
    if balance + Decimal(str(avg_net)) < 0:
        title = "Fluxo de caixa projetado negativo"
        exists = db.scalar(select(Alert).where(
            Alert.user_id==uid, Alert.kind=="projection", Alert.title==title,
            func.date(Alert.created_at)==today
        ))
        if not exists:
            db.add(Alert(user_id=uid, kind="projection", title=title,
                         message="A projeção do próximo mês indica saldo de caixa negativo.",
                         severity="danger"))
    db.commit()

@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    build_alerts(db, u.id)
    today = date.today()
    history = monthly_history(db, u.id, 6)
    accounts = db.scalars(select(Account).where(Account.user_id == u.id)).all()
    goals = db.scalars(select(Goal).where(Goal.user_id == u.id)).all()
    debts = db.scalars(select(Debt).where(Debt.user_id == u.id)).all()
    invoices = db.scalars(select(Invoice).where(Invoice.user_id == u.id, Invoice.status != "paid")).all()
    alerts = db.scalars(select(Alert).where(
        Alert.user_id == u.id, Alert.read == False
    ).order_by(Alert.created_at.desc()).limit(8)).all()

    balance = sum((a.balance for a in accounts), Decimal("0"))
    month = history[-1]
    avg_income = sum(x["income"] for x in history[:-1]) / max(len(history)-1, 1)
    avg_expense = sum(x["expense"] for x in history[:-1]) / max(len(history)-1, 1)
    open_invoice = sum((i.total - i.paid_amount for i in invoices), Decimal("0"))
    debt_balance = sum((d.balance for d in debts), Decimal("0"))
    monthly_debt = sum((d.monthly_payment for d in debts), Decimal("0"))

    # Budget adherence
    current_budgets = db.scalars(select(Budget).where(
        Budget.user_id == u.id, Budget.month == month_start(today)
    )).all()
    if current_budgets:
        spent = category_spend(db, u.id, month_start(today), next_month(today))
        ratios = [
            float(spent.get(b.category, Decimal("0")) / b.limit_amount)
            for b in current_budgets if b.limit_amount > 0
        ]
        budget_adherence = max(0, min(100, 100 - max(ratios, default=0)*100))
    else:
        budget_adherence = 100

    goal_progress = [
        {
            "id": g.id, "name": g.name,
            "target_amount": money(g.target_amount),
            "current_amount": money(g.current_amount),
            "percent": round(float(g.current_amount/g.target_amount*100),1) if g.target_amount else 0,
            "target_date": g.target_date.isoformat() if g.target_date else None
        } for g in goals
    ]

    return {
        "today": today.isoformat(),
        "kpis": {
            "cash_balance": money(balance),
            "current_income": month["income"],
            "current_expense": month["expense"],
            "current_net": month["net"],
            "open_invoices": money(open_invoice),
            "debt_balance": money(debt_balance),
            "monthly_debt": money(monthly_debt),
            "avg_income_5m": round(avg_income,2),
            "avg_expense_5m": round(avg_expense,2),
        },
        "history": history,
        "goals": goal_progress,
        "alerts": [
            {"id": a.id, "title": a.title, "message": a.message, "severity": a.severity,
             "created_at": a.created_at.isoformat()}
            for a in alerts
        ],
        "budget_adherence": round(budget_adherence,1)
    }

@router.get("/cashflow-projection")
def cashflow_projection(months: int = 6, db: Session = Depends(get_db),
                        u: User = Depends(get_current_user)):
    months = max(1, min(months, 24))
    today = date.today()
    history = monthly_history(db, u.id, 6)
    base_income = sum(x["income"] for x in history[:-1]) / max(len(history)-1,1)
    base_expense = sum(x["expense"] for x in history[:-1]) / max(len(history)-1,1)
    recurring = db.scalars(select(Recurring).where(
        Recurring.user_id==u.id, Recurring.active==True
    )).all()
    rec_income = sum((r.amount for r in recurring if r.type=="income" and r.frequency=="monthly"), Decimal("0"))
    rec_expense = sum((r.amount for r in recurring if r.type=="expense" and r.frequency=="monthly"), Decimal("0"))
    # Avoid double counting: use historical variable flow plus recurring future commitments.
    monthly_income = max(Decimal("0"), Decimal(str(base_income))) + rec_income
    monthly_expense = max(Decimal("0"), Decimal(str(base_expense))) + rec_expense
    accounts = db.scalars(select(Account).where(Account.user_id==u.id)).all()
    running = sum((a.balance for a in accounts), Decimal("0"))
    out=[]
    for i in range(1, months+1):
        m = month_start(today) + relativedelta(months=i)
        running += monthly_income - monthly_expense
        out.append({
            "month": m.isoformat(),
            "income": money(monthly_income),
            "expense": money(monthly_expense),
            "net": money(monthly_income-monthly_expense),
            "projected_balance": money(running)
        })
    return {
        "method": "média dos últimos 5 meses + recorrências mensais cadastradas",
        "months": out
    }

@router.get("/budget-smart")
def smart_budget(db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    today = date.today()
    current = month_start(today)
    hist_start = current - relativedelta(months=3)
    spends = {}
    for cat, total in db.execute(select(
        Transaction.category, func.sum(Transaction.amount)
    ).where(
        Transaction.user_id==u.id, Transaction.type=="expense",
        Transaction.status=="posted", Transaction.occurred_at>=hist_start,
        Transaction.occurred_at<current
    ).group_by(Transaction.category)).all():
        spends[str(cat)] = Decimal(str(total or 0)) / 3
    suggestions=[]
    for cat, avg in sorted(spends.items(), key=lambda x:x[1], reverse=True):
        recommended = (avg * Decimal("1.05")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        suggestions.append({
            "category": cat, "average_3m": money(avg),
            "recommended_limit": money(recommended),
            "reason": "média dos últimos 3 meses + margem de 5%"
        })
    return {"month": current.isoformat(), "suggestions": suggestions[:30]}

@router.get("/health")
def financial_health(db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    today = date.today()
    history = monthly_history(db, u.id, 6)
    avg_income = sum(x["income"] for x in history[:-1]) / max(len(history)-1,1)
    avg_expense = sum(x["expense"] for x in history[:-1]) / max(len(history)-1,1)
    accounts = db.scalars(select(Account).where(Account.user_id==u.id)).all()
    debts = db.scalars(select(Debt).where(Debt.user_id==u.id)).all()
    goals = db.scalars(select(Goal).where(Goal.user_id==u.id)).all()
    balance = float(sum((a.balance for a in accounts), Decimal("0")))
    monthly_debt = float(sum((d.monthly_payment for d in debts), Decimal("0")))
    debt_ratio = (monthly_debt / avg_income * 100) if avg_income > 0 else 0
    reserve_months = (balance / avg_expense) if avg_expense > 0 else 99
    current_budget = db.scalars(select(Budget).where(
        Budget.user_id==u.id, Budget.month==month_start(today)
    )).all()
    spent = category_spend(db,u.id,month_start(today),next_month(today))
    budget_overruns = sum(
        1 for b in current_budget if b.limit_amount > 0 and spent.get(b.category,0) > b.limit_amount
    )
    goal_completion = (
        sum(float(g.current_amount/g.target_amount*100) for g in goals if g.target_amount) / len(goals)
        if goals else 0
    )

    cash_score = 25 if balance >= avg_expense*3 else 18 if balance >= avg_expense else 8 if balance >= 0 else 0
    flow_score = 25 if avg_income > avg_expense*1.2 else 18 if avg_income >= avg_expense else 5
    debt_score = 25 if debt_ratio <= 20 else 18 if debt_ratio <= 35 else 8 if debt_ratio <= 50 else 0
    budget_score = 15 if budget_overruns == 0 else 8 if budget_overruns <= 1 else 0
    goal_score = 10 if goal_completion >= 75 else 7 if goal_completion >= 40 else 3 if goals else 0
    total = int(cash_score + flow_score + debt_score + budget_score + goal_score)
    level = "Excelente" if total >= 85 else "Boa" if total >= 70 else "Atenção" if total >= 50 else "Crítica"
    return {
        "score": total, "level": level,
        "components": {
            "reserva": round(cash_score,1), "fluxo": round(flow_score,1),
            "dívidas": round(debt_score,1), "orçamento": round(budget_score,1),
            "metas": round(goal_score,1)
        },
        "metrics": {
            "reserve_months": round(reserve_months,1),
            "debt_ratio": round(debt_ratio,1),
            "avg_income": round(avg_income,2),
            "avg_expense": round(avg_expense,2),
            "goal_completion": round(goal_completion,1),
            "budget_overruns": budget_overruns
        }
    }

@router.post("/simulate")
def simulate(data: SimulationIn, db: Session = Depends(get_db),
             u: User = Depends(get_current_user)):
    if data.months < 1 or data.months > 120:
        raise HTTPException(400, "Horizonte deve estar entre 1 e 120 meses")
    history = monthly_history(db,u.id,6)
    base_income = Decimal(str(sum(x["income"] for x in history[:-1])/max(len(history)-1,1)))
    base_expense = Decimal(str(sum(x["expense"] for x in history[:-1])/max(len(history)-1,1)))
    accounts = db.scalars(select(Account).where(Account.user_id==u.id)).all()
    initial = sum((a.balance for a in accounts), Decimal("0"))
    monthly_income = base_income + Decimal(str(data.monthly_income_change))
    monthly_expense = base_expense + Decimal(str(data.monthly_expense_change))
    if monthly_income < 0 or monthly_expense < 0:
        raise HTTPException(400,"A simulação gerou fluxo mensal negativo inválido")
    balance = initial + Decimal(str(data.one_time_change))
    rows=[]
    rate = Decimal(str(data.annual_rate))/Decimal("100")
    monthly_rate = (Decimal("1")+rate) ** (Decimal("1")/Decimal("12")) - Decimal("1") if rate > -1 else Decimal("0")
    for n in range(1,data.months+1):
        balance = balance * (Decimal("1")+monthly_rate) + monthly_income - monthly_expense
        rows.append({
            "month": n, "income": money(monthly_income), "expense": money(monthly_expense),
            "net": money(monthly_income-monthly_expense), "balance": money(balance)
        })
    return {
        "initial_balance": money(initial),
        "final_balance": rows[-1]["balance"],
        "total_net": money(sum(r["net"] for r in rows)),
        "rows": rows,
        "assumptions": {
            "monthly_income_change": money(data.monthly_income_change),
            "monthly_expense_change": money(data.monthly_expense_change),
            "one_time_change": money(data.one_time_change),
            "annual_rate": float(data.annual_rate)
        }
    }
