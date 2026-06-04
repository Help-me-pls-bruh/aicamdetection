"""
H3 Geospatial Utilities (Uber H3 hexagonal indexing).

Thin compatibility wrapper so the rest of the platform never has to care
whether the installed `h3` package is v4 (latlng_to_cell / grid_disk ...) or
the older v3 (geo_to_h3 / k_ring ...). If h3 isn't installed at all, every
function degrades gracefully instead of crashing.

Why hexagons? Traditional systems split a city into SQUARE grid cells. Square
cells have an inconsistent neighbour relationship (edge neighbours are closer
than diagonal neighbours). H3 hexagons have 6 equidistant neighbours, which
gives cleaner hotspot clustering and more realistic "nearest patrol" coverage.
"""

import math

try:
    import h3
    HAS_H3 = True
    # v4 renamed most functions. Detect which API is present.
    _H3_V4 = hasattr(h3, "latlng_to_cell")
except ImportError:
    HAS_H3 = False
    _H3_V4 = False
    print("[WARN] h3 not installed. Patrol/H3 features use lat-lon fallback. "
          "Install with: pip install h3")

# Resolution 8 ~= 0.46 km edge hexagons (comparable to the existing 500 m grid).
# Good city-scale resolution for KL patrol dispatch.
DEFAULT_RES = 8


def latlng_to_cell(lat, lng, res=DEFAULT_RES):
    """Convert a latitude/longitude into an H3 cell index (string)."""
    if not HAS_H3:
        # Fallback pseudo-cell: round coords to a grid so the rest of the
        # pipeline still has a stable string key to group by.
        return f"approx_{round(lat, 3)}_{round(lng, 3)}"
    if _H3_V4:
        return h3.latlng_to_cell(lat, lng, res)
    return h3.geo_to_h3(lat, lng, res)


def cell_to_latlng(cell):
    """Return the (lat, lng) centre of an H3 cell."""
    if not HAS_H3 or not isinstance(cell, str) or cell.startswith("approx_"):
        if isinstance(cell, str) and cell.startswith("approx_"):
            parts = cell.split("_")
            return float(parts[1]), float(parts[2])
        return 0.0, 0.0
    if _H3_V4:
        lat, lng = h3.cell_to_latlng(cell)
    else:
        lat, lng = h3.h3_to_geo(cell)
    return lat, lng


def cell_to_boundary(cell):
    """
    Return the hexagon outline as a list of [lat, lng] points
    (used to draw the cell polygon on the map).
    """
    if not HAS_H3 or not isinstance(cell, str) or cell.startswith("approx_"):
        return []
    if _H3_V4:
        boundary = h3.cell_to_boundary(cell)
    else:
        boundary = h3.h3_to_geo_boundary(cell)
    return [[pt[0], pt[1]] for pt in boundary]


def grid_disk(cell, k=1):
    """Return all cells within k rings of `cell` (the cell + its neighbours)."""
    if not HAS_H3 or not isinstance(cell, str) or cell.startswith("approx_"):
        return [cell]
    if _H3_V4:
        return list(h3.grid_disk(cell, k))
    return list(h3.k_ring(cell, k))


def grid_distance(cell_a, cell_b):
    """Return the hex-grid distance (number of steps) between two cells."""
    if not HAS_H3 or not isinstance(cell_a, str) or not isinstance(cell_b, str):
        return -1
    if cell_a.startswith("approx_") or cell_b.startswith("approx_"):
        return -1
    try:
        if _H3_V4:
            return h3.grid_distance(cell_a, cell_b)
        return h3.h3_distance(cell_a, cell_b)
    except Exception:
        return -1


def haversine_km(lat1, lon1, lat2, lon2):
    """Great-circle distance between two points in kilometres."""
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = (math.sin(dphi / 2) ** 2
         + math.cos(p1) * math.cos(p2) * math.sin(dlam / 2) ** 2)
    return 2 * R * math.asin(math.sqrt(a))


def estimate_eta_minutes(distance_km, avg_speed_kmh=30.0):
    """
    Rough patrol ETA assuming average urban response speed.
    30 km/h -> ~2 min per km (matches typical city patrol response).
    """
    if avg_speed_kmh <= 0:
        return 0.0
    return round(distance_km / avg_speed_kmh * 60, 1)


if __name__ == "__main__":
    # Quick self-test (Bukit Bintang, KL)
    lat, lng = 3.1466, 101.7108
    cell = latlng_to_cell(lat, lng)
    print("H3 available:", HAS_H3, "| v4 API:", _H3_V4)
    print("Cell:", cell)
    print("Centre:", cell_to_latlng(cell))
    print("Boundary points:", len(cell_to_boundary(cell)))
    print("Neighbours (k=1):", len(grid_disk(cell, 1)))
    print("ETA for 0.8 km:", estimate_eta_minutes(0.8), "min")
