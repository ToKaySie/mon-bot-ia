"""
Configuration module for the Telegram AI Bot.
Loads settings from environment variables.
"""

import os
from dataclasses import dataclass, field


@dataclass
class BotConfig:
    """Bot configuration loaded from environment variables."""

    # Telegram Bot Token (from @BotFather)
    telegram_token: str = ""

    # Ollama Cloud API settings
    ollama_api_url: str = "https://ollama.com/v1"
    ollama_api_key: str = ""
    ollama_model: str = "qwen3.5:397b-cloud"

    # Supabase Database
    supabase_url: str = ""
    supabase_key: str = ""
    supabase_service_key: str = ""

    # Bot behavior
    max_history: int = 20  # Max messages to keep in conversation history
    max_response_length: int = 4000  # Telegram message length limit
    system_prompt: str = (
        "Tu es un assistant IA intelligent, amical et serviable. "
        "Tu réponds de manière concise et précise. "
        "Tu peux répondre en français et en anglais selon la langue de l'utilisateur. "
        "Si tu ne sais pas quelque chose, dis-le honnêtement. "
        "RÈGLE IMPORTANTE: Quand l'utilisateur demande un PDF, cours, fiche ou document, "
        "tu DOIS utiliser la fonction create_pdf et JAMAIS copier le contenu dans ta réponse. "
        "DANS LE PDF : "
        "1. Utilise TOUJOURS le format LaTeX pour les formules mathématiques (ex: $x^2$ ou $$ \sum_{i=1}^n x_i $$). "
        "2. Utilise TOUJOURS des tableaux Markdown pour les listes de données structurées. "
        "3. Produit un contenu académique riche, structuré et esthétique."
    )

    # Rate limiting
    rate_limit_messages: int = 30  # Max messages per period
    rate_limit_period: int = 60  # Period in seconds

    # Allowed users (empty = allow all)
    allowed_users: list = field(default_factory=list)

    @classmethod
    def from_env(cls) -> "BotConfig":
        """Load configuration from environment variables."""
        allowed = os.getenv("ALLOWED_USERS", "")
        allowed_list = [int(uid.strip()) for uid in allowed.split(",") if uid.strip()]

        return cls(
            telegram_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
            ollama_api_url=os.getenv("OLLAMA_API_URL", "https://ollama.com/v1"),
            ollama_api_key=os.getenv("OLLAMA_API_KEY", ""),
            ollama_model=os.getenv("OLLAMA_MODEL", "llama3.1:8b"),
            supabase_url=os.getenv("SUPABASE_URL", ""),
            supabase_key=os.getenv("SUPABASE_KEY", ""),
            supabase_service_key=os.getenv("SUPABASE_SERVICE_KEY", ""),
            max_history=int(os.getenv("MAX_HISTORY", "20")),
            max_response_length=int(os.getenv("MAX_RESPONSE_LENGTH", "4000")),
            system_prompt=os.getenv(
                "SYSTEM_PROMPT",
                cls.system_prompt,
            ),
            rate_limit_messages=int(os.getenv("RATE_LIMIT_MESSAGES", "30")),
            rate_limit_period=int(os.getenv("RATE_LIMIT_PERIOD", "60")),
            allowed_users=allowed_list,
        )

    def validate(self) -> list[str]:
        """Validate the configuration and return a list of errors."""
        errors = []
        if not self.telegram_token:
            errors.append("TELEGRAM_BOT_TOKEN is required")
        if not self.ollama_api_key:
            errors.append("OLLAMA_API_KEY is required")
        return errors
