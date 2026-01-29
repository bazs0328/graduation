from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ResearchCreateRequest(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    summary: Optional[str] = None


class ResearchCreateResponse(BaseModel):
    research_id: int
    session_id: str
    title: Optional[str] = None
    summary: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ResearchEntryCreateRequest(BaseModel):
    entry_type: str = Field(..., min_length=1, max_length=32)
    content: str = Field(..., min_length=1)
    tool_traces: Optional[List[Dict[str, Any]]] = None
    sources: Optional[List[Dict[str, Any]]] = None


class ResearchEntryResponse(BaseModel):
    entry_id: int
    research_id: int
    entry_type: str
    content: str
    tool_traces: Optional[List[Dict[str, Any]]] = None
    sources: Optional[List[Dict[str, Any]]] = None
    created_at: Optional[datetime] = None


class ResearchListItem(BaseModel):
    research_id: int
    title: Optional[str] = None
    summary: Optional[str] = None
    entry_count: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ResearchListResponse(BaseModel):
    items: List[ResearchListItem]


class ResearchDetailResponse(BaseModel):
    research_id: int
    session_id: str
    title: Optional[str] = None
    summary: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    entries: List[ResearchEntryResponse]
