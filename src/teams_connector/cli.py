"""
Command-line interface for Microsoft Teams connector.

Usage:
    teams-connector --app-id <id> --app-password <password>
    teams-connector --env-file .env
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

import click
from dotenv import load_dotenv

from teams_connector.bot import TeamsAmplifierBot

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)


@click.group()
def cli() -> None:
    """Amplifier Teams Connector — bridges Teams messages to Amplifier sessions."""
    pass


@cli.command()
@click.option(
    "--env-file",
    type=click.Path(exists=True, path_type=Path),
    default=".env",
    help="Path to .env file",
)
def onboard(env_file: Path) -> None:
    """Interactive onboarding to verify Teams bot configuration."""
    click.echo("🚀 Teams Connector Onboarding\n")
    
    if env_file.exists():
        load_dotenv(env_file)
        click.secho(f"✅ Loaded environment from {env_file}", fg="green")
    
    # Check credentials
    app_id = os.environ.get("TEAMS_APP_ID")
    app_password = os.environ.get("TEAMS_APP_PASSWORD")
    port = int(os.environ.get("TEAMS_PORT", "3978"))
    
    if not app_id:
        click.secho("❌ TEAMS_APP_ID not found in environment", fg="red")
        click.echo("\nPlease set TEAMS_APP_ID in your .env file.")
        click.echo("See: src/teams_connector/docs/SETUP.md")
        raise click.Abort()
    
    if not app_password:
        click.secho("❌ TEAMS_APP_PASSWORD not found in environment", fg="red")
        click.echo("\nPlease set TEAMS_APP_PASSWORD in your .env file.")
        click.echo("See: src/teams_connector/docs/SETUP.md")
        raise click.Abort()
    
    click.secho("✅ Credentials found in environment", fg="green")
    click.echo(f"   TEAMS_APP_ID: {app_id[:8]}...")
    click.echo(f"   TEAMS_APP_PASSWORD: {app_password[:8]}...")
    click.echo(f"   TEAMS_PORT: {port}")
    
    # Test webhook server
    click.echo("\n🌐 Testing webhook server...")
    click.echo(f"   Starting server on port {port}...")
    
    import socket
    
    # Check if port is available
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('localhost', port))
    sock.close()
    
    if result == 0:
        click.secho(f"⚠️  Port {port} is already in use", fg="yellow")
        click.echo("   Stop any existing teams-connector process first")
    else:
        click.secho(f"✅ Port {port} is available", fg="green")
    
    # Show messaging endpoint
    click.echo("\n📡 Messaging Endpoint Configuration:")
    click.echo("   Your bot needs a public HTTPS endpoint.")
    click.echo("\n   Development (using ngrok):")
    click.echo("     1. Run: ngrok http 3978")
    click.echo("     2. Copy the HTTPS URL (e.g., https://abc123.ngrok.io)")
    click.echo("     3. In Azure Portal → Bot → Configuration:")
    click.echo("        Set Messaging endpoint: https://abc123.ngrok.io/api/messages")
    click.echo("\n   Production:")
    click.echo("     Set Messaging endpoint: https://your-domain.com/api/messages")
    
    # Test health endpoint
    click.echo("\n🏥 To test the health endpoint after starting:")
    click.echo(f"   curl http://localhost:{port}/health")
    
    # Summary
    click.echo("\n" + "="*50)
    click.secho("✅ Onboarding Complete!", fg="green", bold=True)
    click.echo("="*50)
    click.echo("\nNext steps:")
    click.echo("  1. Set up messaging endpoint (see above)")
    click.echo("  2. Run: teams-connector start")
    click.echo("  3. Upload app to Teams (see SETUP.md)")
    click.echo("  4. Send a message to test")
    click.echo("\nDocumentation:")
    click.echo("  Setup: src/teams_connector/docs/SETUP.md")
    click.echo("  Usage: src/teams_connector/docs/USAGE.md")


@cli.command()
@click.option(
    "--bundle",
    type=click.Path(exists=True, path_type=Path),
    default="bundle.md",
    help="Path to Amplifier bundle file (default: bundle.md)",
)
@click.option(
    "--app-id",
    envvar="TEAMS_APP_ID",
    help="Microsoft Teams App ID (or set TEAMS_APP_ID env var)",
)
@click.option(
    "--app-password",
    envvar="TEAMS_APP_PASSWORD",
    help="Microsoft Teams App Password (or set TEAMS_APP_PASSWORD env var)",
)
@click.option(
    "--port",
    type=int,
    default=3978,
    envvar="TEAMS_PORT",
    help="Port for Bot Framework webhook server (default: 3978)",
)
@click.option(
    "--env-file",
    type=click.Path(exists=True, path_type=Path),
    help="Load environment variables from .env file",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Enable verbose (DEBUG) logging",
)
def start(
    bundle: Path,
    app_id: str | None,
    app_password: str | None,
    port: int,
    env_file: Path | None,
    verbose: bool,
) -> None:
    """
    Launch Microsoft Teams connector for Amplifier.
    
    The connector bridges Teams messages to Amplifier sessions using
    the Bot Framework SDK.
    
    Examples:
        # Using command-line arguments
        teams-connector --app-id abc123 --app-password secret123
        
        # Using environment variables
        export TEAMS_APP_ID=abc123
        export TEAMS_APP_PASSWORD=secret123
        teams-connector
        
        # Using .env file
        teams-connector --env-file .env
        
        # Custom bundle and port
        teams-connector --bundle my-bundle.md --port 8080
    """
    # Load .env file if specified
    if env_file:
        load_dotenv(env_file)
        logger.info(f"Loaded environment from {env_file}")
    
    # Enable verbose logging if requested
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Verbose logging enabled")
    
    # Validate required credentials
    if not app_id:
        logger.error("Missing Teams App ID. Provide via --app-id or TEAMS_APP_ID env var")
        sys.exit(1)
    
    if not app_password:
        logger.error("Missing Teams App Password. Provide via --app-password or TEAMS_APP_PASSWORD env var")
        sys.exit(1)
    
    # Validate bundle exists
    if not bundle.exists():
        logger.error(f"Bundle file not found: {bundle}")
        sys.exit(1)
    
    logger.info("=" * 60)
    logger.info("Microsoft Teams Connector for Amplifier")
    logger.info("=" * 60)
    logger.info(f"Bundle: {bundle.absolute()}")
    logger.info(f"App ID: {app_id[:8]}...")
    logger.info(f"Port: {port}")
    logger.info("=" * 60)
    
    # Create and run bot
    bot = TeamsAmplifierBot(
        bundle_path=str(bundle),
        app_id=app_id,
        app_password=app_password,
        port=port,
    )
    
    try:
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down...")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


def main() -> None:
    """Entry point for teams-connector CLI."""
    cli()


if __name__ == "__main__":
    main()
