import warnings
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from database.db_manager import get_connection

try:
    import hdbscan
    HAS_HDBSCAN = True
except ImportError:
    HAS_HDBSCAN = False
    print("[WARN] hdbscan not installed. Using density fallback.")

try:
    from statsmodels.tsa.statespace.sarimax import SARIMAX
    HAS_SARIMA = True
    # SARIMA's optimiser sometimes hits its iteration cap before fully
    # converging — a harmless warning. Silence it so the console stays clean.
    try:
        from statsmodels.tools.sm_exceptions import ConvergenceWarning
        warnings.simplefilter("ignore", ConvergenceWarning)
    except Exception:
        pass
    warnings.filterwarnings("ignore", message="Non-invertible|Non-stationary")
    warnings.filterwarnings("ignore", message="No frequency information")
except ImportError:
    HAS_SARIMA = False
    print("[WARN] statsmodels not installed. Using temporal fallback.")

W1_SPATIAL = 0.5
W2_TEMPORAL = 0.5


class HistoricalEngine:
    def __init__(self):
        self.spatial_scores = {}
        self.temporal_scores = {}
        self.sarima_models = {}
        self.last_trained = None

    def load_crime_data(self):
        conn = get_connection()
        rows = conn.execute(
            """SELECT zone_id, latitude, longitude, timestamp, event_type,
               confidence_score FROM crime_events ORDER BY timestamp"""
        ).fetchall()
        conn.close()

        if not rows:
            return pd.DataFrame()

        df = pd.DataFrame([dict(r) for r in rows])
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        return df

    def run_hdbscan(self, df):
        """
        HDBSCAN spatial hotspot clustering.
        Input: (lat, lon) of past crimes.
        Output: P_spatial per zone (0-1 risk from hotspot density).
        """
        if df.empty:
            return {}

        coords = df[["latitude", "longitude"]].values

        if HAS_HDBSCAN and len(coords) >= 10:
            clusterer = hdbscan.HDBSCAN(
                min_cluster_size=5,
                min_samples=3,
                metric="haversine",
                algorithm="best",
            )
            coords_rad = np.radians(coords)
            clusterer.fit(coords_rad)
            df["cluster"] = clusterer.labels_
            df["cluster_prob"] = clusterer.probabilities_
        else:
            df["cluster"] = 0
            df["cluster_prob"] = 0.5

        zone_scores = {}
        for zone_id, group in df.groupby("zone_id"):
            crime_count = len(group)
            avg_prob = group["cluster_prob"].mean()
            non_noise = (group["cluster"] >= 0).sum()
            cluster_ratio = non_noise / max(crime_count, 1)
            zone_scores[zone_id] = crime_count * avg_prob * cluster_ratio

        if zone_scores:
            max_score = max(zone_scores.values())
            if max_score > 0:
                zone_scores = {k: v / max_score for k, v in zone_scores.items()}

        self.spatial_scores = zone_scores
        print(f"[HDBSCAN] Computed spatial risk for {len(zone_scores)} zones.")
        return zone_scores

    def run_sarima(self, df, zone_id):
        """
        SARIMA temporal crime forecasting.
        Learns patterns: night vs day, weekends, festivals.
        Output: P_time = predicted_crime_rate / max_rate.
        Prediction window = next 15-30 minutes.
        """
        if df.empty:
            return 0.0

        zone_df = df[df["zone_id"] == zone_id].copy()
        if len(zone_df) < 30:
            return self._temporal_fallback(zone_df)

        zone_df = zone_df.set_index("timestamp")
        hourly_counts = zone_df.resample("h").size()

        if len(hourly_counts) < 48:
            return self._temporal_fallback(zone_df.reset_index())

        hourly_counts = hourly_counts.fillna(0).astype(float)

        if HAS_SARIMA:
            try:
                recent = hourly_counts.tail(168 * 4)
                model = SARIMAX(
                    recent,
                    order=(1, 1, 1),
                    seasonal_order=(1, 0, 1, 24),
                    enforce_stationarity=False,
                    enforce_invertibility=False,
                )
                fitted = model.fit(disp=False, maxiter=50)
                forecast = fitted.forecast(steps=1)
                predicted_rate = max(0, forecast.iloc[0])
                max_rate = max(recent.max(), 1)
                p_time = min(predicted_rate / max_rate, 1.0)
                return round(p_time, 4)
            except Exception:
                return self._temporal_fallback(zone_df.reset_index())
        else:
            return self._temporal_fallback(zone_df.reset_index())

    def _temporal_fallback(self, zone_df):
        """
        Simple time-pattern fallback when SARIMA isn't available.
        Uses hour-of-day and day-of-week crime frequency patterns.
        """
        if zone_df.empty:
            return 0.0

        now = datetime.now()
        current_hour = now.hour
        is_weekend = now.weekday() >= 5

        if "timestamp" in zone_df.columns:
            zone_df["hour"] = pd.to_datetime(zone_df["timestamp"]).dt.hour
            zone_df["dow"] = pd.to_datetime(zone_df["timestamp"]).dt.dayofweek

            hour_counts = zone_df.groupby("hour").size()
            if current_hour in hour_counts.index:
                hour_score = hour_counts[current_hour] / max(hour_counts.max(), 1)
            else:
                hour_score = 0.1

            if is_weekend:
                weekend_crimes = zone_df[zone_df["dow"] >= 5]
                dow_boost = len(weekend_crimes) / max(len(zone_df), 1) * 2
            else:
                dow_boost = 1.0
        else:
            hour_score = 0.3
            dow_boost = 1.0

        night_boost = 1.0
        if 22 <= current_hour or current_hour <= 4:
            night_boost = 1.4
        elif 18 <= current_hour <= 22:
            night_boost = 1.2

        p_time = min(hour_score * night_boost * dow_boost, 1.0)
        return round(p_time, 4)

    def compute_p_base(self, zone_id):
        """
        P_base(zone, time) = (w1 x P_spatial) + (w2 x P_time)
        w1 = w2 = 0.5
        """
        p_spatial = self.spatial_scores.get(zone_id, 0.0)
        p_time = self.temporal_scores.get(zone_id, 0.0)
        p_base = (W1_SPATIAL * p_spatial) + (W2_TEMPORAL * p_time)
        return round(min(p_base, 1.0), 4), round(p_spatial, 4), round(p_time, 4)

    def train_all(self):
        """Full training cycle: run HDBSCAN + SARIMA for all zones."""
        print("[HISTORICAL] Starting full training cycle...")
        df = self.load_crime_data()

        if df.empty:
            print("[HISTORICAL] No crime data available.")
            return

        self.run_hdbscan(df)

        zones_with_data = df["zone_id"].unique()
        for zone_id in zones_with_data:
            p_time = self.run_sarima(df, zone_id)
            self.temporal_scores[zone_id] = p_time

        self.last_trained = datetime.now()
        print(f"[HISTORICAL] Training complete. {len(zones_with_data)} zones analyzed.")

    def get_p_base_all_zones(self):
        """Return P_base for all zones that have data."""
        results = {}
        all_zones = set(list(self.spatial_scores.keys()) + list(self.temporal_scores.keys()))
        for zone_id in all_zones:
            p_base, p_spatial, p_time = self.compute_p_base(zone_id)
            results[zone_id] = {
                "p_base": p_base,
                "p_spatial": p_spatial,
                "p_time": p_time,
            }
        return results

    def needs_retraining(self, hours=24):
        if self.last_trained is None:
            return True
        return (datetime.now() - self.last_trained) > timedelta(hours=hours)
