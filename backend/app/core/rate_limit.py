import time
from collections import defaultdict, deque
from threading import Lock
from fastapi import HTTPException, Request
from app.core.config import settings

_lock=Lock()
_hits=defaultdict(deque)

def enforce_auth_rate_limit(request: Request):
    ip=request.client.host if request.client else "unknown"
    key=f"auth:{ip}"
    now=time.monotonic(); window=60.0
    with _lock:
        q=_hits[key]
        while q and now-q[0]>window: q.popleft()
        if len(q)>=settings.rate_limit_per_minute:
            raise HTTPException(429,"Muitas tentativas. Tente novamente em alguns instantes.",headers={"Retry-After":"60"})
        q.append(now)
