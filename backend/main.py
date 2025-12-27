from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
import os
from typing import List

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


MAX_CONTENT_CHARS = 200_000
SUMMARY_SENTENCE_COUNT = 3
SNIPPET_CHAR_COUNT = 240


@dataclass
class Document:
    doc_id: str
    filename: str
    text: str
    segments: List[str]


class UploadResponse(BaseModel):
    doc_id: str
    filename: str
    summary: str
    word_count: int


class AskRequest(BaseModel):
    doc_id: str
    question: str


class Source(BaseModel):
    index: int
    snippet: str


class AskResponse(BaseModel):
    answer: str
    sources: List[Source]


app = FastAPI(title="Vue3 + FastAPI MVP")
frontend_origin = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        frontend_origin,
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DOCUMENTS: dict[str, Document] = {}


@app.get("/api/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/upload", response_model=UploadResponse)
async def upload_file(file: UploadFile = File(...)) -> UploadResponse:
    if not file.filename:
        raise HTTPException(status_code=400, detail="未提供文件名。")

    if not file.content_type or not file.content_type.startswith("text/"):
        raise HTTPException(status_code=400, detail="仅支持 text/* 类型的文件。")

    raw_bytes = await file.read()
    try:
        text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        text = raw_bytes.decode("utf-8", errors="ignore")

    text = text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="文件内容为空或无法解析为文本。")

    if len(text) > MAX_CONTENT_CHARS:
        raise HTTPException(status_code=400, detail="文件过大，请上传更小的文本文件。")

    doc_id = str(uuid.uuid4())
    segments = [segment.strip() for segment in re.split(r"\n{2,}", text) if segment.strip()]
    summary = generate_summary(text)
    document = Document(doc_id=doc_id, filename=file.filename, text=text, segments=segments)
    DOCUMENTS[doc_id] = document

    return UploadResponse(
        doc_id=doc_id,
        filename=file.filename,
        summary=summary,
        word_count=len(text.split()),
    )


@app.post("/api/ask", response_model=AskResponse)
def ask_question(payload: AskRequest) -> AskResponse:
    document = DOCUMENTS.get(payload.doc_id)
    if not document:
        raise HTTPException(status_code=404, detail="未找到对应文档，请先上传文件。")

    question = payload.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="问题不能为空。")

    keywords = extract_keywords(question)
    if not keywords:
        raise HTTPException(status_code=400, detail="问题缺少有效关键词，请重新描述。")

    scored_segments = score_segments(document.segments, keywords)
    top_segments = [segment for _, segment in scored_segments[:3] if segment]

    if not top_segments:
        answer = "未能在文档中找到直接相关内容，请换一种问法或上传更相关的文本。"
        sources: List[Source] = []
    else:
        answer = "\n\n".join(top_segments)
        sources = [
            Source(index=index, snippet=build_snippet(segment))
            for index, segment in enumerate(top_segments, start=1)
        ]

    return AskResponse(answer=answer, sources=sources)


def generate_summary(text: str) -> str:
    sentences = split_sentences(text)
    summary_sentences = sentences[:SUMMARY_SENTENCE_COUNT]
    if summary_sentences:
        return " ".join(summary_sentences)
    return build_snippet(text)


def split_sentences(text: str) -> List[str]:
    parts = re.split(r"(?<=[。.!?])\s+", text)
    return [part.strip() for part in parts if part.strip()]


def extract_keywords(question: str) -> List[str]:
    tokens = re.findall(r"[A-Za-z0-9\u4e00-\u9fa5]+", question)
    return [token.lower() for token in tokens if len(token) >= 2]


def score_segments(segments: List[str], keywords: List[str]) -> List[tuple[int, str]]:
    scored = []
    for segment in segments:
        lowered = segment.lower()
        score = sum(1 for keyword in keywords if keyword in lowered)
        if score:
            scored.append((score, segment))
    scored.sort(key=lambda item: item[0], reverse=True)
    return scored


def build_snippet(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip()
    return cleaned[:SNIPPET_CHAR_COUNT]
