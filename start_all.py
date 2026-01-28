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
    existing_files = list(db_dir.rglob('*.xlsx'))
    seed_files = list(seed_dir.rglob('*.xlsx'))

    # Only skip if we have at least 50% of seed data already
    if len(existing_files) >= len(seed_files) * 0.5:
        print(f"[SYNC] Database has {len(existing_files)} files (seed: {len(seed_files)}), skipping sync")
        return

    print("[SYNC] Database is empty, copying seed data...")
    copied = 0
    for item in seed_dir.iterdir():
        if item.is_dir():
            dest = db_dir / item.name
            if not dest.exists():
                shutil.copytree(item, dest)
                files_in_dir = len(list(item.rglob('*.xlsx')))
                copied += files_in_dir
                print(f"[SYNC] Copied {item.name}/ ({files_in_dir} files)")

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
