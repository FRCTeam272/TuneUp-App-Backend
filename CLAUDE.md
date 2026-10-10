# TuneUp Backend (FLL Scoreboard API)

FastAPI app (`main.py`) on Heroku: `gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app` (Procfile).
Production pins are in `requirements.txt` (**UTF-16 LE encoded**; FastAPI 0.119 — newer FastAPI
removed `app.route`, which `main.py` uses).

## Config
`.env` (gitignored) / env vars, read in `routes/env.py` and `database/database_setup.py`:
- `database_url` — SQLAlchemy URL (Heroku Postgres in prod; `sqlite:///team.db` works locally)
- `password` — shared admin password checked on every write endpoint

## Layout
- `database/database_setup.py` — models (`Team`, `Score`, `Event`, `CacheVersion`), the single shared
  `engine`/`Session`, `bump_cache_versions()`. Importing it runs `create_all` (no migrations;
  new tables appear automatically, column changes do not).
- `routes/` — routers mounted at `/team`, `/score`, `/display`, `/schedule`.
- `routes/cache.py` + `routes/data.py` — response cache (see below).
- `database/load_teams.py` — run from `database/` (`python load_teams.py`): wipes teams+events
  and reloads from `schedule.csv`. CSV columns are mislabeled: "Team Number" holds the name and
  "Team Name" holds the number; row 0 holds the time for each activity column. Event date is
  hard-coded to 2025-11-22.
- `database/query_data.py`, `dummy_data.py`, `scripts/` — one-off utilities, not used by the API.

## Caching — keep this working when editing routes
- Two counters in table `cache_version`: `roster` (team/event tables) and `scores`.
- **Every write must call `bump_cache_versions(session, ROSTER and/or SCORES)` before `commit()`**
  in the same transaction. Forgetting this means other gunicorn workers serve stale data.
- Read endpoints use `cached_response(request, deps, build)`: one query reads the counters, the
  response bytes are reused while they're unchanged, and an ETag (`W/"<release>-r<n>-s<n>"`) lets
  browsers revalidate with 304s. Cache key is the URL path, so don't use it for query-param variants.
- `routes/data.py` holds shared snapshots (`roster()`, `standings()`) built with set-based
  queries — use them instead of per-team queries.

## API contract / OpenAPI
The frontend's typed client is generated from this app's OpenAPI spec (NSwag), so:
- After changing any route, request model or response model, run
  `python scripts/export_openapi.py` (no server/DB needed) and commit `openapi.json`, then run
  `npm run api:update` in the frontend.
- Declare `response_model=` on every route; untyped routes become `any` in the frontend.
- operationIds come from function names (`operation_id()` in `main.py`: `get_all_teams` ->
  `getAllTeams`) and become client method names, so renaming a route function is an API change.
- Pydantic model names become TypeScript type names and must be unique across all routers
  (duplicates get mangled names). Shared models go in `routes/schemas.py`.

## Response quirks the frontend depends on
- `room` is `str(team.room)`, so a missing room is the string `"None"` (except `/schedule/rooms`).
- `/team/get_ranks` only includes teams that have scores.
- `/schedule/` slot `name` is the activity prefix of the *last* event in that time slot.

## Testing locally
No test suite. To compare behavior, run against a copy of `team.db` with
`database_url=sqlite:///...` and `fastapi.testclient.TestClient`. SQLite needs real `datetime`s
(Postgres accepts strings).
