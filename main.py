
from fastapi import FastAPI
from risk_engine.score_route import score_route_segments

app = FastAPI(
    title="Pharos Risk API",
    description="Explainable road risk assessment API",
    version="1.0.0",
)


@app.get("/")
def home():
    return {
        "message": "Pharos Risk API is running!",
        "status": "success",
    }


@app.get("/risk")
def get_route_risk():
    segments = score_route_segments()

    return {
        "total_segments": len(segments),
        "segments": segments,
    }
