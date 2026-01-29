from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import relationship

from .session import Base


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True)
    filename = Column(String(255), nullable=False)
    content_type = Column(String(255), nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    chunks = relationship("Chunk", back_populates="document", cascade="all, delete-orphan")
    quizzes = relationship("Quiz", back_populates="document", cascade="all, delete-orphan")


class Chunk(Base):
    __tablename__ = "chunks"

    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    document = relationship("Document", back_populates="chunks")


class Quiz(Base):
    __tablename__ = "quizzes"

    id = Column(Integer, primary_key=True)
    session_id = Column(String(64), nullable=False, default="default", index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=True, index=True)
    difficulty_plan_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    document = relationship("Document", back_populates="quizzes")
    questions = relationship("QuizQuestion", back_populates="quiz", cascade="all, delete-orphan")
    attempts = relationship("QuizAttempt", back_populates="quiz", cascade="all, delete-orphan")


class QuizQuestion(Base):
    __tablename__ = "quiz_questions"

    id = Column(Integer, primary_key=True)
    quiz_id = Column(Integer, ForeignKey("quizzes.id"), nullable=False, index=True)
    type = Column(String(32), nullable=False)
    difficulty = Column(String(16), nullable=False)
    stem = Column(Text, nullable=False)
    options_json = Column(JSON, nullable=True)
    answer_json = Column(JSON, nullable=True)
    explanation = Column(Text, nullable=True)
    related_concept = Column(String(255), nullable=True)
    source_chunk_ids_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    quiz = relationship("Quiz", back_populates="questions")


class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"

    id = Column(Integer, primary_key=True)
    quiz_id = Column(Integer, ForeignKey("quizzes.id"), nullable=False, index=True)
    submitted_at = Column(DateTime, server_default=func.now(), nullable=False)
    score = Column(Float, nullable=True)
    accuracy = Column(Float, nullable=True)
    summary_json = Column(JSON, nullable=True)

    quiz = relationship("Quiz", back_populates="attempts")


class ConceptStat(Base):
    __tablename__ = "concept_stats"
    __table_args__ = (UniqueConstraint("session_id", "concept", name="uq_concept_stats_session_concept"),)

    id = Column(Integer, primary_key=True)
    session_id = Column(String(64), nullable=False, index=True)
    concept = Column(String(255), nullable=False)
    correct_count = Column(Integer, nullable=False, default=0)
    wrong_count = Column(Integer, nullable=False, default=0)
    last_seen = Column(DateTime, nullable=True)


class LearnerProfile(Base):
    __tablename__ = "learner_profile"

    id = Column(Integer, primary_key=True)
    session_id = Column(String(64), nullable=False, unique=True, index=True)
    ability_level = Column(String(32), nullable=True)
    theta = Column(Float, nullable=True)
    frustration_score = Column(Integer, nullable=False, default=0)
    last_updated = Column(DateTime, server_default=func.now(), nullable=False)


class ResearchSession(Base):
    __tablename__ = "research_sessions"

    id = Column(Integer, primary_key=True)
    session_id = Column(String(64), nullable=False, index=True)
    title = Column(String(255), nullable=True)
    summary = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    entries = relationship("ResearchEntry", back_populates="research", cascade="all, delete-orphan")


class ResearchEntry(Base):
    __tablename__ = "research_entries"

    id = Column(Integer, primary_key=True)
    research_id = Column(Integer, ForeignKey("research_sessions.id"), nullable=False, index=True)
    entry_type = Column(String(32), nullable=False)
    content = Column(Text, nullable=False)
    tool_traces_json = Column(JSON, nullable=True)
    sources_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    research = relationship("ResearchSession", back_populates="entries")
