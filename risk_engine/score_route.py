
import json #reads out generated JSON route data
from pathlib import Path #locates data file realated to the project not the current terminals directory

from risk_engine.scorer import calculate_risk

PROJECT_ROOT = Path(__file__).resolve().parents[1]

ROUTE_DATA_FILE = (
    PROJECT_ROOT
    / "data"
    / "route_segments_with_slope.json"
)

STEEP_SLOPE_THRESHOLD = 6.0

#reads the segmented list from disk 
def load_route_segments():
    with open(ROUTE_DATA_FILE, "r", encoding="utf-8") as file:
        return json.load(file)

#calculates the score for each segment
def score_route_segments():
    segments = load_route_segments()
    results = []

    for segment in segments:
        slope = segment["slope_percent"]

        is_steep = abs(slope) >= STEEP_SLOPE_THRESHOLD  # detects both steep climbs and descents 

        risk = calculate_risk(
            steep_slope=is_steep
        )

        results.append({
            "segment_id": segment["segment_id"],
            "length_m": segment["length_m"],
            "slope_percent": slope,
            "risk_score": risk["score"],
            "risk_level": risk["level"],
            "reasons": risk["reasons"],
        })

    return results


#runs the demonstration only when this file is executed directly; importing it from a test or another module won't automatically print results.
if __name__ == "__main__":
    scored_segments = score_route_segments()

    for segment in scored_segments:
        print(
            f"Segment {segment['segment_id']}: "
            f"slope={segment['slope_percent']}%, "
            f"score={segment['risk_score']}, "
            f"level={segment['risk_level']}, "
            f"reasons={segment['reasons']}"
        )
