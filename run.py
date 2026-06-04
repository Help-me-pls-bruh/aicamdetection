"""
SentinelAI - Main Entry Point
Starts the Flask API backend.
Then run the dashboard separately: streamlit run dashboard/dashboard.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from backend.app import start_server

if __name__ == "__main__":
    start_server(host="0.0.0.0", port=5000)
