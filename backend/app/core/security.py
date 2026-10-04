from datetime import datetime, timedelta, timezone
import hashlib
import secrets
from jose import jwt
from passlib.context import CryptContext
import pyotp
from app.core.config import settings

pwd=CryptContext(schemes=["bcrypt"], deprecated="auto")
ALG="HS256"

def hash_password(p): return pwd.hash(p)
def verify_password(p,h): return pwd.verify(p,h)
def create_token(user_id:int, session_id:int):
    exp=datetime.now(timezone.utc)+timedelta(minutes=settings.access_token_minutes)
    return jwt.encode({"sub":str(user_id),"sid":str(session_id),"typ":"access","exp":exp},settings.jwt_secret,algorithm=ALG)
def decode_token(token): return jwt.decode(token,settings.jwt_secret,algorithms=[ALG])
def new_mfa_secret(): return pyotp.random_base32()
def verify_otp(secret, code): return bool(secret) and pyotp.TOTP(secret).verify(code, valid_window=1)
def new_refresh_token(): return secrets.token_urlsafe(48)
def hash_refresh_token(token): return hashlib.sha256(token.encode("utf-8")).hexdigest()
