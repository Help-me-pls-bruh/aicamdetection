import random
import math
from datetime import datetime, timedelta
from database.db_manager import get_connection, init_database

KL_CENTER_LAT = 3.1390
KL_CENTER_LON = 101.6869

CRIME_HOTSPOTS = [
    {"name": "Bukit Bintang", "lat": 3.1466, "lon": 101.7108, "intensity": 0.9},
    {"name": "Chow Kit", "lat": 3.1635, "lon": 101.6985, "intensity": 0.85},
    {"name": "Petaling Street", "lat": 3.1455, "lon": 101.6953, "intensity": 0.75},
    {"name": "KL Sentral", "lat": 3.1343, "lon": 101.6864, "intensity": 0.6},
    {"name": "Bangsar", "lat": 3.1290, "lon": 101.6713, "intensity": 0.5},
    {"name": "Ampang", "lat": 3.1579, "lon": 101.7650, "intensity": 0.55},
    {"name": "Setapak", "lat": 3.1897, "lon": 101.7150, "intensity": 0.65},
    {"name": "Kepong", "lat": 3.2078, "lon": 101.6360, "intensity": 0.45},
    {"name": "Sri Petaling", "lat": 3.0850, "lon": 101.6650, "intensity": 0.40},
    {"name": "Wangsa Maju", "lat": 3.1950, "lon": 101.7350, "intensity": 0.50},
]

CRIME_TYPES = [
    "THEFT_SNATCH", "ASSAULT", "ROBBERY", "BURGLARY",
    "VEHICLE_THEFT", "VANDALISM", "SUSPICIOUS_ACTIVITY", "DRUG_OFFENSE",
]

CRIME_TYPE_WEIGHTS = [0.25, 0.15, 0.15, 0.10, 0.10, 0.08, 0.12, 0.05]


def generate_crime_near_hotspot(hotspot, base_time):
    spread = 0.008
    lat = hotspot["lat"] + random.gauss(0, spread)
    lon = hotspot["lon"] + random.gauss(0, spread)

    hour = base_time.hour
    if 22 <= hour or hour <= 4:
        night_boost = 1.5
    elif 18 <= hour <= 22:
        night_boost = 1.2
    else:
        night_boost = 0.7

    is_weekend = base_time.weekday() >= 5
    weekend_boost = 1.3 if is_weekend else 1.0

    if random.random() > hotspot["intensity"] * night_boost * weekend_boost * 0.5:
        return None

    crime_type = random.choices(CRIME_TYPES, weights=CRIME_TYPE_WEIGHTS, k=1)[0]
    confidence = round(random.uniform(0.5, 0.98), 2)
    source = random.choice(["POLICE_DB", "POLICE_DB", "POLICE_DB", "CCTV_AI", "USER_APP"])

    return {
        "latitude": round(lat, 6),
        "longitude": round(lon, 6),
        "timestamp": base_time.isoformat(),
        "event_type": crime_type,
        "confidence_score": confidence,
        "source": source,
    }


def seed_historical_data(months=36, events_per_day_range=(15, 45)):
    init_database()
    conn = get_connection()

    existing = conn.execute("SELECT COUNT(*) FROM crime_events").fetchone()[0]
    if existing > 100:
        print(f"[SEED] Database already has {existing} events. Skipping seed.")
        conn.close()
        return

    print(f"[SEED] Generating {months} months of synthetic crime data for KL...")

    end_date = datetime.now()
    start_date = end_date - timedelta(days=months * 30)
    current_date = start_date
    total_events = 0
    batch = []

    while current_date < end_date:
        events_today = random.randint(*events_per_day_range)

        for _ in range(events_today):
            hotspot = random.choices(
                CRIME_HOTSPOTS,
                weights=[h["intensity"] for h in CRIME_HOTSPOTS],
                k=1,
            )[0]

            hour = random.choices(
                range(24),
                weights=[
                    3, 2, 2, 2, 1, 1, 2, 3, 4, 5, 5, 6,
                    6, 5, 5, 5, 6, 7, 8, 9, 9, 8, 6, 4,
                ],
                k=1,
            )[0]
            minute = random.randint(0, 59)
            event_time = current_date.replace(hour=hour, minute=minute, second=random.randint(0, 59))

            event = generate_crime_near_hotspot(hotspot, event_time)
            if event:
                batch.append(event)
                total_events += 1

        current_date += timedelta(days=1)

    from backend.zone_manager import ZoneManager
    zm = ZoneManager()
    zm.create_grid_zones()

    for event in batch:
        zone_id = zm.get_zone_id(event["latitude"], event["longitude"])
        conn.execute(
            """INSERT INTO crime_events (zone_id, latitude, longitude, timestamp,
               event_type, confidence_score, source, is_verified, label)
               VALUES (?, ?, ?, ?, ?, ?, ?, 1, 'TRUE_CRIME')""",
            (
                zone_id, event["latitude"], event["longitude"],
                event["timestamp"], event["event_type"],
                event["confidence_score"], event["source"],
            ),
        )

    conn.commit()
    conn.close()
    print(f"[SEED] Inserted {total_events} historical crime events across {months} months.")


if __name__ == "__main__":
    seed_historical_data()
