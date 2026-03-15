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


@cli.command()
@click.argument("clip_id", type=int)
@click.option("--hook", default="", help="Text hook to overlay (e.g. 'Wait for it...')")
@click.option("--no-reframe", is_flag=True, help="Skip 9:16 reframing")
@click.option("--no-captions", is_flag=True, help="Skip caption generation")
@click.option("--watermark", default="", help="Path to watermark image (PNG)")
@click.pass_context
def render(ctx, clip_id, hook, no_reframe, no_captions, watermark):
    """Render a clip with post-production (reframe, captions, overlays)."""
    from content_engine.database import Clip
    from content_engine.editor.render import render_clip_simple

    config = ctx.obj["config"]
    session = get_session(config)
    clip = session.get(Clip, clip_id)

    if not clip:
        console.print(f"[red]Clip {clip_id} not found.[/red]")
        return

    if not clip.file_path:
        console.print(f"[red]Clip {clip_id} has no file. Extract it first.[/red]")
        return

    # Find transcript for the source
    source = session.get(Source, clip.source_id)
    transcript_path = source.transcript_path if source else None

    console.print(f"Rendering clip [cyan]{clip_id}[/cyan]...")
    steps = []
    if not no_reframe:
        steps.append("9:16 reframe")
    if not no_captions and transcript_path:
        steps.append("captions")
    if hook:
        steps.append(f"hook: '{hook}'")
    if watermark:
        steps.append("watermark")
    console.print(f"  Steps: {', '.join(steps) or 'copy only'}")

    output = render_clip_simple(
        clip, config, session,
        transcript_path=transcript_path,
        hook_text=hook,
        reframe=not no_reframe,
        captions=not no_captions,
        watermark_path=watermark,
    )
    console.print(f"[green]Rendered:[/green] {output}")


@cli.command()
@click.argument("url")
@click.option("--top-n", default=5, help="Number of top clips to extract")
@click.option("--hook", default="", help="Text hook for all clips (or 'auto' for AI-suggested hooks)")
@click.option("--no-reframe", is_flag=True, help="Skip 9:16 reframing")
@click.option("--no-captions", is_flag=True, help="Skip caption generation")
@click.option("--no-render", is_flag=True, help="Skip rendering (clip extraction only)")
@click.option("--watermark", default="", help="Path to watermark image (PNG)")
@click.option("--api-key", default=None, help="Anthropic API key (optional — uses heuristic scoring if not set)")
@click.option("--min-score", default=None, type=float, help="Minimum virality score (default: 6.0 with API, 4.0 without)")
@click.pass_context
def process(ctx, url, top_n, hook, no_reframe, no_captions, no_render, watermark, api_key, min_score):
    """Full pipeline: download → transcribe → find best clips → render.

    This is the main command. Give it a URL and it produces ready-to-post
    short-form clips with captions, reframing, and hook overlays.

    Works without an API key using local heuristic scoring. Add --api-key
    for higher-quality LLM-based clip selection.

    \b
    Examples:
      content-engine process "https://youtube.com/watch?v=..."
      content-engine process "https://youtube.com/watch?v=..." --hook "Wait for it..."
      content-engine process "https://youtube.com/watch?v=..." --top-n 3 --no-reframe
    """
    import os
    from content_engine.sourcer.downloader import download_source
    from content_engine.clipper.pipeline import auto_clip
    from content_engine.editor.render import render_clip_simple
    from content_engine.database import Clip

    config = ctx.obj["config"]
    init_db(config)
    session = get_session(config)

    # Resolve scoring mode
    has_api_key = bool(api_key or os.environ.get("ANTHROPIC_API_KEY"))
    if min_score is None:
        min_score = 6.0 if has_api_key else 4.0

    scoring_mode = "[green]LLM (Claude)[/green]" if has_api_key else "[yellow]local heuristic[/yellow]"
    console.print(f"\n[bold]Content Engine — Full Pipeline[/bold]")
    console.print(f"  Scoring: {scoring_mode}")
    console.print(f"  Top clips: {top_n}, Min score: {min_score}")
    if not has_api_key:
        console.print("  [dim]Tip: Set ANTHROPIC_API_KEY for better clip selection[/dim]")

    # Step 1: Download
    console.print(f"\n[bold cyan]Step 1/{'3' if no_render else '4'}:[/bold cyan] Downloading...")
    console.print(f"  URL: {url}")
    source = download_source(url, config)
    console.print(f"  [green]Done:[/green] {source.title} ({source.duration:.0f}s)")

    # Step 2: Auto-clip (transcribe + score + extract)
    console.print(f"\n[bold cyan]Step 2/{'3' if no_render else '4'}:[/bold cyan] Transcribing & finding best clips...")
    clips = auto_clip(
        source, config, session,
        top_n=top_n,
        min_score=min_score,
        api_key=api_key,
        use_energy=True,
    )

    if not clips:
        console.print("[yellow]No clips found above the score threshold.[/yellow]")
        console.print("[dim]Try lowering --min-score or using a different source.[/dim]")
        return

    console.print(f"  [green]Found {len(clips)} clips[/green]")

    # Step 3: Show clips
    console.print(f"\n[bold cyan]Step 3/{'3' if no_render else '4'}:[/bold cyan] Clips extracted:")
    table = Table()
    table.add_column("Clip ID", style="cyan")
    table.add_column("Time Range")
    table.add_column("Score")
    table.add_column("Suggested Hook")
    table.add_column("File")

    for c in clips:
        table.add_row(
            str(c.id),
            f"{c.start_time:.1f}s - {c.end_time:.1f}s",
            f"{c.virality_score:.1f}" if c.virality_score else "-",
            c.title or "-",
            c.file_path or "-",
        )
    console.print(table)

    # Step 4: Render each clip
    if not no_render:
        console.print(f"\n[bold cyan]Step 4/4:[/bold cyan] Rendering with post-production...")
        rendered = []
        for c in clips:
            # Use auto hook if requested, otherwise use provided hook
            clip_hook = hook
            if hook == "auto" and c.title:
                clip_hook = c.title

            console.print(f"  Rendering clip {c.id}...", end="")
            output = render_clip_simple(
                c, config, session,
                transcript_path=source.transcript_path,
                hook_text=clip_hook,
                reframe=not no_reframe,
                captions=not no_captions,
                watermark_path=watermark,
            )
            rendered.append(output)
            console.print(f" [green]done[/green]")

        console.print(f"\n[bold green]Pipeline complete![/bold green]")
        console.print(f"  Rendered {len(rendered)} clips to: [cyan]{config.storage.rendered_dir}[/cyan]")
        for path in rendered:
            console.print(f"    {path}")
    else:
        console.print(f"\n[bold green]Pipeline complete![/bold green] (rendering skipped)")
        console.print(f"  {len(clips)} clips in: [cyan]{config.storage.clips_dir}[/cyan]")
        console.print("  Run [cyan]content-engine render <clip_id>[/cyan] to render individually")


