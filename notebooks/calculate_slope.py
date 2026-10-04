import sys
from pathlib import Path

# Add project root to Python path
sys.path.append(str(Path(__file__).resolve().parents[1]))

import json

from risk_engine.segmentation import calculate_slope

# --------------------------------------------------
# Load route segments with elevation
# --------------------------------------------------
input_file = Path("data/route_segments_elevation.json")

with open(input_file, "r", encoding="utf-8") as file:
    segments = json.load(file)


# --------------------------------------------------
# Calculate slope for each segment
# --------------------------------------------------
for segment in segments:
    slope = calculate_slope(
        segment["elevation_start_m"],
        segment["elevation_end_m"],
        segment["length_m"],
    )

    segment["slope_percent"] = round(slope, 2)


# --------------------------------------------------
# Save updated segments
# --------------------------------------------------
output_file = Path("data/route_segments_with_slope.json")

with open(output_file, "w", encoding="utf-8") as file:
    json.dump(segments, file, indent=2)


print("Saved slope data to:", output_file)

# --------------------------------------------------
# Show first 5 segments
# --------------------------------------------------
print("\nFirst 5 segments with slope:")

for segment in segments[:5]:
    print(
        f"Segment {segment['segment_id']}: "
        f"{segment['elevation_start_m']} m -> "
        f"{segment['elevation_end_m']} m | "
        f"Slope: {segment['slope_percent']}%"
    )