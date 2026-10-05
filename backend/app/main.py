from .database import Base, engine
from . import models
from fastapi import FastAPI
Base.metadata.create_all(bind=engine)

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