"""
Feedback Loop - Model E: Continuous Learning
After each police response, officer logs true/false positive.
- True positive: reinforce HDBSCAN cluster + SARIMA seasonality
- False positive: penalty weight to event type in fusion engine
- Accumulated feedback over 90-day windows triggers full retraining
"""

from datetime import datetime, timedelta
from database.db_manager import get_connection, submit_feedback


class FeedbackLoop:
    def __init__(self, fusion_engine=None, historical_engine=None):
        self.fusion_engine = fusion_engine
        self.historical_engine = historical_engine
        self.feedback_counts = {"TRUE_CRIME": 0, "FALSE_ALARM": 0}
        self.retrain_threshold = 50

    def process_feedback(self, alert_id, zone_id, label, officer_notes=""):
        """
        Process officer feedback.
        label: 'TRUE_CRIME' or 'FALSE_ALARM'
        """
        submit_feedback(alert_id, zone_id, label, officer_notes)
        self.feedback_counts[label] = self.feedback_counts.get(label, 0) + 1

        if label == "TRUE_CRIME":
            self._reinforce_zone(zone_id)
        elif label == "FALSE_ALARM":
            self._penalize_zone(zone_id)

        total = sum(self.feedback_counts.values())
        if total >= self.retrain_threshold:
            self._trigger_retraining()
            self.feedback_counts = {"TRUE_CRIME": 0, "FALSE_ALARM": 0}

        return {
            "status": "processed",
            "label": label,
            "zone_id": zone_id,
            "total_feedback": total,
        }

    def _reinforce_zone(self, zone_id):
        """True positive: strengthen this zone's risk signals."""
        conn = get_connection()
        row = conn.execute("SELECT p_spatial FROM zones WHERE zone_id = ?", (zone_id,)).fetchone()
        if row:
            new_spatial = min((row["p_spatial"] or 0) + 0.02, 1.0)
            conn.execute(
                "UPDATE zones SET p_spatial = ? WHERE zone_id = ?",
                (new_spatial, zone_id),
            )
        conn.commit()
        conn.close()

    def _penalize_zone(self, zone_id):
        """False positive: reduce this zone's risk signals slightly."""
        conn = get_connection()
        row = conn.execute("SELECT p_spatial FROM zones WHERE zone_id = ?", (zone_id,)).fetchone()
        if row:
            new_spatial = max((row["p_spatial"] or 0) - 0.01, 0.0)
            conn.execute(
                "UPDATE zones SET p_spatial = ? WHERE zone_id = ?",
                (new_spatial, zone_id),
            )
        conn.commit()
        conn.close()

    def _trigger_retraining(self):
        """Trigger full model retraining cycle after accumulated feedback."""
        print("[FEEDBACK] Retraining threshold reached. Triggering model update...")
        if self.historical_engine:
            self.historical_engine.train_all()
            print("[FEEDBACK] Historical engine retrained.")

    def get_accuracy_stats(self):
        conn = get_connection()
        total = conn.execute("SELECT COUNT(*) FROM feedback").fetchone()[0]
        true_crimes = conn.execute(
            "SELECT COUNT(*) FROM feedback WHERE label = 'TRUE_CRIME'"
        ).fetchone()[0]
        false_alarms = conn.execute(
            "SELECT COUNT(*) FROM feedback WHERE label = 'FALSE_ALARM'"
        ).fetchone()[0]
        conn.close()

        accuracy = true_crimes / max(total, 1)
        return {
            "total_feedback": total,
            "true_crimes": true_crimes,
            "false_alarms": false_alarms,
            "accuracy": round(accuracy, 4),
            "false_positive_rate": round(false_alarms / max(total, 1), 4),
        }

    def get_zone_feedback_history(self, zone_id, days=90):
        conn = get_connection()
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        rows = conn.execute(
            """SELECT * FROM feedback WHERE zone_id = ? AND timestamp >= ?
               ORDER BY timestamp DESC""",
            (zone_id, cutoff),
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]
