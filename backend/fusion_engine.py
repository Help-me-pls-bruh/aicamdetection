"""
Probabilistic Risk Fusion Engine (Core Innovation)
Implements all formulas from the SentinelAI specification:

1. P_base = w1*P_spatial + w2*P_time
2. P_event = AI_confidence x Event_Reliability_Weight
3. P_combined = 1 - Product(1 - P_event_i * Decay_i)
   Each event type decays at its own rate (per-category redundancy decay)
4. W_context = W_time x W_crowd x W_recency x W_zone
5. P_realtime = P_combined x W_context
6. Final Risk = alpha*P_base + beta*P_realtime
7. Continuous recalculation with exponential decay (zone-level + per-event)
8. Per-event-type decay intervals (EVENT_DECAY_INTERVALS)
"""

import math
from datetime import datetime, timedelta
from database.db_manager import (
    get_connection, get_active_realtime_events,
    update_zone_risk,
)

EVENT_RELIABILITY_WEIGHTS = {
    "SUSPICIOUS_RUNNING": 0.3,
    "LOITERING": 0.2,
    "CROWD_ANOMALY": 0.5,
    "PERSON_CHASING": 0.7,
    "WEAPON_DETECTED": 0.9,
    "FACE_MATCH_WANTED": 0.95,
    "ASSAULT": 0.7,
    "THEFT_SNATCH": 0.6,
    "ROBBERY": 0.75,
    "SUSPICIOUS_ACTIVITY": 0.3,
    "FIGHTING": 0.7,
    "ABANDONED_OBJECT": 0.4,
    "VEHICLE_THEFT": 0.5,
    "BURGLARY": 0.5,
    "VANDALISM": 0.25,
    "DRUG_OFFENSE": 0.4,
}

ALPHA = 0.4
BETA = 0.6

GAMMA_RECALC = 0.6

RISK_THRESHOLDS = [
    (0.75, "CRITICAL", "RED"),
    (0.55, "HIGH", "ORANGE"),
    (0.30, "MEDIUM", "YELLOW"),
    (0.00, "LOW", "GREEN"),
]

EVENT_DECAY_INTERVALS = {
    "SUSPICIOUS_RUNNING":  {"lambda": 0.08, "recalc_sec": 60},
    "LOITERING":           {"lambda": 0.04, "recalc_sec": 180},
    "CROWD_ANOMALY":       {"lambda": 0.05, "recalc_sec": 120},
    "PERSON_CHASING":      {"lambda": 0.06, "recalc_sec": 90},
    "WEAPON_DETECTED":     {"lambda": 0.01, "recalc_sec": 300},
    "FACE_MATCH_WANTED":   {"lambda": 0.005, "recalc_sec": 600},
    "ASSAULT":             {"lambda": 0.03, "recalc_sec": 120},
    "THEFT_SNATCH":        {"lambda": 0.04, "recalc_sec": 120},
    "ROBBERY":             {"lambda": 0.03, "recalc_sec": 150},
    "SUSPICIOUS_ACTIVITY": {"lambda": 0.10, "recalc_sec": 60},
    "FIGHTING":            {"lambda": 0.03, "recalc_sec": 120},
    "ABANDONED_OBJECT":    {"lambda": 0.05, "recalc_sec": 180},
    "VEHICLE_THEFT":       {"lambda": 0.04, "recalc_sec": 150},
    "BURGLARY":            {"lambda": 0.04, "recalc_sec": 150},
    "VANDALISM":           {"lambda": 0.08, "recalc_sec": 90},
    "DRUG_OFFENSE":        {"lambda": 0.05, "recalc_sec": 120},
}
DEFAULT_EVENT_DECAY = {"lambda": 0.05, "recalc_sec": 120}


