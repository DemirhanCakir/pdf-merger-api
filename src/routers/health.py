from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from src.db import get_session
from src.schemas import HealthOut
from src.services import s3_client

router = APIRouter(tags=["health"])


def _check_db(session: Session) -> str:
    try:
        session.execute(text("SELECT 1"))
        return "ok"
    except Exception:
        return "down"


@router.get("/health", response_model=HealthOut)
def health(session: Session = Depends(get_session)) -> HealthOut:
    db = _check_db(session)
    s3 = "ok" if s3_client.ping() else "down"
    overall = "ok" if db == "ok" and s3 == "ok" else "degraded"
    return HealthOut(status=overall, database=db, s3=s3)
