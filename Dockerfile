# Multi-stage build for smaller image size
FROM python:3.11-alpine AS builder

# Install build dependencies
RUN apk add --no-cache \
    gcc \
    musl-dev \
    python3-dev

# Set working directory
WORKDIR /app

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Copy source code
COPY thinkific_downloader/ ./thinkific_downloader/
COPY setup.py .

# Install the package
RUN pip install --no-cache-dir --user .

# Final stage - minimal runtime image
FROM python:3.11-alpine

# Install only runtime dependencies (minimal FFmpeg)
RUN apk add --no-cache ffmpeg

# Create non-root user for security
RUN adduser -D -s /bin/sh thinkific

# Copy installed packages from builder
COPY --from=builder /root/.local /home/thinkific/.local

# Set working directory and user
WORKDIR /app
USER thinkific

# Add local bin to PATH
ENV PATH=/home/thinkific/.local/bin:$PATH

# Default command
CMD ["python", "-m", "thinkific_downloader"]