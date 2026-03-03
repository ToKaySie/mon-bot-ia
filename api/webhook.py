"""
Telegram AI Bot - Vercel Serverless Webhook Handler

This file handles incoming Telegram webhook requests as a Vercel serverless function.
Deploy this to Vercel for free 24/7 hosting.

Vercel Python runtime expects a class named `handler` that extends BaseHTTPRequestHandler.
"""

import os
import sys
import json
import logging
import asyncio

# Add parent directory to path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from http.server import BaseHTTPRequestHandler
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

from core.config import BotConfig
from core.handlers import BotHandlers

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


# --- Singleton pattern for warm Lambda/Vercel invocations ---
_config = None
_bot_handlers = None


def _get_config():
    """Get or create the config (singleton)."""
    global _config
    if _config is None:
        _config = BotConfig.from_env()
        errors = _config.validate()
        if errors:
            logger.error(f"Config errors: {errors}")
            raise ValueError(f"Configuration errors: {errors}")
    return _config


def _get_handlers():
    """Get or create the bot handlers (singleton)."""
    global _bot_handlers
    if _bot_handlers is None:
        _bot_handlers = BotHandlers(_get_config())
    return _bot_handlers


async def process_update(data: dict):
    """Process a single Telegram update using a fresh Application context."""
    config = _get_config()
    handlers = _get_handlers()

    # Build a fresh application for each request
    # This avoids issues with Application lifecycle in serverless
    app = ApplicationBuilder().token(config.telegram_token).build()

    # Register handlers
    app.add_handler(CommandHandler("start", handlers.start_command))
    app.add_handler(CommandHandler("help", handlers.help_command))
    app.add_handler(CommandHandler("reset", handlers.reset_command))
    app.add_handler(CommandHandler("model", handlers.model_command))
    app.add_handler(CommandHandler("stats", handlers.stats_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.handle_message))
    app.add_error_handler(handlers.error_handler)

    # Initialize, process, then shutdown cleanly
    async with app:
        update = Update.de_json(data, app.bot)
        await app.process_update(update)


class handler(BaseHTTPRequestHandler):
    """Vercel serverless function handler for Telegram webhooks."""

    def do_GET(self):
        """Health check endpoint."""
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({
            "status": "ok",
            "bot": "Telegram AI Bot",
            "engine": "Ollama Cloud",
        }).encode())

    def do_POST(self):
        """Handle incoming Telegram webhook updates."""
        try:
            # Read request body
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            data = json.loads(body)

            logger.info("Received webhook update")

            # Run the async processing
            asyncio.run(process_update(data))

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"ok": True}).encode())

        except Exception as e:
            logger.error(f"Webhook error: {e}", exc_info=True)
            # Always return 200 to Telegram to avoid retries
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"ok": False, "error": str(e)}).encode())

    def log_message(self, format, *args):
        """Suppress default HTTP logging (we use our own logger)."""
        pass
