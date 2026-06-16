from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from config import settings
from database import engine
import models
from routers import (
    admin,
    auth,
    dashboard,
    settings as settings_router,
    properties,
    units,
    lessees,
    rental_agreements,
    invoices,
    payments,
    expenses,
    documents,
    vat,
    webhooks,
)

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Crassus Property Management", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

V1 = "/v1"

app.include_router(auth.router, prefix=V1)
app.include_router(dashboard.router, prefix=V1)
app.include_router(settings_router.router, prefix=V1)
app.include_router(properties.router, prefix=V1)
app.include_router(units.router, prefix=V1)
app.include_router(lessees.router, prefix=V1)
app.include_router(rental_agreements.router, prefix=V1)
app.include_router(invoices.router, prefix=V1)
app.include_router(payments.router, prefix=V1)
app.include_router(expenses.router, prefix=V1)
app.include_router(documents.router, prefix=V1)
app.include_router(vat.router, prefix=V1)
app.include_router(admin.router, prefix=V1)
app.include_router(webhooks.router, prefix=V1)
