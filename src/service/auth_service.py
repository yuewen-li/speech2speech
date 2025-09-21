import jwt
import bcrypt
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from src.utils.config import Config
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.model.base import Base
from src.model.users import User
from src.model.sessions import Session

logger = logging.getLogger(__name__)


class AuthService:
    """JWT-based authentication service with SQLite user storage"""

    def __init__(self, db_url="sqlite:///users.db"):
        self.secret_key = Config.JWT_SECRET_KEY
        self.algorithm = Config.JWT_ALGORITHM
        self.token_expiry_hours = Config.JWT_EXPIRY_HOURS
        self.engine = create_engine(db_url, connect_args={"check_same_thread": False})
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt"""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against hash"""
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))

    def create_user(self, email, password, plan="trial"):
        try:
            with self.Session() as session:
                if session.query(User).filter_by(email=email).first():
                    return None
                password_hash = self.hash_password(password)
                user = User(
                    email=email,
                    password_hash=password_hash,
                    plan=plan,
                    created_at=datetime.utcnow(),
                )
                session.add(user)
                session.commit()
                user_data = {
                    "id": user.id,
                    "email": user.email,
                    "plan": user.plan,
                    "created_at": user.created_at,
                }
                return user_data
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            return None

    def authenticate_user(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate user and return user data"""
        try:
            with self.Session() as session:
                user = session.query(User).filter_by(email=email).first()
                if (
                    not user
                    or not user.is_active
                    or not self.verify_password(password, user.password_hash)
                ):
                    return None
                user.last_login = datetime.utcnow()
                session.commit()
                user_data = {
                    "id": user.id,
                    "email": user.email,
                    "plan": user.plan,
                    "created_at": user.created_at,
                    "plan_activation_date": user.plan_activation_date,
                }
                return user_data
        except Exception as e:
            logger.error(f"Error authenticating user: {e}")
            return None

    def generate_token(self, user_data: Dict[str, Any]) -> str:
        """Generate JWT token for user"""
        try:
            now = datetime.utcnow()
            payload = {
                "user_id": user_data["id"],
                "email": user_data["email"],
                "plan": user_data["plan"],
                "iat": now,
                "exp": now + timedelta(hours=self.token_expiry_hours),
                "jti": f"{user_data['id']}_{now.timestamp()}",  # Unique token ID
            }

            token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

            # Store token in database for potential revocation
            self._store_token(user_data["id"], payload["jti"], payload["exp"])

            return token

        except Exception as e:
            logger.error(f"Error generating token: {e}")
            raise

    def _store_token(self, user_id: int, jti: str, expires_at: datetime):
        """Store token in database"""
        try:
            with self.Session() as session:
                session_obj = Session(
                    user_id=user_id,
                    token_jti=jti,
                    expires_at=expires_at,
                    is_revoked=False,
                )
                session.add(session_obj)
                session.commit()
        except Exception as e:
            logger.error(f"Error storing token: {e}")

    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify JWT token and return user data"""
        try:
            # Decode token
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])

            # Check if token is revoked
            if self._is_token_revoked(payload["jti"]):
                return None

            return {
                "user_id": payload["user_id"],
                "email": payload["email"],
                "plan": payload["plan"],
                "jti": payload["jti"],
            }

        except jwt.ExpiredSignatureError:
            logger.warning("Token has expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return None
        except Exception as e:
            logger.error(f"Error verifying token: {e}")
            return None

    def _is_token_revoked(self, jti: str) -> bool:
        """Check if token is revoked"""
        try:
            with self.Session() as session:
                session_obj = session.query(Session).filter_by(token_jti=jti).first()
                if not session_obj or session_obj.is_revoked:
                    return True
        except Exception as e:
            logger.error(f"Error checking if token is revoked: {e}")
        return False

    def revoke_token(self, jti: str) -> bool:
        """Revoke a specific token"""
        try:
            with self.Session() as session:
                session_obj = session.query(Session).filter_by(token_jti=jti).first()
                if session_obj:
                    session_obj.is_revoked = True
                    session.commit()
                    return True
        except Exception as e:
            logger.error(f"Error revoking token: {e}")
            return False

    def revoke_user_tokens(self, user_id: int) -> bool:
        """Revoke all tokens for a user"""
        try:
            with self.Session() as session:
                session.query(Session).filter_by(user_id=user_id).update(
                    {"is_revoked": True}
                )
                session.commit()
            return True
        except Exception as e:
            logger.error(f"Error revoking user tokens: {e}")
            return False

    def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        try:
            with self.Session() as session:
                user = session.query(User).filter_by(id=user_id).first()
                if not user:
                    return None
                user_data = {
                    "id": user.id,
                    "email": user.email,
                    "plan": user.plan,
                    "created_at": user.created_at,
                    "last_login": user.last_login,
                    "is_active": user.is_active,
                    "plan_activation_date": user.plan_activation_date,
                }
            return user_data
        except Exception as e:
            logger.error(f"Error getting user: {e}")
            return None

    def update_user_plan(self, user_id: int, new_plan: str) -> bool:
        """Update user's subscription plan"""
        try:
            with self.Session() as session:
                user = session.query(User).filter_by(id=user_id).first()
                if user:
                    user.plan = new_plan
                    session.commit()
                    return True
            return False
        except Exception as e:
            logger.error(f"Error updating user plan: {e}")
            return False


if __name__ == "__main__":
    auth_service = AuthService()

    email = "test@example.com"
    password = "password"
    user = auth_service.create_user(email, password)
    if user:
        logger.info(f"User created: {user}")
    else:
        logger.warning("User already exists")
    auth_user = auth_service.authenticate_user(email, password)
    if auth_user:
        logger.info(f"User authenticated: {auth_user}")
        token = auth_service.generate_token(auth_user)
        logger.info(f"Generated token: {token}")

        verified_data = auth_service.verify_token(token)
        if verified_data:
            logger.info(f"Token verified: {verified_data}")
        else:
            logger.warning("Token verification failed")
