"""
Demo Simulator - Generates fake real-time events for presentation.
Run this alongside the backend + dashboard to show the system in action
WITHOUT needing a live camera.

Usage:
  1. Start backend:    python run.py
  2. Start dashboard:  streamlit run dashboard/dashboard.py
  3. Run this:         python demo_simulate.py
"""

import sys
import os
import time
import random
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))

from database.db_manager import init_database
from database.seed_data import seed_historical_data
from backend.zone_manager import ZoneManager
from backend.fusion_engine import FusionEngine
from backend.data_ingestion import ingest_realtime_event

DEMO_SCENARIOS = [
    {
        "name": "SCENARIO 1: Normal Activity",
        "events": [
            {"event_type": "SUSPICIOUS_ACTIVITY", "confidence_score": 0.3,
             "lat": 3.1470, "lon": 101.7100},
        ],
        "expected_risk": "LOW (~5%)",
        "pause": 5,
    },
    {
        "name": "SCENARIO 2: Suspicious Running",
        "events": [
            {"event_type": "SUSPICIOUS_RUNNING", "confidence_score": 0.6,
             "lat": 3.1466, "lon": 101.7108},
        ],
        "expected_risk": "LOW-MEDIUM (~18%)",
        "pause": 5,
    },
    {
        "name": "SCENARIO 3: Person Chasing + Running",
        "events": [
            {"event_type": "SUSPICIOUS_RUNNING", "confidence_score": 0.7,
             "lat": 3.1466, "lon": 101.7108},
            {"event_type": "PERSON_CHASING", "confidence_score": 0.8,
             "lat": 3.1466, "lon": 101.7108},
        ],
        "expected_risk": "HIGH (~60%)",
        "pause": 5,
    },
    {
        "name": "SCENARIO 4: Full Crime in Progress",
        "events": [
            {"event_type": "SUSPICIOUS_RUNNING", "confidence_score": 0.6,
             "lat": 3.1635, "lon": 101.6985},
            {"event_type": "PERSON_CHASING", "confidence_score": 0.8,
             "lat": 3.1635, "lon": 101.6985},
            {"event_type": "THEFT_SNATCH", "confidence_score": 0.7,
             "lat": 3.1635, "lon": 101.6985},
        ],
        "expected_risk": "HIGH-CRITICAL (~79%)",
        "pause": 8,
    },
    {
        "name": "SCENARIO 5: WANTED CRIMINAL DETECTED",
        "events": [
            {"event_type": "FACE_MATCH_WANTED", "confidence_score": 0.92,
             "lat": 3.1455, "lon": 101.6953},
            {"event_type": "SUSPICIOUS_RUNNING", "confidence_score": 0.8,
             "lat": 3.1455, "lon": 101.6953},
        ],
        "expected_risk": "CRITICAL (~97%)",
        "pause": 10,
    },
    {
        "name": "SCENARIO 6: Weapon Detected + Crowd Anomaly",
        "events": [
            {"event_type": "WEAPON_DETECTED", "confidence_score": 0.85,
             "lat": 3.1343, "lon": 101.6864},
            {"event_type": "CROWD_ANOMALY", "confidence_score": 0.7,
             "lat": 3.1343, "lon": 101.6864},
            {"event_type": "ASSAULT", "confidence_score": 0.75,
             "lat": 3.1343, "lon": 101.6864},
        ],
        "expected_risk": "CRITICAL (~95%)",
        "pause": 10,
    },
]


def main():
    print("=" * 60)
    print("  SentinelAI - DEMO SIMULATOR")
    print("  This generates fake events to demonstrate the system")
    print("=" * 60)

    init_database()
    zm = ZoneManager()
    zm.create_grid_zones()
    fusion = FusionEngine()

    print("\nMake sure the backend (run.py) is running!")
    print("Watch the dashboard as scenarios play out.\n")
    input("Press ENTER to start the demo...\n")

    for i, scenario in enumerate(DEMO_SCENARIOS):
        print(f"\n{'='*60}")
        print(f"  {scenario['name']}")
        print(f"  Expected Risk: {scenario['expected_risk']}")
        print(f"{'='*60}")

        for event_data in scenario["events"]:
            event = {
                "latitude": event_data["lat"],
                "longitude": event_data["lon"],
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "event_type": event_data["event_type"],
                "confidence_score": event_data["confidence_score"],
                "source": "CCTV_AI",
            }

            p_event = fusion.compute_p_event(
                event_data["confidence_score"],
                event_data["event_type"],
            )

            success, zone_id = ingest_realtime_event(
                event, zm, p_event=p_event, camera_id="DEMO_CAM"
            )

            print(f"  -> {event_data['event_type']} "
                  f"(conf={event_data['confidence_score']:.0%}, "
                  f"P_event={p_event:.2%}) "
                  f"-> Zone: {zone_id}")

        all_p_events = []
        for event_data in scenario["events"]:
            p = fusion.compute_p_event(
                event_data["confidence_score"],
                event_data["event_type"],
            )
            all_p_events.append({"p_event": p, "event_type": event_data["event_type"],
                                 "confidence_score": event_data["confidence_score"]})

        p_combined = fusion.compute_p_combined(all_p_events)
        print(f"\n  P_combined = {p_combined:.2%}")
        print(f"  (Formula: 1 - Product(1 - P_event_i))")

        print(f"\n  Waiting {scenario['pause']}s before next scenario...")
        print(f"  (Check the dashboard now!)")
        time.sleep(scenario["pause"])

    print(f"\n{'='*60}")
    print("  DEMO COMPLETE")
    print("  All scenarios have been played.")
    print("  The dashboard should show the risk changes.")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
