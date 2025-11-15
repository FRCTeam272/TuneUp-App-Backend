from datetime import datetime
from typing import List
from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from database.database_setup import Event, Team

router = APIRouter()

engine = create_engine('sqlite:///./team.db')
Session = sessionmaker(bind=engine)

class Entry(BaseModel):
    text: str
    team_id: int
    team_name: str | None = None

    def __lt__(self, other):
        if "Table" in self.text and "Table" in other.text:
            return self.text < other.text
        if "Table" in self.text:
            return True
        if "Table" in other.text:
            return False
        
        return self.text < other.text

class ScheduleResponse(BaseModel):
    info: list[Entry]
    name: str
    date: datetime

class RoomAssignmentResponse(BaseModel):
    room: str
    team_id: int
    team_name: str
    judge_session: str
    judge_group: str

@router.get("/", response_model=List[ScheduleResponse])
def get_schedule():
    session = Session()
    events = session.query(Event).all()
    teams = session.query(Team).all()
    session.close()

    events.sort(key=lambda e: e.date) # Sort events by datetime

    schedule = {}
    for event in events:
        if event.date not in schedule:
            schedule[event.date] = []
        schedule[event.date].append(Entry(text=event.name, team_id=event.team_id))
    values = []

    for date in sorted(schedule.keys()):
        temp = []
        text = ""
        for entry in schedule[date]:
            text = entry.text.split(":")[0] if entry.text else ""
            team_name = next((team.name for team in teams if team.id == entry.team_id), None)
            temp.append(Entry(text=entry.text.replace(text + ":", "").strip(), team_id=entry.team_id, team_name=team_name))
            
        temp.sort() # Sort entries by team_id
        values.append(ScheduleResponse(info=temp, date=date, name=text))
    
    return values

@router.get("/rooms", response_model=List[RoomAssignmentResponse])
def room_assignment():
    session = Session()
    teams = session.query(Team).all()
    events = session.query(Event).filter(Event.name.contains("Judge")).all()
    session.close()

    room_assignments = []
    for event in events:
        team = next((team for team in teams if team.id == event.team_id), None)
        if team:
            room_assignments.append(RoomAssignmentResponse(
                room=team.room if hasattr(team, 'room') else "Unknown",
                team_id=team.id,
                team_name=team.name,
                judge_session=event.name.split(":")[0] if event.name else "Unknown",
                judge_group=event.name.split(":")[1].strip() if ":" in event.name else "Unknown"
            ))
    
    return room_assignments