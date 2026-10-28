"""
InfraGuard Security and Authentication Module
Provides password hashing, JWT generation/validation, role-based access control (RBAC),
and audit trail logging.
"""

import os
import hmac
import hashlib
import base64
import json
import secrets
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from backend.app.database.connection import get_db
from backend.app.models.entities import User, AuditLog

SECRET_KEY = os.getenv("SECRET_KEY", "infraguard_super_secret_production_key_32_bytes_min!")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "480"))

security_bearer = HTTPBearer(auto_error=False)

def hash_password(password: str) -> str:
    """Hash a password using salted PBKDF2-HMAC-SHA256."""
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        100000
    )
    return f"{salt}${key.hex()}"

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against the salted hash."""
    try:
        parts = hashed_password.split('$')
        if len(parts) != 2:
            return False
        salt, stored_hash = parts[0], parts[1]
        key = hashlib.pbkdf2_hmac(
            'sha256',
            plain_password.encode('utf-8'),
            salt.encode('utf-8'),
            100000
        )
        return hmac.compare_digest(key.hex(), stored_hash)
    except Exception:
        return False

def _base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode('utf-8').rstrip('=')

def _base64url_decode(data: str) -> bytes:
    padding = '=' * (4 - (len(data) % 4)) if len(data) % 4 != 0 else ''
    return base64.urlsafe_b64decode(data + padding)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Generate a signed HS256 JWT."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        **to_encode,
        "exp": int(expire.timestamp()),
        "iat": int(datetime.utcnow().timestamp())
    }
    
    header_bytes = _base64url_encode(json.dumps(header).encode('utf-8'))
    payload_bytes = _base64url_encode(json.dumps(payload).encode('utf-8'))
    signing_input = f"{header_bytes}.{payload_bytes}"
    signature = hmac.new(
        SECRET_KEY.encode('utf-8'),
        signing_input.encode('utf-8'),
        hashlib.sha256
    ).digest()
    sig_bytes = _base64url_encode(signature)
    return f"{signing_input}.{sig_bytes}"

def decode_access_token(token: str) -> dict:
    """Verify and decode a signed HS256 JWT."""
    try:
        parts = token.split('.')
        if len(parts) != 3:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token structure")
        signing_input = f"{parts[0]}.{parts[1]}"
        expected_sig = hmac.new(
            SECRET_KEY.encode('utf-8'),
            signing_input.encode('utf-8'),
            hashlib.sha256
        ).digest()
        actual_sig = _base64url_decode(parts[2])
        if not hmac.compare_digest(expected_sig, actual_sig):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Signature verification failed")
        
        payload_bytes = _base64url_decode(parts[1])
        payload = json.loads(payload_bytes.decode('utf-8'))
        exp = payload.get("exp")
        if exp and datetime.utcnow().timestamp() > exp:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired")
        return payload
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")

def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
    db: Session = Depends(get_db)
) -> User:
    """Retrieve the authenticated user or raise 401."""
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = credentials.credentials
    payload = decode_access_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token missing subject")
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User account is inactive or not found")
    return user

def require_roles(allowed_roles: List[str]):
    """Role-based authorization dependency factory."""
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation requires one of the following roles: {', '.join(allowed_roles)}"
            )
        return current_user
    return role_checker

def log_audit_trail(
    db: Session,
    user_id: Optional[int],
    action: str,
    entity_type: str,
    entity_id: Optional[str] = None,
    details: Optional[dict] = None,
    ip_address: Optional[str] = None
):
    """Safely record an immutable audit log entry in the database."""
    try:
        details_str = json.dumps(details) if isinstance(details, (dict, list)) else (details or "")
        audit = AuditLog(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id else None,
            details=details_str,
            ip_address=ip_address,
            timestamp=datetime.utcnow()
        )
        db.add(audit)
        db.commit()
    except Exception as e:
        db.rollback()
        # Non-fatal log failure, does not disrupt primary operation
        print(f"Warning: Audit log error: {e}")
