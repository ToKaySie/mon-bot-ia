"""
Script to set the Telegram webhook URL.
Run this after deploying to Vercel to connect Telegram to your serverless function.

Usage:
    python set_webhook.py <VERCEL_URL>

Example:
    python set_webhook.py https://my-bot-ia.vercel.app
"""

import sys
import os
import asyncio
from pathlib import Path

from dotenv import load_dotenv
from telegram import Bot


async def set_webhook(bot_token: str, vercel_url: str):
    """Set the Telegram webhook to the Vercel deployment URL."""
    webhook_url = f"{vercel_url.rstrip('/')}/api/webhook"

    bot = Bot(token=bot_token)

    # Delete any existing webhook
    await bot.delete_webhook(drop_pending_updates=True)
    print(f"🗑️  Ancien webhook supprimé")

    # Set new webhook
    success = await bot.set_webhook(
        url=webhook_url,
        allowed_updates=["message"],
        drop_pending_updates=True,
    )

    if success:
        print(f"✅ Webhook configuré avec succès !")
        print(f"📡 URL: {webhook_url}")

        # Verify
        info = await bot.get_webhook_info()
        print(f"\n📋 Informations du webhook:")
        print(f"   URL: {info.url}")
        print(f"   Pending updates: {info.pending_update_count}")
        print(f"   Max connections: {info.max_connections}")
    else:
        print("❌ Échec de la configuration du webhook")
        sys.exit(1)


async def delete_webhook(bot_token: str):
    """Delete the webhook (switch back to polling mode)."""
    bot = Bot(token=bot_token)
    await bot.delete_webhook(drop_pending_updates=True)
    print("✅ Webhook supprimé. Vous pouvez maintenant utiliser le mode polling (bot.py)")


def main():
    # Load .env
    load_dotenv(Path(__file__).parent / ".env")
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")

    if not bot_token:
        print("❌ TELEGRAM_BOT_TOKEN non trouvé. Configurez votre fichier .env")
        sys.exit(1)

    if len(sys.argv) < 2:
        print("Usage:")
        print("  Configurer le webhook:  python set_webhook.py <VERCEL_URL>")
        print("  Supprimer le webhook:   python set_webhook.py --delete")
        print("\nExemple:")
        print("  python set_webhook.py https://my-bot.vercel.app")
        sys.exit(1)

    if sys.argv[1] == "--delete":
        asyncio.run(delete_webhook(bot_token))
    else:
        vercel_url = sys.argv[1]
        asyncio.run(set_webhook(bot_token, vercel_url))


if __name__ == "__main__":
    main()
