def calculate_slope(elevation_start, elevation_end, length_m):
    if length_m <= 0:
        raise ValueError("Segment length must be greater than 0")

    elevation_change = elevation_end - elevation_start
    slope_percent = (elevation_change / length_m) * 100

    return slope_percent


def create_segments(points, segment_length_m=1000):
    segments = []

    for i in range(len(points) - 1):
        start = points[i]
        end = points[i + 1]

        segment = {
            "segment_id": i + 1,
            "start": start,
            "end": end,
            "length_m": segment_length_m,
        }

        segments.append(segment)

    return segments