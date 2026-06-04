import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "sentinelai.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_database():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS zones (
            zone_id         TEXT PRIMARY KEY,
            lat_min         REAL NOT NULL,
            lat_max         REAL NOT NULL,
            lon_min         REAL NOT NULL,
            lon_max         REAL NOT NULL,
            center_lat      REAL NOT NULL,
            center_lon      REAL NOT NULL,
            zone_type       TEXT DEFAULT 'urban',
            p_spatial       REAL DEFAULT 0.0,
            p_time          REAL DEFAULT 0.0,
            p_base          REAL DEFAULT 0.0,
            p_realtime      REAL DEFAULT 0.0,
            r_zone          REAL DEFAULT 0.0,
            risk_level      TEXT DEFAULT 'LOW',
            last_updated    TEXT
        );

        CREATE TABLE IF NOT EXISTS crime_events (
            event_id        INTEGER PRIMARY KEY AUTOINCREMENT,
            zone_id         TEXT,
            latitude        REAL NOT NULL,
            longitude       REAL NOT NULL,
            timestamp       TEXT NOT NULL,
            event_type      TEXT NOT NULL,
            confidence_score REAL DEFAULT 0.0,
            source          TEXT NOT NULL,
            is_verified     INTEGER DEFAULT 0,
            label           TEXT DEFAULT 'PENDING',
            FOREIGN KEY (zone_id) REFERENCES zones(zone_id)
        );

        CREATE TABLE IF NOT EXISTS realtime_events (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            zone_id         TEXT,
            latitude        REAL NOT NULL,
            longitude       REAL NOT NULL,
            timestamp       TEXT NOT NULL,
            event_type      TEXT NOT NULL,
            confidence_score REAL DEFAULT 0.0,
            source          TEXT NOT NULL,
            p_event         REAL DEFAULT 0.0,
            is_active       INTEGER DEFAULT 1,
            camera_id       TEXT,
            FOREIGN KEY (zone_id) REFERENCES zones(zone_id)
        );

        CREATE TABLE IF NOT EXISTS alerts (
            alert_id        INTEGER PRIMARY KEY AUTOINCREMENT,
            zone_id         TEXT,
            timestamp       TEXT NOT NULL,
            risk_score      REAL NOT NULL,
            risk_level      TEXT NOT NULL,
            alert_type      TEXT NOT NULL,
            description     TEXT,
            is_acknowledged INTEGER DEFAULT 0,
            officer_feedback TEXT,
            FOREIGN KEY (zone_id) REFERENCES zones(zone_id)
        );

        CREATE TABLE IF NOT EXISTS feedback (
            feedback_id     INTEGER PRIMARY KEY AUTOINCREMENT,
            alert_id        INTEGER,
            zone_id         TEXT,
            timestamp       TEXT NOT NULL,
            label           TEXT NOT NULL,
            officer_notes   TEXT,
            FOREIGN KEY (alert_id) REFERENCES alerts(alert_id),
            FOREIGN KEY (zone_id) REFERENCES zones(zone_id)
        );

        CREATE TABLE IF NOT EXISTS zone_risk_history (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            zone_id         TEXT,
            timestamp       TEXT NOT NULL,
            p_base          REAL,
            p_realtime      REAL,
            r_zone          REAL,
            risk_level      TEXT,
            FOREIGN KEY (zone_id) REFERENCES zones(zone_id)
        );

        CREATE TABLE IF NOT EXISTS wanted_persons (
            person_id       INTEGER PRIMARY KEY AUTOINCREMENT,
            name            TEXT NOT NULL,
            image_path      TEXT NOT NULL,
            crime_type      TEXT,
            danger_level    TEXT DEFAULT 'HIGH',
            is_active       INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS patrol_units (
            patrol_id       TEXT PRIMARY KEY,
            name            TEXT NOT NULL,
            latitude        REAL NOT NULL,
            longitude       REAL NOT NULL,
            h3_index        TEXT,
            status          TEXT DEFAULT 'AVAILABLE',
            last_updated    TEXT
        );

        CREATE TABLE IF NOT EXISTS dispatches (
            dispatch_id     INTEGER PRIMARY KEY AUTOINCREMENT,
            alert_id        INTEGER,
            zone_id         TEXT,
            patrol_id       TEXT,
            event_lat       REAL,
            event_lon       REAL,
            h3_index        TEXT,
            risk_score      REAL,
            distance_km     REAL,
            eta_minutes     REAL,
            status          TEXT DEFAULT 'RECOMMENDED',
            timestamp       TEXT NOT NULL,
            FOREIGN KEY (patrol_id) REFERENCES patrol_units(patrol_id)
        );

        CREATE INDEX IF NOT EXISTS idx_crime_zone ON crime_events(zone_id);
        CREATE INDEX IF NOT EXISTS idx_crime_timestamp ON crime_events(timestamp);
        CREATE INDEX IF NOT EXISTS idx_crime_type ON crime_events(event_type);
        CREATE INDEX IF NOT EXISTS idx_realtime_zone ON realtime_events(zone_id);
        CREATE INDEX IF NOT EXISTS idx_realtime_active ON realtime_events(is_active);
        CREATE INDEX IF NOT EXISTS idx_alerts_zone ON alerts(zone_id);
        CREATE INDEX IF NOT EXISTS idx_risk_history_zone ON zone_risk_history(zone_id);
    """)

    # --- Migration: add h3_index to crime_events if it doesn't exist yet ---
    existing_cols = [r[1] for r in cursor.execute("PRAGMA table_info(crime_events)").fetchall()]
    if "h3_index" not in existing_cols:
        cursor.execute("ALTER TABLE crime_events ADD COLUMN h3_index TEXT")
        print("[DB] Added h3_index column to crime_events.")

    conn.commit()
    conn.close()
    print("[DB] Database initialized successfully.")


def backfill_crime_h3(resolution=None):
    """
    Fill in the h3_index for any crime_events that don't have one yet.
    Safe to call repeatedly — only touches rows where h3_index IS NULL.
    """
    from backend.h3_utils import latlng_to_cell, DEFAULT_RES
    res = resolution or DEFAULT_RES
    conn = get_connection()
    rows = conn.execute(
        "SELECT event_id, latitude, longitude FROM crime_events WHERE h3_index IS NULL"
    ).fetchall()
    for r in rows:
        cell = latlng_to_cell(r["latitude"], r["longitude"], res)
        conn.execute(
            "UPDATE crime_events SET h3_index = ? WHERE event_id = ?",
            (cell, r["event_id"]),
        )
    conn.commit()
    conn.close()
    if rows:
        print(f"[DB] Backfilled H3 index for {len(rows)} crime events.")
    return len(rows)


def upsert_patrol(patrol_id, name, lat, lon, h3_index, status="AVAILABLE"):
    conn = get_connection()
    conn.execute(
        """INSERT INTO patrol_units (patrol_id, name, latitude, longitude, h3_index, status, last_updated)
           VALUES (?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(patrol_id) DO UPDATE SET
             name=excluded.name, latitude=excluded.latitude, longitude=excluded.longitude,
             h3_index=excluded.h3_index, status=excluded.status, last_updated=excluded.last_updated""",
        (patrol_id, name, lat, lon, h3_index, status, datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()


def get_patrols():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM patrol_units ORDER BY patrol_id").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_patrol_status(patrol_id, status):
    conn = get_connection()
    conn.execute(
        "UPDATE patrol_units SET status = ?, last_updated = ? WHERE patrol_id = ?",
        (status, datetime.now().isoformat(), patrol_id),
    )
    conn.commit()
    conn.close()


def insert_dispatch(alert_id, zone_id, patrol_id, event_lat, event_lon, h3_index,
                    risk_score, distance_km, eta_minutes, status="RECOMMENDED"):
    conn = get_connection()
    cur = conn.execute(
        """INSERT INTO dispatches (alert_id, zone_id, patrol_id, event_lat, event_lon,
           h3_index, risk_score, distance_km, eta_minutes, status, timestamp)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (alert_id, zone_id, patrol_id, event_lat, event_lon, h3_index,
         risk_score, distance_km, eta_minutes, status, datetime.now().isoformat()),
    )
    dispatch_id = cur.lastrowid
    conn.commit()
    conn.close()
    return dispatch_id


def get_recent_dispatches(limit=50):
    conn = get_connection()
    rows = conn.execute(
        """SELECT d.*, p.name AS patrol_name
           FROM dispatches d LEFT JOIN patrol_units p ON d.patrol_id = p.patrol_id
           ORDER BY d.timestamp DESC LIMIT ?""",
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_crime_h3_intensity(limit_cells=300):
    """
    Aggregate crime counts per H3 cell for the hotspot heatmap.
    Returns [{h3_index, crime_count}] sorted by count desc.
    """
    conn = get_connection()
    rows = conn.execute(
        """SELECT h3_index, COUNT(*) AS crime_count
           FROM crime_events WHERE h3_index IS NOT NULL
           GROUP BY h3_index ORDER BY crime_count DESC LIMIT ?""",
        (limit_cells,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def insert_crime_event(zone_id, lat, lon, timestamp, event_type, confidence, source):
    try:
        from backend.h3_utils import latlng_to_cell
        h3_index = latlng_to_cell(lat, lon)
    except Exception:
        h3_index = None
    conn = get_connection()
    conn.execute(
        """INSERT INTO crime_events (zone_id, latitude, longitude, timestamp,
           event_type, confidence_score, source, h3_index)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (zone_id, lat, lon, timestamp, event_type, confidence, source, h3_index),
    )
    conn.commit()
    conn.close()


def insert_realtime_event(zone_id, lat, lon, timestamp, event_type, confidence, source, p_event, camera_id=None):
    conn = get_connection()
    conn.execute(
        """INSERT INTO realtime_events (zone_id, latitude, longitude, timestamp,
           event_type, confidence_score, source, p_event, camera_id)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (zone_id, lat, lon, timestamp, event_type, confidence, source, p_event, camera_id),
    )
    conn.commit()
    conn.close()


def insert_alert(zone_id, risk_score, risk_level, alert_type, description):
    conn = get_connection()
    conn.execute(
        """INSERT INTO alerts (zone_id, timestamp, risk_score, risk_level, alert_type, description)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (zone_id, datetime.now().isoformat(), risk_score, risk_level, alert_type, description),
    )
    conn.commit()
    conn.close()


def get_historical_crimes(zone_id=None):
    conn = get_connection()
    if zone_id:
        rows = conn.execute(
            "SELECT * FROM crime_events WHERE zone_id = ? ORDER BY timestamp DESC", (zone_id,)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM crime_events ORDER BY timestamp DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_zones():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM zones").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_zone_risk(zone_id, p_spatial, p_time, p_base, p_realtime, r_zone, risk_level):
    now = datetime.now().isoformat()
    conn = get_connection()
    conn.execute(
        """UPDATE zones SET p_spatial=?, p_time=?, p_base=?, p_realtime=?,
           r_zone=?, risk_level=?, last_updated=? WHERE zone_id=?""",
        (p_spatial, p_time, p_base, p_realtime, r_zone, risk_level, now, zone_id),
    )
    conn.execute(
        """INSERT INTO zone_risk_history (zone_id, timestamp, p_base, p_realtime, r_zone, risk_level)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (zone_id, now, p_base, p_realtime, r_zone, risk_level),
    )
    conn.commit()
    conn.close()


def get_active_realtime_events(zone_id=None, minutes=15):
    conn = get_connection()
    if zone_id:
        rows = conn.execute(
            """SELECT * FROM realtime_events
               WHERE zone_id = ? AND is_active = 1
               AND timestamp >= datetime('now', ?)
               ORDER BY timestamp DESC""",
            (zone_id, f"-{minutes} minutes"),
        ).fetchall()
    else:
        rows = conn.execute(
            """SELECT * FROM realtime_events
               WHERE is_active = 1
               AND timestamp >= datetime('now', ?)
               ORDER BY timestamp DESC""",
            (f"-{minutes} minutes",),
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_recent_alerts(limit=50):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM alerts ORDER BY timestamp DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def submit_feedback(alert_id, zone_id, label, notes=""):
    conn = get_connection()
    conn.execute(
        """INSERT INTO feedback (alert_id, zone_id, timestamp, label, officer_notes)
           VALUES (?, ?, ?, ?, ?)""",
        (alert_id, zone_id, datetime.now().isoformat(), label, notes),
    )
    conn.execute(
        "UPDATE alerts SET officer_feedback = ? WHERE alert_id = ?",
        (label, alert_id),
    )
    if label == "TRUE_CRIME":
        conn.execute(
            "UPDATE crime_events SET is_verified = 1, label = 'TRUE_CRIME' WHERE zone_id = ? AND label = 'PENDING' ORDER BY timestamp DESC LIMIT 1",
            (zone_id,),
        )
    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_database()
