# Recipe for packaging cozypdf into a container.
# Build:  docker build -t cozypdf .
# Run:    docker run -p 8000:8000 cozypdf

FROM python:3.12-slim

# Don't write .pyc files, and print logs immediately.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install the packages first. Docker caches this step, so rebuilds are fast
# as long as requirements.txt hasn't changed.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Then copy the project itself.
COPY . .

# Run as a normal user instead of root, which is safer.
RUN useradd --create-home appuser
USER appuser

EXPOSE 8000

# Docker marks the container "unhealthy" if the home page stops answering.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/')"

# --workers 2 handles two requests at once.
# --proxy-headers lets the app see real visitor info when it sits behind a proxy or tunnel.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2", "--proxy-headers", "--forwarded-allow-ips", "*"]
