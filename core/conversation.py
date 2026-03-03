"""
Conversation memory manager.
Stores conversation history per user with automatic cleanup.
"""

import time
from datetime import datetime
import logging
from collections import defaultdict
import os

try:
    from zoneinfo import ZoneInfo
except ImportError:
    pass # Fallback for very old python versions

logger = logging.getLogger(__name__)


class ConversationManager:
    """Manages conversation history for multiple users."""

    def __init__(self, max_history: int = 20, system_prompt: str = ""):
        self.max_history = max_history
        self.system_prompt = system_prompt
        self._conversations: dict[int, list[dict]] = defaultdict(list)
        self._last_activity: dict[int, float] = {}

    def get_messages(self, user_id: int, user_memory: str = "", study_plans: str = "") -> list[dict]:
        """
        Get the full message list for a user, including the system prompt and memory/study plans.

        Returns:
            List of messages in OpenAI chat format.
        """
        messages = []

        prompt_content = self.system_prompt
        
        # Inject Time Awareness (Europe/Paris timezone)
        try:
            now = datetime.now(ZoneInfo("Europe/Paris"))
        except:
            now = datetime.now() # Fallback
            
        days = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
        months = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
        date_str = f"{days[now.weekday()]} {now.day} {months[now.month - 1]} {now.year}"
        time_str = now.strftime("%H:%M")
        
        prompt_content += f"\n\n[CONSCIENCE DU TEMPS]\nNous sommes le {date_str}, il est {time_str} (Heure de Paris)."

        if user_memory or study_plans:
            prompt_content += "\n\n[BASE DE DONNÉES DE L'UTILISATEUR]"
        
        if user_memory:
            prompt_content += f"\nMémoire personnelle :\n{user_memory}"
            
        if study_plans:
            prompt_content += f"\nPlannings de révisions prévus :\n{study_plans}"
            
        if user_memory or study_plans:
            prompt_content += "\n(Sers-toi de ces informations comme base absolue de la réalité de l'utilisateur. IMPÉRATIF : Si la mémoire mentionne ton nom (ex: Tyler), ton rôle ou ta personnalité, tu DOIS absolument incarner et assumer cette identité si l'on te pose la question 'Qui es-tu ?' ou 'Quel est ton nom ?', au lieu de dire que tu es une IA générique)."
            
        if prompt_content:
            prompt_content += "\n\n[INSTRUCTION DE FORMATAGE CRITIQUE]\nTu dois formater TOUTES tes réponses EXCLUSIVEMENT en syntaxe HTML acceptée par Telegram (<b>gras</b>, <i>italique</i>, <code>code</code>). L'utilisation de Markdown (comme **gras**, *italique*, ou # Titre) est STRICTEMENT INTERDITE car cela brise l'affichage."
            messages.append({"role": "system", "content": prompt_content})

        # Add conversation history
        messages.extend(self._conversations[user_id])

        return messages

    def add_user_message(self, user_id: int, content: str) -> None:
        """Add a user message to the conversation history."""
        self._conversations[user_id].append({"role": "user", "content": content})
        self._last_activity[user_id] = time.time()
        self._trim_history(user_id)

    def add_assistant_message(self, user_id: int, content: str) -> None:
        """Add an assistant response to the conversation history."""
        self._conversations[user_id].append({"role": "assistant", "content": content})
        self._trim_history(user_id)

    def clear_history(self, user_id: int) -> None:
        """Clear conversation history for a specific user."""
        self._conversations[user_id] = []
        logger.info(f"Cleared history for user {user_id}")

    def clear_all(self) -> None:
        """Clear all conversation histories."""
        self._conversations.clear()
        self._last_activity.clear()
        logger.info("Cleared all conversation histories")

    def get_stats(self, user_id: int) -> dict:
        """Get conversation stats for a user."""
        history = self._conversations[user_id]
        return {
            "message_count": len(history),
            "max_history": self.max_history,
            "last_activity": self._last_activity.get(user_id),
        }

    def _trim_history(self, user_id: int) -> None:
        """Trim conversation history to max_history messages."""
        history = self._conversations[user_id]
        if len(history) > self.max_history:
            # Keep only the most recent messages
            self._conversations[user_id] = history[-self.max_history:]

    def cleanup_inactive(self, max_idle_seconds: int = 3600) -> int:
        """
        Remove conversations that have been idle for too long.

        Returns:
            Number of conversations cleaned up.
        """
        now = time.time()
        to_remove = []

        for user_id, last_time in self._last_activity.items():
            if now - last_time > max_idle_seconds:
                to_remove.append(user_id)

        for user_id in to_remove:
            del self._conversations[user_id]
            del self._last_activity[user_id]

        if to_remove:
            logger.info(f"Cleaned up {len(to_remove)} inactive conversations")

        return len(to_remove)

    def export_state(self) -> dict:
        """Export the current state (useful for serverless persistence)."""
        return {
            "conversations": dict(self._conversations),
            "last_activity": dict(self._last_activity),
        }

    def import_state(self, state: dict) -> None:
        """Import a previously exported state."""
        self._conversations = defaultdict(list, state.get("conversations", {}))
        self._last_activity = state.get("last_activity", {})
