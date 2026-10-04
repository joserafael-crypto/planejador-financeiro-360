from pydantic import BaseModel, EmailStr, Field

class RegisterIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
class LoginIn(BaseModel):
    email: EmailStr
    password: str
    otp: str|None = Field(default=None, min_length=6, max_length=8)
class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str="bearer"
    expires_in: int
class RefreshIn(BaseModel):
    refresh_token: str = Field(min_length=20)
class MFAConfirmIn(BaseModel):
    code: str = Field(min_length=6, max_length=8)
class MFAEnrollmentOut(BaseModel):
    secret: str
    otpauth_uri: str
