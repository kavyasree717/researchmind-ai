
import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    JSON,
    String,
    Text,
    Uuid,
    Integer,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )

    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("research_sessions.id"),
        nullable=False,
        index=True,
    )

    # Links the report to the research execution that generated it.
    research_run_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("research_runs.id"),
        nullable=True,
        index=True,
    )

    title: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    # Structured report sections stored as JSON.
    content: Mapped[dict] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )

    # Complete formatted report for display and export.
    markdown_content: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Supports multiple report versions for a research session.
    version: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
