from sqlalchemy import String, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from src.models.base import Base
from sqlalchemy.orm import Mapped, mapped_column


class SpotSnapshot(Base):
    __tablename__ = "spot_snapshots"

    symbol: Mapped[str] = mapped_column(String(10), primary_key=True)
    snapshot_time: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), primary_key=True, server_default=func.now()
    )
    data: Mapped[dict] = mapped_column(JSONB)
    source: Mapped[str] = mapped_column(String(50))
