import re
from datetime import datetime, timedelta
from database.db_manager import get_connection, insert_crime_event, insert_realtime_event

CRIME_TYPE_MAP = {
    "snatch theft": "THEFT_SNATCH",
    "robbery-snatch": "THEFT_SNATCH",
    "street theft": "THEFT_SNATCH",
    "bag snatch": "THEFT_SNATCH",
    "pickpocket": "THEFT_SNATCH",
    "mugging": "ROBBERY",
    "armed robbery": "ROBBERY",
    "robbery": "ROBBERY",
    "assault": "ASSAULT",
    "fight": "ASSAULT",
    "physical altercation": "ASSAULT",
    "vehicle theft": "VEHICLE_THEFT",
    "car theft": "VEHICLE_THEFT",
    "motorcycle theft": "VEHICLE_THEFT",
    "burglary": "BURGLARY",
    "break-in": "BURGLARY",
    "vandalism": "VANDALISM",
    "suspicious activity": "SUSPICIOUS_ACTIVITY",
    "suspicious_running": "SUSPICIOUS_RUNNING",
    "loitering": "LOITERING",
    "crowd anomaly": "CROWD_ANOMALY",
    "crowd_anomaly": "CROWD_ANOMALY",
    "person chasing": "PERSON_CHASING",
    "person_chasing": "PERSON_CHASING",
    "weapon detected": "WEAPON_DETECTED",
    "weapon_detected": "WEAPON_DETECTED",
    "face match wanted": "FACE_MATCH_WANTED",
    "face_match_wanted": "FACE_MATCH_WANTED",
    "drug offense": "DRUG_OFFENSE",
}

VALID_SOURCES = {"CCTV_AI", "POLICE_DB", "USER_APP", "IOT_SENSOR"}

DUPLICATE_TIME_WINDOW_SEC = 300
DUPLICATE_DISTANCE_THRESHOLD = 0.002


def normalize_crime_type(raw_type):
    key = raw_type.strip().lower()
    if key in CRIME_TYPE_MAP:
        return CRIME_TYPE_MAP[key]
    cleaned = re.sub(r"[^a-z_]", "_", key).upper()
    return cleaned if cleaned else "UNKNOWN"


def normalize_timestamp(ts_string):
    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%d/%m/%Y %H:%M:%S",
        "%d-%m-%Y %H:%M:%S",
        "%Y/%m/%d %H:%M:%S",
        "%m/%d/%Y %H:%M:%S",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(ts_string, fmt).strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def validate_event(event):
    required = ["latitude", "longitude", "timestamp", "event_type", "source"]
    for field in required:
        if field not in event or event[field] is None:
            return False, f"Missing field: {field}"

    lat, lon = event["latitude"], event["longitude"]
    if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
        return False, "Invalid coordinates"

    if lat == 0 and lon == 0:
        return False, "Null island coordinates"

    return True, "OK"


def is_duplicate(event, zone_id):
    conn = get_connection()
    time_threshold = (
        datetime.strptime(event["timestamp"], "%Y-%m-%d %H:%M:%S")
        - timedelta(seconds=DUPLICATE_TIME_WINDOW_SEC)
    ).strftime("%Y-%m-%d %H:%M:%S")

    rows = conn.execute(
        """SELECT latitude, longitude FROM crime_events
           WHERE zone_id = ? AND event_type = ? AND timestamp >= ?""",
        (zone_id, event["event_type"], time_threshold),
    ).fetchall()
    conn.close()

    for row in rows:
        lat_diff = abs(row["latitude"] - event["latitude"])
        lon_diff = abs(row["longitude"] - event["longitude"])
        if lat_diff < DUPLICATE_DISTANCE_THRESHOLD and lon_diff < DUPLICATE_DISTANCE_THRESHOLD:
            return True
    return False


def ingest_event(raw_event, zone_manager):
    valid, msg = validate_event(raw_event)
    if not valid:
        return False, msg

    event = {
        "latitude": float(raw_event["latitude"]),
        "longitude": float(raw_event["longitude"]),
        "timestamp": normalize_timestamp(str(raw_event["timestamp"])),
        "event_type": normalize_crime_type(str(raw_event["event_type"])),
        "confidence_score": float(raw_event.get("confidence_score", 0.5)),
        "source": raw_event.get("source", "UNKNOWN").upper(),
    }

    if event["source"] not in VALID_SOURCES:
        event["source"] = "UNKNOWN"

    event["confidence_score"] = max(0.0, min(1.0, event["confidence_score"]))

    zone_id = zone_manager.get_zone_id(event["latitude"], event["longitude"])

    if is_duplicate(event, zone_id):
        return False, "Duplicate event detected"

    insert_crime_event(
        zone_id, event["latitude"], event["longitude"],
        event["timestamp"], event["event_type"],
        event["confidence_score"], event["source"],
    )

    return True, zone_id


def ingest_realtime_event(raw_event, zone_manager, p_event=0.0, camera_id=None):
    valid, msg = validate_event(raw_event)
    if not valid:
        return False, msg

    event = {
        "latitude": float(raw_event["latitude"]),
        "longitude": float(raw_event["longitude"]),
        "timestamp": normalize_timestamp(str(raw_event["timestamp"])),
        "event_type": normalize_crime_type(str(raw_event["event_type"])),
        "confidence_score": float(raw_event.get("confidence_score", 0.5)),
        "source": raw_event.get("source", "CCTV_AI").upper(),
    }

    zone_id = zone_manager.get_zone_id(event["latitude"], event["longitude"])

    insert_realtime_event(
        zone_id, event["latitude"], event["longitude"],
        event["timestamp"], event["event_type"],
        event["confidence_score"], event["source"],
        p_event, camera_id,
    )

    insert_crime_event(
        zone_id, event["latitude"], event["longitude"],
        event["timestamp"], event["event_type"],
        event["confidence_score"], event["source"],
    )

    return True, zone_id
