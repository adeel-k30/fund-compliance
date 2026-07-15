# SQLAlchemy ORM models — these define the actual database tables.
# Each class maps directly to a Postgres table. Relationships tell SQLAlchemy
# how to join tables (e.g. an Upload belongs to a Client, has many ValidationIssues).

import uuid
from enum import Enum
from sqlalchemy import Column, ForeignKey, Integer, String, DateTime, Text, Boolean, Enum as SQLAlchemyEnum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.db.session import Base

class UploadStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETE = "complete"
    FAILED = "failed"


# The tenant. Every user and every upload belongs to one Client.
# This is the top-level isolation boundary — one client can never see another's data.
class Client(Base):
    __tablename__ = "clients"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    uploads = relationship("Upload", back_populates="client")
    users = relationship("User", back_populates="client")


# Tracks each file submission. Created as "pending" when the file arrives,
# then updated to "processing" → "complete" (or "failed") by the Celery worker.
class Upload(Base):
    __tablename__ = "uploads"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    client_id = Column(String, ForeignKey("clients.id", ondelete="CASCADE"))
    filename = Column(String, nullable=False)
    template_type = Column(String, nullable=False)
    template_version = Column(String, nullable=True)
    total_rows = Column(Integer)
    rows_with_issues = Column(Integer)
    status = Column(SQLAlchemyEnum(UploadStatus, values_callable=lambda x: [e.value for e in x]), nullable=False, default=UploadStatus.PENDING)
    s3_key = Column(String, nullable=True)
    task_id = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    client = relationship("Client", back_populates="uploads")
    validation_issues = relationship("ValidationIssue", back_populates="upload")


# One row per problem found during validation. Linked to an Upload so the
# client can later retrieve all issues for a specific file submission.
class ValidationIssue(Base):
    __tablename__ = "validation_issues"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    upload_id = Column(String, ForeignKey("uploads.id", ondelete="CASCADE"))
    row_index = Column(Integer, nullable=False)
    isin = Column(String, nullable=True)
    instrument_name = Column(String, nullable=True)
    field_code = Column(String, nullable=False)
    field_label = Column(String, nullable=False)
    rule_type = Column(String, nullable=False)
    message = Column(Text, nullable=False)

    upload = relationship("Upload", back_populates="validation_issues")


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    client_id = Column(String, ForeignKey("clients.id", ondelete="CASCADE"))
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())

    client = relationship("Client", back_populates="users")
