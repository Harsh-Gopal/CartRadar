"""Geo helpers: haversine distance and hex probe grids."""

import math

EARTH_RADIUS_KM = 6371.0
KM_PER_DEG_LAT = 110.574


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def hex_grid(center_lat: float, center_lng: float, radius_km: float, spacing_km: float) -> list[tuple[float, float]]:
    """Hexagonally packed points covering a circle, sorted nearest-first.

    Includes the center point itself.
    """
    km_per_deg_lng = KM_PER_DEG_LAT * math.cos(math.radians(center_lat))
    row_step_km = spacing_km * math.sqrt(3) / 2
    points: list[tuple[float, float]] = []
    n_rows = int(radius_km / row_step_km) + 1
    for row in range(-n_rows, n_rows + 1):
        y_km = row * row_step_km
        x_offset = (spacing_km / 2) if row % 2 else 0.0
        n_cols = int(radius_km / spacing_km) + 1
        for col in range(-n_cols, n_cols + 1):
            x_km = col * spacing_km + x_offset
            if math.hypot(x_km, y_km) > radius_km:
                continue
            points.append((center_lat + y_km / KM_PER_DEG_LAT, center_lng + x_km / km_per_deg_lng))
    points.sort(key=lambda p: haversine_km(center_lat, center_lng, p[0], p[1]))
    return points
