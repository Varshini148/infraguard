"""
InfraGuard Authentication & User Management API Endpoints
"""

from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.database.connection import get_db
from backend.app.models.entities import User
from backend.app.schemas.domain import UserLogin, UserCreate, UserResponse, TokenResponse
from backend.app.security.auth import (
    hash_password, verify_password, create_access_token,
    get_current_user, require_roles, log_audit_trail
)

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/login", response_model=TokenResponse)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    """Authenticate authorized municipal staff and return JWT token."""
    user = db.query(User).filter(User.username == payload.username).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated"
        )

    user.last_login = datetime.utcnow()
    db.commit()

    token = create_access_token(data={"sub": str(user.id), "role": user.role, "name": user.full_name})
    log_audit_trail(db, user.id, "USER_LOGIN", "users", str(user.id), {"username": user.username})

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": user
    }

@router.get("/me", response_model=UserResponse)
def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """Get profile of current authenticated user."""
    return current_user

@router.get("/users", response_model=List[UserResponse])
def list_staff(
    current_user: User = Depends(require_roles(["admin"])),
    db: Session = Depends(get_db)
):
    """List all authorized staff (Admin only)."""
    return db.query(User).all()

@router.post("/users", response_model=UserResponse)
def create_staff_user(
    payload: UserCreate,
    current_user: User = Depends(require_roles(["admin"])),
    db: Session = Depends(get_db)
):
    """Register a new inspector or analyst (Admin only)."""
    existing = db.query(User).filter(
        (User.username == payload.username) | (User.email == payload.email)
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username or email already registered")

    new_user = User(
        username=payload.username,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role=payload.role,
        is_active=True
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    log_audit_trail(db, current_user.id, "CREATE_USER", "users", str(new_user.id), {"role": new_user.role})
    return new_user
