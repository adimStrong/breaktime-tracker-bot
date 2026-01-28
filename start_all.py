"""
Start both the Telegram Bot and Dashboard server.
For Railway deployment or local development.
"""

import os
import sys
import subprocess
import threading

os.environ['BASE_DIR'] = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.environ['BASE_DIR'])


def run_bot():
    """Run the Telegram bot."""
    print("[Bot] Starting Telegram bot...")
    subprocess.run([sys.executable, "breaktime_tracker_bot.py"])


def run_dashboard():
    """Run the dashboard server."""
    print("[Dashboard] Starting dashboard server on port 8000...")
    import uvicorn
    uvicorn.run(
        "dashboard.api:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=False
    )


def fix_stuck_active_breaks():
    """One-time fix: Close any stuck active breaks by adding BACK entries."""
    import pandas as pd
    from datetime import datetime, timezone, timedelta
    from pathlib import Path

    PH_TZ = timezone(timedelta(hours=8))
    now = datetime.now(PH_TZ)
    today = now.strftime('%Y-%m-%d')
    year_month = now.strftime('%Y-%m')

    base_dir = os.environ.get('BASE_DIR', os.path.dirname(os.path.abspath(__file__)))
    log_file = Path(base_dir) / 'database' / year_month / f'break_logs_{today}.xlsx'

    if not log_file.exists():
        print(f"[FIX] No file for today ({today}), skipping fix")
        return

    try:
        df = pd.read_excel(log_file, engine='openpyxl')
        if df.empty:
            return

        # Find active breaks (OUT without BACK)
        active = {}
        df_sorted = df.sort_values('Timestamp')
        for _, row in df_sorted.iterrows():
            user_id = int(row['User ID'])
            action = row['Action']
            if action == 'OUT':
                active[user_id] = row
            elif action == 'BACK' and user_id in active:
                del active[user_id]

        if not active:
            print("[FIX] No stuck active breaks found")
            return

        print(f"[FIX] Found {len(active)} stuck active breaks, adding BACK entries...")

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
            print(f"[FIX] Closing break for {row['Full Name']}")

        # Append and save
        new_df = pd.DataFrame(new_rows)
        df = pd.concat([df, new_df], ignore_index=True)
        df.to_excel(log_file, index=False, engine='openpyxl')
        print(f"[FIX] Fixed {len(new_rows)} stuck breaks")

    except Exception as e:
        print(f"[FIX] Error fixing breaks: {e}")


def sync_seed_data():
    """Copy seed data to database folder if it's empty."""
    import shutil
    from pathlib import Path

    base_dir = os.environ.get('BASE_DIR', os.path.dirname(os.path.abspath(__file__)))
    seed_dir = Path(base_dir) / 'seed_data'
    db_dir = Path(base_dir) / 'database'

    if not seed_dir.exists():
        print("[SYNC] No seed_data folder found, skipping sync")
        return

    db_dir.mkdir(parents=True, exist_ok=True)
    seed_files = list(seed_dir.rglob('*.xlsx'))

    print(f"[SYNC] Checking {len(seed_files)} seed files...")
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

    print(f"[SYNC] Seed data sync complete: {copied} files copied")


if __name__ == "__main__":
    # Sync seed data to volume on first run
    sync_seed_data()

    # Fix any stuck active breaks (one-time cleanup)
    fix_stuck_active_breaks()

    mode = os.getenv("RUN_MODE", "both").lower()

    if mode == "bot":
        # Run only the bot
        run_bot()
    elif mode == "dashboard":
        # Run only the dashboard
        run_dashboard()
    else:
        # Run both in separate threads
        print("=" * 50)
        print("Breaktime Tracker - Starting Bot + Dashboard")
        print("=" * 50)
        print()

        # Start bot in a separate thread
        bot_thread = threading.Thread(target=run_bot, daemon=True)
        bot_thread.start()

        # Run dashboard in main thread (handles signals properly)
        run_dashboard()
