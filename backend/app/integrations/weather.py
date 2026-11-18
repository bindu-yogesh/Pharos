
"""Open-Meteo hourly forecast integration.

Returns raw forecast values. Risk classification thresholds are deliberately
not defined here because the project rules still need team confirmation.
"""
from datetime import datetime, timezone
from typing import Any

import httpx


OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
REQUEST_TIMEOUT_SECONDS = 8.0


class WeatherForecastError(RuntimeError):
    """Raised when a usable Open-Meteo forecast cannot be retrieved."""


async def get_weather_forecast(
    latitude: float,
    longitude: float,
    arrival_time: datetime,
) -> dict[str, Any]:
    """Return hourly precipitation and visibility near the arrival time."""
    if not -90 <= latitude <= 90:
        raise ValueError("Latitude must be between -90 and 90")
    if not -180 <= longitude <= 180:
        raise ValueError("Longitude must be between -180 and 180")

    if arrival_time.tzinfo is None:
        arrival_time = arrival_time.replace(tzinfo=timezone.utc)

    arrival_utc = arrival_time.astimezone(timezone.utc)
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": "precipitation,visibility",
        "forecast_days": 7,
        "timezone": "GMT",
    }

    try:
        async with httpx.AsyncClient(
            timeout=REQUEST_TIMEOUT_SECONDS
        ) as client:
            response = await client.get(OPEN_METEO_URL, params=params)
            response.raise_for_status()
            payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise WeatherForecastError(
            "Unable to retrieve the weather forecast"
        ) from exc

    hourly = payload.get("hourly")
    if not isinstance(hourly, dict):
        raise WeatherForecastError("Forecast response has no hourly data")

    times = hourly.get("time")
    precipitation = hourly.get("precipitation")
    visibility = hourly.get("visibility")

    if not isinstance(times, list):
        raise WeatherForecastError("Forecast timestamps are missing")

    if not isinstance(precipitation, list) or not isinstance(
        visibility, list
    ):
        raise WeatherForecastError("Forecast weather values are missing")

    if not times or len(times) != len(precipitation) or len(times) != len(
        visibility
    ):
        raise WeatherForecastError("Forecast arrays are empty or inconsistent")

    try:
        forecast_times = [
            datetime.fromisoformat(value).replace(tzinfo=timezone.utc)
            for value in times
        ]
        index = min(
            range(len(forecast_times)),
            key=lambda i: abs(
                (forecast_times[i] - arrival_utc).total_seconds()
            ),
        )

        # Hourly forecasts are not precise enough to justify selecting a
        # distant hour for a segment's expected arrival.
        difference_seconds = abs(
            (forecast_times[index] - arrival_utc).total_seconds()
        )
        if difference_seconds > 30 * 60:
            raise WeatherForecastError(
                "No hourly forecast is close enough to the arrival time"
            )

        rainfall_mm = precipitation[index]
        visibility_m = visibility[index]

        if rainfall_mm is not None:
            rainfall_mm = float(rainfall_mm)
            if rainfall_mm < 0:
                raise ValueError("Negative precipitation")

        if visibility_m is not None:
            visibility_m = float(visibility_m)
            if visibility_m < 0:
                raise ValueError("Negative visibility")

    except (TypeError, ValueError, IndexError) as exc:
        if isinstance(exc, WeatherForecastError):
            raise
        raise WeatherForecastError(
            "Forecast contains invalid values"
        ) from exc

    return {
        "forecast_time": forecast_times[index].isoformat(),
        "precipitation_mm": rainfall_mm,
        "visibility_m": visibility_m,
        "source": "Open-Meteo",
    }
