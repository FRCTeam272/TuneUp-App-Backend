from database_setup import Team, Score, engine
from sqlalchemy.orm import sessionmaker

Session = sessionmaker(bind=engine)
session = Session()
import random

if __name__ == "__main__":
    teams = session.query(Team).all()
    scores = [random.randint(0, 300) for _ in range(50)]

    for score in scores:
        team = random.choice(teams)
        new_score = Score(score=score, team_id=team.id)
        session.add(new_score)
    session.commit()
    session.close()