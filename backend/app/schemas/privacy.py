from pydantic import BaseModel, Field
class ConsentIn(BaseModel):
    purpose: str = Field(min_length=1, max_length=100)
    granted: bool
