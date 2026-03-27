from datetime import timedelta

import click
from flask import Flask
from sqlalchemy import delete

from .extensions import db
from .models import Response, utcnow
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
