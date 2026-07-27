# Leadership Jobs Digest — container image.
# Uses the official Playwright Python image so Chromium and all its system
# dependencies are preinstalled (matches the pinned playwright wheel below).
FROM mcr.microsoft.com/playwright/python:v1.60.0-jammy

WORKDIR /app

# Install Python dependencies first for better layer caching.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Ensure the Chromium browser is present for the installed playwright version.
RUN python -m playwright install chromium

# Copy the application source.
COPY . .

# Render (and most hosts) inject the port via $PORT; default to 8000 locally.
ENV PORT=8000
EXPOSE 8000

# Shell form so $PORT expands at runtime.
CMD python -m uvicorn main:app --host 0.0.0.0 --port ${PORT}
