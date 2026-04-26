from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.auth import get_or_create_profile
from app.models.profile import Profile
from app.schemas.profile import ProfileResponse

router = APIRouter(prefix="/profile", tags=["profile"])

@router.get("/me", response_model=ProfileResponse)
def get_my_profile(profile: Profile = Depends(get_or_create_profile)):
    return profile

@router.get("/plan")
def get_my_plan(profile: Profile = Depends(get_or_create_profile)):
    return {"plan": profile.plan}
