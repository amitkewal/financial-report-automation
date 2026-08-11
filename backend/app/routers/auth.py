from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import models, schemas
from app.core.database import get_db
from app.core.security import create_access_token, hash_password, verify_password
from app.deps import get_current_user, require_role

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=schemas.Token)
def login(payload: schemas.LoginRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is inactive")
    token = create_access_token(subject=user.email, extra_claims={"role": user.role.value})
    return schemas.Token(access_token=token, user=user)


@router.get("/me", response_model=schemas.UserOut)
def me(current_user: models.User = Depends(get_current_user)):
    return current_user


@router.post("/users", response_model=schemas.UserOut, status_code=201)
def create_user(
    payload: schemas.UserCreate,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_role(models.Role.ADMIN)),
):
    if db.query(models.User).filter(models.User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    user = models.User(
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        role=payload.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/users", response_model=list[schemas.UserOut])
def list_users(db: Session = Depends(get_db), _: models.User = Depends(require_role(models.Role.ADMIN))):
    return db.query(models.User).order_by(models.User.id).all()


@router.post("/grant-client-access", status_code=204)
def grant_client_access(
    payload: schemas.ClientAccessGrant,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_role(models.Role.ADMIN)),
):
    exists = (
        db.query(models.UserClientAccess)
        .filter(
            models.UserClientAccess.user_id == payload.user_id,
            models.UserClientAccess.client_id == payload.client_id,
        )
        .first()
    )
    if exists:
        return
    db.add(models.UserClientAccess(user_id=payload.user_id, client_id=payload.client_id))
    db.commit()
