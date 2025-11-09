from database.database_setup import Team, Score, engine
from sqlalchemy.orm import sessionmaker
import requests
from bs4 import BeautifulSoup

Session = sessionmaker(bind=engine)

session = Session()


url = "https://www.thebluealliance.com/event/2025mrcmp#teams"
response = requests.get(url)
soup = BeautifulSoup(response.text, 'html.parser')

team_elements = soup.find_all('div', class_='team-name')
for team_element in team_elements:
    team_name = team_element.text.strip()
    # Extract team number from the team_name string
    try:
        team_id = ""
        for i in team_name:
            if i.isdigit():
                team_id += i
            else:
                break
        team_id = int(team_id)
        team_name = team_name[len(str(team_id)):].strip()
    except ValueError:
        print(f"Could not extract team ID from: {team_name}")
        continue

    # Check if team already exists
    existing_team = session.query(Team).filter_by(id=team_id).first()
    if not existing_team:
        new_team = Team(name=team_name, id=team_id)
        session.add(new_team)
        print(f"Added team: {team_name} (ID: {team_id})")
    else:
        print(f"Team already exists: {team_name} (ID: {team_id})")
session.commit()

for i in session.query(Team).all():
    print(i.id, i.name)  # Print team ID and name
    score = Score(team_id=i.id, score=0)
    session.add(score)
    session.commit()

session.close()