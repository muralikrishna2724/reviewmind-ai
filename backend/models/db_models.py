"""SQLAlchemy ORM models for ReviewMind AI."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.types import TypeDecorator, CHAR
from sqlalchemy.orm import relationship

from database import Base


class GUID(TypeDecorator):
    """Platform-independent GUID type — uses PostgreSQL UUID, SQLite CHAR(36)."""
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID())
        return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        return str(value)


class Project(Base):
    __tablename__ = "projects"

    id = Column(GUID, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    source_type = Column(String(20), nullable=False)  # 'git' or 'upload' or 'paste'
    source_url = Column(Text)
    branch = Column(String(100))
    commit_hash = Column(String(40))
    storage_path = Column(Text)
    file_count = Column(Integer, default=0)
    review_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    files = relationship("File", back_populates="project", cascade="all, delete-orphan")
    reviews = relationship("Review", back_populates="project", cascade="all, delete-orphan")


class File(Base):
    __tablename__ = "files"

    id = Column(GUID, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(GUID, ForeignKey("projects.id"), nullable=False)
    path = Column(Text, nullable=False)
    name = Column(String(255), nullable=False)
    size = Column(Integer)
    file_type = Column(String(50))
    reviewed = Column(Boolean, default=False)
    last_reviewed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="files")
    reviews = relationship("Review", back_populates="file")


class Review(Base):
    __tablename__ = "reviews"

    id = Column(GUID, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(GUID, ForeignKey("projects.id"), nullable=False)
    file_id = Column(GUID, ForeignKey("files.id"), nullable=True)
    code_snapshot = Column(Text, nullable=False)
    contributor = Column(String(255))
    file_path = Column(Text)
    memory_mode = Column(String(20), nullable=False)

    critical_issues = Column(Text)       # JSON string
    convention_violations = Column(Text) # JSON string
    contributor_patterns = Column(Text)  # JSON string
    positive_signals = Column(Text)      # JSON string
    summary = Column(Text)
    recalled_entries = Column(Text)      # JSON string

    groq_model = Column(String(100))
    processing_time_ms = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="reviews")
    file = relationship("File", back_populates="reviews")