class FusionEngine:
    def __init__(self):
        self.zone_previous_scores = {}

    def compute_p_event(self, ai_confidence, event_type):
        """
        P_event = AI_confidence x Event Reliability Weight
        """
        weight = EVENT_RELIABILITY_WEIGHTS.get(event_type, 0.3)
        p_event = ai_confidence * weight
        return round(min(p_event, 1.0), 4)

    def compute_p_combined(self, events):
        """
        P_combined = 1 - Product(1 - P_event_i * Decay_i)

        Each event's P_event decays at a rate specific to its crime category:
          Decay_i = e^(-lambda_category * elapsed_minutes)
        High-severity events (weapon, wanted face) decay very slowly;
        low-severity events (running, suspicious activity) decay fast.
        """
        if not events:
            return 0.0

        now = datetime.now()
        product = 1.0
        for event in events:
            p_event = event.get("p_event", 0.0)
            if p_event <= 0:
                confidence = event.get("confidence_score", 0.5)
                event_type = event.get("event_type", "SUSPICIOUS_ACTIVITY")
                p_event = self.compute_p_event(confidence, event_type)

            event_type = event.get("event_type", "SUSPICIOUS_ACTIVITY")
            decay_cfg = EVENT_DECAY_INTERVALS.get(event_type, DEFAULT_EVENT_DECAY)
            elapsed_min = 0.0
            try:
                ts = datetime.fromisoformat(event.get("timestamp", ""))
                elapsed_min = max((now - ts).total_seconds() / 60, 0.0)
            except (ValueError, TypeError):
                pass
            event_decay = math.exp(-decay_cfg["lambda"] * elapsed_min)
            p_event_decayed = p_event * event_decay

            product *= (1 - p_event_decayed)

        p_combined = 1 - product
        return round(min(p_combined, 1.0), 4)

    def compute_w_context(self, zone_id=None, events=None):
        """
        W_context = W_time x W_crowd x W_recency x W_zone

        Contextual weighting factors:
          Time of Day:    Night=1.3, Evening=1.1, Day=1.0
          Crowd Density:  High=1.2, Normal=1.0
          Event Recency:  Just happened=1.5, Recent(<5min)=1.2, Old(>1hr)=0.7
          Area Type:      Known hotspot=1.4, Normal=1.0
        """
        now = datetime.now()
        hour = now.hour

        if 22 <= hour or hour <= 4:
            w_time = 1.3
        elif 18 <= hour < 22:
            w_time = 1.1
        elif 6 <= hour <= 8:
            w_time = 0.9
        else:
            w_time = 1.0

        w_crowd = 1.0
        if events and len(events) >= 5:
            w_crowd = 1.3
        elif events and len(events) >= 3:
            w_crowd = 1.2

        w_recency = 0.7
        if events:
            most_recent = None
            for e in events:
                try:
                    ts = datetime.fromisoformat(e.get("timestamp", ""))
                    if most_recent is None or ts > most_recent:
                        most_recent = ts
                except (ValueError, TypeError):
                    pass

            if most_recent:
                age_minutes = (now - most_recent).total_seconds() / 60
                if age_minutes < 2:
                    w_recency = 1.5
                elif age_minutes < 5:
                    w_recency = 1.2
                elif age_minutes < 15:
                    w_recency = 1.0
                elif age_minutes < 60:
                    w_recency = 0.7
                else:
                    w_recency = 0.4

        w_zone = 1.0
        if zone_id:
            conn = get_connection()
            row = conn.execute(
                "SELECT p_spatial FROM zones WHERE zone_id = ?", (zone_id,)
            ).fetchone()
            conn.close()
            if row and row["p_spatial"] and row["p_spatial"] > 0.6:
                w_zone = 1.4
            elif row and row["p_spatial"] and row["p_spatial"] > 0.3:
                w_zone = 1.2

        w_context = w_time * w_crowd * w_recency * w_zone
        return round(min(w_context, 3.0), 4)

    def compute_p_realtime(self, zone_id):
        """
        P_realtime = P_combined x W_context
        Fetches events from the last 15 minutes, then filters each event
        against its category-specific recalculation interval so that e.g.
        a SUSPICIOUS_RUNNING event expires after 60s but a WEAPON_DETECTED
        event stays active for 300s.
        """
        events = get_active_realtime_events(zone_id, minutes=15)

        if not events:
            return 0.0, []

        now = datetime.now()
        filtered = []
        for event in events:
            event_type = event.get("event_type", "SUSPICIOUS_ACTIVITY")
            decay_cfg = EVENT_DECAY_INTERVALS.get(event_type, DEFAULT_EVENT_DECAY)
            try:
                ts = datetime.fromisoformat(event.get("timestamp", ""))
                age_sec = (now - ts).total_seconds()
            except (ValueError, TypeError):
                age_sec = 0
            if age_sec <= decay_cfg["recalc_sec"]:
                filtered.append(event)

        if not filtered:
            return 0.0, []

        for event in filtered:
            if event.get("p_event", 0) <= 0:
                event["p_event"] = self.compute_p_event(
                    event.get("confidence_score", 0.5),
                    event.get("event_type", "SUSPICIOUS_ACTIVITY"),
                )

        p_combined = self.compute_p_combined(filtered)
        w_context = self.compute_w_context(zone_id, filtered)
        p_realtime = p_combined * w_context
        p_realtime = min(p_realtime, 1.0)
        return round(p_realtime, 4), filtered

    def compute_final_risk(self, zone_id, p_base, p_realtime):
        """
        Final Risk Score = alpha x P_base + beta x P_realtime
        alpha = 0.4 (historical importance)
        beta  = 0.6 (real-time importance)
        """
        raw_score = ALPHA * p_base + BETA * p_realtime
        return round(min(raw_score, 1.0), 4)

    def apply_decay(self, zone_id, new_score):
        """
        Continuous Recalculation:
          New Score = (1 - gamma) x Previous x Decay + gamma x New Input
          Decay = e^(-lambda * t)

        Lambda rules:
          Activity ongoing:   lambda = 0.01 (slow decay, risk stays high)
          No activity:        lambda = 0.05 (normal decay)
          Long silence:       lambda = 0.08-0.1 (fast decay, return to safe)
        """
        prev_data = self.zone_previous_scores.get(zone_id)
        if prev_data is None:
            self.zone_previous_scores[zone_id] = {
                "score": new_score,
                "timestamp": datetime.now(),
            }
            return new_score

        prev_score = prev_data["score"]
        prev_time = prev_data["timestamp"]
        elapsed_minutes = (datetime.now() - prev_time).total_seconds() / 60

        events = get_active_realtime_events(zone_id, minutes=15)
        if events and len(events) > 0:
            lambda_decay = 0.01
        elif elapsed_minutes < 30:
            lambda_decay = 0.05
        else:
            lambda_decay = 0.08

        decay = math.exp(-lambda_decay * elapsed_minutes)
        decayed_score = (1 - GAMMA_RECALC) * prev_score * decay + GAMMA_RECALC * new_score
        decayed_score = min(max(decayed_score, 0.0), 1.0)

        self.zone_previous_scores[zone_id] = {
            "score": decayed_score,
            "timestamp": datetime.now(),
        }

        return round(decayed_score, 4)

    def get_risk_level(self, r_zone):
        """
        Risk Score Interpretation:
          0.0 - 0.30  -> LOW (Green, Safe)
          0.30 - 0.55 -> MEDIUM (Yellow, Caution)
          0.55 - 0.75 -> HIGH (Orange, High Risk)
          0.75 - 1.0  -> CRITICAL (Red, Critical)
        """
        for threshold, level, color in RISK_THRESHOLDS:
            if r_zone >= threshold:
                return level, color
        return "LOW", "GREEN"

    def compute_zone_risk(self, zone_id, p_base_data):
        """Full risk computation pipeline for a single zone."""
        p_base = p_base_data.get("p_base", 0.0)
        p_spatial = p_base_data.get("p_spatial", 0.0)
        p_time = p_base_data.get("p_time", 0.0)

        p_realtime, events = self.compute_p_realtime(zone_id)
        raw_risk = self.compute_final_risk(zone_id, p_base, p_realtime)
        r_zone = self.apply_decay(zone_id, raw_risk)
        risk_level, color = self.get_risk_level(r_zone)

        update_zone_risk(zone_id, p_spatial, p_time, p_base, p_realtime, r_zone, risk_level)

        # Alerting is handled by AlertSystem (with its cooldown) in the risk
        # loop — inserting here too would create a duplicate alert every cycle.

        return {
            "zone_id": zone_id,
            "p_spatial": p_spatial,
            "p_time": p_time,
            "p_base": p_base,
            "p_realtime": p_realtime,
            "r_zone": r_zone,
            "risk_level": risk_level,
            "color": color,
            "active_events": len(events),
        }

    def compute_all_zones(self, p_base_all):
        """Compute risk for all zones in one cycle."""
        results = {}
        for zone_id, p_base_data in p_base_all.items():
            results[zone_id] = self.compute_zone_risk(zone_id, p_base_data)
        return results
