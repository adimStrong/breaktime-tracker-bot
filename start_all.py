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


if __name__ == "__main__":
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
