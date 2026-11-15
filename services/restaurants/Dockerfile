# Image for the Restaurants service.
# Small official Python image (Debian "bookworm", Python 3.12).
FROM python:3.12-slim-bookworm

# Don't write .pyc files; print logs straight away (no buffering).
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

WORKDIR /app

# A normal user with no special rights; the app runs as this user, not as root.
RUN useradd --create-home --uid 10001 appuser

# Install the pinned dependencies first, so Docker can reuse this layer
# when only our code changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy only the files the service needs (no "COPY . .", so tests, .env
# and other local files never end up in the image).
COPY app.py db.py logic.py seed.py service.py seed_data.json ./
COPY migrations/ ./migrations/
# Make sure every file can be read by appuser (files keep the permissions they
# had on your computer, and some were readable only by their owner).
RUN chmod -R a+rX /app

USER appuser
EXPOSE 8000

# gunicorn is a production web server. One worker process (so migrations
# run once at startup) with 4 threads for parallel requests. The long
# timeout leaves time for a paused Azure database to wake up.
CMD ["sh", "-c", "exec gunicorn --bind 0.0.0.0:${PORT} --workers 1 --threads 4 --timeout 120 'app:create_app()'"]
