import pytest
import sqlite3
import tempfile
from pathlib import Path
from datetime import datetime, timezone
from dataclasses import dataclass

from app.store_cache import StoreCache, Store

@pytest.fixture
def cache():
    with tempfile.TemporaryDirectory() as d:
        db_path = Path(d) / "test.db"
        c = StoreCache(db_path)
        yield c
        c.close()

def test_a_new_store_insert(cache: StoreCache):
    store = cache.record_probe(
        lat=12.9716, lng=77.5946,
        store_id="store_1", store_name="Bangalore Central",
        city="Bangalore", pincode="560001", platform="zepto"
    )
    
    assert store is not None
    assert store.id == "store_1"
    assert store.pincode == "560001"
    assert store.lat == 12.9716
    assert store.lng == 77.5946
    
    # Verify in DB
    row = cache._db.execute("SELECT id, platform, name, city, pincode, lat, lng, probe_count, discovered_at, last_seen_at FROM stores WHERE id = 'store_1'").fetchone()
    assert row is not None
    assert row[0] == "store_1"
    assert row[1] == "zepto"
    assert row[4] == "560001"
    assert row[5] == 12.9716
    assert row[6] == 77.5946
    assert row[7] == 1 # probe_count
    assert row[8] == row[9] # discovered_at == last_seen_at initially

def test_b_existing_store_update(cache: StoreCache):
    cache.record_probe(
        lat=12.9716, lng=77.5946,
        store_id="store_2", store_name="Store 2",
        city="City A", pincode="123456", platform="zepto"
    )
    # Update
    cache.record_probe(
        lat=12.9716, lng=77.5946,
        store_id="store_2", store_name="Store 2 Updated",
        city="City A", pincode="123456", platform="zepto"
    )
    
    row = cache._db.execute("SELECT probe_count, name FROM stores WHERE id = 'store_2'").fetchone()
    assert row[0] == 2
    assert row[1] == "Store 2 Updated"
    
def test_c_missing_pincode(cache: StoreCache):
    store = cache.record_probe(
        lat=12.9716, lng=77.5946,
        store_id="store_3", store_name="Store 3",
        city="City B", pincode=None, platform="swiggy"
    )
    
    assert store.pincode is None
    
    row = cache._db.execute("SELECT pincode FROM stores WHERE id = 'store_3'").fetchone()
    assert row[0] is None
    
def test_d_address_cache(cache: StoreCache):
    from app.geocoder import AddressResult
    res = AddressResult(
        formatted_address="Test Address, 560001",
        short_address="Test Address",
        confidence="HIGH",
        provider="nominatim",
        pincode="560001"
    )
    cache.save_address(12.9716, 77.5946, res)
    
    cached = cache.get_address(12.9716, 77.5946)
    assert cached is not None
    assert cached.formatted_address == "Test Address, 560001"
    assert cached.pincode == "560001"
    
def test_f_geographic_isolation(cache: StoreCache):
    cache.record_probe(
        lat=12.9716, lng=77.5946,
        store_id="store_geo", store_name="Geo Store",
        city="Geo City", pincode="560001", platform="zepto"
    )
    
    # A store is only within radius if it was discovered by a probe point within that radius.
    stores = cache.stores_within(12.9716, 77.5946, 2.0, "zepto")
    assert len(stores) == 1
    assert stores[0].id == "store_geo"
    
    stores_far = cache.stores_within(13.9716, 78.5946, 2.0, "zepto")
    assert len(stores_far) == 0

