"""Persistent account, session, billing, and learning-progress records."""

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    locale: Mapped[str] = mapped_column(String(8), default="en")
    created_at: Mapped[int]
    trial_expires_at: Mapped[int]
    subscription_status: Mapped[str] = mapped_column(String(32), default="inactive")
    stripe_customer_id: Mapped[str | None] = mapped_column(String(128), unique=True, nullable=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    display_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    is_owner: Mapped[bool] = mapped_column(default=False)


class LoginSession(Base):
    __tablename__ = "login_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[int]


class LessonProgress(Base):
    __tablename__ = "lesson_progress"
    __table_args__ = (UniqueConstraint("user_id", "lesson_slug", name="uq_user_lesson_progress"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    lesson_slug: Mapped[str] = mapped_column(String(80))
    completed_at: Mapped[int]
    points: Mapped[int] = mapped_column(default=100)


class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    lesson_slug: Mapped[str] = mapped_column(String(80), index=True)
    is_correct: Mapped[bool]
    attempted_at: Mapped[int]


class CoursePurchase(Base):
    """One-time access purchase for a single complete learning path."""

    __tablename__ = "course_purchases"
    __table_args__ = (UniqueConstraint("user_id", "course_slug", name="uq_user_course_purchase"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    course_slug: Mapped[str] = mapped_column(String(80))
    stripe_session_id: Mapped[str] = mapped_column(String(128), unique=True)
    purchased_at: Mapped[int]
