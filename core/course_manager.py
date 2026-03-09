import logging
from supabase import create_client, Client

logger = logging.getLogger(__name__)

class CourseManager:
    """Manages course materials (extracted text from photos) stored in Supabase."""

    def __init__(self, supabase_url: str, supabase_key: str):
        self.supabase_url = supabase_url
        self.supabase_key = supabase_key
        self.enabled = bool(supabase_url and supabase_key)
        
        if self.enabled:
            self.client: Client = create_client(supabase_url, supabase_key)
        else:
            self.client = None

    def add_course_material(self, user_id: int, tag: str, extracted_text: str) -> dict:
        """Saves extracted text from a course photo to the database under a specific tag."""
        if not self.enabled:
            return {"error": "Supabase n'est pas configuré."}
        
        try:
            data = {
                "user_id": user_id,
                "tag": tag.lower(),
                "extracted_text": extracted_text
            }
            
            self.client.table("course_materials").insert(data).execute()
            
            logger.info(f"Course material saved for user {user_id} with tag '{tag}'")
            return {"success": True, "message": f"✅ Cours sauvegardé avec succès sous le tag '{tag}'."}
            
        except Exception as e:
            logger.error(f"Error saving course material: {e}")
            return {"error": f"Erreur lors de la sauvegarde: {e}"}

    def get_course_content_by_tag(self, user_id: int, tag: str) -> str:
        """Retrieves and concatenates all extracted text for a specific tag."""
        if not self.enabled:
            return "Erreur: Base de données non configurée."
            
        try:
            response = self.client.table("course_materials").select("extracted_text").eq("user_id", user_id).eq("tag", tag.lower()).execute()
            
            materials = response.data
            if not materials:
                return f"Aucun contenu trouvé pour le tag '{tag}'."
                
            combined_text = "\n\n--- NOUVELLE PAGE DE COURS ---\n\n".join([item["extracted_text"] for item in materials])
            return combined_text
            
        except Exception as e:
            logger.error(f"Error retrieving course material: {e}")
            return f"Erreur lors de la récupération du cours: {e}"

    def list_tags(self, user_id: int) -> list:
        """Lists all unique course tags for a user."""
        if not self.enabled:
            return []
            
        try:
            # Note: Supabase JS has .select('tag').eq(...), but getting unique requires fetching and filtering in Python 
            # if we don't have a specific RPC.
            response = self.client.table("course_materials").select("tag").eq("user_id", user_id).execute()
            tags = list(set([item["tag"] for item in response.data]))
            return sorted(tags)
            
        except Exception as e:
            logger.error(f"Error listing tags: {e}")
            return []

    def list_tags_with_counts(self, user_id: int) -> dict:
        """Lists all unique course tags for a user along with the count of materials for each tag."""
        if not self.enabled:
            return {}
            
        try:
            response = self.client.table("course_materials").select("tag").eq("user_id", user_id).execute()
            tag_counts = {}
            for item in response.data:
                tag = item["tag"]
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
            return tag_counts
            
        except Exception as e:
            logger.error(f"Error listing tag counts: {e}")
            return {}

def get_course_tool_definition(available_tags: list = None) -> dict:
    """Tool definition for the AI to fetch course content by tag."""
    
    desc = "Récupère le contenu complet d'un cours sauvegardé par l'utilisateur via un tag (mot-clé)."
    if available_tags:
        tags_str = ", ".join(available_tags)
        desc += f"\nTags disponibles pour cet utilisateur : {tags_str}"
        
    return {
        "type": "function",
        "function": {
            "name": "get_course_content",
            "description": desc,
            "parameters": {
                "type": "object",
                "properties": {
                    "tag": {
                        "type": "string",
                        "description": "Le tag du cours à récupérer (ex: maths, histoire)"
                    }
                },
                "required": ["tag"]
            }
        }
    }
