from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.audit import log
from app.core.database import get_db
from app.deps import get_current_user, require_client_access, require_role

router = APIRouter(prefix="/clients", tags=["clients"])


@router.post("", response_model=schemas.ClientOut, status_code=201)
def create_client(
    payload: schemas.ClientCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_role(models.Role.ADMIN)),
):
    client = models.Client(**payload.model_dump())
    db.add(client)
    db.commit()
    db.refresh(client)
    log(db, "client", client.id, user.id, "create", client.name)
    return client


@router.get("", response_model=list[schemas.ClientOut])
def list_clients(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    query = db.query(models.Client)
    if user.role != models.Role.ADMIN:
        allowed_ids = [a.client_id for a in user.client_access]
        query = query.filter(models.Client.id.in_(allowed_ids)) if allowed_ids else query.filter(False)
    return query.order_by(models.Client.name).all()


@router.get("/{client_id}", response_model=schemas.ClientOut)
def get_client(client_id: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    require_client_access(client_id, db, user)
    client = db.get(models.Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client


@router.put("/{client_id}", response_model=schemas.ClientOut)
def update_client(
    client_id: int,
    payload: schemas.ClientUpdate,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_role(models.Role.ADMIN)),
):
    client = db.get(models.Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    for key, value in payload.model_dump().items():
        setattr(client, key, value)
    db.commit()
    db.refresh(client)
    log(db, "client", client.id, user.id, "update")
    return client


@router.delete("/{client_id}", status_code=204)
def delete_client(
    client_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_role(models.Role.ADMIN)),
):
    client = db.get(models.Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    db.delete(client)
    db.commit()
    log(db, "client", client_id, user.id, "delete")
