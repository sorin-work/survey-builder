from datetime import UTC, datetime

from flask_login import UserMixin
from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db


def utcnow() -> datetime:
    """Naive UTC timestamp; all datetimes are stored as UTC without tzinfo."""
    return datetime.now(UTC).replace(tzinfo=None)


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    surveys: Mapped[list["Survey"]] = relationship(back_populates="owner")

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def __repr__(self) -> str:
        return f"<User {self.email}>"


class Survey(db.Model):
    __tablename__ = "surveys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    owner: Mapped[User] = relationship(back_populates="surveys")
    pages: Mapped[list["Page"]] = relationship(
        back_populates="survey", order_by="Page.position", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Survey {self.id} {self.title!r}>"


class Page(db.Model):
    __tablename__ = "pages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    survey_id: Mapped[int] = mapped_column(ForeignKey("surveys.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200), default="")
    position: Mapped[int] = mapped_column(Integer, default=0)

    survey: Mapped[Survey] = relationship(back_populates="pages")
    questions: Mapped[list["Question"]] = relationship(
        back_populates="page", order_by="Question.position", cascade="all, delete-orphan"
    )


class Question(db.Model):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    page_id: Mapped[int] = mapped_column(ForeignKey("pages.id", ondelete="CASCADE"), index=True)
    type: Mapped[str] = mapped_column(String(30))
    prompt: Mapped[str] = mapped_column(String(500))
    help_text: Mapped[str] = mapped_column(String(500), default="")
    required: Mapped[bool] = mapped_column(Boolean, default=False)
    position: Mapped[int] = mapped_column(Integer, default=0)
    settings: Mapped[dict] = mapped_column(JSON, default=dict)

    page: Mapped[Page] = relationship(back_populates="questions")
    choices: Mapped[list["Choice"]] = relationship(
        back_populates="question", order_by="Choice.position", cascade="all, delete-orphan"
    )


class Choice(db.Model):
    __tablename__ = "choices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    question_id: Mapped[int] = mapped_column(
        ForeignKey("questions.id", ondelete="CASCADE"), index=True
    )
    label: Mapped[str] = mapped_column(String(300))
    position: Mapped[int] = mapped_column(Integer, default=0)

    question: Mapped[Question] = relationship(back_populates="choices")
