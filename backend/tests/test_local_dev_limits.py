import asyncio
from types import SimpleNamespace

from fastapi.testclient import TestClient
from starlette.requests import Request

from app import main
from app.links import extract_product_id
from app.platforms.blinkit import BlinkitClient, _parse_snippets


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
    """When Playwright fetch fails (returns None), the result should be 'error'
    not 'out_of_stock'. A failed check is not the same as confirmed unavailability.
    """
    client = BlinkitClient(transport=None)

    async def fail_fetch(*args, **kwargs):
        return None

    monkeypatch.setattr(client, "_fetch_product_via_playwright", fail_fetch)

    async def run_checks() -> None:
        store = await client.resolve_store(12.9716, 77.5946, product_id="10532")
        product = await client.product_at_store("10532", "any", lat=12.9716, lng=77.5946)
        assert store.serviceable is True
        # Playwright failure → error, NOT out_of_stock (to avoid false "unavailable" signals)
        assert product.status == "error"
        await client.aclose()

    asyncio.run(run_checks())


def test_blinkit_parse_snippets_in_stock() -> None:
    """_parse_snippets must return in_stock when the product snippet has
    inventory=5, is_sold_out=False, product_state='available'.
    These fields live directly on the identity-matched snippet — not on a
    separate 'widget'-typed snippet as the old code expected.
    """
    snippets = [
        {
            "data": {
                "identity": {"id": "10532"},
                "variant": {"text": "250 g"},
                "normal_price": {"text": "₹160"},
                "inventory": 5,
                "is_sold_out": False,
                "product_state": "available",
                "stepper_data": {"state": {"title": {"text": "enabled"}}},
                "rfc_actions_v2": {
                    "default": [
                        {
                            "remove_from_cart": {
                                "cart_item": {
                                    "product_name": "Tata Tea Gold",
                                    "brand": "Tata Tea Gold",
                                    "unit": "250 g",
                                    "price": 160,
                                    "mrp": 160,
                                }
                            },
                            "type": "remove_from_cart",
                        }
                    ]
                },
                "atc_actions_v2": {"default": [None]},  # null ATC is typical for in-cart items
            }
        }
    ]
    result = _parse_snippets(snippets, "10532")
    assert result.status == "in_stock", f"Expected in_stock, got {result.status}"
    assert result.name == "Tata Tea Gold"
    assert result.price == 160.0
    assert result.raw_variant == "250 g"


def test_blinkit_parse_snippets_out_of_stock() -> None:
    """_parse_snippets must return out_of_stock when is_sold_out=True."""
    snippets = [
        {
            "data": {
                "identity": {"id": "99999"},
                "inventory": 0,
                "is_sold_out": True,
                "product_state": "sold_out",
                "rfc_actions_v2": {
                    "default": [
                        {
                            "remove_from_cart": {
                                "cart_item": {
                                    "product_name": "Some Product OOS",
                                    "price": 50,
                                    "mrp": 50,
                                    "unit": "500 ml",
                                }
                            }
                        }
                    ]
                },
            }
        }
    ]
    result = _parse_snippets(snippets, "99999")
    assert result.status == "out_of_stock", f"Expected out_of_stock, got {result.status}"


def test_blinkit_parse_snippets_not_carried() -> None:
    """_parse_snippets must return not_carried when no snippet matches the product ID."""
    snippets = [
        {"data": {"identity": {"id": "other"}, "inventory": 5}}
    ]
    result = _parse_snippets(snippets, "10532")
    assert result.status == "not_carried", f"Expected not_carried, got {result.status}"

