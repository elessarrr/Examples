# Use Python 3.9 slim image as base
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8050

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV DASH_DEBUG_MODE=False

# Set memory and CPU constraints
ENV PYTHONMALLOC=malloc
ENV MALLOC_TRIM_THRESHOLD_=100000

# Configure Gunicorn for production
RUN pip install gunicorn gevent

# Set resource limits
ENV WORKERS=4
ENV THREADS=2
ENV MAX_REQUESTS=1000
ENV TIMEOUT=30

# Run the application with Gunicorn
CMD ["gunicorn", "-w", "$WORKERS", "--threads", "$THREADS", "--max-requests", "$MAX_REQUESTS", "--timeout", "$TIMEOUT", "--worker-class", "gevent", "--bind", "0.0.0.0:8050", "app:server"]