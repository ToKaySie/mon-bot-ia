"""
Telegram AI Bot - Webhook Server for Cloud Deployment (Render, Railway, etc.)

This uses python-telegram-bot's built-in webhook server.
It automatically starts a web server and registers the webhook with Telegram.

Usage:
    Set the RENDER_EXTERNAL_URL or WEBHOOK_URL environment variable, then:
    python webhook_server.py
"""

import os
import sys
import logging
from pathlib import Path

from dotenv import load_dotenv
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

from core.config import BotConfig
from core.handlers import BotHandlers

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


def main():
    """Start the bot in webhook mode for cloud deployment."""

    # Load environment variables
    load_dotenv(Path(__file__).parent / ".env")

    # Load and validate config
    config = BotConfig.from_env()
    errors = config.validate()

    if errors:
        logger.error("Configuration errors:")
        for error in errors:
            logger.error(f"  - {error}")
        sys.exit(1)

    # Determine the external URL
    # Render sets RENDER_EXTERNAL_URL automatically
    external_url = os.getenv("RENDER_EXTERNAL_URL") or os.getenv("WEBHOOK_URL", "")

    if not external_url:
        logger.error("❌ RENDER_EXTERNAL_URL or WEBHOOK_URL must be set!")
        logger.error("   On Render, this is set automatically.")
        logger.error("   Otherwise, set WEBHOOK_URL to your server's public URL.")
        sys.exit(1)

    # Port - Render sets the PORT env var
    port = int(os.getenv("PORT", "10000"))
    webhook_path = "/webhook"
    webhook_url = f"{external_url.rstrip('/')}{webhook_path}"

    logger.info("=" * 50)
    logger.info("🤖 Bot IA Telegram - Mode Webhook (Cloud)")
    logger.info(f"📡 Ollama API: {config.ollama_api_url}")
    logger.info(f"🧠 Modèle: {config.ollama_model}")
    logger.info(f"🌐 Webhook URL: {webhook_url}")
    logger.info(f"🔌 Port: {port}")
    logger.info("=" * 50)

    # Create bot handlers
    handlers = BotHandlers(config)

    # Build the application
    app = ApplicationBuilder().token(config.telegram_token).build()

    # Register command handlers
    app.add_handler(CommandHandler("start", handlers.start_command))
    app.add_handler(CommandHandler("help", handlers.help_command))
    app.add_handler(CommandHandler("reset", handlers.reset_command))
    app.add_handler(CommandHandler("model", handlers.model_command))
    app.add_handler(CommandHandler("stats", handlers.stats_command))
    app.add_handler(CommandHandler("dbcheck", handlers.dbcheck_command))
    app.add_handler(CommandHandler("pdf", handlers.pdf_command))
    app.add_handler(CommandHandler("cours", handlers.cours_command))

    # Register message handler
    app.add_handler(MessageHandler(filters.PHOTO, handlers.handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.handle_message))

    # Register error handler
    app.add_error_handler(handlers.error_handler)

    # Fix for Python 3.12+ / Cloud environments: Ensure an event loop exists
    import asyncio
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    # Start webhook server
    logger.info("🚀 Démarrage du serveur webhook...")

    app.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=webhook_path,
        webhook_url=webhook_url,
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()
