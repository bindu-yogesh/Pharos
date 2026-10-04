import requests


# Temporary route points for OSRM testing.
# Final Shiradi Ghat coordinates will be verified later.
start = (75.71261, 12.87261)
end = (75.605, 12.806)


def create_segments(coordinates, edge_distances, target_length_m=1000):
    """
    Split the route into approximately 1 km segments.

    edge_distances are the actual road distances provided
    by OSRM for consecutive route points.
    """

    segments = []

    segment_id = 1
    segment_start = coordinates[0]

    segment_distance = 0
    edge_start = coordinates[0]

    for i in range(len(edge_distances)):

        edge_end = coordinates[i + 1]
        edge_distance = edge_distances[i]

        segment_distance += edge_distance

        if segment_distance >= target_length_m:

            segments.append(
                {
                    "segment_id": segment_id,
                    "start": segment_start,
                    "end": edge_end,
                    "length_m": round(
                        segment_distance,
                        2,
                    ),
                }
            )

            segment_id += 1

            segment_start = edge_end
            segment_distance = 0

        edge_start = edge_end

    # Add the final partial segment.
    if segment_distance > 0:

        segments.append(
            {
                "segment_id": segment_id,
                "start": segment_start,
                "end": coordinates[-1],
                "length_m": round(
                    segment_distance,
                    2,
                ),
            }
        )

    return segments


# --------------------------------------------------
# Get route from OSRM
# --------------------------------------------------

url = (
    f"https://router.project-osrm.org/route/v1/driving/"
    f"{start[0]},{start[1]};{end[0]},{end[1]}"
)

params = {
    "overview": "full",
    "geometries": "geojson",
    "annotations": "true",
}


response = requests.get(url, params=params)

print("Status code:", response.status_code)

data = response.json()

if data["code"] != "Ok":
    print("Routing failed:", data["code"])
    raise SystemExit(1)


# --------------------------------------------------
# Extract route information
# --------------------------------------------------

route = data["routes"][0]

coordinates = route["geometry"]["coordinates"]

annotation = route["legs"][0]["annotation"]

edge_distances = annotation["distance"]


print("Route distance:", route["distance"], "meters")
print("Route duration:", route["duration"], "seconds")
print("Number of route points:", len(coordinates))

print(
    "Number of OSRM edge distances:",
    len(edge_distances),
)

print(
    "Sum of OSRM edge distances:",
    round(sum(edge_distances), 2),
    "meters",
)


# --------------------------------------------------
# Create approximately 1 km segments
# --------------------------------------------------

segments = create_segments(
    coordinates,
    edge_distances,
)


print(
    "\nNumber of ~1 km segments:",
    len(segments),
)


print("\nFirst 5 segments:")

for segment in segments[:5]:
    print(segment)


# --------------------------------------------------
# Validate segmentation
# --------------------------------------------------

total_segment_distance = sum(
    segment["length_m"]
    for segment in segments
)

difference = route["distance"] - total_segment_distance


print("\nSegmentation validation:")

print(
    "OSRM route distance:",
    round(route["distance"], 2),
    "meters",
)

print(
    "Sum of segment distances:",
    round(total_segment_distance, 2),
    "meters",
)

print(
    "Difference:",
    round(difference, 2),
    "meters",
)
import json
from pathlib import Path


# --------------------------------------------------
# Save route segments
# --------------------------------------------------

output_file = Path("data/route_segments.json")

with open(output_file, "w", encoding="utf-8") as file:
    json.dump(segments, file, indent=2)

print("\nSaved route segments to:", output_file)