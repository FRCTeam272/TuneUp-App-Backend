from datetime import datetime
from typing import List
from fastapi import APIRouter, Request
from pydantic import BaseModel
from database.database_setup import ROSTER
from routes.cache import cached_response
from routes.data import roster

router = APIRouter()

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

# Schedule and room data only change when the roster is reloaded, so these are served from
# cache for the whole event.
@router.get("/", response_model=List[ScheduleResponse])
def get_schedule(request: Request):
    return cached_response(request, (ROSTER,), lambda session, versions: _build_schedule(roster(session, versions)))

def _build_schedule(data):
    events = sorted(data.events, key=lambda e: e.date) # Sort events by datetime

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
            team = data.teams_by_id.get(entry.team_id)
            team_name = team.name if team else None
            temp.append(Entry(text=entry.text.replace(text + ":", "").strip(), team_id=entry.team_id, team_name=team_name))
            
        temp.sort() # Sort entries by team_id
        values.append(ScheduleResponse(info=temp, date=date, name=text))
    
    return values

@router.get("/rooms", response_model=List[RoomAssignmentResponse])
def room_assignment(request: Request):
    return cached_response(request, (ROSTER,), lambda session, versions: _build_rooms(roster(session, versions)))

def _build_rooms(data):
    room_assignments = []
    for event in data.events:
        if "Judge" not in event.name:
            continue
        team = data.teams_by_id.get(event.team_id)
        if team:
            if not hasattr(team, "room"):
                team.room = "Unknown"
            room_assignments.append(RoomAssignmentResponse(
                room=team.room,
                team_id=team.id,
                team_name=team.name,
                judge_session=event.name.split(":")[0] if event.name else "Unknown",
                judge_group=event.name.split(":")[1].strip() if ":" in event.name else "Unknown"
            ))
    
    return room_assignments
