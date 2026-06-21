"""Fleet API - sole Postgres writer and agent tool layer for Shepherd."""
from fastapi import FastAPI

from app.routers import (
    accidents,
    attendance,
    care,
    config,
    customers,
    documents,
    drivers,
    events,
    km,
    kpi,
    maintenance_types,
    reports,
    vehicles,
)

app = FastAPI(
    title="Shepherd Fleet API",
    version="0.1.0",
    description=(
        "Internal tool layer for Shepherd fleet management. "
        "The only service that writes to Postgres. "
        "Enforces the permission matrix and ownership scope on every endpoint. "
        "Called by the LangGraph agent and n8n as typed tools."
    ),
    contact={"name": "Shepherd Team", "email": "team@shepherd.local"},
    docs_url="/docs",
    redoc_url="/redoc",
)

app.include_router(vehicles.router)
app.include_router(drivers.router)
app.include_router(customers.router)
app.include_router(km.router)
app.include_router(accidents.router)
app.include_router(care.router)
app.include_router(documents.router)
app.include_router(reports.router)
app.include_router(events.router)
app.include_router(config.router)
app.include_router(kpi.router)
app.include_router(attendance.router)
app.include_router(maintenance_types.router)


@app.get("/health", tags=["health"], summary="Health check", description="Returns 200 when the service is up.")
def health() -> dict:
    return {"status": "ok"}
