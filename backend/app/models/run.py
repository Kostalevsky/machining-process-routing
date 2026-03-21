from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base
from app.models.enums import RunStatus
from app.models.mixins import TimestampMixin


class Run(TimestampMixin, Base):
    __tablename__ = "runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[RunStatus] = mapped_column(
        Enum(RunStatus, name="run_status"),
        default=RunStatus.CREATED,
        nullable=False,
    )
    source_artifact_id: Mapped[int | None] = mapped_column(
        ForeignKey("artifacts.id", ondelete="SET NULL"),
        nullable=True,
    )
    selected_collage_artifact_id: Mapped[int | None] = mapped_column(
        ForeignKey("artifacts.id", ondelete="SET NULL"),
        nullable=True,
    )
    latest_generation_id: Mapped[int | None] = mapped_column(
        ForeignKey("generations.id", ondelete="SET NULL"),
        nullable=True,
    )

    user = relationship("User", back_populates="runs")
    artifacts = relationship(
        "Artifact",
        back_populates="run",
        foreign_keys="Artifact.run_id",
        cascade="all, delete-orphan",
    )
    generations = relationship(
        "Generation",
        back_populates="run",
        foreign_keys="Generation.run_id",
        cascade="all, delete-orphan",
    )
    events = relationship("RunEvent", back_populates="run", cascade="all, delete-orphan")
