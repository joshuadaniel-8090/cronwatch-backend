from fastapi import APIRouter, Depends, HTTPException, status
import httpx
from app.core.config import settings
from pydantic import BaseModel, EmailStr
from app.core.auth import get_or_create_profile, verify_supabase_token

router = APIRouter(prefix="/auth", tags=["auth"])

class AuthSchema(BaseModel):
    email: EmailStr
    password: str

@router.post("/register")
async def register(auth_data: AuthSchema):
    url = f"{settings.SUPABASE_URL}/auth/v1/signup"
    headers = {
        "apikey": settings.SUPABASE_ANON_KEY,
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json={
            "email": auth_data.email,
            "password": auth_data.password,
        }, headers=headers)
        
        if response.status_code != 200:
            detail = response.json().get("msg", "Registration failed")
            raise HTTPException(status_code=response.status_code, detail=detail)
        
        return response.json()

@router.post("/login")
async def login(auth_data: AuthSchema):
    url = f"{settings.SUPABASE_URL}/auth/v1/token?grant_type=password"
    headers = {
        "apikey": settings.SUPABASE_ANON_KEY,
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json={
            "email": auth_data.email,
            "password": auth_data.password,
        }, headers=headers)
        
        if response.status_code != 200:
            detail = response.json().get("error_description", "Login failed")
            raise HTTPException(status_code=response.status_code, detail=detail)
        
        data = response.json()
        return {
            "access_token": data["access_token"],
            "token_type": "bearer",
            "user": data["user"]
        }

@router.get("/me")
async def get_me(
    payload: dict = Depends(verify_supabase_token),
    profile: dict = Depends(get_or_create_profile)
):
    profile["email"] = payload.get("email")
    return profile
