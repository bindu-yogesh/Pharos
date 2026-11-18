import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.app.integrations.osrm import OSRMError, get_route


class FakeAsyncClient:
    def __init__(self, payload):
        self.payload = payload
        self.request_url = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def get(self, *args, **kwargs):
        self.request_url = args[0]
        response = MagicMock()
        response.raise_for_status = MagicMock()
        response.json = MagicMock(return_value=self.payload)
        return response


@pytest.mark.parametrize("payload", [
    None,
    [],
    "invalid",
    123,
])
def test_get_route_rejects_non_object_json_response(payload):
    async def run():
        with patch(
            "backend.app.integrations.osrm.httpx.AsyncClient",
            side_effect=lambda **kwargs: FakeAsyncClient(payload),
        ):
            with pytest.raises(OSRMError):
                await get_route((75.0, 12.0), (75.1, 12.1))

    asyncio.run(run())


@pytest.mark.parametrize("routes", [
    None,
    {},
    "invalid",
    123,
])
def test_get_route_rejects_invalid_routes_collection(routes):
    async def run():
        payload = {"code": "Ok", "routes": routes}
        with patch(
            "backend.app.integrations.osrm.httpx.AsyncClient",
            side_effect=lambda **kwargs: FakeAsyncClient(payload),
        ):
            with pytest.raises(OSRMError):
                await get_route((75.0, 12.0), (75.1, 12.1))

    asyncio.run(run())


def test_get_route_rejects_empty_routes():
    async def run():
        payload = {"code": "Ok", "routes": []}
        with patch(
            "backend.app.integrations.osrm.httpx.AsyncClient",
            side_effect=lambda **kwargs: FakeAsyncClient(payload),
        ):
            with pytest.raises(OSRMError):
                await get_route((75.0, 12.0), (75.1, 12.1))

    asyncio.run(run())

def test_get_route_uses_configured_osrm_base_url(monkeypatch):
    from backend.app.integrations.osrm import settings

    async def run():
        payload = {"code": "Ok", "routes": [{}]}
        fake_client = FakeAsyncClient(payload)
        monkeypatch.setattr(
            settings,
            "osrm_base_url",
            "https://routing.example.com",
        )

        with patch(
            "backend.app.integrations.osrm.httpx.AsyncClient",
            return_value=fake_client,
        ):
            await get_route((75.0, 12.0), (75.1, 12.1))

        assert fake_client.request_url.startswith(
            "https://routing.example.com/route/v1/driving/"
        )

    asyncio.run(run())
