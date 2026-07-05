import math
from app.grid import hex_grid, haversine_km

points = hex_grid(30.73, 76.65, 5.0, 2.0)
for p in points:
    dist = haversine_km(30.73, 76.65, p[0], p[1])
    print(f"Dist: {dist:.2f} km")
