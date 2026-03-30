# Readwise Reader Personal Site

## Running

The site runs as a Docker container. Start it with:

```bash
docker compose up -d
```

Access at: http://127.0.0.1:5555

The container uses `restart: unless-stopped` — it recovers from crashes automatically and starts on boot (requires Docker Desktop set to start at login).

## Setup

Requires `.env` file with `READWISE_TOKEN=your_token_here`

See README.md for full setup instructions.

## Common commands

| Action | Command |
|--------|---------|
| Start | `docker compose up -d` |
| Stop | `docker compose down` |
| Logs | `docker compose logs -f` |
| Rebuild | `docker compose up -d --build` |
