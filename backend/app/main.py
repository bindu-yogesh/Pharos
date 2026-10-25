
from fastapi import FastAPI

from .models import User, Report
from .routers.auth import router as auth_router, profile_router


app = FastAPI(
    title="Pharos API",
    description="Backend API for the Pharos road safety system",
    version="0.1.0",
)

# Authentication endpoints: /auth/register and /auth/login
app.include_router(auth_router)

# User profile endpoint: PUT /user/profile
app.include_router(profile_router)


@app.get("/")
def root():
    return {"message": "Pharos API is running"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}
