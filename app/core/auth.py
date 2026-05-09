from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
import httpx
from app.core.config import settings
from app.core.supabase import supabase
from datetime import datetime, timedelta

_jwks_cache = {}
_jwks_last_fetched = None
JWKS_CACHE_TTL = timedelta(hours=1)

security = HTTPBearer()

async def get_jwks():
    global _jwks_cache, _jwks_last_fetched
    
    now = datetime.now()
    if _jwks_cache and _jwks_last_fetched and (now - _jwks_last_fetched < JWKS_CACHE_TTL):
        return _jwks_cache

    url = f"{settings.SUPABASE_URL}/auth/v1/.well-known/jwks.json"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail="Failed to fetch JWKS from Supabase")
        
        _jwks_cache = response.json()
        _jwks_last_fetched = now
        return _jwks_cache

async def verify_supabase_token(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    token = credentials.credentials
    try:
        jwks = await get_jwks()
        unverified_header = jwt.get_unverified_header(token)
        
        key = next(
            (k for k in jwks["keys"] if k["kid"] == unverified_header["kid"]),
            None
        )
        
        if not key:
            raise HTTPException(status_code=401, detail="No matching key found in JWKS")
        
        payload = jwt.decode(
            token,
            key,
            algorithms=["ES256"],
            options={
                "verify_aud": False,
            }
        )
        return payload
        
    except JWTError as e:
        print(f"JWT Verification Error: {str(e)}")
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

def get_or_create_profile(user_id: str = Depends(get_current_user_id)) -> dict:
    result = supabase.table("profiles").select("*").eq("id", user_id).execute()

    if not result.data:
        insert_result = supabase.table("profiles").insert({
            "id": user_id,
            "plan": "free"
        }).execute()
        return insert_result.data[0]

    return result.data[0]
