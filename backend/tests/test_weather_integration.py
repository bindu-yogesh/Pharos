
import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from backend.app.integrations.weather import (
    WeatherForecastError,
    get_weather_forecast,
)


def test_returns_forecast_near_arrival_time():
    payload = {
        "hourly": {
            "time": [
                "2026-10-28T10:00",
                "2026-10-28T11:00",
            ],
            "precipitation": [2.5, 8.0],
            "visibility": [10000, 3000],
        }
    }

    response = MagicMock()
    response.raise_for_status.return_value = None
    response.json.return_value = payload

    client = AsyncMock()
    client.get.return_value = response

    with patch(
        "backend.app.integrations.weather.httpx.AsyncClient"
    ) as client_class:
        client_class.return_value.__aenter__.return_value = client

        result = asyncio.run(
            get_weather_forecast(
                12.85,
                75.60,
                datetime(
                    2026, 10, 28, 10, 50, tzinfo=timezone.utc
                ),
            )
        )

    assert result["precipitation_mm"] == 8.0
    assert result["visibility_m"] == 3000.0
    assert result["forecast_time"] == "2026-10-28T11:00:00+00:00"
    assert result["source"] == "Open-Meteo"


def test_rejects_invalid_coordinates():
    with pytest.raises(ValueError, match="Latitude"):
        asyncio.run(
            get_weather_forecast(
                95,
                75.6,
                datetime(
                    2026, 10, 28, 10, tzinfo=timezone.utc
                ),
            )
        )


def test_rejects_missing_hourly_data():
    response = MagicMock()
    response.raise_for_status.return_value = None
    response.json.return_value = {}

    client = AsyncMock()
    client.get.return_value = response

    with patch(
        "backend.app.integrations.weather.httpx.AsyncClient"
    ) as client_class:
        client_class.return_value.__aenter__.return_value = client

        with pytest.raises(WeatherForecastError):
            asyncio.run(
                get_weather_forecast(
                    12.85,
                    75.60,
                    datetime(
                        2026, 10, 28, 10, tzinfo=timezone.utc
                    ),
                )
            )


def test_handles_http_failure():
    client = AsyncMock()
    client.get.side_effect = httpx.ConnectError(
        "network unavailable"
    )

    with patch(
        "backend.app.integrations.weather.httpx.AsyncClient"
    ) as client_class:
        client_class.return_value.__aenter__.return_value = client

        with pytest.raises(WeatherForecastError):
            asyncio.run(
                get_weather_forecast(
                    12.85,
                    75.60,
                    datetime(
                        2026, 10, 28, 10, tzinfo=timezone.utc
                    ),
                )
            )