@cli.command(name="auto-clip")
@click.argument("source_id", type=int)
@click.option("--top-n", default=5, help="Number of top clips to extract")
@click.option("--min-score", default=6.0, help="Minimum virality score (0-10)")
@click.option("--api-key", default=None, help="Anthropic API key (or set ANTHROPIC_API_KEY)")
@click.option("--no-energy", is_flag=True, help="Disable audio energy blending")
@click.pass_context
def auto_clip_cmd(ctx, source_id, top_n, min_score, api_key, no_energy):
    """Automatically find and extract the best clips from a source."""
    from content_engine.clipper.pipeline import auto_clip

    config = ctx.obj["config"]
    init_db(config)
    session = get_session(config)
    source = session.get(Source, source_id)

    if not source:
        console.print(f"[red]Source {source_id} not found.[/red]")
        return

    console.print(f"Auto-clipping: [cyan]{source.title or source.url}[/cyan]")
    console.print(f"  Settings: top_n={top_n}, min_score={min_score}, energy={'off' if no_energy else 'on'}")

    clips = auto_clip(
        source, config, session,
        top_n=top_n,
        min_score=min_score,
        api_key=api_key,
        use_energy=not no_energy,
    )

    if not clips:
        console.print("[yellow]No clips met the score threshold.[/yellow]")
        return

    table = Table(title=f"Extracted {len(clips)} clips")
    table.add_column("ID", style="cyan")
    table.add_column("Time Range")
    table.add_column("Score")
    table.add_column("Title")

    for c in clips:
        table.add_row(
            str(c.id),
            f"{c.start_time:.1f}s - {c.end_time:.1f}s",
            f"{c.virality_score:.1f}" if c.virality_score else "-",
            c.title or "-",
        )

    console.print(table)


if __name__ == "__main__":
    cli()
