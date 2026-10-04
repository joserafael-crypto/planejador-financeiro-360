from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.config import settings
from app.api import auth, finance, ai, intelligence, privacy, agent
from app.db.session import Base, engine
from app.models import models

app = FastAPI(title="Planejador Financeiro 360° API", version="2.4.0")

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request:Request, call_next):
        response=await call_next(request)
        if settings.security_headers_enabled:
            response.headers["X-Content-Type-Options"]="nosniff"
            response.headers["X-Frame-Options"]="DENY"
            response.headers["Referrer-Policy"]="no-referrer"
            response.headers["Permissions-Policy"]="camera=(), microphone=(), geolocation=()"
            response.headers["Content-Security-Policy"]="default-src 'self'; frame-ancestors 'none'; base-uri 'self'"
        return response

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(CORSMiddleware,allow_origins=[x.strip() for x in settings.cors_origins.split(",") if x.strip()],allow_credentials=False,allow_methods=["GET","POST","PUT","PATCH","DELETE","OPTIONS"],allow_headers=["Authorization","Content-Type"],max_age=600)

@app.get("/health")
def health(): return {"status":"ok","version":"2.4.0"}

app.include_router(auth.router,prefix="/api")
app.include_router(finance.router,prefix="/api")
app.include_router(intelligence.router,prefix="/api")
app.include_router(ai.router,prefix="/api")
app.include_router(privacy.router,prefix="/api")
app.include_router(agent.router,prefix="/api")
