from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app import models
from app.core.database import get_db
from app.core.security import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> models.User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise credentials_exception
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise credentials_exception
    user = db.query(models.User).filter(models.User.email == payload["sub"]).first()
    if user is None or not user.is_active:
        raise credentials_exception
    return user


def require_role(*roles: models.Role):
    def checker(user: models.User = Depends(get_current_user)) -> models.User:
        if user.role != models.Role.ADMIN and user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        return user

    return checker


def require_client_access(client_id: int, db: Session, user: models.User) -> None:
    if user.role == models.Role.ADMIN:
        return
    access = (
        db.query(models.UserClientAccess)
        .filter(
            models.UserClientAccess.user_id == user.id,
            models.UserClientAccess.client_id == client_id,
        )
        .first()
    )
    if not access:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No access to this client")


def require_fund_access(fund: models.Fund, db: Session, user: models.User) -> None:
    require_client_access(fund.client_id, db, user)
