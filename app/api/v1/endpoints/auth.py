from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ....core.database import get_db
from ....core.security import hash_password, verify_password, create_access_token
from ....models.models import User
from ....schemas.schemas import RegisterRequest, LoginRequest, AuthResponse, UserResponse
from ..deps import get_current_user

router = APIRouter()

@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    # Check if username or email exists
    if db.query(User).filter(User.email == req.email).first():
        raise HTTPException(status_code=400, detail="Email is already registered")
    if db.query(User).filter(User.username == req.username).first():
        raise HTTPException(status_code=400, detail="Username is already taken")

    user = User(
        email=req.email,
        username=req.username,
        display_name=req.displayName or req.username,
        hashed_password=hash_password(req.password),
        role="user"
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(subject=user.id)
    return AuthResponse(
        user=UserResponse(
            id=user.id,
            email=user.email,
            username=user.username,
            displayName=user.display_name,
            role=user.role,
            avatarUrl=user.avatar_url,
            createdAt=user.created_at
        ),
        accessToken=token
    )

@router.post("/login", response_model=AuthResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(
        (User.username == req.username_or_email) | (User.email == req.username_or_email)
    ).first()

    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username/email or password"
        )

    token = create_access_token(subject=user.id)
    return AuthResponse(
        user=UserResponse(
            id=user.id,
            email=user.email,
            username=user.username,
            displayName=user.display_name,
            role=user.role,
            avatarUrl=user.avatar_url,
            createdAt=user.created_at
        ),
        accessToken=token
    )

@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        username=current_user.username,
        displayName=current_user.display_name,
        role=current_user.role,
        avatarUrl=current_user.avatar_url,
        createdAt=current_user.created_at
    )

