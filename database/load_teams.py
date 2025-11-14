from sqlalchemy.orm import sessionmaker
from database_setup import Team, Event, engine
import pandas as pd
import os
from datetime import datetime, timedelta

Session = sessionmaker(bind=engine)
session = Session()

def load_teams_and_events_from_csv(csv_file_path='schedule.csv'):
    """
    Load teams and events from the schedule CSV file
    """
    try:
        # Read the CSV file
        df = pd.read_csv(csv_file_path)
        
        print(f"Loading data from {csv_file_path}")
        print(f"Total rows: {len(df)}")
        
        # Filter out columns that are completely empty
        columns_with_values = []
        for col in df.columns:
            has_values = df[col].notna().any() and (df[col].astype(str).str.strip() != '').any()
            if has_values:
                columns_with_values.append(col)
        
        print(f"Columns with values: {len(columns_with_values)}")
        
        # Filter dataframe to only include columns with values
        df_filtered = df[columns_with_values]
        
        # Extract time mapping from the first row (index 0)
        time_mapping = {}
        first_row = df_filtered.iloc[0] if len(df_filtered) > 0 else None
        if first_row is not None:
            for col in columns_with_values:
                value = first_row[col]
                if pd.notna(value) and str(value).strip() != '' and col not in ['Index:', 'Rm:Num', 'Team Number', 'Team Name']:
                    time_mapping[col] = str(value).strip()
        
        print(f"Extracted {len(time_mapping)} time mappings")
        
        # Clear existing data
        print("Clearing existing teams and events...")
        session.query(Event).delete()
        session.query(Team).delete()
        session.commit()
        
        teams_added = 0
        events_added = 0
        
        # Process each team row
        for index, row in df_filtered.iterrows():
            # Skip rows without team information (first row is headers/times)
            team_number = row.get('Team Number', '')
            team_name = row.get('Team Name', '')
            room_number = row.get('Rm:Num', '')
            
            if pd.isna(team_number) or str(team_number).strip() == '':
                continue
            
            # Clean up team data
            team_number_clean = str(team_number).strip()
            team_name_clean = str(team_name).strip() if not pd.isna(team_name) else team_number_clean
            room_number_clean = str(room_number).strip() if not pd.isna(room_number) else None
            
            # Create team with proper ID assignment
            try:
                team_id = int(float(team_name_clean)) if team_name_clean.replace('.', '').isdigit() else None
            except (ValueError, TypeError):
                team_id = None
            
            if team_id is None:
                team_id = teams_added + 1000  # Use high numbers to avoid conflicts
            
            # Create team - handle case where room field might not exist in current DB
            try:
                team = Team(
                    id=team_id,
                    name=team_number_clean,
                    room=room_number_clean
                )
            except TypeError:
                # Fallback if room field doesn't exist in current database schema
                team = Team(
                    id=team_id,
                    name=team_number_clean
                )
                print(f"Note: Room field not available in current schema for team {team_number_clean}")
            session.add(team)
            teams_added += 1
            
            if hasattr(team, 'room'):
                print(f"Added team: {team_number_clean} (Room: {room_number_clean})")
            else:
                print(f"Added team: {team_number_clean}")
            
            # Create events for this team - set to November 22, 2025
            base_date = datetime(2025, 11, 22, 8, 30, 0, 0)
            
            for activity, details in row.items():
                if activity not in ['Index:', 'Rm:Num', 'Team Number', 'Team Name'] and pd.notna(details) and str(details).strip() != '':
                    # Get the time for this activity
                    event_time = base_date
                    if activity in time_mapping:
                        time_str = time_mapping[activity]
                        try:
                            # Parse time string (e.g., "9:00 AM", "1:30 PM") for November 22, 2025
                            event_time = datetime.strptime(f"2025-11-22 {time_str}", "%Y-%m-%d %I:%M %p")
                        except ValueError:
                            print(f"Could not parse time '{time_str}' for activity '{activity}'")
                    
                    # Create event
                    event = Event(
                        name=f"{activity}: {str(details).strip()}",
                        date=event_time,
                        team_id=team.id
                    )
                    session.add(event)
                    events_added += 1
        
        # Commit all changes
        session.commit()
        
        print(f"\nSuccessfully loaded:")
        print(f"- {teams_added} teams")
        print(f"- {events_added} events")
        
        # Display summary
        total_teams = session.query(Team).count()
        total_events = session.query(Event).count()
        print(f"\nDatabase totals:")
        print(f"- {total_teams} teams in database")
        print(f"- {total_events} events in database")
        
        return True
        
    except Exception as e:
        print(f"Error loading data: {e}")
        session.rollback()
        return False
    finally:
        session.close()

def display_teams():
    """Display all teams in the database"""
    session = Session()
    try:
        teams = session.query(Team).all()
        print(f"\n=== All Teams ({len(teams)}) ===")
        for team in teams:
            if hasattr(team, 'room'):
                print(f"ID: {team.id}, Name: {team.name}, Room: {team.room}")
            else:
                print(f"ID: {team.id}, Name: {team.name}")
    finally:
        session.close()

def display_events(limit=20):
    """Display sample events from the database"""
    session = Session()
    try:
        events = session.query(Event).limit(limit).all()
        print(f"\n=== Sample Events (showing {len(events)} of total) ===")
        for event in events:
            team = session.query(Team).filter_by(id=event.team_id).first()
            team_name = team.name if team else "Unknown"
            print(f"Team: {team_name}, Event: {event.name}, Time: {event.date}")
    finally:
        session.close()

if __name__ == "__main__":
    # Load teams and events from CSV
    if load_teams_and_events_from_csv():
        # Display loaded data
        display_teams()
        display_events(30)
    else:
        print("Failed to load data from CSV")

