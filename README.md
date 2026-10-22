# I-adore-pdf

A self-hosted PDF toolkit in the style of iLovePDF. Everything runs on your own machine or server.

| Tool | What it does |
| --- | --- |
| Merge PDF | Combine several PDFs, in any order |
| Split PDF | Extract page ranges (`1-3,5,8-`) or save every page as a separate PDF (ZIP) |
| Image to PDF | JPG, PNG or WEBP to PDF, with EXIF rotation fixed, optional A4 pages |
| Compress PDF | Three presets (low, recommended, extreme) with before/after sizes |
| Scan document | Photos to flat black and white PDF pages: finds the page edges, straightens the perspective, supports several photos in one PDF |
| OCR PDF | Makes scanned PDFs searchable (English and Indonesian) |

Stack: FastAPI (Python 3.12) + React, Vite and TypeScript. Compression uses Ghostscript, scanning uses OpenCV, OCR uses OCRmyPDF with Tesseract.

## Run it (Docker)

```bash
docker compose up --build
```

Open <http://localhost:8000>. The port is bound to `127.0.0.1`, so only your own machine can reach it.

> **No login by default.** That is fine on localhost. Set `AUTH_USERNAME` and `AUTH_PASSWORD` before you expose the app to any network (see [Deploying](#deploying)).

## Develop

With hot reload for both backend and frontend:

```bash
docker compose -f docker-compose.dev.yml up --build
```

- Web app (Vite): <http://localhost:5173>
- API (FastAPI): <http://localhost:8000/api/docs>

Without Docker you need Python 3.12 and Node 24, plus Ghostscript and Tesseract for compression and OCR (those two tools are skipped in tests when missing):

```bash
# backend
cd backend
python -m venv .venv && .venv/Scripts/activate      # Windows; use .venv/bin/activate elsewhere
pip install -r requirements-dev.txt
pytest

# frontend
cd frontend
npm ci
npm test
npm run dev
```

The most reliable way to run the full backend test suite (including Ghostscript and real OCR) is inside the Docker image:

```bash
docker compose -f docker-compose.dev.yml build backend
docker run --rm --user root -v "$PWD/backend:/srv/backend" -w /srv/backend \
  i-adore-pdf-backend sh -c "pip install -q -r requirements-dev.txt && python -m pytest -q"
```

(Adjust the image name to what `docker images` shows for your checkout, for example `re_ilovepdf-backend`.)

## Configuration

Set these as environment variables, or in a `.env` file next to `docker-compose.yml` (see `.env.example`).

| Variable | Default | Meaning |
| --- | --- | --- |
| `AUTH_USERNAME`, `AUTH_PASSWORD` | empty | Turns on HTTP Basic login. Set both or neither; the app refuses to start with only one. |
| `MAX_FILE_MB` | `50` | Largest single upload |
| `MAX_TOTAL_MB` | `200` | Largest combined upload per request |
| `JOB_TTL_SECONDS` | `1800` | Results are deleted this long after creation |
| `RATE_LIMIT_PER_MINUTE` | `120` | POST requests per client per minute. `0` turns it off. |
| `TRUST_PROXY_HEADERS` | `false` | Read the client IP from `X-Forwarded-For`. Only enable behind a proxy you control. |
| `CORS_ORIGINS` | empty | Comma-separated origins allowed to call the API from another website. Empty means same-origin only. |

## Deploying

The image needs Ghostscript and Tesseract, so use a container host. Serverless platforms such as Vercel are not a fit.

1. **Turn on login.** Set `AUTH_USERNAME` and a long random `AUTH_PASSWORD`. HTTP Basic sends the password with every request, so only use it over HTTPS.
2. **Serve over HTTPS** through a reverse proxy or your platform's router (Caddy, Nginx, Railway, Render, Fly.io all do this). Then set `TRUST_PROXY_HEADERS=true` so rate limiting sees real client IPs.
3. **Choose the port exposure.** `docker-compose.yml` binds `127.0.0.1:8000`. For a reverse proxy on the same host that is what you want. On a platform that routes traffic itself, expose container port `8000` instead.
4. **Size the machine.** OCR and compression are CPU and memory heavy. 2 GB RAM is a sensible minimum, and `/tmp` is a 2 GB tmpfs in the compose file, which also caps how much can be processed at once.

Platform notes:

- **VPS** (any Linux box with Docker): copy the repo, create `.env`, run `docker compose up -d --build`, and put Caddy or Nginx in front for HTTPS.
- **Railway, Render, Fly.io**: deploy from the root `Dockerfile`, set the variables above in the dashboard, and let the platform provide HTTPS. Expose port `8000`.

## Security notes

- Without `AUTH_USERNAME`/`AUTH_PASSWORD` anyone who can reach the port can use the tools. Keep that to localhost.
- Uploads are checked by file content (not just the extension), size-limited, and stored under random names that are deleted after `JOB_TTL_SECONDS`.
- External programs (Ghostscript, Tesseract) are started without a shell and with a timeout.
- The container runs as a non-root user, with a read-only filesystem, all Linux capabilities dropped, and `no-new-privileges`.
- Responses include `X-Content-Type-Options`, `X-Frame-Options` and a Content-Security-Policy.
- The in-memory rate limiter is per process. If you run several replicas, add limiting at the proxy too.
- Files from the web are not scanned for malware. Do not open untrusted outputs on a machine you care about.

## Project layout

```
backend/app/    FastAPI app: routers/ (HTTP), services/ (PDF, image, OCR logic), utils/
backend/tests/  pytest suite
frontend/src/   React app: pages/, components/, hooks/, lib/, api/
Dockerfile      production image (builds the frontend, serves it from FastAPI)
docker-compose.yml, docker-compose.dev.yml
```
