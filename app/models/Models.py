# app/models/base.py
from __future__ import annotations
from passlib.context import CryptContext

from datetime import datetime
from typing import Optional, List, Dict, Any

from sqlalchemy import (
    String,
    Integer,
    Text,
    DateTime,
    ForeignKey,
    CheckConstraint,
    UniqueConstraint,
    LargeBinary,
    func,
    Float,
    JSON,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import UserDefinedType


class Base(DeclarativeBase):
    pass


# -------------------------
# Oracle VECTOR type helper
# -------------------------
class OracleVector4096F32(UserDefinedType):
    """
    Compiles to Oracle VECTOR(4096, FLOAT32).

    This is enough to let SQLAlchemy create the table and understand the column type.
    Bind values should be provided as python `array.array('f', ...)` when inserting,
    typically via raw SQL execution. (python-oracledb supports binding vectors.)
    """

    cache_ok = True

    def get_col_spec(self, **kw) -> str:
        return "VECTOR(4096, FLOAT32)"


# -------------------------
# Tables
# -------------------------
class Tenant(Base):
    __tablename__ = "tenants"

    tenant_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.systimestamp(), nullable=False
    )

    users: Mapped[List["AppUser"]] = relationship(
        back_populates="tenant", cascade="all, delete-orphan"
    )
    documents: Mapped[List["Document"]] = relationship(
        back_populates="tenant", cascade="all, delete-orphan"
    )
    conversations: Mapped[List["Conversation"]] = relationship(
        back_populates="tenant", cascade="all, delete-orphan"
    )


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AppUser(Base):
    __tablename__ = "app_users"

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True)

    tenant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tenants.tenant_id"), nullable=False, index=True, default=1
    )

    email: Mapped[Optional[str]] = mapped_column(String(320))
    display_name: Mapped[Optional[str]] = mapped_column(String(200))

    password_hash: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    last_login: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    preferences: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.systimestamp(),
        nullable=False,
    )

    tenant: Mapped["Tenant"] = relationship(back_populates="users")

    owned_documents: Mapped[List["Document"]] = relationship(
        back_populates="owner",
        cascade="all, delete-orphan",
    )

    conversations: Mapped[List["Conversation"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

    def verify_password(self, password: str) -> bool:
        return pwd_context.verify(password, self.password_hash)

    def set_password(self, password: str) -> None:
        self.password_hash = pwd_context.hash(password)


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (
        CheckConstraint(
            "status IN ('uploaded','processing','ready','failed')",
            name="ck_documents_status",
        ),
    )

    doc_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tenants.tenant_id"), nullable=False, index=True
    )
    owner_user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("app_users.user_id"), nullable=False, index=True
    )

    title: Mapped[Optional[str]] = mapped_column(String(500))
    filename: Mapped[Optional[str]] = mapped_column(String(500))
    mime_type: Mapped[Optional[str]] = mapped_column(String(200))
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    status: Mapped[str] = mapped_column(String(30), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.systimestamp(), nullable=False
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    tenant: Mapped["Tenant"] = relationship(back_populates="documents")
    owner: Mapped["AppUser"] = relationship(back_populates="owned_documents")

    versions: Mapped[List["DocumentVersion"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )
    chunks: Mapped[List["DocumentChunk"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )
    permissions: Mapped[List["DocumentPermission"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )


class DocumentVersion(Base):
    __tablename__ = "document_versions"
    __table_args__ = (UniqueConstraint("doc_id", "version_num", name="uq_doc_version"),)

    version_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    doc_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("documents.doc_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_num: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.systimestamp(), nullable=False
    )

    document: Mapped["Document"] = relationship(back_populates="versions")
    blob: Mapped[Optional["DocumentBlob"]] = relationship(
        back_populates="version", cascade="all, delete-orphan", uselist=False
    )
    text: Mapped[Optional["DocumentText"]] = relationship(
        back_populates="version", cascade="all, delete-orphan", uselist=False
    )
    chunks: Mapped[List["DocumentChunk"]] = relationship(
        back_populates="version", cascade="all, delete-orphan"
    )


class DocumentBlob(Base):
    __tablename__ = "document_blobs"

    version_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("document_versions.version_id", ondelete="CASCADE"),
        primary_key=True,
    )
    blob_data: Mapped[Optional[bytes]] = mapped_column(LargeBinary)

    version: Mapped["DocumentVersion"] = relationship(back_populates="blob")


class DocumentText(Base):
    __tablename__ = "document_text"

    version_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("document_versions.version_id", ondelete="CASCADE"),
        primary_key=True,
    )
    extracted_text: Mapped[Optional[str]] = mapped_column(Text)  # CLOB
    structure_json: Mapped[Optional[str]] = mapped_column(Text)  # JSON stored as CLOB
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.systimestamp(), nullable=False
    )

    version: Mapped["DocumentVersion"] = relationship(back_populates="text")


class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    __table_args__ = (UniqueConstraint("version_id", "chunk_index", name="uq_chunk"),)

    chunk_id: Mapped[int] = mapped_column(Integer, primary_key=True)

    version_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("document_versions.version_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    doc_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("documents.doc_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tenant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tenants.tenant_id"), nullable=False, index=True
    )

    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    page_start: Mapped[Optional[int]] = mapped_column(Integer)
    page_end: Mapped[Optional[int]] = mapped_column(Integer)
    section_path: Mapped[Optional[str]] = mapped_column(String(2000))
    token_count: Mapped[Optional[int]] = mapped_column(Integer)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)  # CLOB

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.systimestamp(), nullable=False
    )

    version: Mapped["DocumentVersion"] = relationship(back_populates="chunks")
    document: Mapped["Document"] = relationship(back_populates="chunks")
    tenant: Mapped["Tenant"] = relationship()

    embedding: Mapped[Optional["ChunkEmbedding"]] = relationship(
        back_populates="chunk", cascade="all, delete-orphan", uselist=False
    )


