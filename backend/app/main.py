
from fastapi import FastAPI

from .models import User, Report

app = FastAPI(
    title="Pharos API",
    description="Backend API for the Pharos road safety system",
    version="0.1.0",
)


@app.get("/")
def root():
    return {"message": "Pharos API is running"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}
