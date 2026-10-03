from dataclasses import dataclass
from typing import Protocol
@dataclass(frozen=True)
class ProviderAccount:
    external_id:str; name:str; balance:float; currency:str="BRL"
class OpenFinanceProvider(Protocol):
    def create_consent(self,user_id:int,scopes:list[str])->str: ...
    def revoke_consent(self,consent_id:str)->None: ...
    def list_accounts(self,consent_id:str)->list[ProviderAccount]: ...
    def list_transactions(self,consent_id:str,account_id:str)->list[dict]: ...
class NotConfiguredOpenFinanceProvider:
    def _disabled(self): raise RuntimeError("Open Finance não está habilitado; integração de provedor pertence à V3")
    def create_consent(self,user_id,scopes): self._disabled()
    def revoke_consent(self,consent_id): self._disabled()
    def list_accounts(self,consent_id): self._disabled()
    def list_transactions(self,consent_id,account_id): self._disabled()
