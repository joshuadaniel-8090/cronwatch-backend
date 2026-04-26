from fastapi import APIRouter, Depends
from app.core.auth import get_or_create_profile

router = APIRouter(prefix="/profile", tags=["profile"])

@router.get("/me")
def get_my_profile(profile: dict = Depends(get_or_create_profile)):
    return profile
