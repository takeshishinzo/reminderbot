from database import Base
from sqlalchemy import Column, Integer, String, BigInteger, DateTime, func, ForeignKey
from sqlalchemy.orm import mapped_column, Mapped, relationship
from datetime import datetime

class Reminders(Base):
    __tablename__ = "reminders"

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )

    text: Mapped[str]
    remind_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    trigger: Mapped[str] = mapped_column(default="date", nullable=False)

    user: Mapped["Users"] = relationship(
        back_populates="reminders"
    )

class Users(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    timezone: Mapped[str] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    reminders: Mapped[list["Reminders"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan"
    )
