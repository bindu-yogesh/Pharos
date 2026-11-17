from fastapi import FastAPI

from .models import User, Report
from .routers.routes import assess_route, router as routes_router
from .schemas.route import RouteResponse

app = FastAPI(
    title="Pharos API",
    description="Backend API for the Pharos road safety system",
    version="0.1.0",
)

app.include_router(routes_router)

# Backward-compatible alias matching the README API contract.
app.add_api_route(
    "/route",
    assess_route,
    methods=["POST"],
    response_model=RouteResponse,
    tags=["Routing and Risk"],
)


@app.get("/")
def root():
    return {"message": "Pharos API is running"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}
