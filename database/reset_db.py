"""Delete every score, contact, event and team, leaving an empty database for a new tournament.

Run from database/:

    python reset_db.py

load_teams.py calls reset_data() itself, so loading a new schedule already clears everything. Run this
directly only to empty the database without loading a schedule.

Rows are deleted rather than the tables dropped: running API workers keep working, and cache_version
stays in place to tell them their cached responses are stale.
"""
import sys

from database_setup import ROSTER, SCORES, Event, Score, Session, Team, TeamContact, bump_cache_versions, engine

# Team last: Postgres refuses to delete a team that other rows still reference.
TABLES = (("scores", Score), ("contacts", TeamContact), ("events", Event), ("teams", Team))


def reset_data(session):
    """Delete all tournament data. Adds to `session`; the caller commits, so a failed reload can roll it back."""
    for _, model in TABLES:
        session.query(model).delete()
    bump_cache_versions(session, ROSTER, SCORES)


def confirm_reset():
    """Say what would be deleted and from where. True if the user types 'yes' or there is nothing to delete."""
    with Session() as session:
        counts = {label: session.query(model).count() for label, model in TABLES}
    if not any(counts.values()):
        return True
    print(f"Database: {engine.url.host or engine.url.database}")
    print("This permanently deletes " + ", ".join(f"{count} {label}" for label, count in counts.items()))
    return input("Type 'yes' to continue: ").strip().lower() == "yes"


if __name__ == "__main__":
    if not confirm_reset():
        sys.exit("Cancelled - nothing deleted")
    with Session() as session:
        reset_data(session)
        session.commit()
    print("Database cleared")
