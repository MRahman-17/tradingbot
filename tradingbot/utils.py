#!/usr/bin/env python3
"""
Utility functions for the trading system
"""
import os
import time
from datetime import datetime
import logging

logger = logging.getLogger("Utils")


def create_heartbeat(bot_name):
    """Create a heartbeat file with current timestamp"""
    heartbeat_dir = "logs/heartbeats"
    os.makedirs(heartbeat_dir, exist_ok=True)
    heartbeat_file = os.path.join(heartbeat_dir, f"{bot_name}_heartbeat.txt")

    try:
        with open(heartbeat_file, 'w') as f:
            f.write(f"Last heartbeat: {datetime.now().isoformat()}")
        logger.debug(f"Heartbeat created for {bot_name}")
    except Exception as e:
        logger.error(f"Error creating heartbeat for {bot_name}: {e}")


import sqlite3


def log_activity(bot_name, action):
    """Log bot activity to SQLite database"""
    db_dir = "data"
    os.makedirs(db_dir, exist_ok=True)
    db_path = os.path.join(db_dir, 'bot_activity.db')

    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()

        # Create table if it doesn't exist
        c.execute('''
        CREATE TABLE IF NOT EXISTS activity_log
        (timestamp TEXT, bot TEXT, action TEXT)
        ''')

        # Insert activity
        c.execute("INSERT INTO activity_log VALUES (?, ?, ?)",
                  (datetime.now().isoformat(), bot_name, action))

        conn.commit()
        conn.close()
        logger.debug(f"Activity logged for {bot_name}: {action}")
    except Exception as e:
        logger.error(f"Error logging activity for {bot_name}: {e}")
