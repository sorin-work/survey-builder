from datetime import UTC, date, datetime

from flask import current_app
from flask_login import UserMixin
from sqlalchemy import JSON, Boolean, Date, DateTime, ForeignKey, Integer, String, Text
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

    surveys: Mapped[list["Survey"]] = relationship(
        back_populates="owner", cascade="all, delete-orphan", passive_deletes=True
    )

    def set_password(self, password: str) -> None:
        method = current_app.config.get("PASSWORD_HASH_METHOD", "scrypt")
        self.password_hash = generate_password_hash(password, method=method)

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
    thank_you_message: Mapped[str] = mapped_column(Text, default="", server_default="")
    status: Mapped[str] = mapped_column(String(20), default="draft")
    share_token: Mapped[str | None] = mapped_column(String(32), unique=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime)
    closes_on: Mapped[date | None] = mapped_column(Date)
    response_limit: Mapped[int | None] = mapped_column(Integer)
    # Kiosk mode: let the same browser submit several responses.
    allow_multiple: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    owner: Mapped[User] = relationship(back_populates="surveys")
    pages: Mapped[list["Page"]] = relationship(
        back_populates="survey", order_by="Page.position", cascade="all, delete-orphan"
    )
    responses: Mapped[list["Response"]] = relationship(
        back_populates="survey", cascade="all, delete-orphan", passive_deletes=True
    )

    @property
    def questions(self) -> list["Question"]:
        return [q for page in self.pages for q in page.questions]

    def question_number(self, question: "Question") -> int:
        """1-based number of a question across all pages."""
        return self.questions.index(question) + 1

    def __repr__(self) -> str:
        return f"<Survey {self.id} {self.title!r}>"


class Page(db.Model):
    __tablename__ = "pages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    survey_id: Mapped[int] = mapped_column(ForeignKey("surveys.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200), default="")
    description: Mapped[str] = mapped_column(Text, default="", server_default="")
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
    branch_rules: Mapped[list["BranchRule"]] = relationship(
        back_populates="question",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="BranchRule.id",
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


class BranchRule(db.Model):
    """Skip logic: if ``question`` is answered with ``choice``, continue at
    ``target_page`` instead of the next page. No target page means "end the survey"."""

    __tablename__ = "branch_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    question_id: Mapped[int] = mapped_column(
        ForeignKey("questions.id", ondelete="CASCADE"), index=True
    )
    choice_id: Mapped[int] = mapped_column(ForeignKey("choices.id", ondelete="CASCADE"))
    target_page_id: Mapped[int | None] = mapped_column(ForeignKey("pages.id", ondelete="CASCADE"))

    question: Mapped[Question] = relationship(back_populates="branch_rules")
    choice: Mapped[Choice] = relationship()
    target_page: Mapped[Page | None] = relationship()

    @property
    def ends_survey(self) -> bool:
        return self.target_page_id is None


class Response(db.Model):
    """One respondent's pass through a survey. Respondents are anonymous."""

    __tablename__ = "responses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    survey_id: Mapped[int] = mapped_column(ForeignKey("surveys.id", ondelete="CASCADE"), index=True)
    key: Mapped[str] = mapped_column(String(32), unique=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, index=True)

    survey: Mapped[Survey] = relationship(back_populates="responses")
    answers: Mapped[list["Answer"]] = relationship(
        back_populates="response", cascade="all, delete-orphan", passive_deletes=True
    )

    @property
    def is_complete(self) -> bool:
        return self.completed_at is not None


class Answer(db.Model):
    """A single answer value. Multiple choice answers store one row per choice."""

    __tablename__ = "answers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    response_id: Mapped[int] = mapped_column(
        ForeignKey("responses.id", ondelete="CASCADE"), index=True
    )
    question_id: Mapped[int] = mapped_column(
        ForeignKey("questions.id", ondelete="CASCADE"), index=True
    )
    choice_id: Mapped[int | None] = mapped_column(ForeignKey("choices.id", ondelete="CASCADE"))
    text_value: Mapped[str | None] = mapped_column(Text)
    number_value: Mapped[int | None] = mapped_column(Integer)
    date_value: Mapped[date | None] = mapped_column(Date)

    response: Mapped[Response] = relationship(back_populates="answers")
    question: Mapped[Question] = relationship()
    choice: Mapped[Choice | None] = relationship()
