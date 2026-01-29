"""
Start both the Telegram Bot and Dashboard server.
For Railway deployment or local development.
"""

import os
import sys
import subprocess
import threading
import time
from datetime import datetime, timezone, timedelta

os.environ['BASE_DIR'] = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.environ['BASE_DIR'])

# Philippine Timezone (UTC+8)
PH_TZ = timezone(timedelta(hours=8))


def get_timestamp():
    """Get current timestamp in Philippine timezone for logging."""
    return datetime.now(PH_TZ).strftime('%Y-%m-%d %H:%M:%S')


def run_bot():
    """Run the Telegram bot with auto-restart on crash."""
    while True:
        print(f"[{get_timestamp()}] [Bot] Starting Telegram bot...")
        try:
            result = subprocess.run([sys.executable, "-u", "breaktime_tracker_bot.py"])
            print(f"[{get_timestamp()}] [Bot] Bot exited with code {result.returncode}")
            if result.returncode == 0:
                break  # Clean exit
            print(f"[{get_timestamp()}] [Bot] Restarting in 5 seconds...")
            time.sleep(5)
        except Exception as e:
            print(f"[{get_timestamp()}] [Bot] Error: {e}, restarting in 5 seconds...")
            time.sleep(5)


def run_dashboard():
    """Run the dashboard server."""
    print(f"[{get_timestamp()}] [Dashboard] Starting dashboard server on port 8000...")
    import uvicorn
    uvicorn.run(
        "dashboard.api:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=False
    )


def run_health_check():
    """
    Periodically log health status.
    Runs in a background thread.
    """
    HEALTH_CHECK_INTERVAL = 300  # 5 minutes in seconds

    while True:
        try:
            time.sleep(HEALTH_CHECK_INTERVAL)

            # Count today's breaks
            from pathlib import Path
            import pandas as pd

            now = datetime.now(PH_TZ)
            today = now.strftime('%Y-%m-%d')
            year_month = now.strftime('%Y-%m')

            base_dir = os.environ.get('BASE_DIR', os.path.dirname(os.path.abspath(__file__)))
            log_file = Path(base_dir) / 'database' / year_month / f'break_logs_{today}.xlsx'

            break_count = 0
            if log_file.exists():
                try:
                    df = pd.read_excel(log_file, engine='openpyxl')
                    break_count = len(df)
                except Exception:
                    pass

            print(f"[{get_timestamp()}] [HEALTH] Heartbeat - System OK | Breaks logged today: {break_count}")

        except Exception as e:
            print(f"[{get_timestamp()}] [HEALTH] Health check error: {e}")


def fix_stuck_active_breaks():
    """
    One-time fix: Close any stuck active breaks by adding BACK entries.
    This function is designed to be fail-safe - if anything goes wrong,
    it logs the error and continues without crashing the startup.
    """
    try:
        import pandas as pd
        from pathlib import Path

        now = datetime.now(PH_TZ)
        today = now.strftime('%Y-%m-%d')
        year_month = now.strftime('%Y-%m')

        base_dir = os.environ.get('BASE_DIR', os.path.dirname(os.path.abspath(__file__)))
        log_file = Path(base_dir) / 'database' / year_month / f'break_logs_{today}.xlsx'

        if not log_file.exists():
            print(f"[{get_timestamp()}] [FIX] No file for today ({today}), skipping fix")
            return

        try:
            df = pd.read_excel(log_file, engine='openpyxl')
        except Exception as e:
            print(f"[{get_timestamp()}] [FIX] Error reading log file: {e}")
            return

        if df.empty:
            print(f"[{get_timestamp()}] [FIX] Log file is empty, nothing to fix")
            return

        # Find active breaks (OUT without BACK)
        active = {}
        try:
            df_sorted = df.sort_values('Timestamp')
            for _, row in df_sorted.iterrows():
                user_id = int(row['User ID'])
                action = row['Action']
                if action == 'OUT':
                    active[user_id] = row
                elif action == 'BACK' and user_id in active:
                    del active[user_id]
        except Exception as e:
            print(f"[{get_timestamp()}] [FIX] Error analyzing breaks: {e}")
            return

        if not active:
            print(f"[{get_timestamp()}] [FIX] No stuck active breaks found")
            return

        print(f"[{get_timestamp()}] [FIX] Found {len(active)} stuck active breaks, adding BACK entries...")

        # Add BACK entries for stuck breaks
        timestamp = now.strftime('%Y-%m-%d %H:%M:%S')
        new_rows = []
        for user_id, row in active.items():
            new_rows.append({
                'User ID': user_id,
                'Username': row['Username'],
                'Full Name': row['Full Name'],
                'Break Type': row['Break Type'],
                'Action': 'BACK',
                'Timestamp': timestamp,
                'Duration (minutes)': 0,
                'Reason': 'Auto-closed by system'
            })
            print(f"[{get_timestamp()}] [FIX] Closing break for {row['Full Name']}")

        # Append and save
        try:
            new_df = pd.DataFrame(new_rows)
            df = pd.concat([df, new_df], ignore_index=True)
            df.to_excel(log_file, index=False, engine='openpyxl')
            print(f"[{get_timestamp()}] [FIX] Fixed {len(new_rows)} stuck breaks")
        except Exception as e:
            print(f"[{get_timestamp()}] [FIX] Error saving fixed breaks: {e}")

    except Exception as e:
        # Catch-all: Never let this function crash the bot startup
        print(f"[{get_timestamp()}] [FIX] Unexpected error (continuing anyway): {e}")


