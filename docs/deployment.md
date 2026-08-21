# Deployment

The Docker image is the supported way to run survey-builder. It runs the
database migrations on start and then serves the app with gunicorn on port 8000.

## Checklist

1. **PostgreSQL** 15 or newer. Point `DATABASE_URL` at it, for example
   `postgresql://surveys:secret@db.internal:5432/surveys`.
2. **`SECRET_KEY`**: a long random value, e.g. `python -c "import secrets; print(secrets.token_urlsafe(48))"`.
   Changing it signs everyone out and invalidates half-finished survey sessions.
3. **HTTPS** in front of the app (a reverse proxy or load balancer), then set
   `SECURE_COOKIES=true`.
4. `SEED_DEMO=false` (the default outside docker compose).
5. Create the first account: `docker compose exec web flask create-user you@example.com`.

## Reverse proxy

The app expects to be served at the root path. A minimal nginx location:

```nginx
location / {
    proxy_pass http://127.0.0.1:4416;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Request-ID $request_id;
}
```

Set `TRUSTED_PROXIES=1` so the app trusts the proxy's `X-Forwarded-*` headers;
without it share links are generated with `http://` even when the site is
served over HTTPS.

The `X-Request-ID` header is echoed back and written to the request log, which
makes it easy to match proxy and app logs.

## Health checks

`GET /healthz` returns `200 {"status": "ok", "database": "ok"}` and `503` when
the database cannot be reached. The image's `HEALTHCHECK` uses it.

## Housekeeping

Responses that were started but never submitted are kept so the completion
rate can be computed. Remove old ones from time to time:

```bash
docker compose exec web flask prune-incomplete --days 30
```

## Backups

All state is in PostgreSQL. Back it up with `pg_dump`; there are no uploaded
files to copy.

## Upgrading

Pull the new image and restart the container. Migrations run automatically;
they only add tables, columns and indexes, so a rollback to the previous image
keeps working against the upgraded schema.
