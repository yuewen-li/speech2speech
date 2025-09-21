import jwt
import bcrypt
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from src.utils.config import Config

logger = logging.getLogger(__name__)


class AuthService:
    """JWT-based authentication service with SQLite user storage"""

    def __init__(self, db_path: str = "users.db"):
        self.secret_key = Config.JWT_SECRET_KEY
        self.db_path = db_path
        self.algorithm = "HS256"
        self.token_expiry_hours = 1

        # Initialize database
        self._init_database()

    def _init_database(self):
        """Initialize SQLite database with users table"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Create users table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    plan TEXT DEFAULT 'trial',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1,
                    plan_activation_date TIMESTAMP
                )
            """
            )

            # Create sessions table for token blacklisting
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    token_jti TEXT UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP NOT NULL,
                    is_revoked BOOLEAN DEFAULT 0,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            """
            )

            conn.commit()
            conn.close()
            logger.info("Database initialized successfully")

        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            raise

    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt"""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against hash"""
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))

    def create_user(
        self, email: str, password: str, plan: str = "trial"
    ) -> Optional[Dict[str, Any]]:
        """Create a new user"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Check if user already exists
            cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
            if cursor.fetchone():
                conn.close()
                return None

            # Create user
            password_hash = self.hash_password(password)
            cursor.execute(
                """
                INSERT INTO users (email, password_hash, plan)
                VALUES (?, ?, ?)
            """,
                (email, password_hash, plan),
            )

            user_id = cursor.lastrowid
            conn.commit()
            conn.close()

            logger.info(f"User created: {email}")
            return {
                "id": user_id,
                "email": email,
                "plan": plan,
                "created_at": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error creating user: {e}")
            return None

    def authenticate_user(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate user and return user data"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT id, email, password_hash, plan, is_active, created_at, plan_activation_date
                FROM users WHERE email = ?
            """,
                (email,),
            )

            user = cursor.fetchone()
            if not user:
                conn.close()
                return None

            (
                user_id,
                email,
                password_hash,
                plan,
                is_active,
                created_at,
                plan_activation_date,
            ) = user

            if not is_active:
                conn.close()
                return None

            if not self.verify_password(password, password_hash):
                conn.close()
                return None

            # Update last login
            cursor.execute(
                """
                UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?
            """,
                (user_id,),
            )
            conn.commit()
            conn.close()

            return {
                "id": user_id,
                "email": email,
                "plan": plan,
                "created_at": created_at,
                "plan_activation_date": plan_activation_date,
            }

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
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO sessions (user_id, token_jti, expires_at)
                VALUES (?, ?, ?)
            """,
                (user_id, jti, expires_at),
            )

            conn.commit()
            conn.close()

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
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT is_revoked FROM sessions WHERE token_jti = ?
            """,
                (jti,),
            )

            result = cursor.fetchone()
            conn.close()

            return result[0] if result else True  # Consider missing tokens as revoked

        except Exception as e:
            logger.error(f"Error checking token revocation: {e}")
            return True

    def revoke_token(self, jti: str) -> bool:
        """Revoke a specific token"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                UPDATE sessions SET is_revoked = 1 WHERE token_jti = ?
            """,
                (jti,),
            )

            conn.commit()
            conn.close()

            logger.info(f"Token revoked: {jti}")
            return True

        except Exception as e:
            logger.error(f"Error revoking token: {e}")
            return False

    def revoke_user_tokens(self, user_id: int) -> bool:
        """Revoke all tokens for a user"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                UPDATE sessions SET is_revoked = 1 WHERE user_id = ?
            """,
                (user_id,),
            )

            conn.commit()
            conn.close()

            logger.info(f"All tokens revoked for user: {user_id}")
            return True

        except Exception as e:
            logger.error(f"Error revoking user tokens: {e}")
            return False

    def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT id, email, plan, created_at, last_login, is_active, plan_activation_date
                FROM users WHERE id = ?
            """,
                (user_id,),
            )

            user = cursor.fetchone()
            conn.close()

            if not user:
                return None

            return {
                "id": user[0],
                "email": user[1],
                "plan": user[2],
                "created_at": user[3],
                "last_login": user[4],
                "is_active": bool(user[5]),
            }

        except Exception as e:
            logger.error(f"Error getting user: {e}")
            return None

    def update_user_plan(self, user_id: int, new_plan: str) -> bool:
        """Update user's subscription plan"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                UPDATE users SET plan = ? WHERE id = ?
            """,
                (new_plan, user_id),
            )

            conn.commit()
            conn.close()

            logger.info(f"User {user_id} plan updated to {new_plan}")
            return True

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
