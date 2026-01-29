from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db import models


@dataclass
class ResearchError(Exception):
    status_code: int
    message: str
    details: Optional[Dict[str, object]] = None


def _get_research_or_error(db: Session, research_id: int, session_id: str) -> models.ResearchSession:
    research = db.query(models.ResearchSession).filter(models.ResearchSession.id == research_id).first()
    if not research:
        raise ResearchError(404, "Research not found", {"research_id": research_id})
    if research.session_id != session_id:
        raise ResearchError(
            403,
            "Session mismatch",
            {"research_id": research_id, "session_id": session_id},
        )
    return research


def create_research_session(
    db: Session,
    session_id: str,
    title: Optional[str],
    summary: Optional[str],
) -> models.ResearchSession:
    research = models.ResearchSession(
        session_id=session_id,
        title=title,
        summary=summary,
    )
    db.add(research)
    db.commit()
    db.refresh(research)
    return research


def add_research_entry(
    db: Session,
    session_id: str,
    research_id: int,
    entry_type: str,
    content: str,
    tool_traces: Optional[List[Dict[str, Any]]],
    sources: Optional[List[Dict[str, Any]]],
) -> models.ResearchEntry:
    research = _get_research_or_error(db, research_id, session_id)
    research.updated_at = func.now()
    entry = models.ResearchEntry(
        research_id=research.id,
        entry_type=entry_type,
        content=content,
        tool_traces_json=tool_traces,
        sources_json=sources,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def list_research_sessions(db: Session, session_id: str) -> List[Tuple[models.ResearchSession, int]]:
    sessions = (
        db.query(models.ResearchSession)
        .filter(models.ResearchSession.session_id == session_id)
        .order_by(models.ResearchSession.updated_at.desc(), models.ResearchSession.id.desc())
        .all()
    )
    if not sessions:
        return []
    ids = [item.id for item in sessions]
    counts = dict(
        db.query(models.ResearchEntry.research_id, func.count(models.ResearchEntry.id))
        .filter(models.ResearchEntry.research_id.in_(ids))
        .group_by(models.ResearchEntry.research_id)
        .all()
    )
    return [(item, int(counts.get(item.id, 0))) for item in sessions]


def get_research_detail(
    db: Session,
    session_id: str,
    research_id: int,
) -> Tuple[models.ResearchSession, List[models.ResearchEntry]]:
    research = _get_research_or_error(db, research_id, session_id)
    entries = (
        db.query(models.ResearchEntry)
        .filter(models.ResearchEntry.research_id == research.id)
        .order_by(models.ResearchEntry.created_at.asc(), models.ResearchEntry.id.asc())
        .all()
    )
    return research, entries
