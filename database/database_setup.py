from sqlalchemy import Column, ForeignKey, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine

Base = declarative_base()

class Team(Base):
    __tablename__ = 'team'
    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    room = Column(String(250), nullable=True)

class Score(Base):
    __tablename__ = 'score'

    id = Column(Integer, primary_key=True)
    score = Column(Integer, nullable=False)
    team_id = Column(Integer, ForeignKey('team.id'))
    team = relationship(Team)

class Event(Base):
    __tablename__ = 'event'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(250), nullable=False)
    date = Column(DateTime, nullable=False)
    team_id = Column(Integer, ForeignKey('team.id'))
    team = relationship(Team)
# we will have to move this to an online endpoint at some point
engine = create_engine('sqlite:///team.db')


Base.metadata.create_all(engine)
