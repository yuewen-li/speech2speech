from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from typing import Optional
import logging
from src.service.auth_service import AuthService

logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Speech Translation Auth API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize auth service
auth_service = AuthService()

# Security scheme
security = HTTPBearer()


class Plan(str):
    TRIAL = "trial"
    PREMIUM = "premium"
    LIMITED = "limited"


# Pydantic models
class UserRegister(BaseModel):
    email: EmailStr
    password: str
    plan: str = Plan.TRIAL.value


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    email: str
    plan: str


class UserInfo(BaseModel):
    id: int
    email: str
    plan: str
    created_at: str
    last_login: Optional[str]
    is_active: bool


class TokenRevoke(BaseModel):
    token: str


# Dependency to get current user
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    token = credentials.credentials
    user_data = auth_service.verify_token(token)

    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user_data


def check_and_update_plan(user):
    now = datetime.utcnow()
    if user.plan == Plan.TRIAL.value:
        signup_date = datetime.strptime(user.created_at, "%Y-%m-%d %H:%M:%S")
        if now - signup_date > timedelta(days=7):
            auth_service.update_user_plan(user.id, Plan.LIMITED.value)
    elif user.plan == Plan.PREMIUM.value:
        plan_activation_date = datetime.strptime(
            user.plan_activation_date, "%Y-%m-%d %H:%M:%S"
        )
        if now - plan_activation_date > timedelta(days=30):
            auth_service.update_user_plan(user.id, Plan.LIMITED.value)
    return user.plan


# Auth endpoints
@app.post("/auth/register", response_model=TokenResponse)
async def register_user(user_data: UserRegister):
    """Register a new user and return JWT token"""
    try:
        # Validate plan
        if user_data.plan not in Plan.__members__:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid plan value.",
            )

        # Create user
        user = auth_service.create_user(
            email=user_data.email, password=user_data.password, plan=user_data.plan
        )

        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists",
            )

        # Generate token
        token = auth_service.generate_token(user)

        return TokenResponse(
            access_token=token,
            user_id=user["id"],
            email=user["email"],
            plan=user["plan"],
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in user registration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@app.post("/auth/login", response_model=TokenResponse)
async def login_user(login_data: UserLogin):
    """Login user and return JWT token"""
    try:
        # Authenticate user
        user = auth_service.authenticate_user(
            email=login_data.email, password=login_data.password
        )

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        check_and_update_plan(user)

        # Generate token
        token = auth_service.generate_token(user)

        return TokenResponse(
            access_token=token,
            user_id=user["id"],
            email=user["email"],
            plan=user["plan"],
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in user login: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@app.get("/auth/me", response_model=UserInfo)
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """Get current user information"""
    try:
        user = auth_service.get_user(current_user["user_id"])

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        return UserInfo(**user)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@app.post("/auth/revoke")
async def revoke_token(
    token_data: TokenRevoke, current_user: dict = Depends(get_current_user)
):
    """Revoke a specific token"""
    try:
        # Verify the token belongs to the current user
        token_user = auth_service.verify_token(token_data.token)

        if not token_user or token_user["user_id"] != current_user["user_id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Cannot revoke this token"
            )

        success = auth_service.revoke_token(token_user["jti"])

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to revoke token",
            )

        return {"message": "Token revoked successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error revoking token: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@app.post("/auth/logout")
async def logout_user(current_user: dict = Depends(get_current_user)):
    """Logout user (revoke all tokens)"""
    try:
        success = auth_service.revoke_user_tokens(current_user["user_id"])

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to logout",
            )

        return {"message": "Logged out successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error logging out user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "service": "auth-api"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8002)
