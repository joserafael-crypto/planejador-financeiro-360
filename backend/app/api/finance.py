
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from dateutil.relativedelta import relativedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.models import (
    User, Account, Card, Invoice, Transaction, Recurring, InstallmentPlan,
    Installment, Transfer, Budget, Alert, Goal, Debt, AuditLog
)
from app.schemas.finance import *

router = APIRouter(prefix="/api/finance", tags=["finance"])

def own(db, model, obj_id, user_id):
    obj = db.scalar(select(model).where(model.id == obj_id, model.user_id == user_id))
    if not obj:
        raise HTTPException(404, f"{model.__name__} não encontrado")
    return obj

def month_start(d):
    return d.replace(day=1)

def next_month(d):
    return d.replace(day=1) + relativedelta(months=1)

def invoice_for_month(db, user_id, card, ref):
    ref = month_start(ref)
    inv = db.scalar(select(Invoice).where(
        Invoice.user_id == user_id,
        Invoice.card_id == card.id,
        Invoice.reference_month == ref
    ))
    if inv:
        return inv
    closing = date(ref.year, ref.month, min(card.closing_day, 28))
    due_month = next_month(ref)
    due = date(due_month.year, due_month.month, min(card.due_day, 28))
    inv = Invoice(
        user_id=user_id, card_id=card.id, reference_month=ref,
        closing_date=closing, due_date=due
    )
    db.add(inv)
    db.flush()
    return inv

def invoice_for(db, user_id, card, d):
    ref = month_start(d)
    if d.day > card.closing_day:
        ref = next_month(ref)
    return invoice_for_month(db, user_id, card, ref)

def refresh_invoice(db, inv):
    inv.total = db.scalar(
        select(func.coalesce(func.sum(Transaction.amount), 0))
        .where(Transaction.invoice_id == inv.id, Transaction.type == "expense")
    ) or Decimal("0")
    if inv.paid_amount >= inv.total and inv.total > 0:
        inv.status = "paid"
    elif date.today() > inv.due_date and inv.total > inv.paid_amount:
        inv.status = "overdue"
    elif inv.total > 0:
        inv.status = "closed" if date.today() >= inv.closing_date else "open"

