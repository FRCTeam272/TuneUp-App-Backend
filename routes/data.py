"""Cached snapshots of the database shared by the read endpoints.

Each snapshot is built with a handful of set-based queries (instead of one query per team) and
reused until its cache_version counters change. Snapshots are plain tuples/dicts so they can be
shared between request threads safely; treat them as read-only.
"""
from collections import namedtuple

from database.database_setup import ROSTER, SCORES, Event, Score, Team
from routes.cache import memoize

TeamRow = namedtuple("TeamRow", "id name room")
EventRow = namedtuple("EventRow", "id name date team_id")
Standing = namedtuple("Standing", "team scores top_three_scores average_top_three")

Roster = namedtuple("Roster", "teams teams_by_id events events_by_team")
Standings = namedtuple("Standings", "ranked by_team_id team_score_lists")


def _load_roster(session):
    teams = [TeamRow(t.id, t.name, t.room) for t in session.query(Team).all()]
    events = [EventRow(e.id, e.name, e.date, e.team_id)
              for e in session.query(Event).order_by(Event.id).all()]
    events_by_team = {}
    for event in events:
        events_by_team.setdefault(event.team_id, []).append(event)
    return Roster(teams, {t.id: t for t in teams}, events, events_by_team)


def roster(session, versions):
    """Teams and events. Only changes when teams/events are edited or reloaded from CSV."""
    return memoize("data:roster", (ROSTER,), versions, _load_roster, session)


def summarize(scores):
    top_three = sorted(scores, reverse=True)[:3]
    average = (sum(top_three) / len(top_three)) if top_three else 0
    return top_three, average


def _load_standings(session, versions):
    teams = roster(session, versions).teams
    # Keyed by every team_id in the score table, including ids with no team row (get_ranks relies on that).
    team_score_lists = {}
    for team_id, score in session.query(Score.team_id, Score.score).order_by(Score.id).all():
        team_score_lists.setdefault(team_id, []).append(score)

    standings = []
    for team in teams:
        scores = team_score_lists.get(team.id, [])
        standings.append(Standing(team, scores, *summarize(scores)))
    ranked = sorted(standings, key=lambda s: s.average_top_three, reverse=True)
    return Standings(ranked, {s.team.id: s for s in standings}, team_score_lists)


def standings(session, versions):
    """Every team with its scores and top-three average, best first."""
    return memoize("data:standings", (ROSTER, SCORES), versions,
                   lambda s: _load_standings(s, versions), session)
