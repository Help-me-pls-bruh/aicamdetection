import math
from database.db_manager import get_connection

KL_CENTER_LAT = 3.1390
KL_CENTER_LON = 101.6869
GRID_SIZE_M = 500
EARTH_RADIUS_M = 6_371_000

LAT_RANGE = (3.05, 3.25)
LON_RANGE = (101.60, 101.80)


class ZoneManager:
    def __init__(self):
        self.zones = {}
        self.lat_step = GRID_SIZE_M / EARTH_RADIUS_M * (180 / math.pi)
        self.lon_step = GRID_SIZE_M / (
            EARTH_RADIUS_M * math.cos(math.radians(KL_CENTER_LAT))
        ) * (180 / math.pi)

    def create_grid_zones(self):
        conn = get_connection()
        existing = conn.execute("SELECT COUNT(*) FROM zones").fetchone()[0]
        if existing > 0:
            rows = conn.execute("SELECT * FROM zones").fetchall()
            for r in rows:
                self.zones[r["zone_id"]] = dict(r)
            conn.close()
            print(f"[ZONE] Loaded {len(self.zones)} existing zones.")
            return

        lat = LAT_RANGE[0]
        row_idx = 0
        while lat < LAT_RANGE[1]:
            col_idx = 0
            lon = LON_RANGE[0]
            while lon < LON_RANGE[1]:
                zone_id = f"Z_{row_idx:03d}_{col_idx:03d}"
                lat_max = lat + self.lat_step
                lon_max = lon + self.lon_step
                center_lat = (lat + lat_max) / 2
                center_lon = (lon + lon_max) / 2

                zone_data = {
                    "zone_id": zone_id,
                    "lat_min": round(lat, 6),
                    "lat_max": round(lat_max, 6),
                    "lon_min": round(lon, 6),
                    "lon_max": round(lon_max, 6),
                    "center_lat": round(center_lat, 6),
                    "center_lon": round(center_lon, 6),
                }
                self.zones[zone_id] = zone_data

                conn.execute(
                    """INSERT INTO zones (zone_id, lat_min, lat_max, lon_min, lon_max,
                       center_lat, center_lon)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        zone_id, zone_data["lat_min"], zone_data["lat_max"],
                        zone_data["lon_min"], zone_data["lon_max"],
                        zone_data["center_lat"], zone_data["center_lon"],
                    ),
                )
                lon += self.lon_step
                col_idx += 1
            lat += self.lat_step
            row_idx += 1

        conn.commit()
        conn.close()
        print(f"[ZONE] Created {len(self.zones)} grid zones ({GRID_SIZE_M}m x {GRID_SIZE_M}m).")

    def get_zone_id(self, lat, lon):
        if lat < LAT_RANGE[0] or lat > LAT_RANGE[1]:
            return "Z_OUTSIDE"
        if lon < LON_RANGE[0] or lon > LON_RANGE[1]:
            return "Z_OUTSIDE"

        row_idx = int((lat - LAT_RANGE[0]) / self.lat_step)
        col_idx = int((lon - LON_RANGE[0]) / self.lon_step)
        zone_id = f"Z_{row_idx:03d}_{col_idx:03d}"

        if zone_id in self.zones:
            return zone_id
        return "Z_OUTSIDE"

    def get_zone_center(self, zone_id):
        if zone_id in self.zones:
            z = self.zones[zone_id]
            return z.get("center_lat", 0), z.get("center_lon", 0)
        return KL_CENTER_LAT, KL_CENTER_LON

    def get_all_zone_ids(self):
        return list(self.zones.keys())

    def get_neighboring_zones(self, zone_id):
        parts = zone_id.split("_")
        if len(parts) != 3:
            return []
        row = int(parts[1])
        col = int(parts[2])
        neighbors = []
        for dr in [-1, 0, 1]:
            for dc in [-1, 0, 1]:
                if dr == 0 and dc == 0:
                    continue
                nid = f"Z_{row + dr:03d}_{col + dc:03d}"
                if nid in self.zones:
                    neighbors.append(nid)
        return neighbors
