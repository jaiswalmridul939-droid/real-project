import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import JWT_SECRET
from app.core.database import get_db
from app.models import Admin

ALGORITHM = "HS256"
bearer = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 240_000).hex()
    return f"pbkdf2_sha256${salt}${digest}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, salt, digest = stored_hash.split("$", 2)
        candidate = hashlib.pbkdf2_hmac(algorithm.removeprefix("pbkdf2_"), password.encode(), salt.encode(), 240_000).hex()
        return algorithm == "pbkdf2_sha256" and hmac.compare_digest(candidate, digest)
    except (ValueError, TypeError):
        return False


def create_access_token(email: str) -> str:
    expires = datetime.now(timezone.utc) + timedelta(hours=8)
    return jwt.encode({"sub": email, "exp": expires}, JWT_SECRET, algorithm=ALGORITHM)


def require_admin(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> Admin:
    unauthorized = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Admin sign-in required")
    if credentials is None:
        raise unauthorized
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[ALGORITHM])
        email = payload.get("sub")
    except JWTError:
        raise unauthorized
    admin = db.query(Admin).filter(Admin.email == email).first()
    if admin is None:
        raise unauthorized
    return admin