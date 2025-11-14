from sqlalchemy.orm import sessionmaker
from database_setup import Team, Event, engine
from datetime import datetime

Session = sessionmaker(bind=engine)

def show_team_schedule(team_name_search=None, team_id=None):
    """Show complete schedule for a specific team"""
    session = Session()
    try:
        if team_id:
            team = session.query(Team).filter_by(id=team_id).first()
        else:
            team = session.query(Team).filter(Team.name.like(f'%{team_name_search}%')).first()
        
        if not team:
            print(f"Team not found: {team_name_search or team_id}")
            return
        
        events = session.query(Event).filter_by(team_id=team.id).order_by(Event.date).all()
        
        print(f"\n=== Schedule for {team.name} (ID: {team.id}) ===")
        if hasattr(team, 'room') and team.room:
            print(f"Room: {team.room}")
        print(f"Total Events: {len(events)}")
        print("-" * 60)
        
        for event in events:
            time_str = event.date.strftime("%I:%M %p")
            print(f"{time_str:>8} | {event.name}")
            
    finally:
        session.close()

def show_schedule_by_time():
    """Show all events organized by time"""
    session = Session()
    try:
        events = session.query(Event).order_by(Event.date).all()
        
        print(f"\n=== Schedule by Time (Total: {len(events)} events) ===")
        print("-" * 80)
        
        current_time = None
        for event in events:
            event_time = event.date.strftime("%I:%M %p")
            team = session.query(Team).filter_by(id=event.team_id).first()
            team_name = team.name if team else "Unknown"
            
            if event_time != current_time:
                print(f"\n{event_time}")
                print("-" * 20)
                current_time = event_time
            
            print(f"  {team_name:25} | {event.name}")
            
    finally:
        session.close()

def show_team_summary():
    """Show summary of all teams"""
    session = Session()
    try:
        teams = session.query(Team).order_by(Team.id).all()
        
        print(f"\n=== Team Summary ({len(teams)} teams) ===")
        print("-" * 60)
        
        for team in teams:
            event_count = session.query(Event).filter_by(team_id=team.id).count()
            room_info = f" (Room: {team.room})" if hasattr(team, 'room') and team.room else ""
            print(f"ID: {team.id:5} | {team.name:30}{room_info} | {event_count} events")
            
    finally:
        session.close()

def search_events(search_term):
    """Search for events containing specific text"""
    session = Session()
    try:
        events = session.query(Event).filter(Event.name.like(f'%{search_term}%')).order_by(Event.date).all()
        
        print(f"\n=== Events containing '{search_term}' ({len(events)} found) ===")
        print("-" * 80)
        
        for event in events:
            team = session.query(Team).filter_by(id=event.team_id).first()
            team_name = team.name if team else "Unknown"
            time_str = event.date.strftime("%I:%M %p")
            print(f"{time_str:>8} | {team_name:25} | {event.name}")
            
    finally:
        session.close()

if __name__ == "__main__":
    print("Database Query Examples:")
    print("=" * 50)
    
    # Show team summary
    show_team_summary()
    
    # Show specific team schedule
    show_team_schedule("RoboHatters Red")
    
    # Show events by time (first 20)
    print("\n=== First 20 Events by Time ===")
    session = Session()
    events = session.query(Event).order_by(Event.date).limit(20).all()
    for event in events:
        team = session.query(Team).filter_by(id=event.team_id).first()
        team_name = team.name if team else "Unknown"
        time_str = event.date.strftime("%I:%M %p")
        print(f"{time_str:>8} | {team_name:25} | {event.name}")
    session.close()
    
    # Search for specific activities
    search_events("Judge")
    
    print("\nUse the functions in this script to explore the data:")
    print("- show_team_schedule('team_name') or show_team_schedule(team_id=1234)")
    print("- show_schedule_by_time()")
    print("- show_team_summary()")
    print("- search_events('search_term')")