class ChunkEmbedding(Base):
    __tablename__ = "chunk_embeddings"

    # PK is also FK to chunks (1:1)
    chunk_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("document_chunks.chunk_id", ondelete="CASCADE"),
        primary_key=True,
    )
    tenant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tenants.tenant_id"), nullable=False, index=True
    )

    embedding_model_id: Mapped[str] = mapped_column(String(200), nullable=False)
    embedding_dim: Mapped[int] = mapped_column(Integer, nullable=False)

    # Oracle VECTOR(4096, FLOAT32)
    embedding: Mapped[object] = mapped_column(OracleVector4096F32(), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.systimestamp(), nullable=False
    )

    chunk: Mapped["DocumentChunk"] = relationship(back_populates="embedding")
    tenant: Mapped["Tenant"] = relationship()


class DocumentPermission(Base):
    __tablename__ = "document_permissions"
    __table_args__ = (
        CheckConstraint(
            "principal_type IN ('user','group')",
            name="ck_docperm_principal_type",
        ),
        CheckConstraint(
            "role IN ('owner','reader','writer','admin')",
            name="ck_docperm_role",
        ),
    )

    doc_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("documents.doc_id", ondelete="CASCADE"),
        primary_key=True,
    )
    principal_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    principal_type: Mapped[str] = mapped_column(String(20), primary_key=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.systimestamp(), nullable=False
    )

    document: Mapped["Document"] = relationship(back_populates="permissions")


class DocumentJob(Base):
    __tablename__ = "document_jobs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('queued','running','succeeded','failed','canceled')",
            name="ck_docjobs_status",
        ),
    )

    job_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tenants.tenant_id"), nullable=False, index=True
    )
    doc_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("documents.doc_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("document_versions.version_id", ondelete="SET NULL"),
        index=True,
    )

    status: Mapped[str] = mapped_column(String(20), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100)

    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=3)

    locked_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    locked_by: Mapped[Optional[str]] = mapped_column(String(200))

    last_error: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.systimestamp(), nullable=False
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    tenant: Mapped["Tenant"] = relationship()
    document: Mapped["Document"] = relationship()


class Conversation(Base):
    __tablename__ = "conversations"

    conversation_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tenants.tenant_id"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("app_users.user_id"), nullable=False, index=True
    )

    chat_model_id: Mapped[str] = mapped_column(String(200), nullable=False)
    title: Mapped[Optional[str]] = mapped_column(String(500))

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.systimestamp(), nullable=False
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    tenant: Mapped["Tenant"] = relationship(back_populates="conversations")
    user: Mapped["AppUser"] = relationship(back_populates="conversations")

    messages: Mapped[List["Message"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan"
    )


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (
        CheckConstraint(
            "role IN ('user','assistant','system')", name="ck_messages_role"
        ),
    )

    message_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    conversation_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("conversations.conversation_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)  # CLOB

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.systimestamp(), nullable=False
    )

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")
    retrieval_events: Mapped[List["RetrievalEvent"]] = relationship(
        back_populates="message", cascade="all, delete-orphan"
    )
    citations: Mapped[List["MessageCitation"]] = relationship(
        back_populates="message", cascade="all, delete-orphan"
    )


class MessageCitation(Base):
    __tablename__ = "message_citations"

    citation_id: Mapped[int] = mapped_column(Integer, primary_key=True)

    message_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("messages.message_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    doc_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("documents.doc_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    chunk_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("document_chunks.chunk_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    page_start: Mapped[Optional[int]] = mapped_column(Integer)
    page_end: Mapped[Optional[int]] = mapped_column(Integer)
    section_path: Mapped[Optional[str]] = mapped_column(String(2000))
    score: Mapped[Optional[float]] = mapped_column(Float)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.systimestamp(), nullable=False
    )

    message: Mapped["Message"] = relationship(back_populates="citations")


class RetrievalEvent(Base):
    __tablename__ = "retrieval_events"

    event_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    message_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("messages.message_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    query_text: Mapped[str] = mapped_column(Text, nullable=False)  # CLOB
    filters_json: Mapped[Optional[str]] = mapped_column(Text)  # JSON as CLOB
    results_json: Mapped[Optional[str]] = mapped_column(Text)  # JSON as CLOB

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.systimestamp(), nullable=False
    )

    message: Mapped["Message"] = relationship(back_populates="retrieval_events")
