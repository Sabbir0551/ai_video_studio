# ==============================================================================
# AI Video Studio - Production Container
# Includes FFmpeg with libass & HarfBuzz, Bengali Noto Fonts, and Python runtime
# ==============================================================================
FROM python:3.11-slim-bookworm

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    STUDIO_ENV=production \
    PORT=8000

# Install system dependencies, FFmpeg with libass/libfreetype/harfbuzz, and fonts
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libass-dev \
    fonts-noto-core \
    fonts-noto-extra \
    fonts-roboto \
    fontconfig \
    libgl1 \
    libglib2.0-0 \
    curl \
    && fc-cache -fv \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source code and bundled assets
COPY assets/ ./assets/
COPY backend/ ./backend/
COPY pyproject.toml .env.example ./

# Ensure data and project directories exist
RUN mkdir -p data/projects data/renders data/cache data/uploads

EXPOSE 8000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start FastAPI application
CMD ["uvicorn", "backend.app.api.main:app", "--host", "0.0.0.0", "--port", "8000"]

