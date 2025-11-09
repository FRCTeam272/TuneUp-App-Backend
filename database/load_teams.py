from sqlalchemy.orm import sessionmaker
from database_setup import Team, engine
import os


Session = sessionmaker(bind=engine)

session = Session()

file_loc = os.path.join(os.path.dirname(__file__), 'teams.csv')

with open(file_loc, 'r') as file:
    for line in file:
        team_name, team_id = line.strip().split(',', 1)
        team = Team(id=int(team_id), name=team_name)
        session.add(team)

session.commit()