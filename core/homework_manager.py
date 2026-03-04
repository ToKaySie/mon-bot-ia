"""
Homework (devoirs) manager for the Telegram bot.
Handles CRUD operations on the 'devoirs' Supabase table.
Auto-cleans expired homework (1 day after due date).
"""

import logging
from datetime import datetime, timedelta, date
from supabase import create_client, Client

logger = logging.getLogger(__name__)


def get_homework_tools() -> list[dict]:
    """Return all homework-related tool definitions for the AI."""
    return [
        {
            "type": "function",
            "function": {
                "name": "add_homework",
                "description": """Ajoute un devoir dans l'agenda de l'utilisateur.
Utilise cette fonction quand l'utilisateur mentionne un devoir, un travail à rendre, un exercice à faire, un contrôle à préparer, etc.
Extrais la matière, la description et la date de rendu du message.""",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "subject": {
                            "type": "string",
                            "description": "Matière du devoir (ex: Maths, Français, Histoire, Physique...)"
                        },
                        "description": {
                            "type": "string",
                            "description": "Description du devoir (ex: Exercices 1 à 5 p.42, Dissertation sur Balzac...)"
                        },
                        "due_date": {
                            "type": "string",
                            "description": "Date de rendu au format YYYY-MM-DD (ex: 2026-03-10)"
                        }
                    },
                    "required": ["subject", "description", "due_date"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "list_homework",
                "description": """Affiche la liste des devoirs de l'utilisateur.
Utilise cette fonction quand l'utilisateur demande ses devoirs, son agenda, ce qu'il a à faire, etc.""",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "mark_homework_done",
                "description": """Marque un devoir comme fait/terminé.
Utilise cette fonction quand l'utilisateur dit qu'il a fini un devoir.""",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "homework_id": {
                            "type": "integer",
                            "description": "ID du devoir à marquer comme fait"
                        }
                    },
                    "required": ["homework_id"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "delete_homework",
                "description": """Supprime un devoir de la liste.
Utilise cette fonction quand l'utilisateur veut retirer un devoir.""",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "homework_id": {
                            "type": "integer",
                            "description": "ID du devoir à supprimer"
                        }
                    },
                    "required": ["homework_id"]
                }
            }
        }
    ]


class HomeworkManager:
    """Manages homework entries in Supabase."""

    def __init__(self, supabase_url: str, supabase_key: str, service_key: str = None):
        self.enabled = bool(supabase_url and supabase_key)
        if self.enabled:
            key = service_key or supabase_key
            self.client: Client = create_client(supabase_url, key)
        else:
            self.client = None

    def _cleanup_expired(self):
        """Delete homework where due_date < today - 1 day."""
        if not self.enabled:
            return
        try:
            cutoff = (date.today() - timedelta(days=1)).isoformat()
            self.client.table("devoirs").delete().lt("due_date", cutoff).execute()
        except Exception as e:
            logger.warning(f"Homework cleanup error: {e}")

    def add(self, user_id: int, subject: str, description: str, due_date: str) -> dict:
        """Add a new homework entry."""
        if not self.enabled:
            return {"error": "Base de données non configurée"}

        try:
            # Validate date
            parsed_date = datetime.strptime(due_date, "%Y-%m-%d").date()
            
            result = self.client.table("devoirs").insert({
                "user_id": user_id,
                "subject": subject,
                "description": description,
                "due_date": due_date,
                "status": "non fait"
            }).execute()

            if result.data:
                entry = result.data[0]
                return {
                    "success": True,
                    "message": f"📝 Devoir ajouté !\n• {subject} : {description}\n• Pour le {parsed_date.strftime('%d/%m/%Y')}"
                }
            return {"error": "Erreur lors de l'ajout"}

        except ValueError:
            return {"error": f"Date invalide : '{due_date}'. Utilise le format YYYY-MM-DD."}
        except Exception as e:
            logger.error(f"Error adding homework: {e}")
            return {"error": str(e)}

    def list_all(self, user_id: int) -> dict:
        """List all active homework for a user."""
        if not self.enabled:
            return {"error": "Base de données non configurée"}

        try:
            # Clean up expired first
            self._cleanup_expired()

            result = (
                self.client.table("devoirs")
                .select("*")
                .eq("user_id", user_id)
                .gte("due_date", (date.today() - timedelta(days=1)).isoformat())
                .order("due_date")
                .execute()
            )

            devoirs = result.data or []

            if not devoirs:
                return {"success": True, "devoirs": [], "message": "📚 Aucun devoir en cours ! Tu es à jour 🎉"}

            lines = []
            for d in devoirs:
                due = datetime.strptime(d["due_date"], "%Y-%m-%d").date()
                days_left = (due - date.today()).days
                
                if days_left < 0:
                    urgency = "⚠️ EN RETARD"
                elif days_left == 0:
                    urgency = "🔴 Aujourd'hui"
                elif days_left == 1:
                    urgency = "🟠 Demain"
                elif days_left <= 3:
                    urgency = "🟡 Bientôt"
                else:
                    urgency = "🟢"

                status_icon = "✅" if d["status"] == "fait" else "⬜"
                lines.append(
                    f"{status_icon} #{d['id']} | {d['subject']} — {d['description']}\n"
                    f"   📅 {due.strftime('%d/%m/%Y')} ({urgency})"
                )

            header = f"📚 **Tes devoirs** ({len(devoirs)})\n\n"
            body = "\n\n".join(lines)
            footer = "\n\n💡 Dis « j'ai fini le devoir #X » pour le marquer fait."

            return {"success": True, "devoirs": devoirs, "message": header + body + footer}

        except Exception as e:
            logger.error(f"Error listing homework: {e}")
            return {"error": str(e)}

    def mark_done(self, homework_id: int, user_id: int = None) -> dict:
        """Mark a homework as done."""
        if not self.enabled:
            return {"error": "Base de données non configurée"}

        try:
            query = self.client.table("devoirs").update({"status": "fait"}).eq("id", homework_id)
            if user_id:
                query = query.eq("user_id", user_id)
            result = query.execute()

            if result.data:
                d = result.data[0]
                return {"success": True, "message": f"✅ Devoir #{homework_id} marqué comme fait ! ({d['subject']} — {d['description']})"}
            return {"error": f"Devoir #{homework_id} non trouvé"}

        except Exception as e:
            logger.error(f"Error marking homework done: {e}")
            return {"error": str(e)}

    def delete(self, homework_id: int, user_id: int = None) -> dict:
        """Delete a homework entry."""
        if not self.enabled:
            return {"error": "Base de données non configurée"}

        try:
            query = self.client.table("devoirs").delete().eq("id", homework_id)
            if user_id:
                query = query.eq("user_id", user_id)
            result = query.execute()

            if result.data:
                return {"success": True, "message": f"🗑 Devoir #{homework_id} supprimé"}
            return {"error": f"Devoir #{homework_id} non trouvé"}

        except Exception as e:
            logger.error(f"Error deleting homework: {e}")
            return {"error": str(e)}
