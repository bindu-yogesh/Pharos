from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .models import User, Report
from .routers.auth import router as auth_router, profile_router
from .routers.reports import router as reports_router
from .routers.admin import router as admin_router
from .routers.routes import router as routes_router
from .routers.risk_routes import risk_router
from .routers.trips import router as trips_router
from .routers.devices import router as devices_router
from .services.trip_monitor import start_trip_monitor, stop_trip_monitor


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_trip_monitor()
    try:
        yield
    finally:
        stop_trip_monitor()


app = FastAPI(
    title="Pharos API",
    description="Backend API for the Pharos road safety system",
    version="0.1.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^http://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_router)
app.include_router(profile_router)
app.include_router(reports_router)
app.include_router(admin_router)
app.include_router(routes_router)
app.include_router(risk_router)
app.include_router(trips_router)
app.include_router(devices_router)


@app.get("/")
def root():
    return {"message": "Pharos API is running"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}
