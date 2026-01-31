"""
Breaktime Tracker Dashboard - REST API
FastAPI backend serving dashboard data from Excel files.
"""

import os
import sys
from datetime import date, datetime, timedelta, timezone

# Philippine Timezone (UTC+8)
PH_TIMEZONE = timezone(timedelta(hours=8))

def get_ph_now():
    """Get current datetime in Philippine timezone."""
    return datetime.now(PH_TIMEZONE)

def get_ph_date():
    """Get current date in Philippine timezone."""
    return get_ph_now().date()
from typing import Optional
from dataclasses import asdict

# Setup path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('BASE_DIR', os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

# Static files directory
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")

from dashboard.data_layer import (
    get_realtime_metrics,
    get_break_distribution_today,
    get_agent_performance_today,
    get_hourly_distribution_today,
    get_compliance_trend,
    get_full_dashboard_data,
    get_break_logs,
    get_active_breaks,
    load_data_for_period,
)

# ============================================
# APP SETUP
# ============================================

app = FastAPI(
    title="Breaktime Tracker Dashboard API",
    description="REST API for Break Time Tracking Dashboard",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS - allow all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# ============================================
# ROUTES
# ============================================

@app.get("/", tags=["Dashboard"], include_in_schema=False)
async def root():
    """Serve the dashboard."""
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {
        "status": "ok",
        "service": "Breaktime Tracker Dashboard API",
        "version": "1.0.0",
        "message": "Dashboard UI not found. API is running.",
        "docs": "/docs"
    }


@app.get("/history", tags=["Dashboard"], include_in_schema=False)
async def history_page():
    """Serve the history page."""
    history_path = os.path.join(STATIC_DIR, "history.html")
    if os.path.exists(history_path):
        return FileResponse(history_path)
    return {"message": "History page not found"}


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "timestamp": get_ph_now().isoformat()
    }


# ============================================
# DASHBOARD DATA
# ============================================

