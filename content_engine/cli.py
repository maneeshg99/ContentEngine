"""CLI entry point for the content engine."""

from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from content_engine.config import load_config
from content_engine.database import SourceStatus, init_db, get_session, Source

console = Console()


@click.group()
@click.option("--config", default="config.yaml", help="Path to config file")
@click.pass_context
def cli(ctx, config):
    """Content Engine — Short-form content pipeline."""
    ctx.ensure_object(dict)
    ctx.obj["config"] = load_config(config)


@cli.command()
@click.pass_context
def init(ctx):
    """Initialize the database and storage directories."""
    config = ctx.obj["config"]

    # Create storage directories
    for dir_name in [
        config.storage.raw_dir,
        config.storage.clips_dir,
        config.storage.rendered_dir,
        config.storage.transcripts_dir,
    ]:
        Path(dir_name).mkdir(parents=True, exist_ok=True)
        console.print(f"  Created [cyan]{dir_name}[/cyan]")

    # Initialize database
    init_db(config)
    console.print("  Database initialized")
    console.print("\n[green]Content Engine initialized successfully.[/green]")


@cli.command()
@click.argument("url")
@click.pass_context
def download(ctx, url):
    """Download a video/audio from a URL."""
    from content_engine.sourcer.downloader import download_source

    config = ctx.obj["config"]
    init_db(config)

    console.print(f"Downloading: [cyan]{url}[/cyan]")
    source = download_source(url, config)
    console.print(f"[green]Downloaded:[/green] {source.title}")
    console.print(f"  File: {source.file_path}")
    console.print(f"  Duration: {source.duration:.1f}s")


@cli.command()
@click.argument("source_id", type=int)
@click.pass_context
def transcribe(ctx, source_id):
    """Transcribe a downloaded source."""
    from content_engine.clipper.transcriber import transcribe_source

    config = ctx.obj["config"]
    session = get_session(config)
    source = session.get(Source, source_id)

    if not source:
        console.print(f"[red]Source {source_id} not found.[/red]")
        return

    if source.status not in (SourceStatus.DOWNLOADED, SourceStatus.TRANSCRIBED):
        console.print(f"[red]Source must be downloaded first. Status: {source.status.value}[/red]")
        return

    console.print(f"Transcribing: [cyan]{source.title}[/cyan]")
    transcript_path = transcribe_source(source, config, session)
    console.print(f"[green]Transcript saved:[/green] {transcript_path}")


@cli.command()
@click.argument("source_id", type=int)
@click.option("--start", type=float, required=True, help="Start time in seconds")
@click.option("--end", type=float, required=True, help="End time in seconds")
@click.option("--title", default=None, help="Clip title")
@click.pass_context
def clip(ctx, source_id, start, end, title):
    """Extract a clip from a source by timestamp."""
    from content_engine.clipper.cutter import extract_clip

    config = ctx.obj["config"]
    session = get_session(config)
    source = session.get(Source, source_id)

    if not source:
        console.print(f"[red]Source {source_id} not found.[/red]")
        return

    console.print(f"Extracting clip: [cyan]{start:.1f}s - {end:.1f}s[/cyan]")
    clip_record = extract_clip(source, start, end, config, session, title=title)
    console.print(f"[green]Clip extracted:[/green] {clip_record.file_path}")
    console.print(f"  Duration: {clip_record.duration:.1f}s")


@cli.command(name="list")
@click.option("--type", "list_type", type=click.Choice(["sources", "clips"]), default="sources")
@click.pass_context
def list_items(ctx, list_type):
    """List sources or clips."""
    config = ctx.obj["config"]
    session = get_session(config)

    if list_type == "sources":
        sources = session.query(Source).all()
        table = Table(title="Sources")
        table.add_column("ID", style="cyan")
        table.add_column("Title")
        table.add_column("Channel")
        table.add_column("Duration")
        table.add_column("Status")

        for s in sources:
            dur = f"{s.duration:.0f}s" if s.duration else "-"
            table.add_row(str(s.id), s.title or "-", s.channel or "-", dur, s.status.value)

        console.print(table)
    else:
        from content_engine.database import Clip
        clips = session.query(Clip).all()
        table = Table(title="Clips")
        table.add_column("ID", style="cyan")
        table.add_column("Source")
        table.add_column("Time Range")
        table.add_column("Duration")
        table.add_column("Status")

        for c in clips:
            time_range = f"{c.start_time:.1f}s - {c.end_time:.1f}s"
            table.add_row(str(c.id), str(c.source_id), time_range, f"{c.duration:.1f}s", c.status.value)

        console.print(table)


if __name__ == "__main__":
    cli()
