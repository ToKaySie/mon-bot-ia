import os
import sys
import logging
import json
import asyncio
from pathlib import Path
from flask import Flask, request, jsonify
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

# Initialize Flask app
server = Flask(__name__)

# Global bot application
bot_app = None

@server.route('/')
def home():
    """Root endpoint for UptimeRobot."""
    return "Bot is running!", 200

@server.route('/health')
def health():
    """Health check endpoint."""
    return jsonify({
        "status": "ok",
        "bot": "Telegram AI Bot",
        "engine": "Ollama Cloud",
    }), 200

@server.route('/webhook', methods=['POST'])
async def webhook():
    """Handle incoming Telegram webhook updates."""
    if bot_app is None:
        return "Bot not initialized", 500
        
    try:
        data = request.get_json()
        update = Update.de_json(data, bot_app.bot)
        await bot_app.process_update(update)
        return "OK", 200
    except Exception as e:
        logger.error(f"Webhook error: {e}", exc_info=True)
        return "Internal Server Error", 200 # Always return 200 to Telegram to avoid retries

async def setup_bot():
    """Initialize the Telegram bot application."""
    global bot_app
    
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

    webhook_path = "/webhook"
    webhook_url = f"{external_url.rstrip('/')}{webhook_path}"

    logger.info("=" * 50)
    logger.info("🤖 Bot IA Telegram - Mode Webhook (Cloud) with Flask")
    logger.info(f"🌐 Webhook URL: {webhook_url}")
    logger.info(f"🏥 Health Check: {external_url.rstrip('/')}/health")
    logger.info("=" * 50)

    # Create bot handlers
    handlers = BotHandlers(config)

    # Build the application
    bot_app = ApplicationBuilder().token(config.telegram_token).build()

    # Register command handlers
    bot_app.add_handler(CommandHandler("start", handlers.start_command))
    bot_app.add_handler(CommandHandler("help", handlers.help_command))
    bot_app.add_handler(CommandHandler("reset", handlers.reset_command))
    bot_app.add_handler(CommandHandler("model", handlers.model_command))
    bot_app.add_handler(CommandHandler("stats", handlers.stats_command))
    bot_app.add_handler(CommandHandler("pdf", handlers.pdf_command))
    bot_app.add_handler(CommandHandler("cours", handlers.cours_command))

    # Register message handler
    bot_app.add_handler(MessageHandler(filters.PHOTO, handlers.handle_photo))
    bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.handle_message))

    # Register error handler
    bot_app.add_error_handler(handlers.error_handler)

    # Initialize bot
    await bot_app.initialize()
    await bot_app.bot.set_webhook(url=webhook_url, drop_pending_updates=True)
    await bot_app.start()

    # Start background jobs (Reminders)
    if bot_app.job_queue:
        bot_app.job_queue.run_repeating(handlers.check_reminders, interval=3600, first=10)
        logger.info("📅 JobQueue activée.")
    
    return bot_app

if __name__ == "__main__":
    # Create event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # Run bot setup
    loop.run_until_complete(setup_bot())
    
    # Run Flask server
    port = int(os.getenv("PORT", "10000"))
    logger.info(f"🚀 Serveur Web prêt sur le port {port}")
    
    # Flask normally runs in its own event loop or blocking. 
    # To run both Flask and PTB together, we can use a library like gunicorn or 
    # run flask in a thread, or use a WSGI server that supports async.
    # For simplicity on Render, we can use 'flask run' style but we need PTB logic to stay alive.
    
    # Actually, PTB's Application has a built-in webhook runner that uses Starlette/Tornado/etc.
    # But the user specifically wants Flask. 
    # I'll use a simple background thread for the bot if I were to use polling,
    # but here we use webhooks. So Flask is the main entry point for requests.
    
    # One catch: server.run() is blocking. The bot is initialized but needs to stay alive.
    # But for Webhooks, the bot doesn't need a separate polling loop. 
    # It just needs to be initialized.
    
    # However, to be extra safe and follow best practices for Render:
    server.run(host='0.0.0.0', port=port)
