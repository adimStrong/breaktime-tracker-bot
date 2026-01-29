"""
Excel Online Handler
Manages Excel Online operations for break event logging.
With circuit breaker pattern for resilience.
"""

import os
import asyncio
from typing import Optional
from datetime import datetime, timedelta

from .auth import is_configured
from .graph_client import get_client

# Excel configuration from environment
EXCEL_FILE_ID = os.getenv('EXCEL_FILE_ID', '')
EXCEL_TABLE_NAME = os.getenv('EXCEL_TABLE_NAME', 'BreakLog')
EXCEL_SYNC_ENABLED = os.getenv('EXCEL_SYNC_ENABLED', 'false').lower() == 'true'

# Sync timeout in seconds
SYNC_TIMEOUT_SECONDS = 5

# Track initialization status
_initialized = False
_init_failed = False

# Circuit breaker state
_consecutive_failures = 0
_circuit_open_until: Optional[datetime] = None
CIRCUIT_BREAKER_THRESHOLD = 3  # failures before tripping
CIRCUIT_BREAKER_RESET_MINUTES = 5  # minutes before retry


def _is_circuit_open() -> bool:
    """Check if the circuit breaker is open (sync disabled temporarily)."""
    global _circuit_open_until
    if _circuit_open_until is None:
        return False
    if datetime.now() >= _circuit_open_until:
        # Reset circuit breaker
        print(f"[Excel] Circuit breaker reset - re-enabling sync")
        _circuit_open_until = None
        return False
    return True


def _record_success():
    """Record a successful sync, resetting failure count."""
    global _consecutive_failures
    _consecutive_failures = 0


def _record_failure():
    """Record a failed sync, potentially tripping the circuit breaker."""
    global _consecutive_failures, _circuit_open_until
    _consecutive_failures += 1
    if _consecutive_failures >= CIRCUIT_BREAKER_THRESHOLD:
        _circuit_open_until = datetime.now() + timedelta(minutes=CIRCUIT_BREAKER_RESET_MINUTES)
        print(f"[Excel] Circuit breaker TRIPPED after {_consecutive_failures} failures - sync disabled for {CIRCUIT_BREAKER_RESET_MINUTES} minutes")


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

    # Check circuit breaker
    if _is_circuit_open():
        return False

    # Initialize if needed
    if not _initialized and not await init_excel_handler():
        _record_failure()
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

        # Add row to Excel table with timeout
        client = get_client()
        result = await asyncio.wait_for(
            client.add_table_row(EXCEL_FILE_ID, EXCEL_TABLE_NAME, row_data),
            timeout=SYNC_TIMEOUT_SECONDS
        )

        if 'error' in result:
            print(f"[Excel] Failed to add row: {result['error']}")
            _record_failure()
            return False

        print(f"[Excel] Synced {action}: {full_name} - {break_type}")
        _record_success()
        return True

    except asyncio.TimeoutError:
        print(f"[Excel] Sync timeout after {SYNC_TIMEOUT_SECONDS}s")
        _record_failure()
        return False
    except Exception as e:
        print(f"[Excel] Error adding break event: {e}")
        _record_failure()
        return False


async def _add_break_event_safe(
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
    Safe wrapper for add_break_event that catches all exceptions.
    Used for fire-and-forget background sync.
    """
    try:
        await add_break_event(
            user_id, username, full_name, break_type,
            action, timestamp, duration, reason
        )
    except Exception as e:
        print(f"[Excel] Background sync error: {e}")
        _record_failure()


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
    Non-blocking wrapper for add_break_event.
    Schedules the sync as a background task - never blocks the bot.
    Failures don't raise exceptions or affect bot operation.
    """
    if not EXCEL_SYNC_ENABLED:
        return

    # Check circuit breaker early to avoid unnecessary work
    if _is_circuit_open():
        return

    try:
        # Try to get the running event loop
        loop = asyncio.get_running_loop()
        # Schedule as background task - fire and forget
        loop.create_task(_add_break_event_safe(
            user_id, username, full_name, break_type,
            action, timestamp, duration, reason
        ))
    except RuntimeError:
        # No running event loop - this shouldn't happen in normal bot operation
        # but handle gracefully anyway
        print("[Excel] Warning: No event loop available for sync")
    except Exception as e:
        # Never let Excel sync errors break the bot
        print(f"[Excel] Sync scheduling error (non-blocking): {e}")


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
