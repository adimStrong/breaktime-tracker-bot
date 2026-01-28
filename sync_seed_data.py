"""
Sync seed data to Railway volume on startup.
Copies historical data from seed_data folder to database folder if volume is empty.
"""

import os
import shutil
from pathlib import Path

def sync_seed_data():
    """Copy seed data to database folder if it's empty."""
    base_dir = os.environ.get('BASE_DIR', os.path.dirname(os.path.abspath(__file__)))

    seed_dir = Path(base_dir) / 'seed_data'
    db_dir = Path(base_dir) / 'database'

    # Check if seed data exists
    if not seed_dir.exists():
        print("[SYNC] No seed_data folder found, skipping sync")
        return

    # Check if database folder is empty or missing
    db_dir.mkdir(parents=True, exist_ok=True)

    # Count existing files in database
    existing_files = list(db_dir.rglob('*.xlsx'))

    if len(existing_files) > 0:
        print(f"[SYNC] Database already has {len(existing_files)} files, skipping seed sync")
        return

    # Copy seed data to database
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

if __name__ == '__main__':
    sync_seed_data()
