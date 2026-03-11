"""
Telegram AI Bot - Webhook Server for Cloud Deployment (Render, Railway, etc.)

This uses a custom Tornado server to handle both Telegram webhooks
and a /health endpoint for monitoring and keeping the service alive.
"""

import os
import sys
import logging
import json
import asyncio
from pathlib import Path

import tornado.web
import tornado.ioloop
import tornado.httpserver
from dotenv import load_dotenv
from telegram import Update
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


class HealthHandler(tornado.web.RequestHandler):
    """Handler for the /health endpoint."""
    def get(self):
        self.set_header("Content-Type", "application/json")
        self.write(json.dumps({
            "status": "ok",
            "bot": "Telegram AI Bot",
            "engine": "Ollama Cloud",
        }))


class WebhookHandler(tornado.web.RequestHandler):
    """Handler for Telegram webhook updates."""
    def initialize(self, app):
        self.app = app

    async def post(self):
        """Handle incoming Telegram webhook updates."""
        try:
            data = json.loads(self.request.body)
            update = Update.de_json(data, self.app.bot)
            await self.app.process_update(update)
            self.set_status(200)
            self.write("OK")
        except Exception as e:
            logger.error(f"Webhook error: {e}", exc_info=True)
            self.set_status(200)  # Always return 200 to Telegram


async def main():
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
    external_url = os.getenv("RENDER_EXTERNAL_URL") or os.getenv("WEBHOOK_URL", "")

    if not external_url:
        logger.error("❌ RENDER_EXTERNAL_URL or WEBHOOK_URL must be set!")
        sys.exit(1)

    # Port - Render sets the PORT env var
    port = int(os.getenv("PORT", "10000"))
    webhook_path = "/webhook"
    webhook_url = f"{external_url.rstrip('/')}{webhook_path}"

    logger.info("=" * 50)
    logger.info("🤖 Bot IA Telegram - Mode Webhook (Cloud)")
    logger.info(f"🌐 Webhook URL: {webhook_url}")
    logger.info(f"🔌 Port: {port}")
    logger.info(f"🏥 Health Check: {external_url.rstrip('/')}/health")
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

    # Initialize bot
    await app.initialize()
    await app.bot.set_webhook(url=webhook_url, drop_pending_updates=True)
    await app.start()

    # Start background jobs (Reminders)
    if app.job_queue:
        app.job_queue.run_repeating(handlers.check_reminders, interval=3600, first=10)
        logger.info("📅 JobQueue activée.")

    # Create Tornado application
    tornado_app = tornado.web.Application([
        (r"/health", HealthHandler),
        (webhook_path, WebhookHandler, dict(app=app)),
    ])

    # Start Tornado server
    http_server = tornado.httpserver.HTTPServer(tornado_app)
    http_server.listen(port)
    
    logger.info("🚀 Serveur Web prêt (Webhook + Health Check)")
    
    # Keep the event loop running
    try:
        await asyncio.Event().wait()
    finally:
        # Graceful shutdown
        await app.stop()
        await app.shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
