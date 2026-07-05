import asyncio
from types import SimpleNamespace

from fastapi.testclient import TestClient
from starlette.requests import Request

from app import main
from app.links import extract_product_id
from app.platforms.blinkit import BlinkitClient


class _FailIfCalled:
    def __getattr__(self, name: str):
        raise AssertionError(f"unexpected limiter call: {name}")


class _ReleaseOnlyGate:
    def __init__(self) -> None:
        self.released = 0

    def try_acquire(self) -> bool:
        raise AssertionError("localhost search should not touch the concurrency gate")

    def release(self) -> None:
        self.released += 1


class _FakeClient:
    platform_name = "zepto"
    display_name = "Zepto"

    async def aclose(self) -> None:
        return None


class _FakeCache:
    def close(self) -> None:
        return None


def _make_request(host: str = "localhost:8400") -> Request:
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/api/search",
        "raw_path": b"/api/search",
        "query_string": b"",
        "root_path": "",
        "headers": [(b"host", host.encode())],
        "client": ("127.0.0.1", 54321),
        "server": ("localhost", 8400),
        "app": SimpleNamespace(state=SimpleNamespace(limiter=_FailIfCalled())),
    }
    return Request(scope)


def test_localhost_requests_are_unmetered() -> None:
    request = _make_request()

    assert main._local_requests_are_unmetered(request) is True


def test_require_rate_skips_localhost_requests() -> None:
    request = _make_request()

    # The request should return cleanly without touching the limiter.
    asyncio.run(main.require_rate(request))


def test_localhost_search_skips_search_limits(monkeypatch) -> None:
    monkeypatch.setattr(main.config, "DEV_MODE", False)
    monkeypatch.setattr(main, "_create_clients", lambda: {"zepto": _FakeClient()})

    async def fake_run_search(*args, **kwargs):
        yield {
            "type": "done",
            "summary": {
                "in_stock": 0,
                "out_of_stock": 0,
                "not_carried": 0,
                "error": 0,
                "stores": 0,
            },
        }

    monkeypatch.setattr(main, "run_search", fake_run_search)

    with TestClient(main.app, base_url="http://localhost:8400") as client:
        main.app.state.search_gate = _ReleaseOnlyGate()
        main.app.state.limiter = _FailIfCalled()
        main.app.state.global_searches = _FailIfCalled()
        main.app.state.cache = _FakeCache()

        response = client.get(
            "/api/search",
            params={
                "pvid": "p1",
                "platform": "zepto",
                "lat": 12.9716,
                "lng": 77.5946,
                "radius_km": 3,
            },
        )

    assert response.status_code == 200
    assert "You've reached your search limit" not in response.text
    assert '"type": "done"' in response.text


def test_extract_swiggy_canonical_slug_link() -> None:
    platform, product_id = extract_product_id(
        "https://www.swiggy.com/instamart/p/happilo-premium-all-natural-fox-nuts-phool-makhana-3FBX227N1S"
    )

    assert platform == "swiggy"
    assert product_id == "3FBX227N1S"


def test_blinkit_gracefully_falls_back_when_blocked(monkeypatch) -> None:
    client = BlinkitClient(transport=None)

    async def fail_fetch(*args, **kwargs):
        raise main.PlatformError("blocked")

    monkeypatch.setattr(client, "_fetch_product_page", fail_fetch)

    async def run_checks() -> None:
        store = await client.resolve_store(12.9716, 77.5946, product_id="10532")
        product = await client.product_at_store("10532", "any", lat=12.9716, lng=77.5946)
        assert store.serviceable is False
        assert product.status == "not_carried"
        await client.aclose()

    asyncio.run(run_checks())
