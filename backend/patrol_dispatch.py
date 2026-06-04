"""
Patrol Dispatch Engine  (H3 Spatial Intelligence layer)

Workflow:
    Crime Event (lat/lon)
        -> H3 cell
        -> nearest AVAILABLE patrol (haversine)
        -> distance + ETA
        -> dispatch recommendation (stored in DB)

PROTOTYPE NOTE: patrol units use SIMULATED GPS locations. The architecture is
designed to scale to real patrol units / live GPS feeds — only the data source
would change, not the logic.
"""

from datetime import datetime
from backend.h3_utils import (
    latlng_to_cell, cell_to_latlng, grid_disk, grid_distance,
    haversine_km, estimate_eta_minutes, DEFAULT_RES, HAS_H3,
)
from database.db_manager import (
    upsert_patrol, get_patrols, insert_dispatch, update_patrol_status,
)

# Simulated patrol units positioned around Kuala Lumpur.
# (Real deployment would stream these positions from vehicle GPS.)
SIMULATED_PATROLS = [
    {"patrol_id": "PATROL_ALPHA",   "name": "Patrol Alpha",   "lat": 3.1466, "lon": 101.7108},  # Bukit Bintang
    {"patrol_id": "PATROL_BRAVO",   "name": "Patrol Bravo",   "lat": 3.1635, "lon": 101.6985},  # Chow Kit
    {"patrol_id": "PATROL_CHARLIE", "name": "Patrol Charlie", "lat": 3.1343, "lon": 101.6864},  # KL Sentral
    {"patrol_id": "PATROL_DELTA",   "name": "Patrol Delta",   "lat": 3.1897, "lon": 101.7150},  # Setapak
    {"patrol_id": "PATROL_ECHO",    "name": "Patrol Echo",    "lat": 3.1290, "lon": 101.6713},  # Bangsar
    {"patrol_id": "PATROL_FOXTROT", "name": "Patrol Foxtrot", "lat": 3.1579, "lon": 101.7650},  # Ampang
]

# Each patrol "covers" a k-ring of hexagons around its position.
COVERAGE_K = 3


class PatrolDispatch:
    def __init__(self, resolution=DEFAULT_RES):
        self.resolution = resolution

    def seed_patrols(self, force=False):
        """Create simulated patrol units (idempotent unless force=True)."""
        existing = get_patrols()
        if existing and not force:
            print(f"[PATROL] {len(existing)} patrol units already present.")
            return existing

        for p in SIMULATED_PATROLS:
            cell = latlng_to_cell(p["lat"], p["lon"], self.resolution)
            upsert_patrol(p["patrol_id"], p["name"], p["lat"], p["lon"], cell, "AVAILABLE")
        print(f"[PATROL] Seeded {len(SIMULATED_PATROLS)} simulated patrol units. "
              f"(H3 active: {HAS_H3})")
        return get_patrols()

    def get_coverage(self, patrol):
        """Return the list of H3 cells a patrol covers (k-ring around it)."""
        cell = patrol.get("h3_index")
        if not cell:
            cell = latlng_to_cell(patrol["latitude"], patrol["longitude"], self.resolution)
        return grid_disk(cell, COVERAGE_K)

    def get_all_coverage(self):
        """{patrol_id: {name, center_cell, cells:[...]}} for every patrol."""
        coverage = {}
        for patrol in get_patrols():
            cells = self.get_coverage(patrol)
            coverage[patrol["patrol_id"]] = {
                "name": patrol["name"],
                "center_cell": patrol.get("h3_index"),
                "cells": cells,
                "cell_count": len(cells),
            }
        return coverage

    def find_nearest_patrol(self, lat, lon, only_available=True):
        """
        Find the closest patrol to an event location.
        Returns (patrol_dict, distance_km) or (None, None).
        """
        patrols = get_patrols()
        if only_available:
            avail = [p for p in patrols if p.get("status") == "AVAILABLE"]
            patrols = avail or patrols  # fall back to all if none free

        best, best_dist = None, None
        for p in patrols:
            d = haversine_km(lat, lon, p["latitude"], p["longitude"])
            if best_dist is None or d < best_dist:
                best, best_dist = p, d
        return best, best_dist

    def which_patrol_covers(self, event_cell):
        """
        Return the patrol responsible for the event's H3 cell.
        Coverage zones overlap, so among all patrols whose zone contains the
        cell we pick the one whose centre is closest (fewest hex steps).
        """
        if not event_cell:
            return None
        candidates = []
        for patrol in get_patrols():
            if event_cell in self.get_coverage(patrol):
                steps = grid_distance(event_cell, patrol.get("h3_index"))
                steps = steps if steps is not None and steps >= 0 else 999
                candidates.append((steps, patrol))
        if not candidates:
            return None
        candidates.sort(key=lambda x: x[0])
        return candidates[0][1]

    def recommend_dispatch(self, lat, lon, zone_id=None, risk_score=0.0,
                           alert_id=None, store=True):
        """
        Full dispatch recommendation for an incident.
        Returns a dict the dashboard can render directly.
        """
        event_cell = latlng_to_cell(lat, lon, self.resolution)
        patrol, distance_km = self.find_nearest_patrol(lat, lon)

        if patrol is None:
            return {
                "success": False,
                "reason": "No patrol units available.",
                "h3_index": event_cell,
            }

        eta = estimate_eta_minutes(distance_km)
        covering = self.which_patrol_covers(event_cell)
        hex_steps = grid_distance(event_cell, patrol.get("h3_index"))

        dispatch_id = None
        if store:
            dispatch_id = insert_dispatch(
                alert_id, zone_id, patrol["patrol_id"], lat, lon, event_cell,
                round(risk_score, 4), round(distance_km, 3), eta, "RECOMMENDED",
            )

        return {
            "success": True,
            "dispatch_id": dispatch_id,
            "event_lat": lat,
            "event_lon": lon,
            "h3_index": event_cell,
            "zone_id": zone_id,
            "risk_score": round(risk_score, 4),
            "nearest_patrol": {
                "patrol_id": patrol["patrol_id"],
                "name": patrol["name"],
                "lat": patrol["latitude"],
                "lon": patrol["longitude"],
                "status": patrol.get("status"),
            },
            "distance_km": round(distance_km, 2),
            "eta_minutes": eta,
            "hex_distance": hex_steps,
            "covered_by": covering["name"] if covering else "Outside all coverage zones",
        }


if __name__ == "__main__":
    from database.db_manager import init_database
    init_database()
    pd = PatrolDispatch()
    pd.seed_patrols()

    print("\n--- Coverage zones ---")
    for pid, info in pd.get_all_coverage().items():
        print(f"  {info['name']:16s} covers {info['cell_count']} H3 cells "
              f"(center {info['center_cell']})")

    print("\n--- Dispatch test: incident at Chow Kit (3.1640, 101.6990) ---")
    rec = pd.recommend_dispatch(3.1640, 101.6990, zone_id="Z_TEST",
                                risk_score=0.91, store=False)
    import json
    print(json.dumps(rec, indent=2))
