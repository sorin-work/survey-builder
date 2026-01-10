import click
from flask import Flask

from .seed import DEMO_EMAIL, DEMO_PASSWORD, seed_demo


def register_cli(app: Flask) -> None:
    @app.cli.command("seed-demo")
    @click.option("--responses", default=140, show_default=True, help="Customer survey responses.")
    def seed_demo_command(responses: int) -> None:
        """Create the demo account with sample surveys and responses."""
        if seed_demo(responses=responses):
            click.echo(f"Demo data created. Sign in as {DEMO_EMAIL} / {DEMO_PASSWORD}")
        else:
            click.echo("Demo account already exists, nothing to do.")
