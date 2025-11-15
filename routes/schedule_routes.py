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