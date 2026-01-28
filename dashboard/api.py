"""
Breaktime Tracker Dashboard - REST API
FastAPI backend serving dashboard data from Excel files.
"""

import os
import sys
from datetime import date, datetime, timedelta
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
        "timestamp": datetime.now().isoformat()
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


# ============================================
# BREAK DISTRIBUTION
# ============================================

@app.get("/api/distribution/today", tags=["Distribution"])
async def get_distribution_today():
    """Get break distribution by type for today."""
    try:
        dist = get_break_distribution_today()
        return {
            "date": str(date.today()),
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
            "date": str(date.today()),
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
            "date": str(date.today()),
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
