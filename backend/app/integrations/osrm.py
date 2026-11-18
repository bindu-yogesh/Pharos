"""OSRM routing service integration."""

import httpx

from ..core.config import settings

OSRM_TIMEOUT_SECONDS = 10.0


class OSRMError(Exception):
    """Raised when the OSRM routing service fails."""


async def get_route(
    origin: tuple[float, float],
    destination: tuple[float, float],
    alternatives: bool = True,
) -> dict:
    """Fetch driving routes from OSRM.

    Coordinates must be (longitude, latitude).
    Returns the OSRM response containing route geometry and metadata.
    """
    coordinates = (
        f"{origin[0]},{origin[1]};"
        f"{destination[0]},{destination[1]}"
    )
    url = f"{settings.osrm_base_url}/route/v1/driving/{coordinates}"

    params = {
    "overview": "full",
    "geometries": "geojson",
    "steps": "true",
    "annotations": "true",
    "alternatives": str(alternatives).lower(),
}

    try:
        async with httpx.AsyncClient(
            timeout=OSRM_TIMEOUT_SECONDS
        ) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
    except httpx.TimeoutException as exc:
        raise OSRMError("OSRM routing request timed out.") from exc
    except httpx.HTTPError as exc:
        raise OSRMError("OSRM routing service is unavailable.") from exc
    except ValueError as exc:
        raise OSRMError("OSRM returned an invalid response.") from exc

    if not isinstance(data, dict):
        raise OSRMError("OSRM returned an invalid response.")

    routes = data.get("routes")
    if (
        data.get("code") != "Ok"
        or not isinstance(routes, list)
        or not routes
        or not all(isinstance(route, dict) for route in routes)
    ):
        raise OSRMError("No valid route was found between these locations.")

    return data