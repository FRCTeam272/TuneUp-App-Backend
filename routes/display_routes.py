import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from database_setup import Team, Score, Event
import routes.env as env

router = APIRouter()

# Setup database engine and session
engine = create_engine('sqlite:///./team.db')
Session = sessionmaker(bind=engine)
class EventBase(BaseModel):
    name: str
    date: datetime.datetime | None = None
class display_team_scores_response(BaseModel):
    team_id: int
    team_name: str
    scores: list[int]
    top_three_scores: list[int]
    average_top_three: float
    events: list[EventBase] | None = None
@router.get("/")
def display_scores():
    session = Session()
    teams = session.query(Team).all()

    combined_data = []
    for team in teams:
        team_scores = session.query(Score).filter_by(team_id=team.id).all()
        team_scores = [int(str(score.score)) for score in team_scores]
        
        # Calculate top three scores and average
        all_scores = sorted(team_scores, reverse=True)
        top_three_scores = all_scores[:3]
        average_top_three = (sum(top_three_scores) / len(top_three_scores)) if top_three_scores else 0

        combined_data.append(display_team_scores_response(
            team_id=int(str(team.id)),
            team_name=str(team.name),
            scores=team_scores,
            top_three_scores=top_three_scores,
            average_top_three=average_top_three,
            events=None
        ))
    combined_data.sort(key=lambda x: x.average_top_three, reverse=True)
    session.close()
    return combined_data

class display_team_scores_request(BaseModel):
    team_id: int
@router.get("/{team_id}")
def display_team_scores(team_id: int):
    session = Session()
    team = session.query(Team).filter_by(id=team_id).first()
    if not team:
        session.close()
        raise HTTPException(status_code=404, detail="Team not found")

    team_scores = session.query(Score).filter_by(team_id=team.id).all()
    team_scores = [int(str(score.score)) for score in team_scores]

    # Calculate top three scores and average
    all_scores = sorted(team_scores, reverse=True)
    top_three_scores = all_scores[:3]
    average_top_three = (sum(top_three_scores) / len(top_three_scores)) if top_three_scores else 0
    
    session.close()
    return display_team_scores_response(
        team_id=int(str(team.id)),
        team_name=str(team.name),
        scores=team_scores,
        top_three_scores=top_three_scores,
        average_top_three=average_top_three,
    )   

class AddEventRequest(BaseModel):
    team_id: int
    event_name: str
    event_date: str
    password: str
@router.post("/add_event")
def add_event(request: AddEventRequest):
    if request.password != env.password_env:
        raise HTTPException(status_code=403, detail="Unauthorized")

    session = Session()
    team = session.query(Team).filter_by(id=request.team_id).first()
    if not team:
        session.close()
        raise HTTPException(status_code=404, detail="Team not found")

    new_event = Event(name=request.event_name, date=request.event_date, team_id=request.team_id)
    session.add(new_event)
    session.commit()
    session.refresh(new_event)
    session.close()
    return new_event.serialize

# Pydantic models for request bodies
class CheckPasswordRequest(BaseModel):
    password: str
class CheckPasswordResponse(BaseModel):
    status: bool
@router.post("/check_password", response_model=CheckPasswordResponse)
def check_password(request: CheckPasswordRequest):
    print(f"password: {request.password}, env.password_env: {env.password_env}")

    if request.password == env.password_env:
        return CheckPasswordResponse(status=True)
    else:
        return CheckPasswordResponse(status=False)