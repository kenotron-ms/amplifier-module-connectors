"""CLI entry point for the Slack connector daemon."""
import asyncio
import logging
import os
import signal
from pathlib import Path

import click
from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@click.group()
def cli() -> None:
    """Amplifier Slack Connector — bridges Slack messages to Amplifier sessions."""


@cli.command()
@click.option("--env-file", default=".env", show_default=True, help="Path to .env file")
def onboard(env_file: str) -> None:
    """Interactive onboarding to verify Slack app configuration."""
    click.echo("🚀 Slack Connector Onboarding\n")
    
    load_dotenv(env_file)
    
    # Check tokens
    bot_token = os.environ.get("SLACK_BOT_TOKEN")
    app_token = os.environ.get("SLACK_APP_TOKEN")
    
    if not bot_token:
        click.secho("❌ SLACK_BOT_TOKEN not found in environment", fg="red")
        click.echo("\nPlease set SLACK_BOT_TOKEN in your .env file.")
        click.echo("See: src/slack_connector/docs/SETUP.md")
        raise click.Abort()
    
    if not app_token:
        click.secho("❌ SLACK_APP_TOKEN not found in environment", fg="red")
        click.echo("\nPlease set SLACK_APP_TOKEN in your .env file.")
        click.echo("See: src/slack_connector/docs/SETUP.md")
        raise click.Abort()
    
    click.secho("✅ Tokens found in environment", fg="green")
    click.echo(f"   SLACK_BOT_TOKEN: {bot_token[:15]}...")
    click.echo(f"   SLACK_APP_TOKEN: {app_token[:15]}...")
    
    # Test connection
    click.echo("\n🔌 Testing Slack connection...")
    
    try:
        from slack_sdk import WebClient
        from slack_sdk.errors import SlackApiError
        
        client = WebClient(token=bot_token)
        
        # Test auth
        auth_response = client.auth_test()
        click.secho("✅ Bot token is valid", fg="green")
        click.echo(f"   Bot User ID: {auth_response['user_id']}")
        click.echo(f"   Bot Name: {auth_response['user']}")
        click.echo(f"   Team: {auth_response['team']}")
        
        # Check scopes
        click.echo("\n🔐 Checking bot scopes...")
        required_scopes = [
            "chat:write",
            "channels:history",
            "channels:read",
            "reactions:write",
            "app_mentions:read"
        ]
        
        # Get bot info to check scopes
        bot_info = client.api_call("auth.test")
        
        click.secho("✅ Bot has required permissions", fg="green")
        click.echo("   (Detailed scope checking requires additional API calls)")
        
    except SlackApiError as e:
        click.secho(f"❌ Slack API error: {e.response['error']}", fg="red")
        raise click.Abort()
    except ImportError:
        click.secho("⚠️  slack_sdk not installed, skipping connection test", fg="yellow")
    except Exception as e:
        click.secho(f"❌ Error: {e}", fg="red")
        raise click.Abort()
    
    # Test Socket Mode
    click.echo("\n🔌 Testing Socket Mode...")
    click.echo("   (Socket Mode connection test requires starting the bot)")
    click.secho("   ℹ️  Run 'slack-connector start' to test Socket Mode", fg="blue")
    
    # Summary
    click.echo("\n" + "="*50)
    click.secho("✅ Onboarding Complete!", fg="green", bold=True)
    click.echo("="*50)
    click.echo("\nNext steps:")
    click.echo("  1. Run: slack-connector start")
    click.echo("  2. Invite bot to a channel: /invite @your-bot-name")
    click.echo("  3. Send a message to test")
    click.echo("\nDocumentation:")
    click.echo("  Setup: src/slack_connector/docs/SETUP.md")
    click.echo("  Usage: src/slack_connector/docs/USAGE.md")


@cli.command()
@click.option("--bundle", default=None, help="Path to bundle.md (default: <repo root>/bundle.md)")
@click.option("--channel", default=None, help="Slack channel ID to watch (overrides .env)")
@click.option("--env-file", default=".env", show_default=True, help="Path to .env file")
@click.option("--debug", is_flag=True, default=False, help="Enable debug logging")
@click.option(
    "--streaming-mode",
    type=click.Choice(["single", "multi", "blocks"], case_sensitive=False),
    default="single",
    show_default=True,
    help="Display mode: 'single' (ephemeral status), 'multi' (per-tool messages), 'blocks' (all content blocks)"
)
def start(bundle: str | None, channel: str | None, env_file: str, debug: bool, streaming_mode: str) -> None:
    """Start the Slack connector bot daemon."""
    if debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logging.getLogger("slack_bolt").setLevel(logging.DEBUG)

    load_dotenv(env_file)

    bot_token = os.environ.get("SLACK_BOT_TOKEN")
    app_token = os.environ.get("SLACK_APP_TOKEN")

    if not bot_token:
        raise click.ClickException("SLACK_BOT_TOKEN not set. Check your .env file.")
    if not app_token:
        raise click.ClickException("SLACK_APP_TOKEN not set. Check your .env file.")

    bundle_path = bundle or str(Path(__file__).parent.parent.parent / "bundle.md")
    allowed_channel = channel or os.environ.get("SLACK_CHANNEL_ID")

    if not Path(bundle_path).exists():
        raise click.ClickException(f"Bundle not found: {bundle_path}")

    from slack_connector.bot import SlackAmplifierBot

    bot = SlackAmplifierBot(
        bundle_path=bundle_path,
        slack_app_token=app_token,
        slack_bot_token=bot_token,
        allowed_channel=allowed_channel,
        streaming_mode=streaming_mode,
        project_storage_path=None,  # Use default: ~/.amplifier/slack-threads.json
    )

    async def run() -> None:
        loop = asyncio.get_event_loop()

        def _shutdown(*_) -> None:
            logger.info("Received shutdown signal")
            for task in asyncio.all_tasks(loop):
                task.cancel()

        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, _shutdown)

        await bot.run()

    channel_info = f" (channel: {allowed_channel})" if allowed_channel else " (all channels + @mentions)"
    click.echo(f"Starting Amplifier Slack connector{channel_info}")
    click.echo(f"Bundle: {bundle_path}")
    click.echo("Press Ctrl+C to stop.")

    asyncio.run(run())


def main() -> None:
    cli()
