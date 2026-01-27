"""
Excel Online Handler
Manages Excel Online operations for break event logging.
"""

import os
import asyncio
from typing import Optional
from datetime import datetime

from .auth import is_configured
from .graph_client import get_client

# Excel configuration from environment
EXCEL_FILE_ID = os.getenv('EXCEL_FILE_ID', '')
EXCEL_TABLE_NAME = os.getenv('EXCEL_TABLE_NAME', 'BreakLog')
EXCEL_SYNC_ENABLED = os.getenv('EXCEL_SYNC_ENABLED', 'false').lower() == 'true'

# Track initialization status
_initialized = False
_init_failed = False


async def init_excel_handler() -> bool:
    """
    Initialize the Excel handler and verify configuration.
    Returns True if Excel sync is properly configured and working.
    """
    global _initialized, _init_failed

    if _init_failed:
        return False

    if _initialized:
        return True

    if not EXCEL_SYNC_ENABLED:
        print("[Excel] Sync disabled (EXCEL_SYNC_ENABLED != true)")
        return False

    if not is_configured():
        print("[Excel] Microsoft credentials not configured")
        _init_failed = True
        return False

    if not EXCEL_FILE_ID:
        print("[Excel] EXCEL_FILE_ID not set")
        _init_failed = True
        return False

    # Verify we can access the Excel file
    try:
        client = get_client()
        result = await client.get_table_info(EXCEL_FILE_ID, EXCEL_TABLE_NAME)

        if 'error' in result:
            print(f"[Excel] Failed to access table: {result['error']}")
            # Don't mark as failed - might be temporary
            return False

        print(f"[Excel] Handler initialized - Table '{EXCEL_TABLE_NAME}' found")
        _initialized = True
        return True

    except Exception as e:
        print(f"[Excel] Initialization error: {e}")
        return False


async def add_break_event(
    user_id: int,
    username: str,
    full_name: str,
    break_type: str,
    action: str,
    timestamp: Optional[datetime] = None,
    duration: Optional[float] = None,
    reason: Optional[str] = None
) -> bool:
    """
    Add a break event to the Excel Online table.

    Args:
        user_id: Telegram user ID
        username: Telegram username
        full_name: User's full name
        break_type: Type of break (e.g., "Eating", "Comfort Room", etc.)
        action: "OUT" or "BACK"
        timestamp: Event timestamp (defaults to now)
        duration: Duration in minutes (only for BACK action)
        reason: Reason for break (only for "Other" type)

    Returns:
        True if successfully synced, False otherwise
    """
    if not EXCEL_SYNC_ENABLED:
        return False

    # Initialize if needed
    if not _initialized and not await init_excel_handler():
        return False

    try:
        # Format timestamp
        if timestamp is None:
            timestamp = datetime.now()
        timestamp_str = timestamp.strftime('%Y-%m-%d %H:%M:%S')

        # Format duration
        duration_val = round(duration, 2) if duration is not None else ""

        # Format reason
        reason_val = reason if reason else ""

        # Build row data
        # Columns: Timestamp, User ID, Username, Full Name, Break Type, Action, Duration, Reason
        row_data = [[
            timestamp_str,
            user_id,
            username or "N/A",
            full_name,
            break_type,
            action,
            duration_val,
            reason_val
        ]]

        # Add row to Excel table
        client = get_client()
        result = await client.add_table_row(EXCEL_FILE_ID, EXCEL_TABLE_NAME, row_data)

        if 'error' in result:
            print(f"[Excel] Failed to add row: {result['error']}")
            return False

        print(f"[Excel] Synced {action}: {full_name} - {break_type}")
        return True

    except Exception as e:
        print(f"[Excel] Error adding break event: {e}")
        return False


def sync_break_event(
    user_id: int,
    username: str,
    full_name: str,
    break_type: str,
    action: str,
    timestamp: Optional[datetime] = None,
    duration: Optional[float] = None,
    reason: Optional[str] = None
) -> None:
    """
    Synchronous wrapper for add_break_event.
    Runs the async function in a new event loop if needed.
    Non-blocking - failures don't raise exceptions.
    """
    if not EXCEL_SYNC_ENABLED:
        return

    try:
        # Try to get the running event loop
        try:
            loop = asyncio.get_running_loop()
            # If we're in an async context, create a task
            asyncio.create_task(add_break_event(
                user_id, username, full_name, break_type,
                action, timestamp, duration, reason
            ))
        except RuntimeError:
            # No running event loop, create a new one
            asyncio.run(add_break_event(
                user_id, username, full_name, break_type,
                action, timestamp, duration, reason
            ))
    except Exception as e:
        # Never let Excel sync errors break the bot
        print(f"[Excel] Sync error (non-blocking): {e}")


async def ensure_table_exists() -> bool:
    """
    Ensure the Excel table exists, creating it if necessary.
    Note: This requires the Excel file to already exist with headers in row 1.
    """
    if not EXCEL_SYNC_ENABLED or not is_configured() or not EXCEL_FILE_ID:
        return False

    try:
        client = get_client()

        # Check if table exists
        result = await client.get_table_info(EXCEL_FILE_ID, EXCEL_TABLE_NAME)

        if 'error' not in result:
            print(f"[Excel] Table '{EXCEL_TABLE_NAME}' already exists")
            return True

        # Table doesn't exist - try to create it
        # Assumes headers are in A1:H1
        print(f"[Excel] Creating table '{EXCEL_TABLE_NAME}'...")
        create_result = await client.create_table(
            EXCEL_FILE_ID,
            "A1:H1",
            has_headers=True
        )

        if 'error' in create_result:
            print(f"[Excel] Failed to create table: {create_result['error']}")
            return False

        # Rename the table
        # Note: Graph API creates tables with auto-generated names
        # You may need to rename it manually in Excel or use PATCH

        print(f"[Excel] Table created successfully")
        return True

    except Exception as e:
        print(f"[Excel] Error ensuring table exists: {e}")
        return False
