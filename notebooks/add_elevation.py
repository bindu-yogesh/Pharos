import json
import requests
from pathlib import Path

# --------------------------------------------------
# Load route segments
# --------------------------------------------------
input_file = Path("data/route_segments.json")

with open(input_file, "r", encoding="utf-8") as file:
    segments = json.load(file)

# --------------------------------------------------
# Collect unique segment endpoints
# --------------------------------------------------
coordinates = []

for segment in segments:
    coordinates.append(tuple(segment["start"]))

# Add the final endpoint
coordinates.append(tuple(segments[-1]["end"]))

# --------------------------------------------------
# Prepare coordinates for Open-Meteo
# --------------------------------------------------
latitudes = ",".join(str(coord[1]) for coord in coordinates)
longitudes = ",".join(str(coord[0]) for coord in coordinates)

# --------------------------------------------------
# Request elevation data
# --------------------------------------------------
url = "https://api.open-meteo.com/v1/elevation"

params = {
    "latitude": latitudes,
    "longitude": longitudes,
}

response = requests.get(url, params=params)

print("Status code:", response.status_code)

response.raise_for_status()

data = response.json()

elevations = data["elevation"]

print("Number of elevation points:", len(elevations))

# --------------------------------------------------
# Add elevation to each segment
# --------------------------------------------------
for i, segment in enumerate(segments):
    segment["elevation_start_m"] = elevations[i]
    segment["elevation_end_m"] = elevations[i + 1]

# --------------------------------------------------
# Save updated segments
# --------------------------------------------------
output_file = Path("data/route_segments_elevation.json")

with open(output_file, "w", encoding="utf-8") as file:
    json.dump(segments, file, indent=2)

print("Saved elevation data to:", output_file)

# --------------------------------------------------
# Show first 5 segments
# --------------------------------------------------
print("\nFirst 5 segments with elevation:")

for segment in segments[:5]:
    print(
        segment["segment_id"],
        "Start elevation:", segment["elevation_start_m"],
        "m | End elevation:", segment["elevation_end_m"],
        "m"
    )