from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from database.database_setup import SCORES, Session, Team, Score, bump_cache_versions
import routes.env as env
from routes.schemas import DetailResponse


router = APIRouter()


class ScoreRequest(BaseModel):
    id: int | None = None
    team_id: int
    score: int
    password: str = ""
class CreateScoreResponse(BaseModel):
    id: int
    team_id: int
    score: int
@router.post("/", response_model=CreateScoreResponse)
def create_score(request: ScoreRequest):
    if request.password != env.password_env: 
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    session = Session()
    team = session.query(Team).filter_by(id=request.team_id).first()
    if not team:
        session.close()
        raise HTTPException(status_code=404, detail="Team not found")

    new_score = Score(team_id=request.team_id, score=request.score)
    session.add(new_score)
    bump_cache_versions(session, SCORES)
    session.commit()
    session.refresh(new_score)
    session.close()
    return CreateScoreResponse(id=int(str(new_score.id)), team_id=int(str(new_score.team_id)), score=int(str(new_score.score)))

class DeleteScoreRequest(BaseModel):
    # Either `id` alone, or `team_id` + `score` (deletes one matching score).
    id: int | None = None
    team_id: int | None = None
    score: int | None = None
    password: str = ""
@router.post("/delete", response_model=DetailResponse)
def delete_score(request: DeleteScoreRequest):
    if request.password != env.password_env: 
        raise HTTPException(status_code=403, detail="Unauthorized")
    db_score = None
    session = Session()
    # deletion when score_id is provided
    if request.id:
        db_score = session.query(Score).filter_by(id=request.id).first()
    # deletion when team_id and score are provided
    elif request.team_id and request.score is not None:
        db_score = session.query(Score).filter_by(team_id=request.team_id, score=request.score).first()

    if not db_score:
        session.close()
        raise HTTPException(status_code=404, detail="Score not found")

    session.delete(db_score)
    bump_cache_versions(session, SCORES)
    session.commit()
    session.close()
    return {"detail": True}
