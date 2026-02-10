from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session
from starlette import status

from backend.database.db import get_db
from backend.database.models import User
from backend.schemas import UserCreate, LoginRequest, LoginResponseToken, CurrentUser, LogoutResponse
from backend.database.security import hash_password, verify_password, create_access_token, get_current_user

router = APIRouter()

@router.post("/auth/register", response_model = LoginResponseToken)
def register(user: UserCreate, db: Session = Depends(get_db)):

    user_db = User(
        username = user.username,
        email = user.email,
        password= hash_password(user.password)
    )

    db.add(user_db)
    db.commit()
    db.refresh(user_db)

    token = create_access_token({"sub": str(user_db.user_id)})
    print("pw bytes:", len(user.password.encode("utf-8")))

    return {"access_token": token, "token_type": "bearer"}

@router.post("/auth/login", response_model=LoginResponseToken)
def login(payload: LoginRequest, db: Session = Depends(get_db)):

    user_db = (
        db.query(User)
        .filter(func.lower(User.email) == func.lower(payload.email))
        .first()
    )

    if user_db is None or not verify_password(payload.password, user_db.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    token = create_access_token({"sub": str(user_db.user_id)})

    return {"access_token": token, "token_type": "bearer"}

@router.get("/auth/me", response_model = CurrentUser)
def me(current_user: User = Depends(get_current_user)):
    return current_user

@router.post("/auth/logout", response_model = LogoutResponse)
def logout(current_user: User = Depends(get_current_user)):
    return {"status": "ok"}