# Use official Python 3.13 slim image for smaller size
FROM python:3.13-slim

# Set working directory inside container
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    RUN_MODE=both

# Copy requirements file
COPY bot_requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r bot_requirements.txt

# Copy application files
COPY breaktime_tracker_bot.py .
COPY start_all.py .
COPY run_dashboard.py .

# Copy Microsoft Excel Online sync module
COPY microsoft/ ./microsoft/

# Copy utility scripts
COPY scripts/ ./scripts/

# Copy dashboard module
COPY dashboard/ ./dashboard/

# Create database directory
RUN mkdir -p /app/database

# Expose dashboard port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || python -c "import sys; sys.exit(0)"

# Run both bot and dashboard
# Set RUN_MODE=bot for bot only, RUN_MODE=dashboard for dashboard only
CMD ["python", "-u", "start_all.py"]
