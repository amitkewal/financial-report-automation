import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import models
from app.core.database import SessionLocal, init_db
from app.core.security import hash_password
from app.routers import auth, clients, funds, mapping, reports, templates, uploads, validation

app = FastAPI(title="Multi-Client Financial Report Automation Platform", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(clients.router)
app.include_router(funds.router)
app.include_router(templates.router)
app.include_router(mapping.router)
app.include_router(uploads.router)
app.include_router(validation.router)
app.include_router(reports.router)


def _seed_admin():
    db = SessionLocal()
    try:
        if db.query(models.User).count() == 0:
            admin_email = os.environ.get("FRA_ADMIN_EMAIL", "admin@example.com")
            admin_password = os.environ.get("FRA_ADMIN_PASSWORD", "ChangeMe123!")
            db.add(
                models.User(
                    email=admin_email,
                    full_name="Platform Admin",
                    hashed_password=hash_password(admin_password),
                    role=models.Role.ADMIN,
                )
            )
            db.commit()
    finally:
        db.close()


@app.on_event("startup")
def on_startup():
    init_db()
    _seed_admin()


@app.get("/health")
def health():
    return {"status": "ok"}
