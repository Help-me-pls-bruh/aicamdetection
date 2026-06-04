"""
Alert System - generates and manages alerts based on risk thresholds.
Triggers when risk score crosses HIGH (0.55) or CRITICAL (0.75).
"""

from datetime import datetime
from database.db_manager import insert_alert, get_recent_alerts, get_connection


class AlertSystem:
    def __init__(self):
        self.active_alerts = {}
        self.alert_cooldown = {}
        self.cooldown_seconds = 120

    def check_and_alert(self, zone_id, r_zone, risk_level, events=None):
        now = datetime.now()

        if zone_id in self.alert_cooldown:
            elapsed = (now - self.alert_cooldown[zone_id]).total_seconds()
            if elapsed < self.cooldown_seconds:
                return None

        if risk_level == "CRITICAL":
            alert = self._create_alert(zone_id, r_zone, risk_level, "CRITICAL_ALERT", events)
            self.alert_cooldown[zone_id] = now
            return alert

        elif risk_level == "HIGH":
            alert = self._create_alert(zone_id, r_zone, risk_level, "HIGH_ALERT", events)
            self.alert_cooldown[zone_id] = now
            return alert

        if zone_id in self.active_alerts and risk_level in ("LOW", "MEDIUM"):
            del self.active_alerts[zone_id]

        return None

    def _create_alert(self, zone_id, r_zone, risk_level, alert_type, events):
        event_summary = ""
        if events:
            parts = []
            for e in events[:5]:
                etype = e.get("event_type", "unknown")
                conf = e.get("confidence_score", 0)
                parts.append(f"{etype}({conf:.0%})")
            event_summary = " | ".join(parts)

        if alert_type == "CRITICAL_ALERT":
            description = f"CRITICAL: Zone {zone_id} risk at {r_zone:.0%}. {event_summary}"
        else:
            description = f"HIGH RISK: Zone {zone_id} risk at {r_zone:.0%}. {event_summary}"

        insert_alert(zone_id, r_zone, risk_level, alert_type, description)

        alert = {
            "zone_id": zone_id,
            "risk_score": r_zone,
            "risk_level": risk_level,
            "alert_type": alert_type,
            "description": description,
            "timestamp": datetime.now().isoformat(),
            "events": events or [],
        }

        self.active_alerts[zone_id] = alert

        if alert_type == "CRITICAL_ALERT":
            print(f"\n{'='*60}")
            print(f"  *** CRITICAL ALERT ***")
            print(f"  Zone: {zone_id}")
            print(f"  Risk: {r_zone:.0%}")
            print(f"  {event_summary}")
            print(f"{'='*60}\n")

        return alert

    def check_wanted_person_alert(self, event):
        if event.get("event_type") == "FACE_MATCH_WANTED":
            zone_id = "CAMERA_ZONE"
            person_name = event.get("person_name", "Unknown")
            description = (
                f"WANTED PERSON DETECTED: {person_name} | "
                f"Confidence: {event.get('confidence_score', 0):.0%} | "
                f"Location: ({event.get('latitude')}, {event.get('longitude')})"
            )

            insert_alert(zone_id, 0.99, "CRITICAL", "WANTED_PERSON", description)

            print(f"\n{'!'*60}")
            print(f"  *** WANTED PERSON DETECTED ***")
            print(f"  Name: {person_name}")
            print(f"  Confidence: {event.get('confidence_score', 0):.0%}")
            print(f"{'!'*60}\n")

            return {
                "zone_id": zone_id,
                "alert_type": "WANTED_PERSON",
                "person_name": person_name,
                "description": description,
                "timestamp": datetime.now().isoformat(),
            }
        return None

    def get_active_alerts(self):
        return list(self.active_alerts.values())

    def get_alert_history(self, limit=50):
        return get_recent_alerts(limit)
