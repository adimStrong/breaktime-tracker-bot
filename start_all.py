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
