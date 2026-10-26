
from math import cos, radians, sqrt


EARTH_RADIUS_M = 6_371_000


def distance_to_segment_m(latitude, longitude, segment):
    """Approximate distance from a coordinate to a segment in metres."""
    start_lon, start_lat = segment["start"]
    end_lon, end_lat = segment["end"]

    reference_lat = radians(latitude)
    metres_per_degree_lat = 111_320
    metres_per_degree_lon = 111_320 * cos(reference_lat)

    def project(lat, lon):
        return (
            (lon - longitude) * metres_per_degree_lon,
            (lat - latitude) * metres_per_degree_lat,
        )

    start_x, start_y = project(start_lat, start_lon)
    end_x, end_y = project(end_lat, end_lon)

    dx = end_x - start_x
    dy = end_y - start_y
    length_squared = dx * dx + dy * dy

    if length_squared == 0:
        return sqrt(start_x * start_x + start_y * start_y)

    fraction = -(start_x * dx + start_y * dy) / length_squared
    fraction = max(0.0, min(1.0, fraction))

    closest_x = start_x + fraction * dx
    closest_y = start_y + fraction * dy

    return sqrt(closest_x * closest_x + closest_y * closest_y)


def match_incidents_to_segments(
    incidents,
    segments,
    max_distance_m=500,
):
    """Return segment IDs with at least one nearby geolocated incident."""
    if max_distance_m < 0:
        raise ValueError("max_distance_m cannot be negative")

    matched = {segment["segment_id"]: [] for segment in segments}

    for incident in incidents:
        latitude = incident.get("latitude")
        longitude = incident.get("longitude")

        if latitude is None or longitude is None:
            continue

        nearest_segment = None
        nearest_distance = float("inf")

        for segment in segments:
            distance = distance_to_segment_m(
                latitude,
                longitude,
                segment,
            )

            if distance < nearest_distance:
                nearest_distance = distance
                nearest_segment = segment

        if (
            nearest_segment is not None
            and nearest_distance <= max_distance_m
        ):
            matched[nearest_segment["segment_id"]].append(
                incident["id"]
            )

    return matched
