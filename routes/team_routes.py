import datetime
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from database.database_setup import ROSTER, SCORES, Session, Team, Score, Event, bump_cache_versions
from routes.cache import cached_response, current_versions, not_found
from routes.data import roster, standings, summarize
from routes.schemas import DetailResponse
import routes.env as env

router = APIRouter()


class TeamRequest(BaseModel):
    team_id: int
    name: str | None = None
    password: str = ""
class EventBase(BaseModel):
    name: str
    date: datetime.datetime
class TeamSingularResponse(BaseModel):
    team_id: int
    name: str
    room: str | None = None
    scores: list[int]
    top_three_scores: list[int]
    average_top_three: float
    events: list[EventBase] | None = None
class TeamDataBulkResponse(BaseModel):
    team_data: list[TeamSingularResponse]

class RankResponse(BaseModel):
    id: int
    score: float

def _team_response(standing, events_by_team):
    team = standing.team
    return TeamSingularResponse(
        team_id=team.id,
        name=str(team.name),
        room=str(team.room),
        scores=standing.scores,
        top_three_scores=standing.top_three_scores,
        average_top_three=standing.average_top_three,
        events=[EventBase(name=str(event.name), date=event.date) for event in events_by_team.get(team.id, [])]
    )

@router.get("/", response_model=TeamDataBulkResponse)
def get_all_teams(request: Request):
    def build(session, versions):
        events_by_team = roster(session, versions).events_by_team
        return TeamDataBulkResponse(team_data=[
            _team_response(standing, events_by_team) for standing in standings(session, versions).ranked
        ])
    return cached_response(request, (ROSTER, SCORES), build)

@router.get("/get_ranks", response_model=list[RankResponse])
def get_ranks(request: Request):
    def build(session, versions):
        combined_data = [RankResponse(id=team_id, score=summarize(scores)[1])
                         for team_id, scores in standings(session, versions).team_score_lists.items()]
        combined_data.sort(key=lambda x: x.score, reverse=True)
        return combined_data
    return cached_response(request, (ROSTER, SCORES), build)

@router.get("/{team_id}", response_model=TeamSingularResponse)
def get_team(team_id: int, request: Request):
    def build(session, versions):
        standing = standings(session, versions).by_team_id.get(team_id)
        if not standing:
            raise not_found()
        return _team_response(standing, roster(session, versions).events_by_team)
    return cached_response(request, (ROSTER, SCORES), build)

@router.post("/", response_model=TeamSingularResponse)
def create_team(request: TeamRequest):
    if request.password != env.password_env:
        raise HTTPException(status_code=403, detail="Unauthorized")

    session = Session()
    new_team = Team(name=request.name, id=request.team_id)
    session.add(new_team)
    bump_cache_versions(session, ROSTER)
    session.commit()
    session.refresh(new_team)
    session.close()
    return TeamSingularResponse(
        team_id=int(str(new_team.id)),
        name=str(new_team.name),
        room=str(new_team.room) if hasattr(new_team, 'room') else None,
        scores=[],
        top_three_scores=[],
        average_top_three=0.0,
        events=[]
    )

class DeleteTeamResponse(BaseModel):
    detail: str
@router.post("/delete", response_model=DeleteTeamResponse)
def delete_team(request: TeamRequest):
    if request.password != env.password_env:
        raise HTTPException(status_code=403, detail="Unauthorized")

    session = Session()
    team = session.query(Team).filter_by(id=request.team_id).first()
    if not team:
        session.close()
        raise HTTPException(status_code=404, detail="Team not found")
    
    # Scores and events reference the team, so Postgres rejects deleting the team while they exist.
    session.query(Score).filter_by(team_id=request.team_id).delete()
    session.query(Event).filter_by(team_id=request.team_id).delete()
    session.delete(team)
    bump_cache_versions(session, ROSTER, SCORES)
    session.commit()
    session.close()
    return {"detail": "Team deleted"}

@router.post("/rename", response_model=DetailResponse)
def rename_team(request: TeamRequest):
    if request.password != env.password_env:
        raise HTTPException(status_code=403, detail="Unauthorized")

    session = Session()
    team = session.query(Team).filter_by(id=request.team_id).first()
    if not team:
        session.close()
        raise HTTPException(status_code=404, detail="Team not found")
    
    team.name = request.name # pyright: ignore[reportAttributeAccessIssue]
    bump_cache_versions(session, ROSTER)
    session.commit()
    session.refresh(team)
    session.close()
    return {"detail": True}

@router.post("/get_events", response_model=list[EventBase])
def get_events(request: TeamRequest):
    # POST so it can't use HTTP caching, but it still reuses the cached roster snapshot.
    with Session() as session:
        data = roster(session, current_versions(session))
    if request.team_id not in data.teams_by_id:
        raise not_found()
    return [EventBase(name=str(event.name), date=event.date) for event in data.events_by_team.get(request.team_id, [])]
