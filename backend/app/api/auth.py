from fastapi import APIRouter
from pydantic import BaseModel
from app.core.auth import issue_token

router = APIRouter(prefix="/auth", tags=["Auth"])


class LoginRequest(BaseModel):
    password: str


@router.post("/login")
async def login(payload: LoginRequest):
    token = issue_token(payload.password)
    return {"token": token}
