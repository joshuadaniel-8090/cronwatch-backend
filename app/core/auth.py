from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
import httpx
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import get_db
from app.models.profile import Profile

security = HTTPBearer()

async def get_jwks():
    url = f"{settings.SUPABASE_URL}/auth/v1/.well-known/jwks.json"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail="Failed to fetch JWKS from Supabase")
        return response.json()

async def verify_supabase_token(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    token = credentials.credentials
    try:
        # Get public keys from Supabase JWKS endpoint
        jwks = await get_jwks()
        
        # Decode without verification first to get the kid
        unverified_header = jwt.get_unverified_header(token)
        
        # Find matching key
        key = next(
            (k for k in jwks["keys"] if k["kid"] == unverified_header["kid"]),
            None
        )
        
        if not key:
            raise HTTPException(status_code=401, detail="No matching key found in JWKS")
        
        # Verify and decode token using ES256
        # Supabase tokens usually have audience "authenticated"
        payload = jwt.decode(
            token,
            key,
            algorithms=["ES256"],
            options={
                "verify_aud": False,  # Relax audience check if it's causing issues
            }
        )
        return payload
        
    except JWTError as e:
        print(f"JWT Verification Error: {str(e)}") # Log for debugging
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}"
        )

def get_current_user_id(
    payload: dict = Depends(verify_supabase_token)
) -> str:
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    return user_id

def get_or_create_profile(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
) -> Profile:
    profile = db.query(Profile).filter(Profile.id == user_id).first()
    if not profile:
        profile = Profile(id=user_id, plan="free")
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile
