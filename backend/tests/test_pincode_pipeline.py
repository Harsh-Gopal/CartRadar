import asyncio
import sqlite3
import pytest
from datetime import datetime, timezone

from app.store_cache import StoreCache, Store
from app.geocoder import StoreAddressResolver, GeocodingProvider, AddressResult
from app.platforms.swiggy import SwiggyClient

class MockGeocoder(GeocodingProvider):
    async def reverse_geocode(self, lat: float, lng: float) -> AddressResult | None:
        if lat == 25.61 and lng == 85.12:
            return AddressResult(
                formatted_address="Warehouse A, Patna, Bihar, 803210",
                short_address="Warehouse A",
                confidence="HIGH",
                provider="mock",
                pincode="803210"
            )
        elif lat == 25.63 and lng == 85.11:
            return AddressResult(
                formatted_address="Near P&M Mall, Digha, Patna, Bihar, 800010",
                short_address="Near P&M Mall",
                confidence="HIGH",
                provider="mock",
                pincode="800010"
            )
        return None

@pytest.fixture
def cache(tmp_path):
    # Use in-memory or temp file DB for tests
    db_path = tmp_path / "test_mega.db"
    return StoreCache(db_path)

@pytest.fixture
def resolver():
    return StoreAddressResolver(geocoder=MockGeocoder())

@pytest.mark.asyncio
async def test_every_real_store_has_pincode_after_geocode(cache, resolver):
    store = Store(id="123", name="Test", city=None, pincode=None, lat=25.61, lng=85.12, platform="mock")
    await resolver.resolve_for_store(store, cache)
    assert store.pincode == "803210"
    assert "803210" in store.city

@pytest.mark.asyncio
async def test_missing_pincode_does_not_fail_result(cache, resolver):
    store = Store(id="456", name="Test", city=None, pincode=None, lat=1.0, lng=1.0, platform="mock")
    await resolver.resolve_for_store(store, cache)
    assert store.pincode is None
    assert store.city is None

@pytest.mark.asyncio
async def test_pincode_survives_db_roundtrip(cache):
    now = datetime.now(timezone.utc).isoformat()
    # Insert a store
    cache._upsert_store(25.61, 85.12, "123", "Test", "Patna", "803210", now, "mock")
    cache._db.commit()

    # Read back via stores_within (needs a probe point first)
    cache._db.execute("INSERT INTO probed_points (lat, lng, platform, store_id, serviceable, probed_at) VALUES (?, ?, ?, ?, ?, ?)",
                      (25.61, 85.12, "mock", "123", 1, now))
    cache._db.commit()

    stores = cache.stores_within(25.61, 85.12, radius_km=5.0, platform="mock")
    assert len(stores) == 1
    assert stores[0].pincode == "803210"

@pytest.mark.asyncio
async def test_store_cannot_inherit_another_stores_pincode(cache, resolver):
    store_a = Store(id="A", name="A", city=None, pincode=None, lat=25.61, lng=85.12, platform="mock")
    store_b = Store(id="B", name="B", city=None, pincode=None, lat=25.63, lng=85.11, platform="mock")

    await resolver.resolve_for_store(store_a, cache)
    await resolver.resolve_for_store(store_b, cache)

    assert store_a.pincode == "803210"
    assert store_b.pincode == "800010"
    assert store_a.pincode != store_b.pincode

@pytest.mark.asyncio
async def test_stores_outside_radius_rejected(cache):
    now = datetime.now(timezone.utc).isoformat()
    # Store at (0, 0)
    cache._upsert_store(0.0, 0.0, "1", "Test", "City", "111111", now, "mock")
    cache._db.execute("INSERT INTO probed_points (lat, lng, platform, store_id, serviceable, probed_at) VALUES (?, ?, ?, ?, ?, ?)",
                      (0.0, 0.0, "mock", "1", 1, now))
    
    # Store at (10, 10) - far away
    cache._upsert_store(10.0, 10.0, "2", "Test2", "City2", "222222", now, "mock")
    cache._db.execute("INSERT INTO probed_points (lat, lng, platform, store_id, serviceable, probed_at) VALUES (?, ?, ?, ?, ?, ?)",
                      (10.0, 10.0, "mock", "2", 1, now))
    cache._db.commit()

    stores = cache.stores_within(0.0, 0.0, radius_km=5.0, platform="mock")
    assert len(stores) == 1
    assert stores[0].id == "1"

@pytest.mark.asyncio
async def test_stores_from_other_city_not_returned(cache):
    now = datetime.now(timezone.utc).isoformat()
    # Patna Store
    cache._upsert_store(25.6, 85.1, "patna_1", "Test", "Patna", "800001", now, "mock")
    cache._db.execute("INSERT INTO probed_points (lat, lng, platform, store_id, serviceable, probed_at) VALUES (?, ?, ?, ?, ?, ?)",
                      (25.6, 85.1, "mock", "patna_1", 1, now))
    
    # Bangalore Store
    cache._upsert_store(12.9, 77.6, "blr_1", "Test", "Bangalore", "560001", now, "mock")
    cache._db.execute("INSERT INTO probed_points (lat, lng, platform, store_id, serviceable, probed_at) VALUES (?, ?, ?, ?, ?, ?)",
                      (12.9, 77.6, "mock", "blr_1", 1, now))
    cache._db.commit()

    stores = cache.stores_within(25.6, 85.1, radius_km=10.0, platform="mock")
    assert len(stores) == 1
    assert stores[0].id == "patna_1"

@pytest.mark.asyncio
async def test_synthetic_swiggy_stores_not_persisted():
    client = SwiggyClient()
    # We can mock _fetch_page or just look at logic
    # The logic in resolve_store currently returns StoreResolution(serviceable=False, store_id=None)
    # when no store_id is found, preventing synthetic store creation.
    # We'll just verify the return object structure if no store_id is present in a mock html
    import app.platforms.swiggy as swiggy_mod
    
    async def mock_fetch(*args, **kwargs):
        return "<html></html>"
    
    swiggy_mod._fetch_page = mock_fetch
    
    res = await client.resolve_store(25.6, 85.1)
    assert res.serviceable is False
    assert res.store_id is None

@pytest.mark.asyncio
async def test_stable_warehouse_identity_across_scans(cache, resolver):
    now = datetime.now(timezone.utc).isoformat()
    store_id = "stable_1"
    
    # Scan 1
    store1 = Store(id=store_id, name="Test", city=None, pincode=None, lat=25.61, lng=85.12, platform="mock")
    await resolver.resolve_for_store(store1, cache)
    cache._upsert_store(store1.lat, store1.lng, store1.id, store1.name, store1.city, store1.pincode, now, store1.platform)
    
    # Scan 2 (Later time, maybe different name, but same store_id)
    now2 = datetime.now(timezone.utc).isoformat()
    store2 = Store(id=store_id, name="Test Updated", city=store1.city, pincode=store1.pincode, lat=25.61, lng=85.12, platform="mock")
    await resolver.resolve_for_store(store2, cache)
    updated_store = cache._upsert_store(store2.lat, store2.lng, store2.id, store2.name, store2.city, store2.pincode, now2, store2.platform)
    
    assert updated_store.id == store_id
    assert updated_store.pincode == "803210" # Unchanged
    assert updated_store.name == "Test Updated"
