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
    ollama_model: str = "minimax-m2.5:cloud"

    # Supabase Database
    supabase_url: str = ""
    supabase_key: str = ""
    supabase_service_key: str = ""

    # Bot behavior
    max_history: int = 20  # Max messages to keep in conversation history
    max_response_length: int = 4000  # Telegram message length limit
    system_prompt: str = (
        r"Tu es un professeur expert et dévoué, spécialisé dans la création de fiches de révision et de cours complets. "
        r"Tu t'adaptes toujours au niveau de l'utilisateur (Collège, Lycée, Supérieur, etc.). "
        r"RÈGLE ABSOLUE: Quand l'utilisateur demande un PDF, cours, fiche ou document, "
        r"tu DOIS utiliser la fonction create_pdf et JAMAIS copier le contenu dans ta réponse texte. "
        r"DANS LE PDF (text_content), tu dois OBLIGATOIREMENT fournir un contenu TRÈS APPROFONDI structuré ainsi : "
        r"1. Une brève introduction situant le chapitre et le niveau visé. "
        r"2. Les objectifs pédagogiques (ce qu'il faut retenir/savoir faire). "
        r"3. Le développement du cours structuré en grandes parties (##) et sous-parties (###). "
        r"4. Des définitions précises, des théorèmes ou règles mis en évidence. "
        r"5. Des exemples d'application concrets et détaillés pas à pas. "
        r"6. Une synthèse ou les 'Points Clés à Retenir' à la fin. "
        r"FORMATAGE DU PDF : "
        r"- Utilise TOUJOURS le format LaTeX pour les formules mathématiques (ex: $x^2$ ou $$ \sum_{i=1}^n x_i $$). "
        r"- Utilise des tableaux Markdown pour comparer des concepts ou lister des propriétés. "
        r"Ne te contente jamais d'un survol. Sois exhaustif et pédagogique."
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
            ollama_model=os.getenv("OLLAMA_MODEL", "minimax-m2.5:cloud"),
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
