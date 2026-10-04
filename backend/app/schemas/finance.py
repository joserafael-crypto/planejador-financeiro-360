
from datetime import date
from decimal import Decimal
from pydantic import BaseModel, Field

class AccountIn(BaseModel):
    name:str
    kind:str="bank"
    balance:Decimal=Decimal("0")
    credit_limit:Decimal|None=None
class CardIn(BaseModel):
    name:str
    brand:str|None=None
    last4:str|None=None
    credit_limit:Decimal=Decimal("0")
    closing_day:int=Field(ge=1,le=28)
    due_day:int=Field(ge=1,le=28)
    account_id:int|None=None
class TxIn(BaseModel):
    description:str
    category:str="Outros"
    type:str
    amount:Decimal=Field(gt=0)
    occurred_at:date
    account_id:int|None=None
    card_id:int|None=None
class RecurringIn(BaseModel):
    description:str
    category:str="Recorrente"
    amount:Decimal=Field(gt=0)
    type:str
    frequency:str
    next_date:date
    account_id:int|None=None
    card_id:int|None=None
class InstallmentIn(BaseModel):
    description:str
    category:str="Parcelado"
    total_amount:Decimal=Field(gt=0)
    total_count:int=Field(ge=2,le=120)
    first_due_date:date
    card_id:int|None=None
    account_id:int|None=None
class TransferIn(BaseModel):
    from_account_id:int
    to_account_id:int
    amount:Decimal=Field(gt=0)
    transfer_date:date
    description:str="Transferência"
class BudgetIn(BaseModel):
    category:str
    month:date
    limit_amount:Decimal=Field(gt=0)
    alert_percent:int=Field(ge=1,le=100,default=80)
class GoalIn(BaseModel):
    name:str
    target_amount:Decimal=Field(gt=0)
    current_amount:Decimal=Decimal("0")
    target_date:date|None=None
class DebtIn(BaseModel):
    creditor:str
    balance:Decimal=Field(gt=0)
    monthly_payment:Decimal=Field(gt=0)
    interest_rate:Decimal=Decimal("0")

class GoalContributionIn(BaseModel):
    amount: Decimal = Field(gt=0)

class SimulationIn(BaseModel):
    months: int = Field(default=12, ge=1, le=120)
    monthly_income_change: Decimal = Decimal("0")
    monthly_expense_change: Decimal = Decimal("0")
    one_time_change: Decimal = Decimal("0")
    annual_rate: Decimal = Decimal("0")
