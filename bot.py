"""
Telegram AI Bot - Local Mode (Polling)
Run this file to start the bot locally on your machine.

Usage:
    1. Copy .env.example to .env and fill in your credentials
    2. Run: python bot.py
"""

import logging
import sys
from pathlib import Path

from dotenv import load_dotenv
from threading import Thread
import os
from flask import Flask
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

from core.config import BotConfig
from core.handlers import BotHandlers

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)



# Initialize Flask app for keep-alive
server = Flask(__name__)

@server.route('/')
def home():
    return "Bot is running (Polling mode)!", 200

def run_server():
    port = int(os.environ.get("PORT", "10000"))
    server.run(host='0.0.0.0', port=port)

def main():
    """Start the bot in polling mode (local development)."""
    # Start the keep-alive server in a background thread
    Thread(target=run_server, daemon=True).start()


    # Load environment variables
    env_path = Path(__file__).parent / ".env"
    load_dotenv(env_path)

    # Load and validate config
    config = BotConfig.from_env()
    errors = config.validate()

    if errors:
        logger.error("Configuration errors:")
        for error in errors:
            logger.error(f"  - {error}")
        logger.error("\nPlease copy .env.example to .env and fill in your credentials.")
        sys.exit(1)

    logger.info("=" * 50)
    logger.info("🤖 Bot IA Telegram - Mode Local (Polling)")
    logger.info(f"📡 Ollama API: {config.ollama_api_url}")
    logger.info(f"🧠 Modèle: {config.ollama_model}")
    logger.info(f"💬 Historique max: {config.max_history} messages")
    logger.info(f"⏱  Rate limit: {config.rate_limit_messages}/{config.rate_limit_period}s")
    if config.allowed_users:
        logger.info(f"👤 Utilisateurs autorisés: {config.allowed_users}")
    else:
        logger.info("👤 Tous les utilisateurs sont autorisés")
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
    app.add_handler(CommandHandler("pdf", handlers.pdf_command))
    app.add_handler(CommandHandler("cours", handlers.cours_command))

    # Register message handler (for all text messages)
    app.add_handler(MessageHandler(filters.PHOTO, handlers.handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.handle_message))

    # Register error handler
    app.add_error_handler(handlers.error_handler)

    # Start background jobs (Reminders)
    if app.job_queue:
        app.job_queue.run_repeating(handlers.check_reminders, interval=3600, first=10)
        logger.info("📅 JobQueue activée : Vérification des rappels toutes les heures.")

    # Start polling
    logger.info("🚀 Bot démarré ! Appuyez sur Ctrl+C pour arrêter.")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
