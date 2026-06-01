from sqlalchemy import String, DateTime
from sqlalchemy.sql import func
from src.models.base import Base
from sqlalchemy.orm import Mapped, mapped_column


class News(Base):
    __tablename__ = "news"

    symbol: Mapped[str] = mapped_column(String(10), primary_key=True)
    url: Mapped[str] = mapped_column(String(500), primary_key=True)
    title: Mapped[str] = mapped_column(String(500))
    content: Mapped[str] = mapped_column(String)
    publish_time: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True))
    source_name: Mapped[str | None] = mapped_column(String(100))
    updated_at = mapped_column(DateTime(timezone=True), server_default=func.now())
