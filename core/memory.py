import logging
from datetime import datetime
from supabase import create_client, Client

logger = logging.getLogger(__name__)

class MemoryManager:
    """Manages long-term structured memory for users using Supabase database."""

    def __init__(self, supabase_url: str, supabase_key: str):
        self.enabled = bool(supabase_url and supabase_key)
        
        if self.enabled:
            logger.info("Initializing Supabase memory manager...")
            try:
                self.supabase: Client = create_client(supabase_url, supabase_key)
            except Exception as e:
                logger.error(f"Failed to initialize Supabase client: {e}")
                self.enabled = False
        else:
            logger.warning("Supabase URL or Key is missing. Permanent memory is disabled.")
            
        # In-memory fallback if DB is not configured
        self.local_memories = []
        self.local_study_plans = []

    def get_memory_count(self) -> int:
        """Get the total number of memories currently stored."""
        if not self.enabled:
            return len(self.local_memories)
            
        try:
            # We fetch user_id just to count rows
            result = self.supabase.table("memories").select("id", count="exact").execute()
            return result.count if result.count is not None else 0
        except Exception as e:
            logger.error(f"Supabase count error: {e}")
            return len(self.local_memories)

    def get_all_memories(self, user_id: int) -> str:
        """Fetch all memories for a user, aggregated as a single string."""
        if not self.enabled:
            memories = [m["content"] for m in self.local_memories if m.get("user_id") == user_id]
            return "\n".join(memories) if memories else ""
            
        try:
            response = self.supabase.table("memories").select("content").eq("user_id", user_id).execute()
            memories = [row.get("content", "") for row in response.data]
            return "\n".join(memories) if memories else ""
        except Exception as e:
            logger.error(f"Failed to fetch memories from Supabase: {e}")
            return f"ERREUR DB (Memories): {e}"
            
    def get_all_study_plans(self, user_id: int) -> str:
        """Fetch all study plans for a user, aggregated as a single string."""
        if not self.enabled:
            plans = [p["plan_details"] for p in self.local_study_plans if p.get("user_id") == user_id]
            return "\n".join(plans) if plans else ""
            
        try:
            response = self.supabase.table("study_plans").select("plan_details").eq("user_id", user_id).execute()
            plans = [row.get("plan_details", "") for row in response.data]
            return "\n".join(plans) if plans else ""
        except Exception as e:
            logger.error(f"Failed to fetch study plans from Supabase: {e}")
            return f"ERREUR DB (Plans): {e}"

    def add_memory(self, user_id: int, content: str) -> None:
        """Add a new memory to the user's brain."""
        timestamp = datetime.now().isoformat()
        
        if not self.enabled:
            logger.warning("Saving memory locally (ephemeral) because Supabase is disabled.")
            self.local_memories.append({
                "user_id": user_id,
                "content": content,
                "timestamp": timestamp
            })
            return

        try:
            data = {
                "user_id": user_id,
                "content": content
            }
            # Remove explicit timestamp and let Postgres handle it with DEFAULT NOW()
            self.supabase.table("memories").insert(data).execute()
            logger.info(f"Memory saved to Supabase for user {user_id}: {content[:50]}...")
            
        except Exception as e:
            logger.error(f"Failed to save memory to Supabase: {e}", exc_info=True)
            # Fallback to local memory
            self.local_memories.append({
                "user_id": user_id,
                "content": content,
                "timestamp": timestamp
            })

    def add_study_plan(self, user_id: int, plan_details: str) -> None:
        """Add a new study plan / scheduled revision."""
        timestamp = datetime.now().isoformat()
        if not self.enabled:
            logger.warning("Saving study plan locally (ephemeral) because Supabase is disabled.")
            self.local_study_plans.append({
                "user_id": user_id,
                "plan_details": plan_details,
                "timestamp": timestamp
            })
            return

        try:
            data = {
                "user_id": user_id,
                "plan_details": plan_details
            }
            self.supabase.table("study_plans").insert(data).execute()
            logger.info(f"Study plan saved for user {user_id}: {plan_details[:50]}...")
            
        except Exception as e:
            logger.error(f"Failed to save study plan to Supabase: {e}", exc_info=True)
            self.local_study_plans.append({
                "user_id": user_id,
                "plan_details": plan_details,
                "timestamp": timestamp
            })

    def search_memory(self, user_id: int, query: str) -> str:
        """Search memories for a specific user using PostgreSQL text search / ilike."""
        logger.info(f"Searching memory for user {user_id} with query: '{query}'")
        
        if not self.enabled:
            # Fallback to local search
            return self._search_local(user_id, query)
            
        try:
            results = []
            query_words = [word for word in query.lower().split() if len(word) > 2] # ignore small words
            
            # Fetch user memories natively through Postgres
            response = self.supabase.table("memories").select("content, created_at").eq("user_id", user_id).order("created_at", desc=True).limit(200).execute()
            
            for mem in response.data:
                content_lower = mem.get("content", "").lower()
                # If there are query words, check if any match. If empty query, show all.
                if not query_words or any(word in content_lower for word in query_words):
                    date_str = ""
                    if mem.get("created_at"):
                        try:
                            # Handle standard isoformat from Supabase
                            iso_str = mem["created_at"].split(".")[0] if "." in mem["created_at"] else mem["created_at"]
                            iso_str = iso_str.replace("Z", "")
                            date_obj = datetime.fromisoformat(iso_str)
                            date_str = f"[{date_obj.strftime('%d/%m/%Y')}] "
                        except ValueError:
                            date_str = "[Date inconnue] "
                            
                    results.append(f"{date_str}{mem['content']}")
            
            if not results:
                return "Aucune information trouvée dans la mémoire pour cette recherche."
            
            return "\n".join(results[:10]) # Return max 10 results to not blow up the LLM context
            
        except Exception as e:
            logger.error(f"Search failed in Supabase: {e}")
            return self._search_local(user_id, query)
            
    def _search_local(self, user_id: int, query: str) -> str:
        """Fallback local keyword search."""
        results = []
        query_words = query.lower().split()
        
        for mem in self.local_memories:
            if mem.get("user_id") == user_id:
                content_lower = mem.get("content", "").lower()
                if any(word in content_lower for word in query_words):
                    results.append(f"{mem['content']}")
                    
        return "\n".join(results) if results else "Aucune information trouvée dans la mémoire."
