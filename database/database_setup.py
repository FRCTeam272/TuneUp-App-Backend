from sqlalchemy import Column, ForeignKey, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy import create_engine, update
from sqlalchemy.exc import IntegrityError

from dotenv import load_dotenv
import os

load_dotenv()  # take environment variables from .env file
password_env = os.getenv("password", "")
database_url_env = os.getenv("database_url", "")

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

# Version counters that back the response cache in routes/cache.py.
# Every write to a table bumps the matching key in the same transaction, which is how
# all gunicorn workers learn their cached responses are stale.
ROSTER = "roster"  # team + event tables (loaded from CSV, rarely change)
SCORES = "scores"  # score table (changes all day during an event)
CACHE_KEYS = (ROSTER, SCORES)

class CacheVersion(Base):
    __tablename__ = 'cache_version'
    key = Column(String(50), primary_key=True)
    version = Column(Integer, nullable=False, default=0)

# Single engine + session factory shared by every route module.
# pool_pre_ping avoids errors from connections Heroku Postgres has closed while idle.
engine = create_engine(database_url_env, pool_pre_ping=True)
Session = sessionmaker(bind=engine)

def bump_cache_versions(session, *keys):
    """Mark cached data for `keys` stale. Call before session.commit() of the write it describes."""
    session.execute(update(CacheVersion).where(CacheVersion.key.in_(keys)).values(version=CacheVersion.version + 1))

def _ensure_cache_versions():
    with Session() as session:
        for key in CACHE_KEYS:
            if session.get(CacheVersion, key) is None:
                session.add(CacheVersion(key=key, version=0))
        try:
            session.commit()
        except IntegrityError:
            session.rollback()  # another worker inserted the rows first

Base.metadata.create_all(engine)
_ensure_cache_versions()
