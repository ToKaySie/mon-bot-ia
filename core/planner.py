import logging
from datetime import datetime, date
from supabase import create_client, Client
import json

logger = logging.getLogger(__name__)

class PlannerManager:
    """Manages exams and revision schedules in Supabase."""

    def __init__(self, supabase_url: str, supabase_key: str):
        self.supabase_url = supabase_url
        self.supabase_key = supabase_key
        self.enabled = bool(supabase_url and supabase_key)
        
        if self.enabled:
            self.client: Client = create_client(supabase_url, supabase_key)
        else:
            self.client = None

    def create_smart_plan(self, user_id: int, subject: str, exam_date: str, goal_description: str, sessions_json: str) -> dict:
        """Saves a generated study plan to the database."""
        if not self.enabled:
            return {"error": "Supabase n'est pas configuré."}
        
        try:
            # 1. Insert Exam
            exam_data = {
                "user_id": user_id,
                "subject": subject,
                "exam_date": exam_date,
                "goal_description": goal_description
            }
            exam_res = self.client.table("exams").insert(exam_data).execute()
            exam_id = exam_res.data[0]["id"]
            
            # 2. Insert Sessions
            sessions = json.loads(sessions_json)
            sessions_data = []
            for session in sessions:
                sessions_data.append({
                    "exam_id": exam_id,
                    "user_id": user_id,
                    "planned_date": session["date"],
                    "topic": session["topic"]
                })
                
            self.client.table("revision_sessions").insert(sessions_data).execute()
            
            logger.info(f"Smart plan created for user {user_id}, exam: {subject}")
            return {
                "success": True, 
                "exam_id": exam_id,
                "message": f"✅ Calendrier de révision pour '{subject}' généré et sauvegardé avec succès."
            }
            
        except Exception as e:
            logger.error(f"Error creating smart plan: {e}")
            return {"error": f"Erreur lors de la création du planning: {e}"}

    def get_todays_reminders(self) -> list:
        """Fetches sessions scheduled for today that haven't been notified yet."""
        if not self.enabled:
            return []
            
        try:
            today_str = date.today().isoformat()
            response = self.client.table("revision_sessions") \
                .select("*, exams(subject)") \
                .eq("planned_date", today_str) \
                .eq("notified", False) \
                .execute()
                
            return response.data
        except Exception as e:
            logger.error(f"Error fetching reminders: {e}")
            return []

    def mark_notified(self, session_id: int):
        """Marks a session as notified."""
        if not self.enabled: return
        try:
            self.client.table("revision_sessions").update({"notified": True}).eq("id", session_id).execute()
        except Exception as e:
            logger.error(f"Error marking notified: {e}")

def get_planner_tool_definition() -> dict:
    return {
        "type": "function",
        "function": {
            "name": "generate_smart_plan",
            "description": "Crée un calendrier de révision. Utilise-le quand l'utilisateur déclare un examen (ex: 'J'ai mon bac dans 2 mois'). Tu dois calculer les dates de révision et fournir un tableau JSON des sessions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "subject": {
                        "type": "string",
                        "description": "Le nom de l'examen ou de la matière (ex: 'Bac de Français', 'Partiel Maths')"
                    },
                    "exam_date": {
                        "type": "string",
                        "description": "Date de l'examen au format YYYY-MM-DD"
                    },
                    "goal_description": {
                        "type": "string",
                        "description": "Description de l'objectif (ex: 'Viser 16/20, revoir les textes classiques')"
                    },
                    "sessions_json": {
                        "type": "string",
                        "description": 'Un tableau JSON des sessions. Format exigé en chaine de caractères : [{"date": "YYYY-MM-DD", "topic": "Description précise de la session"}]. Distribue les sessions intelligemment jusqu\'à la date de l\'examen.'
                    },
                    "generate_pdf": {
                        "type": "boolean",
                        "description": "Toujours mettre à True pour que l'IA génère aussi un tableau de bord visuel."
                    }
                },
                "required": ["subject", "exam_date", "goal_description", "sessions_json", "generate_pdf"]
            }
        }
    }
