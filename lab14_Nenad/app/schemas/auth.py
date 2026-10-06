from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=6, max_length=100)


class UserResponse(BaseModel):
    id: int
    username: str
    role: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
