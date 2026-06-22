from datetime import timedelta

import click
from flask import Flask
from sqlalchemy import delete, select

from .auth import EMAIL_RE, MIN_PASSWORD_LENGTH, normalize_email
from .domain.export import to_csv
from .extensions import db
from .models import Response, Survey, User, utcnow
from .seed import DEMO_EMAIL, DEMO_PASSWORD, seed_demo


def prune_incomplete(days: int) -> int:
    """Delete responses that were started but never finished more than ``days`` ago."""
    cutoff = utcnow() - timedelta(days=days)
    result = db.session.execute(
        delete(Response).where(Response.completed_at.is_(None), Response.started_at < cutoff)
    )
    db.session.commit()
    return result.rowcount


def register_cli(app: Flask) -> None:
    @app.cli.command("seed-demo")
    @click.option("--responses", default=140, show_default=True, help="Customer survey responses.")
    def seed_demo_command(responses: int) -> None:
        """Create the demo account with sample surveys and responses."""
        if seed_demo(responses=responses):
            click.echo(f"Demo data created. Sign in as {DEMO_EMAIL} / {DEMO_PASSWORD}")
        else:
            click.echo("Demo account already exists, nothing to do.")

    @app.cli.command("prune-incomplete")
    @click.option("--days", default=30, show_default=True, help="Keep newer drafts.")
    def prune_incomplete_command(days: int) -> None:
        """Delete abandoned (never submitted) responses older than --days."""
        removed = prune_incomplete(days)
        click.echo(f"Removed {removed} abandoned response{'s' if removed != 1 else ''}.")

    @app.cli.command("create-user")
    @click.argument("email")
    @click.option("--name", default="", help="Display name (defaults to the email).")
    @click.password_option()
    def create_user_command(email: str, name: str, password: str) -> None:
        """Create an owner account."""
        email = normalize_email(email)
        if not EMAIL_RE.match(email):
            raise click.BadParameter("not a valid email address", param_hint="EMAIL")
        if len(password) < MIN_PASSWORD_LENGTH:
            raise click.BadParameter(f"use at least {MIN_PASSWORD_LENGTH} characters")
        if db.session.scalar(select(User).filter_by(email=email)):
            raise click.ClickException(f"{email} already has an account")
        user = User(email=email, name=name.strip() or email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        click.echo(f"Created {email}.")

    @app.cli.command("export-csv")
    @click.argument("survey_id", type=int)
    @click.option(
        "--output", "-o", type=click.File("w"), default="-", help="File (default stdout)."
    )
    def export_csv_command(survey_id: int, output) -> None:
        """Write the completed responses of a survey as CSV."""
        survey = db.session.get(Survey, survey_id)
        if survey is None:
            raise click.ClickException(f"no survey with id {survey_id}")
        output.write(to_csv(survey))