def sync_seed_data():
    """Copy seed data to database folder if it's empty."""
    try:
        import shutil
        from pathlib import Path

        base_dir = os.environ.get('BASE_DIR', os.path.dirname(os.path.abspath(__file__)))
        seed_dir = Path(base_dir) / 'seed_data'
        db_dir = Path(base_dir) / 'database'

        if not seed_dir.exists():
            print(f"[{get_timestamp()}] [SYNC] No seed_data folder found, skipping sync")
            return

        db_dir.mkdir(parents=True, exist_ok=True)
        seed_files = list(seed_dir.rglob('*.xlsx'))

        print(f"[{get_timestamp()}] [SYNC] Checking {len(seed_files)} seed files...")
        copied = 0
        for seed_file in seed_files:
            # Get relative path from seed_dir
            rel_path = seed_file.relative_to(seed_dir)
            dest_file = db_dir / rel_path

            # Only copy if file doesn't exist
            if not dest_file.exists():
                dest_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(seed_file, dest_file)
                copied += 1

        print(f"[{get_timestamp()}] [SYNC] Seed data sync complete: {copied} files copied")
    except Exception as e:
        print(f"[{get_timestamp()}] [SYNC] Error syncing seed data (continuing anyway): {e}")


if __name__ == "__main__":
    print(f"[{get_timestamp()}] " + "=" * 50)
    print(f"[{get_timestamp()}] Breaktime Tracker - Startup")
    print(f"[{get_timestamp()}] " + "=" * 50)

    # Sync seed data to volume on first run
    sync_seed_data()

    # Fix any stuck active breaks (one-time cleanup)
    # This is wrapped in try-catch internally, so it won't crash startup
    fix_stuck_active_breaks()

    mode = os.getenv("RUN_MODE", "both").lower()

    if mode == "bot":
        # Run only the bot
        print(f"[{get_timestamp()}] Mode: bot only")
        run_bot()
    elif mode == "dashboard":
        # Run only the dashboard
        print(f"[{get_timestamp()}] Mode: dashboard only")
        run_dashboard()
    else:
        # Run both in separate threads
        print(f"[{get_timestamp()}] Mode: bot + dashboard")
        print()

        # Start health check in a background thread
        health_thread = threading.Thread(target=run_health_check, daemon=True)
        health_thread.start()
        print(f"[{get_timestamp()}] [HEALTH] Health check started (every 5 minutes)")

        # Start bot in a separate thread
        bot_thread = threading.Thread(target=run_bot, daemon=True)
        bot_thread.start()

        # Run dashboard in main thread (handles signals properly)
        run_dashboard()