@app.get("/api/dashboard", tags=["Dashboard"])
async def get_dashboard():
    """Get complete dashboard data in one call."""
    try:
        data = get_full_dashboard_data()
        return JSONResponse(content=data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/realtime", tags=["Dashboard"])
async def get_realtime():
    """Get real-time metrics for dashboard header."""
    try:
        metrics = get_realtime_metrics()
        return metrics.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/active-breaks", tags=["Dashboard"])
async def get_active():
    """Get list of agents currently on break (OUT without BACK)."""
    try:
        active = get_active_breaks()
        return {
            "count": len(active),
            "active_breaks": [asdict(a) for a in active],
            "timestamp": get_ph_now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# BREAK DISTRIBUTION
# ============================================

@app.get("/api/distribution/today", tags=["Distribution"])
async def get_distribution_today():
    """Get break distribution by type for today."""
    try:
        dist = get_break_distribution_today()
        return {
            "date": str(get_ph_date()),
            "distribution": [asdict(d) for d in dist]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# AGENT PERFORMANCE
# ============================================

@app.get("/api/agents", tags=["Agents"])
async def get_agents_performance():
    """Get performance metrics for all agents today."""
    try:
        agents = get_agent_performance_today()
        return {
            "date": str(get_ph_date()),
            "count": len(agents),
            "agents": [asdict(a) for a in agents]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# HOURLY ANALYSIS
# ============================================

@app.get("/api/hourly/today", tags=["Hourly"])
async def get_hourly_today():
    """Get hourly break distribution for today."""
    try:
        hourly = get_hourly_distribution_today()
        return {
            "date": str(get_ph_date()),
            "hourly": [asdict(h) for h in hourly]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# TRENDS
# ============================================

@app.get("/api/trend", tags=["Trends"])
async def get_trend_data(
    days: int = Query(7, ge=1, le=90, description="Days of trend data")
):
    """Get break trend over time."""
    try:
        trend = get_compliance_trend(days)
        return {
            "days": days,
            "trend": [asdict(t) for t in trend]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# HISTORICAL DATA
# ============================================

@app.get("/api/history/logs", tags=["History"])
async def get_history_logs(
    start: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end: str = Query(..., description="End date (YYYY-MM-DD)"),
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    break_type: Optional[str] = Query(None, description="Filter by break type"),
    limit: int = Query(100, ge=1, le=1000, description="Max records"),
    offset: int = Query(0, ge=0, description="Offset for pagination")
):
    """Get historical break logs with filters."""
    try:
        start_date = datetime.strptime(start, "%Y-%m-%d").date()
        end_date = datetime.strptime(end, "%Y-%m-%d").date()

        result = get_break_logs(start_date, end_date, user_id, break_type, limit, offset)
        return result
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# SYSTEM MANAGEMENT
# ============================================

@app.post("/api/system/reset", tags=["System"])
async def reset_system():
    """
    Reset system: Clear bot cache signal and close all active breaks.
    The bot will pick up the signal and clear its in-memory sessions.
    """
    try:
        # Write signal file for bot to clear its cache
        signal_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "database",
            ".clear_cache_signal"
        )
        os.makedirs(os.path.dirname(signal_file), exist_ok=True)

        with open(signal_file, 'w') as f:
            f.write(get_ph_now().isoformat())

        return {
            "status": "success",
            "message": "Reset signal sent. Bot will clear cache on next check cycle.",
            "signal_file": signal_file,
            "timestamp": get_ph_now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/system/force-close-all", tags=["System"])
async def force_close_all_breaks(check_days: int = Query(3, ge=1, le=7, description="Days to check for orphaned breaks")):
    """
    Force close all active breaks by writing BACK entries to Excel.
    Checks multiple days back to find orphaned breaks.
    """
    try:
        import pandas as pd
        from datetime import timedelta

        now = get_ph_now()
        today = get_ph_date()
        year_month = today.strftime('%Y-%m')
        timestamp = now.strftime('%Y-%m-%d %H:%M:%S')

        # Use BASE_DIR for Railway volume compatibility
        base_dir = os.environ.get('BASE_DIR', os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        database_dir = os.path.join(base_dir, "database")

        # Collect all active breaks from multiple days
        all_breaks = {}  # user_id -> (row, date_str)

        for days_back in range(check_days):
            check_date = now - timedelta(days=days_back)
            date_str = check_date.strftime('%Y-%m-%d')
            check_year_month = check_date.strftime('%Y-%m')
            log_file = os.path.join(database_dir, check_year_month, f"break_logs_{date_str}.xlsx")

            if not os.path.exists(log_file):
                continue

            try:
                df = pd.read_excel(log_file, engine='openpyxl')
                if df.empty:
                    continue

                df_sorted = df.sort_values('Timestamp')
                for _, row in df_sorted.iterrows():
                    user_id = int(row['User ID'])
                    action = row['Action']
                    if action == 'OUT':
                        all_breaks[user_id] = (row.to_dict(), date_str)
                    elif action == 'BACK' and user_id in all_breaks:
                        del all_breaks[user_id]
            except Exception as e:
                print(f"[Force-Close] Error reading {log_file}: {e}")
                continue

        closed_count = 0
        if all_breaks:
            # Write BACK entries to today's file
            month_dir = os.path.join(database_dir, year_month)
            os.makedirs(month_dir, exist_ok=True)
            log_file = os.path.join(month_dir, f"break_logs_{today}.xlsx")

            if os.path.exists(log_file):
                df = pd.read_excel(log_file, engine='openpyxl')
            else:
                df = pd.DataFrame(columns=['User ID', 'Username', 'Full Name', 'Break Type', 'Action', 'Timestamp', 'Duration (minutes)', 'Reason'])

            for user_id, (row_dict, date_str) in all_breaks.items():
                # Calculate duration
                try:
                    out_time_str = str(row_dict['Timestamp']).split('.')[0]
                    out_time = datetime.strptime(out_time_str, '%Y-%m-%d %H:%M:%S')
                    duration = round((now.replace(tzinfo=None) - out_time).total_seconds() / 60, 1)
                except:
                    duration = 0

                new_row = pd.DataFrame([[
                    user_id,
                    row_dict.get('Username', 'N/A'),
                    row_dict.get('Full Name', 'Unknown'),
                    row_dict.get('Break Type', 'Unknown'),
                    'BACK',
                    timestamp,
                    duration,
                    f'System force-closed (from {date_str})'
                ]], columns=['User ID', 'Username', 'Full Name', 'Break Type', 'Action', 'Timestamp', 'Duration (minutes)', 'Reason'])

                df = pd.concat([df, new_row], ignore_index=True)
                closed_count += 1
                print(f"[Force-Close] Closed: {row_dict.get('Full Name')} - {row_dict.get('Break Type')} ({duration:.0f}min from {date_str})")

            df.to_excel(log_file, index=False, engine='openpyxl')

        # Send reset signal to bot (use BASE_DIR for Railway compatibility)
        signal_file = os.path.join(database_dir, ".clear_cache_signal")
        os.makedirs(os.path.dirname(signal_file), exist_ok=True)
        with open(signal_file, 'w') as f:
            f.write(get_ph_now().isoformat())

        return {
            "status": "success",
            "closed_count": closed_count,
            "days_checked": check_days,
            "message": f"Force-closed {closed_count} active breaks and sent cache clear signal to bot.",
            "timestamp": get_ph_now().isoformat()
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# EXPORT
# ============================================

@app.get("/api/export/csv", tags=["Export"])
async def export_csv(
    start: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end: str = Query(..., description="End date (YYYY-MM-DD)"),
    user_id: Optional[int] = Query(None, description="Filter by user ID")
):
    """Export break logs as CSV."""
    import io
    import csv

    try:
        start_date = datetime.strptime(start, "%Y-%m-%d").date()
        end_date = datetime.strptime(end, "%Y-%m-%d").date()

        result = get_break_logs(start_date, end_date, user_id, None, 10000, 0)
        logs = result['logs']

        # Generate CSV
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Timestamp', 'Full Name', 'User ID', 'Break Type', 'Action', 'Duration (min)', 'Reason'])

        for log in logs:
            writer.writerow([
                log['timestamp'],
                log['full_name'],
                log['user_id'],
                log['break_type'],
                log['action'],
                log['duration_minutes'] or '',
                log['reason'] or ''
            ])

        output.seek(0)
        filename = f"break_logs_{start}_{end}.csv"

        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# RUN SERVER
# ============================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
