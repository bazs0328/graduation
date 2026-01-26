from typing import List, Optional

from pydantic import BaseModel, Field


class SourceResolveRequest(BaseModel):
    chunk_ids: List[int] = Field(..., min_length=1)
    preview_len: Optional[int] = Field(default=120, ge=20, le=500)


class SourceItem(BaseModel):
    chunk_id: int
    document_id: int
    document_name: Optional[str] = None
    text_preview: str


class SourceResolveResponse(BaseModel):
    items: List[SourceItem] = Field(default_factory=list)
    missing_chunk_ids: List[int] = Field(default_factory=list)
