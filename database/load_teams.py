from sqlalchemy.orm import sessionmaker
from database_setup import Team, Event, engine, ROSTER, SCORES, bump_cache_versions
from load_contacts import load_contacts
from reset_db import confirm_reset, reset_data
from file_picker import pick_csv
import pandas as pd
import sys
import os
from datetime import date, datetime, timedelta

# Day of the tournament; every event in the schedule is placed on this date.
EVENT_DATE = date(2026, 11, 21)

Session = sessionmaker(bind=engine)
session = Session()

def _clean_cell(value):
    if pd.isna(value):
        return None
    text = str(value).strip()
    return text or None


def _as_int(text):
    try:
        return int(float(text))
    except (TypeError, ValueError):
        return None


def load_teams_and_events_from_csv(csv_file_path='schedule.csv', contacts_file_path='contacts.csv'):
    """
    Load teams and events from the schedule CSV file, then team contacts from contacts_file_path
    (if it exists - see load_contacts.py).
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
        print("Clearing all existing data (scores, contacts, events and teams)...")
        reset_data(session)
        # No commit here: the wipe and the reload commit together, so a failure leaves the old data intact.
        
        teams_added = 0
        events_added = 0
        
        # Process each team row
        for index, row in df_filtered.iterrows():
            # Skip rows without team information (first row is headers/times)
            number_cell = _clean_cell(row.get('Team Number'))
            name_cell = _clean_cell(row.get('Team Name'))
            room_number_clean = _clean_cell(row.get('Rm:Num'))

            if number_cell is None and name_cell is None:
                continue

            # Older schedules had "Team Number"/"Team Name" swapped, so use whichever cell is the number.
            if _as_int(number_cell) is not None:
                team_id, team_name_clean = _as_int(number_cell), name_cell or number_cell
            elif _as_int(name_cell) is not None:
                team_id, team_name_clean = _as_int(name_cell), number_cell or name_cell
            else:
                team_id, team_name_clean = None, number_cell or name_cell

            if team_id is None:
                team_id = teams_added + 1000  # Use high numbers to avoid conflicts
                print(f"Warning: no team number for '{team_name_clean}', using id {team_id}")

            team = Team(id=team_id, name=team_name_clean, room=room_number_clean)
            session.add(team)
            teams_added += 1
            print(f"Added team: {team_id} {team_name_clean} (Room: {room_number_clean})")

            # Create events for this team on EVENT_DATE
            base_date = datetime.combine(EVENT_DATE, datetime.min.time()).replace(hour=8, minute=30)
            
            for activity, details in row.items():
                if activity not in ['Index:', 'Rm:Num', 'Team Number', 'Team Name'] and pd.notna(details) and str(details).strip() != '':
                    # Get the time for this activity
                    event_time = base_date
                    if activity in time_mapping:
                        time_str = time_mapping[activity]
                        try:
                            # Parse time string (e.g., "9:00 AM", "1:30 PM") on EVENT_DATE
                            event_time = datetime.combine(EVENT_DATE, datetime.strptime(time_str, "%I:%M %p").time())
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
        
        if contacts_file_path and os.path.exists(contacts_file_path):
            load_contacts(session, contacts_file_path)
        else:
            print(f"No {contacts_file_path} found - teams have no contact info (run load_contacts.py later)")

        # Commit all changes (and tell running API workers to drop their cached responses)
        bump_cache_versions(session, ROSTER, SCORES)
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

CSV_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'CSV_Imports')

if __name__ == "__main__":
    # Paths can be given on the command line (python load_teams.py schedule.csv contacts.csv);
    # otherwise a file dialog asks for each one.
    schedule_path = sys.argv[1] if len(sys.argv) > 1 else pick_csv("Select the schedule CSV (teams and events)", initialdir=CSV_DIR)
    if not schedule_path:
        sys.exit("No schedule file selected - nothing loaded")
    contacts_path = sys.argv[2] if len(sys.argv) > 2 else pick_csv(
        "Select the contacts CSV (e.g. receipts.csv) - Cancel to skip contacts",
        initialdir=os.path.dirname(os.path.abspath(schedule_path)),
    )

    if not confirm_reset():
        sys.exit("Cancelled - nothing changed")

    # Load teams and events from CSV
    if load_teams_and_events_from_csv(schedule_path, contacts_path):
        # Display loaded data
        display_teams()
        display_events(30)
    else:
        print("Failed to load data from CSV")

