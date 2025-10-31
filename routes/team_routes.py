import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from database_setup import Event, Team, Score

import routes.env as env

router = APIRouter()

# Setup database engine and session
engine = create_engine('sqlite:///./team.db')
Session = sessionmaker(bind=engine)


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
    scores: list[int]
    top_three_scores: list[int]
    average_top_three: float
    events: list[EventBase] | None = None
class TeamDataBulkResponse(BaseModel):
    team_data: list[TeamSingularResponse]

class RankResponse(BaseModel):
    id: int
    score: float

@router.get("/", response_model=TeamDataBulkResponse)
def get_all_teams():
    session = Session()
    teams = session.query(Team).all()
    session.close()
    response = TeamDataBulkResponse(team_data=[])
    for team in teams:
        scores = session.query(Score).filter_by(team_id=team.id).all()
        team_data = {
            'team_id': int(str(team.id)),
            'name': str(team.name),
            'scores': [],
            'top_three_scores': [],
            'average_top_three': 0.0
        }
        team_data['scores'] = [int(str(score.score)) for score in scores]
        # Calculate top three scores and average
        all_scores = sorted(team_data['scores'], reverse=True)
        team_data['top_three_scores'] = all_scores[:3]
        team_data['average_top_three'] = (sum(team_data['top_three_scores']) / len(team_data['top_three_scores'])) if team_data['top_three_scores'] else 0

        response.team_data.append(TeamSingularResponse(
            team_id=int(str(team.id)),
            name=str(team.name),
            scores=team_data['scores'],
            top_three_scores=team_data['top_three_scores'],
            average_top_three=team_data['average_top_three'],
            events=None
        ))
    response.team_data.sort(key=lambda x: x.average_top_three, reverse=True)
    return response

@router.get("/get_ranks", response_model=list[RankResponse])
def get_ranks():
    session = Session()
    combined_data = []
    
    scores = session.query(Score).all()
    team_scores_map = {}
    for score_obj in scores:
        team_id = int(str(score_obj.team_id))
        score = int(str(score_obj.score))
        if team_id not in team_scores_map:
            team_scores_map[team_id] = []
        team_scores_map[team_id].append(score)

    for team_id, team_scores in team_scores_map.items():
        all_scores = sorted(team_scores, reverse=True)
        top_three_scores = all_scores[:3]
        average_top_three = (sum(top_three_scores) / len(top_three_scores)) if top_three_scores else 0
        combined_data.append(RankResponse(id=team_id, score=average_top_three))

    combined_data.sort(key=lambda x: x.score, reverse=True)
    session.close()

    return combined_data

    team_data: list[TeamSingularResponse]
@router.get("/{team_id}", response_model=TeamSingularResponse)
def get_team(team_id: int):
    session = Session()
    team = session.query(Team).filter_by(id=team_id).first()
    if not team:
        session.close()
        raise HTTPException(status_code=404, detail="Team not found")
    
    scores = session.query(Score).filter_by(team_id=team_id).all()
    session.close()
    
    team_data = {
        'team_id': int(str(team.id)),
        'name': str(team.name),
        'scores': [],
        'top_three_scores': [],
        'average_top_three': 0.0
    }
    team_data['scores'] = [int(str(score.score)) for score in scores]
    
    events = session.query(Event).filter_by(team_id=team_id).all()
    

    # Calculate top three scores and average
    all_scores = sorted(team_data['scores'], reverse=True)
    team_data['top_three_scores'] = all_scores[:3]
    team_data['average_top_three'] = (sum(team_data['top_three_scores']) / len(team_data['top_three_scores'])) if team_data['top_three_scores'] else 0
    
    return TeamSingularResponse(
        team_id=int(str(team.id)),
        name=str(team.name),
        scores=team_data['scores'],
        top_three_scores=team_data['top_three_scores'],
        average_top_three=team_data['average_top_three'],
        events=[EventBase(name=str(event.name), date=datetime.datetime.now()) for event in events]
    )

@router.post("/", response_model=TeamSingularResponse)
def create_team(request: TeamRequest):
    if request.password != env.password_env:
        raise HTTPException(status_code=403, detail="Unauthorized")

    session = Session()
    new_team = Team(name=request.name, id=request.team_id)
    session.add(new_team)
    session.commit()
    session.refresh(new_team)
    session.close()
    return TeamSingularResponse(
        team_id=int(str(new_team.id)),
        name=str(new_team.name),
        scores=[],
        top_three_scores=[],
        average_top_three=0.0,
        events=[]
    )

@router.post("/delete")
def delete_team(request: TeamRequest):
    if request.password != env.password_env:
        raise HTTPException(status_code=403, detail="Unauthorized")

    session = Session()
    team = session.query(Team).filter_by(id=request.team_id).first()
    if not team:
        session.close()
        raise HTTPException(status_code=404, detail="Team not found")
    
    session.delete(team)
    session.commit()
    session.close()
    return {"detail": "Team deleted"}

@router.post("/rename")
def rename_team(request: TeamRequest):
    if request.password != env.password_env:
        raise HTTPException(status_code=403, detail="Unauthorized")

    session = Session()
    team = session.query(Team).filter_by(id=request.team_id).first()
    if not team:
        session.close()
        raise HTTPException(status_code=404, detail="Team not found")
    
    team.name = request.name # pyright: ignore[reportAttributeAccessIssue]
    session.commit()
    session.refresh(team)
    session.close()
    return {"detail": True}

@router.post("/get_events", response_model=list[EventBase])
def get_events(request: TeamRequest):
    session = Session()
    team = session.query(Team).filter_by(id=request.team_id).first()
    if not team:
        session.close()
        raise HTTPException(status_code=404, detail="Team not found")

    events = session.query(Event).filter_by(team_id=request.team_id).all()
    session.close()
    return [EventBase(name=str(event.name), date=datetime.datetime.now()) for event in events]