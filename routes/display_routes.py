import datetime
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from database.database_setup import ROSTER, SCORES, Session, Team, Event, bump_cache_versions
from routes.cache import cached_response, not_found
from routes.data import standings
import routes.env as env

router = APIRouter()

class DisplayEvent(BaseModel):
    name: str
    date: datetime.datetime | None = None
class DisplayTeamScoresResponse(BaseModel):
    team_id: int
    team_name: str
    room: str | None = None
    scores: list[int]
    top_three_scores: list[int]
    average_top_three: float
    events: list[DisplayEvent] | None = None
def _display_response(standing):
    return DisplayTeamScoresResponse(
        team_id=standing.team.id,
        team_name=str(standing.team.name),
        room=str(standing.team.room),
        scores=standing.scores,
        top_three_scores=standing.top_three_scores,
        average_top_three=standing.average_top_three,
    )

@router.get("/", response_model=list[DisplayTeamScoresResponse])
def display_scores(request: Request):
    return cached_response(request, (ROSTER, SCORES), lambda session, versions: [
        _display_response(standing) for standing in standings(session, versions).ranked
    ])

class display_team_scores_request(BaseModel):
    team_id: int
@router.get("/{team_id}", response_model=DisplayTeamScoresResponse)
def display_team_scores(team_id: int, request: Request):
    def build(session, versions):
        standing = standings(session, versions).by_team_id.get(team_id)
        if not standing:
            raise not_found()
        return _display_response(standing)
    return cached_response(request, (ROSTER, SCORES), build)

class AddEventRequest(BaseModel):
    team_id: int
    event_name: str
    event_date: str
    password: str
class AddEventResponse(BaseModel):
    id: int
    name: str
    date: datetime.datetime
    team_id: int
@router.post("/add_event", response_model=AddEventResponse)
def add_event(request: AddEventRequest):
    if request.password != env.password_env:
        raise HTTPException(status_code=403, detail="Unauthorized")

    session = Session()
    team = session.query(Team).filter_by(id=request.team_id).first()
    if not team:
        session.close()
        raise HTTPException(status_code=404, detail="Team not found")

    try:
        event_date = datetime.datetime.fromisoformat(request.event_date)
    except ValueError:
        event_date = request.event_date  # let the database parse other formats, as before
    new_event = Event(name=request.event_name, date=event_date, team_id=request.team_id)
    session.add(new_event)
    bump_cache_versions(session, ROSTER)
    session.commit()
    session.refresh(new_event)
    session.close()
    return {"id": new_event.id, "name": new_event.name, "date": new_event.date, "team_id": new_event.team_id}

# Pydantic models for request bodies
class CheckPasswordRequest(BaseModel):
    password: str
class CheckPasswordResponse(BaseModel):
    status: bool
@router.post("/check_password", response_model=CheckPasswordResponse)
def check_password(request: CheckPasswordRequest):
    if request.password == env.password_env:
        return CheckPasswordResponse(status=True)
    else:
        return CheckPasswordResponse(status=False)