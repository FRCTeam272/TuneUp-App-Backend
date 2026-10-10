"""Version-validated response cache for the read endpoints.

Each gunicorn worker keeps its own in-process cache, so a plain TTL cache would serve stale
data from workers that didn't handle the write. Instead every cached value is tagged with the
`cache_version` counters it was built from (see database/database_setup.py). A read costs one
query to fetch the current counters; the expensive queries only run when a counter moved.

The same counters form the HTTP ETag, so browsers revalidate with If-None-Match and get a
bodiless 304 when nothing changed.

Out-of-band edits (manual SQL, scripts) must bump the counters too, e.g.
    UPDATE cache_version SET version = version + 1;
"""
import os
import threading

from fastapi import HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse, Response
from sqlalchemy import select

from database.database_setup import CacheVersion, Session

# Changes whenever a new release is deployed so browsers never get a 304 for a response
# whose shape changed. HEROKU_RELEASE_VERSION needs `heroku labs:enable runtime-dyno-metadata`.
_RELEASE = os.getenv("HEROKU_RELEASE_VERSION", "dev")

_entries = {}  # name -> (versions tuple, value)
_locks = {}
_locks_guard = threading.Lock()


def _lock_for(name):
    with _locks_guard:
        return _locks.setdefault(name, threading.Lock())


def current_versions(session):
    return {key: version for key, version in session.execute(select(CacheVersion.key, CacheVersion.version))}


def memoize(name, deps, versions, build, session):
    """Return the cached value for `name`, rebuilding it with build(session) if any of the
    `deps` counters changed since it was built."""
    stamp = tuple(versions.get(key, 0) for key in deps)
    entry = _entries.get(name)
    if entry and entry[0] == stamp:
        return entry[1]
    with _lock_for(name):  # one rebuild at a time per key; other threads wait and reuse it
        entry = _entries.get(name)
        if entry and entry[0] == stamp:
            return entry[1]
        value = build(session)
        _entries[name] = (stamp, value)
        return value


def cached_response(request: Request, deps, build):
    """Serve a JSON response for this request path, cached until a `deps` counter changes.

    build(session, versions) returns the response content (models, lists, dicts) or raises
    HTTPException; errors are never cached."""
    with Session() as session:
        versions = current_versions(session)
        stamp = "-".join(f"{key[0]}{versions.get(key, 0)}" for key in deps)
        etag = f'W/"{_RELEASE}-{stamp}"'
        headers = {"ETag": etag, "Cache-Control": "no-cache"}  # no-cache = revalidate every time

        if request.headers.get("if-none-match") == etag:
            return Response(status_code=304, headers=headers)

        name = request.url.path
        body = memoize(name, deps, versions,
                       lambda s: JSONResponse(jsonable_encoder(build(s, versions))).body, session)
        return Response(content=body, media_type="application/json", headers=headers)


def not_found(detail="Team not found"):
    return HTTPException(status_code=404, detail=detail)
