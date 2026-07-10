# URL Shortener Service

A lightweight and fast URL shortening service built with **Django** (no DRF).  
It allows you to create short links, set custom aliases, define expiration dates, track click statistics, and deactivate or delete links.

---

## Features

- **Create short URLs** – automatically generates a unique short code or lets you specify a custom one.
- **Set expiration date** – links can expire after a certain date/time.
- **Redirect** – visiting the short URL redirects to the original URL.
- **Click statistics** – each redirect is logged with IP address and user agent.
- **Info endpoint** – retrieve metadata about a link, including click count and recent clicks.
- **Deactivate** – temporarily disable a link without deleting it.
- **Delete** – permanently remove a link and its logs.

---

## Quick Start

### Using Docker

1. Pull the image from Docker Hub (replace `yourusername` with your Docker Hub username):

```bash
docker run -d -p 8000:8000 yourusername/shortlink-service:latest
```

2. The service will be available at `http://localhost:8000`.

### Local Development (without Docker)

1. Clone the repository:
```bash
git clone https://github.com/yourusername/shortlink.git
cd shortlink-service
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate      # Linux/macOS
# or venv\Scripts\activate    # Windows
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up the database:
```bash
python manage.py migrate
```

5. Create a superuser (optional, for admin interface):
```bash
python manage.py createsuperuser
```

6. Run the development server:
```bash
python manage.py runserver
```

The service will run at `http://127.0.0.1:8000`.

---

## API Endpoints

All endpoints return/accept **JSON** unless stated otherwise.

### 1. Create a short link

**POST** `/api/links/`

Request body:
```json
{
    "original_url": "https://example.com/very/long/path",
    "custom_code": "myalias",          // optional, auto‑generated if omitted
    "expires_at": "2026-12-31T23:59:59Z"  // optional, ISO 8601 datetime
}
```

Response (201 Created):
```json
{
    "short_url": "http://localhost:8000/s/myalias",
    "short_code": "myalias",
    "original_url": "https://example.com/very/long/path",
    "expires_at": "2026-12-31T23:59:59+00:00"
}
```

### 2. Redirect

**GET** `/s/<short_code>`

Returns an HTTP 302 redirect to the original URL.  
If the link is expired or inactive, returns 410 (Gone) or 404 (Not Found).

### 3. Get link information

**GET** `/api/links/<short_code>/`

Response (200 OK):
```json
{
    "original_url": "https://example.com/very/long/path",
    "short_code": "myalias",
    "created_at": "2025-01-01T12:00:00Z",
    "expires_at": "2026-12-31T23:59:59Z",
    "is_active": true,
    "click_count": 42,
    "recent_clicks": [
        {
            "timestamp": "2025-01-02T10:00:00Z",
            "ip_address": "192.168.1.1",
            "user_agent": "Mozilla/5.0 ..."
        }
    ]
}
```

### 4. Deactivate a link

**POST** `/api/links/<short_code>/deactivate/`

Response (200 OK):
```json
{
    "status": "deactivated",
    "short_code": "myalias"
}
```

### 5. Delete a link (permanent)

**DELETE** `/api/links/<short_code>/delete/`

Response (200 OK):
```json
{
    "status": "deleted",
    "short_code": "myalias"
}
```

---

## Rate Limiting

The API enforces rate limits to prevent abuse:

- `POST requests` – **10 requests per minute** per IP address.
- `GET requests` – **30 requests per minute** per IP address.

When the limit is exceeded, the server responds with **`429 Too Many Requests`** and a JSON error message:

```json
{
    "error": "Sorry you are blocked"
}
```

Limits are implemented using **[django-ratelimit](https://github.com/jsocol/django-ratelimit)** with **Redis** as the storage backend for counters.

---

## Redis Configuration

Redis is used for:

- Storing rate‑limit counters.
- Caching (optional, can be extended).

### Setting up Redis locally

1. Start Redis (e.g., via Docker):
   ```bash
   docker run -d -p 6379:6379 redis:7-alpine
   ```
   or natively with `redis-server`.

2. Set the environment variable:
   ```bash
   export REDIS_URL=redis://localhost:6379/1
   ```

3. Run the Django server – Redis will be automatically used.

### Fallback behaviour

If Redis is not available (or `REDIS_URL` is not set), the application falls back to **local‑memory cache** (per process) – this is **not recommended for production** but useful for development and testing. In production, always use Redis.

---

## Configuration via Environment Variables

You can override settings using environment variables:

| Variable       | Description                                    | Default         |
|----------------|------------------------------------------------|-----------------|
| `DB_NAME`      | PostgreSQL database name                       | `shortlink-db`      |
| `DB_USER`      | PostgreSQL user                                | `postgres`      |
| `DB_PASSWORD`  | PostgreSQL password                            | `1234`         |
| `DB_HOST`      | PostgreSQL host                                | `localhost`     |
| `DB_PORT`      | PostgreSQL port                                | `5432`          |
| `SECRET_KEY`   | Django secret key                              | `secret`      |
| `REDIS_URL`    | Redis url for caching and ratelimiting support | `my-redis-url`      |

---

## Running Tests

The project uses Django's built-in test framework. To run all tests:

```bash
python manage.py test links/tests/
```

---

## Docker Multi‑Architecture Build

The Dockerfile is based on `python:3.11-slim-bookworm` and supports three platforms:

- `linux/amd64` (Intel/AMD)
- `linux/arm64` (ARM 64-bit, e.g., AWS Graviton, Apple Silicon)
- `linux/arm/v7` (ARM 32-bit, e.g., Raspberry Pi 3/4)

Images are built using Docker Buildx and QEMU emulation, so you can run them on any of these architectures.