@router.get("/summary")
def summary(db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    income = db.scalar(select(func.coalesce(func.sum(Transaction.amount), 0)).where(
        Transaction.user_id == u.id, Transaction.type == "income",
        Transaction.occurred_at <= date.today(), Transaction.status == "posted"
    )) or 0
    expense = db.scalar(select(func.coalesce(func.sum(Transaction.amount), 0)).where(
        Transaction.user_id == u.id, Transaction.type == "expense",
        Transaction.occurred_at <= date.today(), Transaction.status == "posted"
    )) or 0
    open_invoices = db.scalar(select(func.coalesce(func.sum(Invoice.total - Invoice.paid_amount), 0)).where(
        Invoice.user_id == u.id, Invoice.status != "paid"
    )) or 0
    account_balance = db.scalar(select(func.coalesce(func.sum(Account.balance), 0)).where(
        Account.user_id == u.id
    )) or 0
    return {
        "income": income, "expense": expense, "balance": income - expense,
        "account_balance": account_balance, "open_invoices": open_invoices
    }

@router.get("/accounts")
def accounts(db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    return db.scalars(select(Account).where(Account.user_id == u.id).order_by(Account.name)).all()

@router.post("/accounts")
def create_account(data: AccountIn, db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    a = Account(user_id=u.id, **data.model_dump())
    db.add(a); db.commit(); db.refresh(a)
    return a

@router.get("/cards")
def cards(db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    return db.scalars(select(Card).where(Card.user_id == u.id).order_by(Card.name)).all()

@router.post("/cards")
def create_card(data: CardIn, db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    if data.account_id:
        own(db, Account, data.account_id, u.id)
    c = Card(user_id=u.id, **data.model_dump())
    db.add(c); db.commit(); db.refresh(c)
    return c

@router.get("/invoices")
def invoices(db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    invs = db.scalars(select(Invoice).where(Invoice.user_id == u.id).order_by(Invoice.due_date)).all()
    for i in invs:
        refresh_invoice(db, i)
    db.commit()
    return invs

@router.post("/invoices/{invoice_id}/pay")
def pay_invoice(invoice_id: int, amount: Decimal, account_id: int | None = None,
                db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    inv = own(db, Invoice, invoice_id, u.id)
    if amount <= 0:
        raise HTTPException(400, "Valor inválido")
    refresh_invoice(db, inv)
    remaining = inv.total - inv.paid_amount
    if amount > remaining:
        raise HTTPException(400, "Pagamento superior ao saldo da fatura")
    if account_id:
        acc = own(db, Account, account_id, u.id)
        if acc.balance < amount:
            raise HTTPException(400, "Saldo insuficiente para pagar a fatura")
        acc.balance -= amount
    inv.paid_amount += amount
    refresh_invoice(db, inv)
    db.add(AuditLog(user_id=u.id, action="invoice.payment",
                    detail=f"invoice={inv.id};amount={amount}"))
    db.commit()
    return inv

@router.get("/transactions")
def transactions(db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    return db.scalars(select(Transaction).where(
        Transaction.user_id == u.id
    ).order_by(Transaction.occurred_at.desc(), Transaction.id.desc())).all()

@router.post("/transactions")
def create_transaction(data: TxIn, db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    if data.type not in ("income", "expense"):
        raise HTTPException(400, "type deve ser income ou expense")
    if data.account_id:
        own(db, Account, data.account_id, u.id)
    card = None
    if data.card_id:
        card = own(db, Card, data.card_id, u.id)
        if data.type != "expense":
            raise HTTPException(400, "Cartão só pode registrar despesa")
    inv = invoice_for(db, u.id, card, data.occurred_at) if card else None
    t = Transaction(user_id=u.id, invoice_id=inv.id if inv else None, **data.model_dump())
    db.add(t)
    if data.account_id and data.occurred_at <= date.today():
        acc = own(db, Account, data.account_id, u.id)
        acc.balance += data.amount if data.type == "income" else -data.amount
    db.commit(); db.refresh(t)
    if inv:
        refresh_invoice(db, inv); db.commit()
    return t

@router.get("/recurrings")
def recurrings(db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    return db.scalars(select(Recurring).where(
        Recurring.user_id == u.id
    ).order_by(Recurring.next_date)).all()

@router.post("/recurrings")
def create_recurring(data: RecurringIn, db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    if data.type not in ("income", "expense"):
        raise HTTPException(400, "type inválido")
    if data.frequency not in ("weekly", "monthly", "yearly"):
        raise HTTPException(400, "frequency inválida")
    if data.account_id: own(db, Account, data.account_id, u.id)
    if data.card_id: own(db, Card, data.card_id, u.id)
    r = Recurring(user_id=u.id, **data.model_dump())
    db.add(r); db.commit(); db.refresh(r)
    return r

@router.post("/recurrings/{recurring_id}/launch")
def launch_recurring(recurring_id: int, db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    r = own(db, Recurring, recurring_id, u.id)
    if not r.active:
        raise HTTPException(400, "Recorrência inativa")
    payload = TxIn(
        description=r.description, category=r.category, type=r.type,
        amount=r.amount, occurred_at=r.next_date,
        account_id=r.account_id, card_id=r.card_id
    )
    t = create_transaction(payload, db, u)
    if r.frequency == "weekly":
        r.next_date += relativedelta(weeks=1)
    elif r.frequency == "monthly":
        r.next_date += relativedelta(months=1)
    else:
        r.next_date += relativedelta(years=1)
    db.commit()
    return t

@router.get("/installments")
def installments(db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    plans = db.scalars(select(InstallmentPlan).where(
        InstallmentPlan.user_id == u.id
    ).order_by(InstallmentPlan.first_due_date)).all()
    out = []
    for p in plans:
        items = db.scalars(select(Installment).where(
            Installment.plan_id == p.id
        ).order_by(Installment.number)).all()
        out.append({"plan": p, "installments": items})
    return out

@router.post("/installments")
def create_installment_plan(data: InstallmentIn, db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    if data.card_id: own(db, Card, data.card_id, u.id)
    if data.account_id: own(db, Account, data.account_id, u.id)
    amount = (data.total_amount / data.total_count).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    p = InstallmentPlan(user_id=u.id, installment_amount=amount, **data.model_dump())
    db.add(p); db.flush()
    running = Decimal("0")
    for n in range(1, data.total_count + 1):
        val = amount if n < data.total_count else data.total_amount - running
        running += val
        due = data.first_due_date + relativedelta(months=n - 1)
        inv = None
        if data.card_id:
            card = own(db, Card, data.card_id, u.id)
            inv = invoice_for_month(db, u.id, card, due)
        db.add(Installment(
            plan_id=p.id, invoice_id=inv.id if inv else None,
            number=n, amount=val, due_date=due
        ))
        if data.card_id:
            db.add(Transaction(
                user_id=u.id, card_id=data.card_id,
                invoice_id=inv.id if inv else None,
                installment_plan_id=p.id, description=data.description,
                category=data.category, type="expense", amount=val,
                occurred_at=due, status="scheduled"
            ))
    db.commit(); db.refresh(p)
    return p

@router.post("/installments/{installment_id}/pay")
def pay_installment(installment_id: int, db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    ins = db.scalar(select(Installment).join(
        InstallmentPlan, Installment.plan_id == InstallmentPlan.id
    ).where(Installment.id == installment_id, InstallmentPlan.user_id == u.id))
    if not ins:
        raise HTTPException(404, "Parcela não encontrada")
    if ins.status == "paid":
        raise HTTPException(400, "Parcela já paga")
    ins.status = "paid"; ins.paid_at = date.today()
    p = db.get(InstallmentPlan, ins.plan_id)
    p.paid_count += 1
    if p.paid_count >= p.total_count:
        p.status = "completed"
    db.commit()
    return ins

@router.get("/transfers")
def transfers(db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    return db.scalars(select(Transfer).where(
        Transfer.user_id == u.id
    ).order_by(Transfer.transfer_date.desc())).all()

@router.post("/transfers")
def create_transfer(data: TransferIn, db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    if data.from_account_id == data.to_account_id:
        raise HTTPException(400, "Contas de origem e destino devem ser diferentes")
    source = own(db, Account, data.from_account_id, u.id)
    dest = own(db, Account, data.to_account_id, u.id)
    if source.balance < data.amount:
        raise HTTPException(400, "Saldo insuficiente")
    tr = Transfer(user_id=u.id, **data.model_dump())
    db.add(tr)
    source.balance -= data.amount
    dest.balance += data.amount
    db.commit(); db.refresh(tr)
    return tr

@router.get("/budgets")
def budgets(db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    bs = db.scalars(select(Budget).where(
        Budget.user_id == u.id
    ).order_by(Budget.month.desc(), Budget.category)).all()
    out = []
    for b in bs:
        start = month_start(b.month); end = next_month(start)
        spent = db.scalar(select(func.coalesce(func.sum(Transaction.amount), 0)).where(
            Transaction.user_id == u.id, Transaction.type == "expense",
            Transaction.category == b.category,
            Transaction.occurred_at >= start, Transaction.occurred_at < end,
            Transaction.status == "posted"
        )) or 0
        out.append({
            "budget": b, "spent": spent,
            "remaining": b.limit_amount - spent,
            "percent": float(spent / b.limit_amount * 100) if b.limit_amount else 0
        })
    return out

@router.post("/budgets")
def create_budget(data: BudgetIn, db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    b = db.scalar(select(Budget).where(
        Budget.user_id == u.id, Budget.category == data.category,
        Budget.month == month_start(data.month)
    ))
    if b:
        b.limit_amount = data.limit_amount
        b.alert_percent = data.alert_percent
    else:
        b = Budget(user_id=u.id, month=month_start(data.month), **data.model_dump(exclude={"month"}))
        db.add(b)
    db.commit(); db.refresh(b)
    return b

@router.get("/alerts")
def alerts(db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    return db.scalars(select(Alert).where(
        Alert.user_id == u.id
    ).order_by(Alert.created_at.desc()).limit(100)).all()

@router.post("/alerts/refresh")
def refresh_alerts(db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    now = date.today()
    bs = db.scalars(select(Budget).where(Budget.user_id == u.id)).all()
    for b in bs:
        start = month_start(b.month); end = next_month(start)
        if start.year != now.year or start.month != now.month:
            continue
        spent = db.scalar(select(func.coalesce(func.sum(Transaction.amount), 0)).where(
            Transaction.user_id == u.id, Transaction.type == "expense",
            Transaction.category == b.category,
            Transaction.occurred_at >= start, Transaction.occurred_at < end,
            Transaction.status == "posted"
        )) or 0
        pct = (spent / b.limit_amount * 100) if b.limit_amount else 0
        if pct >= b.alert_percent:
            title = f"Orçamento: {b.category}"
            exists = db.scalar(select(Alert).where(
                Alert.user_id == u.id, Alert.kind == "budget",
                Alert.title == title, func.date(Alert.created_at) == now
            ))
            if not exists:
                sev = "danger" if pct >= 100 else "warning"
                db.add(Alert(
                    user_id=u.id, kind="budget", title=title,
                    message=f"Você utilizou {pct:.0f}% do orçamento de {b.category}.",
                    severity=sev
                ))
    invs = db.scalars(select(Invoice).where(
        Invoice.user_id == u.id, Invoice.status != "paid"
    )).all()
    for i in invs:
        refresh_invoice(db, i)
        if i.due_date <= now and i.total > i.paid_amount:
            title = f"Fatura vencida #{i.id}"
            exists = db.scalar(select(Alert).where(
                Alert.user_id == u.id, Alert.kind == "invoice",
                Alert.title == title, func.date(Alert.created_at) == now
            ))
            if not exists:
                db.add(Alert(
                    user_id=u.id, kind="invoice", title=title,
                    message=f"Fatura vencida em {i.due_date.strftime('%d/%m/%Y')}.",
                    severity="danger"
                ))
    db.commit()
    return alerts(db, u)

@router.post("/alerts/{alert_id}/read")
def read_alert(alert_id: int, db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    a = own(db, Alert, alert_id, u.id)
    a.read = True
    db.commit()
    return a

@router.get("/goals")
def goals(db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    return db.scalars(select(Goal).where(Goal.user_id == u.id)).all()

@router.post("/goals")
def create_goal(data: GoalIn, db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    if data.current_amount > data.target_amount:
        raise HTTPException(400, "Valor atual não pode superar a meta")
    g = Goal(user_id=u.id, **data.model_dump())
    db.add(g); db.commit(); db.refresh(g)
    return g

@router.post("/goals/{goal_id}/contribute")
def contribute_goal(goal_id: int, data: GoalContributionIn,
                    db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    g = own(db, Goal, goal_id, u.id)
    if g.current_amount + data.amount > g.target_amount:
        raise HTTPException(400, "A contribuição ultrapassa a meta")
    g.current_amount += data.amount
    db.add(AuditLog(user_id=u.id, action="goal.contribution",
                    detail=f"goal={goal_id};amount={data.amount}"))
    db.commit(); db.refresh(g)
    return g

@router.get("/debts")
def debts(db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    return db.scalars(select(Debt).where(Debt.user_id == u.id)).all()

@router.post("/debts")
def create_debt(data: DebtIn, db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    d = Debt(user_id=u.id, **data.model_dump())
    db.add(d); db.commit(); db.refresh(d)
    return d
