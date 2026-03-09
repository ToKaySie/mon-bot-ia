"""
Telegram bot handlers.
Defines all command and message handlers for the bot.
"""

import logging
import html
import time
import asyncio
import re

from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode, ChatAction

from core.config import BotConfig
from core.ollama_client import OllamaClient, OllamaError
from core.conversation import ConversationManager
from core.rate_limiter import RateLimiter
from core.memory import MemoryManager
from core.pdf_manager import PDFManager, get_pdf_tool_definition, get_create_pdf_tool_definition, get_delete_pdf_tool_definition, get_pdf_system_context
from core.homework_manager import HomeworkManager, get_homework_tools

logger = logging.getLogger(__name__)


class BotHandlers:
    """Telegram bot command and message handlers."""

    def __init__(self, config: BotConfig):
        self.config = config
        self.ollama = OllamaClient(config)
        self.memory = MemoryManager(
            supabase_url=config.supabase_url,
            supabase_key=config.supabase_key
        )
        self.conversations = ConversationManager(
            max_history=config.max_history,
            system_prompt=config.system_prompt,
        )
        self.rate_limiter = RateLimiter(
            max_messages=config.rate_limit_messages,
            period_seconds=config.rate_limit_period,
        )
        self.pdf_manager = PDFManager(
            supabase_url=config.supabase_url,
            supabase_key=config.supabase_key,
            service_key=config.supabase_service_key or None
        )
        self.homework = HomeworkManager(
            supabase_url=config.supabase_url,
            supabase_key=config.supabase_key,
            service_key=config.supabase_service_key or None
        )
        self._start_time = time.time()

    def _is_user_allowed(self, user_id: int) -> bool:
        """Check if a user is allowed to use the bot."""
        if not self.config.allowed_users:
            return True  # No restriction
        return user_id in self.config.allowed_users

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command."""
        user = update.effective_user
        if not self._is_user_allowed(user.id):
            await update.message.reply_text("⛔ Vous n'êtes pas autorisé à utiliser ce bot.")
            return

        welcome_message = (
            f"👋 Bonjour {html.escape(user.first_name)} !\n\n"
            f"Je suis un assistant IA propulsé par <b>Ollama Cloud</b>.\n"
            f"Envoyez-moi un message et je vous répondrai !\n\n"
            f"📚 <b>Bibliothèque PDF :</b>\n"
            f"Demandez-moi un document et je vous l'envoie directement !\n\n"
            f"📝 <b>Commandes disponibles :</b>\n"
            f"/start - Afficher ce message\n"
            f"/reset - Réinitialiser la conversation courante\n"
            f"/model - Voir/changer le modèle IA\n"
            f"/pdf - Voir la bibliothèque de PDFs\n"
            f"/stats - Statistiques de la conversation\n"
            f"/help - Aide détaillée"
        )

        await update.message.reply_text(welcome_message, parse_mode=ParseMode.HTML)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /help command."""
        user = update.effective_user
        if not self._is_user_allowed(user.id):
            return

        help_text = (
            "🤖 <b>Guide d'utilisation</b>\n\n"
            "Envoyez-moi simplement un message texte et je vous répondrai.\n\n"
            "💡 <b>Fonctionnalités :</b>\n"
            "• Conversation contextuelle\n"
            "• <b>Mémoire passive globale</b> : Je retiens automatiquement ce qui est important.\n"
            "• <b>Bibliothèque de PDFs</b> : Demandez un document et je vous l'envoie !\n"
            "• Réponses intelligentes et naturelles\n\n"
            "⚙️ <b>Commandes :</b>\n"
            "/start - Message de bienvenue\n"
            "/reset - Effacer l'historique de conversation à court terme\n"
            "/model - Voir le modèle IA utilisé\n"
            "/model &lt;nom&gt; - Changer de modèle\n"
            "/pdf - Liste des PDFs\n"
            "/pdf &lt;mot&gt; - Chercher un PDF\n"
            "/stats - Voir les statistiques\n"
            "/help - Ce message d'aide\n\n"
            "💡 <b>Astuce PDF :</b>\n"
            "Demandez naturellement : « Envoie-moi le PDF de maths »\n"
            "ou « J'ai besoin du document sur la physique »"
        )

        await update.message.reply_text(help_text, parse_mode=ParseMode.HTML)

    async def reset_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /reset command - clear conversation history."""
        user = update.effective_user
        if not self._is_user_allowed(user.id):
            return

        self.conversations.clear_history(user.id)
        await update.message.reply_text(
            "🔄 Conversation réinitialisée ! Envoyez un nouveau message pour recommencer."
        )

    async def model_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /model command - view or change the AI model."""
        user = update.effective_user
        if not self._is_user_allowed(user.id):
            return

        args = context.args
        if args:
            new_model = " ".join(args)
            self.config.ollama_model = new_model
            await update.message.reply_text(
                f"✅ Modèle changé en : <code>{html.escape(new_model)}</code>",
                parse_mode=ParseMode.HTML,
            )
        else:
            await update.message.reply_text(
                f"🤖 Modèle actuel : <code>{html.escape(self.config.ollama_model)}</code>\n\n"
                f"Pour changer : /model &lt;nom_du_modèle&gt;",
                parse_mode=ParseMode.HTML,
            )

    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /stats command - show conversation statistics."""
        user = update.effective_user
        if not self._is_user_allowed(user.id):
            return

        stats = self.conversations.get_stats(user.id)
        remaining = self.rate_limiter.get_remaining(user.id)
        uptime = time.time() - self._start_time

        # Format uptime
        hours, remainder = divmod(int(uptime), 3600)
        minutes, seconds = divmod(remainder, 60)

        stats_text = (
            "📊 <b>Statistiques</b>\n\n"
            f"💬 Messages courts : {stats['message_count']}/{stats['max_history']}\n"
            f"🧠 Faits mémorisés (Total) : {self.memory.get_memory_count()}\n"
            f"🚀 Messages restants : {remaining}/{self.config.rate_limit_messages}\n"
            f"☁️ Cloud DB : {'✅ Active' if self.memory.enabled else '❌ Inactive'}\n"
            f"🤖 Modèle : <code>{html.escape(self.config.ollama_model)}</code>\n"
            f"⏱ Uptime : {hours}h {minutes}m {seconds}s"
        )

        await update.message.reply_text(stats_text, parse_mode=ParseMode.HTML)

    async def pdf_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /pdf command - search and send PDFs from library."""
        user = update.effective_user
        if not self._is_user_allowed(user.id):
            return

        if not self.pdf_manager.enabled:
            await update.message.reply_text(
                "❌ La bibliothèque de PDFs n'est pas configurée.\n"
                "Contactez l'administrateur."
            )
            return

        args = context.args
        
        if not args:
            pdfs = self.pdf_manager.search_pdfs("")
            if not pdfs:
                await update.message.reply_text(
                    "📚 La bibliothèque de PDFs est vide.\n"
                    "Utilisez le dashboard pour ajouter des documents."
                )
                return
            
            message = "📚 **Bibliothèque de PDFs**\n\n"
            for i, pdf in enumerate(pdfs[:10], 1):
                message += f"{i}. {pdf['title']}\n"
                if pdf.get("description"):
                    message += f"   📝 {pdf['description'][:50]}...\n"
            
            message += f"\n💡 Pour chercher : /pdf <mot-clé>\n"
            message += f"   Pour télécharger : /pdf #<numéro>"
            
            await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
            return

        query = " ".join(args)
        
        if query.startswith("#"):
            try:
                index = int(query[1]) - 1
                pdfs = self.pdf_manager.search_pdfs("")
                if 0 <= index < len(pdfs):
                    pdf = pdfs[index]
                    await update.message.reply_text(
                        f"📄 {pdf['title']}\n\n"
                        f"Téléchargement en cours..."
                    )
                    await context.bot.send_document(
                        chat_id=update.message.chat_id,
                        document=pdf['public_url'],
                        caption=pdf.get("description", "")
                    )
                else:
                    await update.message.reply_text("❌ Numéro de PDF invalide.")
            except (ValueError, IndexError):
                await update.message.reply_text("❌ Format invalide. Utilisez /pdf #<numéro>")
        else:
            pdfs = self.pdf_manager.search_pdfs(query)
            if not pdfs:
                await update.message.reply_text(f"🔍 Aucun PDF trouvé pour « {query} »")
                return
            
            message = f"🔍 **Résultats pour « {query} »**\n\n"
            for i, pdf in enumerate(pdfs[:5], 1):
                message += f"{i}. {pdf['title']}\n"
                if pdf.get("description"):
                    message += f"   📝 {pdf['description'][:50]}...\n"
            
            message += f"\n💡 Téléchargez avec /pdf #<numéro>"
            
            await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)

    async def dbcheck_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /dbcheck command - debug database connection."""
        user = update.effective_user
        if not self._is_user_allowed(user.id): return
        
        await update.message.reply_text("🔍 Vérification de la base de données en cours...")
        
        try:
            mem_count = self.memory.get_memory_count()
            user_mems = self.memory.get_all_memories(user.id)
            user_plans = self.memory.get_all_study_plans(user.id)
            
            report = f"✅ Connecté à Supabase : {self.memory.enabled}\n"
            report += f"📊 Total global de mémos (Table Entière) : {mem_count}\n"
            report += f"🆔 Ton ID Utilisateur lu par Telegram : {user.id}\n\n"
            report += f"🧠 <b>Tes Faits (Filtre ID exact) :</b>\n{html.escape(user_mems) if user_mems else 'Rien'}\n\n"
            
            # Diagnostic absolu : on va chercher les 5 dernières lignes direct dans la DB sans filtrer par utilisateur
            if not user_mems and mem_count > 0:
                raw_db = self.memory.supabase.table("memories").select("user_id", "content").limit(5).execute()
                report += f"\n🚨 <b>[MODE DUMP DIAGNOSTIC]</b>\nVoici ce qui se trouve réelement dans la base de données :\n"
                for row in raw_db.data:
                    report += f"- ID: {row['user_id']} | Fait: {row['content'][:30]}...\n"
                report += f"\n<i>Si l'ID du dump est différent du tien, alors la base de données a tronqué le nombre (BigInt bug).</i>"
            
            await update.message.reply_text(report, parse_mode=ParseMode.HTML)
            
        except Exception as e:
            await update.message.reply_text(f"❌ Erreur critique lors de l'accès DB : {e}")


    def _is_pdf_request(self, text: str) -> tuple[bool, str]:
        """Detect if user is asking for a PDF and extract search query."""
        text_lower = text.lower()
        pdf_keywords = [
            "pdf", "document", "fichier", "télécharge", "envoie", "envoi",
            "cherche", "trouve", "copie", "cours", "chapitre", "lesson",
            "besoin de", "j'ai besoin", "donne-moi", "donne moi"
        ]
        
        has_pdf_keyword = any(kw in text_lower for kw in pdf_keywords)
        
        if has_pdf_keyword:
            query = text
            for word in ["le pdf", "un pdf", "le document", "un document", "de ", "du ", "des "]:
                idx = text_lower.find(word)
                if idx != -1:
                    query = text[idx + len(word):].strip()
                    break
            
            words_to_remove = ["pdf", "document", "télécharge", "envoie", "envoi", "trouve", "cherche", "s'il te plaît", "svp", "?", "!"]
            for word in words_to_remove:
                query = query.replace(word, "").strip()
            
            return True, query if query else text
        return False, ""

    async def _handle_pdf_request(self, update: Update, context: ContextTypes.DEFAULT_TYPE, query: str) -> bool:
        """Handle PDF request. Returns True if handled."""
        if not self.pdf_manager.enabled:
            return False
        
        pdfs = self.pdf_manager.search_pdfs(query)
        
        if not pdfs:
            return False
        
        if len(pdfs) == 1:
            pdf = pdfs[0]
            await update.message.reply_text(
                f"📄 {pdf['title']}\n\n"
                f"Téléchargement en cours..."
            )
            await context.bot.send_document(
                chat_id=update.message.chat_id,
                document=pdf['public_url'],
                caption=pdf.get("description", "")
            )
            return True
        
        message = f"📄 J'ai trouvé plusieurs documents pour « {query} » :\n\n"
        for i, pdf in enumerate(pdfs[:5], 1):
            message += f"{i}. {pdf['title']}\n"
            if pdf.get("description"):
                message += f"   📝 {pdf['description'][:50]}...\n"
        
        message += f"\n💡 Dis-moi le numéro pour télécharger"
        
        await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
        
        self._pending_pdf_downloads[update.effective_user.id] = [p["id"] for p in pdfs[:5]]
        return True

    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle incoming photos - process with AI Vision."""
        user = update.effective_user
        message = update.message

        if not self._is_user_allowed(user.id):
            await message.reply_text("⛔ Vous n'êtes pas autorisé à utiliser ce bot.")
            return

        if not self.rate_limiter.is_allowed(user.id):
            reset_time = self.rate_limiter.get_reset_time(user.id)
            await message.reply_text(f"⚠️ Trop de messages ! Réessayez dans {int(reset_time)}s.")
            return

        # Get the highest quality photo
        photo = message.photo[-1]
        caption = message.caption or "Analyse cette image."

        logger.info(f"Photo from {user.id} with caption: {caption[:100]}...")
        await context.bot.send_chat_action(chat_id=message.chat_id, action=ChatAction.TYPING)

        try:
            # Download photo to memory
            photo_file = await context.bot.get_file(photo.file_id)
            import io
            import base64
            
            photo_bytes = io.BytesIO()
            await photo_file.download_to_memory(photo_bytes)
            photo_bytes.seek(0)
            
            # Convert to base64
            base64_image = base64.b64encode(photo_bytes.read()).decode('utf-8')
            
            # Prepare multi-modal content
            content = [
                {"type": "text", "text": caption},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{base64_image}"
                    }
                }
            ]
            
            # Add to conversation history (we store the multi-modal content)
            self.conversations.add_user_message(user.id, content)
            
            # Get full context
            user_memories = self.memory.get_all_memories(user.id)
            user_plans = self.memory.get_all_study_plans(user.id)
            messages = self.conversations.get_messages(user.id, user_memory=user_memories, study_plans=user_plans)
            
            # Call Ollama
            response_dict = await self.ollama.chat(messages)
            ai_text = response_dict.get("content", "Désolé, je n'ai pas pu analyser cette image.")
            
            self.conversations.add_assistant_message(user.id, ai_text)
            await self._send_long_message(message, ai_text)
            
        except Exception as e:
            logger.error(f"Error handling photo: {e}", exc_info=True)
            await message.reply_text("❌ Une erreur s'est produite lors de l'analyse de l'image.")

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle incoming text messages - main AI conversation handler."""
        user = update.effective_user
        message = update.message

        if not self._is_user_allowed(user.id):
            await message.reply_text("⛔ Vous n'êtes pas autorisé à utiliser ce bot.")
            return

        if not self.rate_limiter.is_allowed(user.id):
            reset_time = self.rate_limiter.get_reset_time(user.id)
            await message.reply_text(f"⚠️ Trop de messages ! Réessayez dans {int(reset_time)}s.")
            return

        user_text = message.text
        if not user_text or not user_text.strip():
            return

        logger.info(f"Message from {user.id}: {user_text[:100]}...")

        if not hasattr(self, '_pending_pdf_downloads'):
            self._pending_pdf_downloads = {}
        
        if hasattr(self, '_pending_pdf_downloads') and user.id in self._pending_pdf_downloads:
            try:
                index = int(user_text.strip()) - 1
                pdf_ids = self._pending_pdf_downloads[user.id]
                if 0 <= index < len(pdf_ids):
                    pdf = self.pdf_manager.get_pdf_by_id(pdf_ids[index])
                    if pdf:
                        await context.bot.send_document(
                            chat_id=message.chat_id,
                            document=pdf['public_url'],
                            caption=f"📄 {pdf['title']}"
                        )
                        del self._pending_pdf_downloads[user.id]
                        return
            except (ValueError, IndexError):
                pass

        is_pdf, query = self._is_pdf_request(user_text)
        if is_pdf and self.pdf_manager.enabled:
            handled = await self._handle_pdf_request(update, context, query)
            if handled:
                return

        await context.bot.send_chat_action(chat_id=message.chat_id, action=ChatAction.TYPING)
        self.conversations.add_user_message(user.id, user_text)

        try:
            user_memories = self.memory.get_all_memories(user.id)
            user_plans = self.memory.get_all_study_plans(user.id)
            
            messages = self.conversations.get_messages(user.id, user_memory=user_memories, study_plans=user_plans)
            
            available_pdfs = self.pdf_manager.get_all_pdfs() if self.pdf_manager.enabled else []
            tools = []
            if self.pdf_manager.enabled:
                tools.append(get_pdf_tool_definition(available_pdfs))
                tools.append(get_create_pdf_tool_definition())
                tools.append(get_delete_pdf_tool_definition(available_pdfs))
                
                # Inject PDF context with user profile for personalized content
                pdf_context = get_pdf_system_context(user_memories, user_plans)
                messages = [messages[0]] + [{"role": "system", "content": pdf_context}] + messages[1:]
            
            # Homework tools
            if self.homework.enabled:
                tools.extend(get_homework_tools())
            
            response_dict = await self.ollama.chat(messages, tools=tools if tools else None)
            
            ai_text = response_dict.get("content", "")
            
            if response_dict.get("tool_calls"):
                import json
                
                func_response = ""
                
                for tool_call in response_dict["tool_calls"]:
                    func_name = tool_call["function"]["name"]
                    args = json.loads(tool_call["function"]["arguments"])
                    func_response = ""
                    
                    if func_name == "send_pdf":
                        query = args.get("query", "")
                        pdfs = self.pdf_manager.search_pdfs(query)
                        
                        if not pdfs:
                            func_response = "Aucun PDF trouvé pour cette recherche."
                        elif len(pdfs) == 1:
                            pdf = pdfs[0]
                            await context.bot.send_document(
                                chat_id=message.chat_id,
                                document=pdf['public_url'],
                                caption=f"📄 {pdf['title']}"
                            )
                            func_response = f"PDF envoyé: {pdf['title']}"
                        else:
                            func_response = "Plusieurs PDFs trouvés: " + ", ".join([p['title'] for p in pdfs])
                    
                    elif func_name == "create_pdf":
                        title = args.get("title", "Document")
                        text_content = args.get("text_content") or args.get("content", "")
                        latex_content = args.get("latex_content")
                        
                        if not text_content:
                            func_response = "ERROR: No content provided"
                        else:
                            await context.bot.send_chat_action(chat_id=message.chat_id, action=ChatAction.UPLOAD_DOCUMENT)
                            
                            result = self.pdf_manager.create_pdf(title, latex_content=latex_content, text_content=text_content)
                            
                            if result and result.get("success"):
                                try:
                                    import io
                                    pdf_bytes = result.get("pdf_bytes")
                                    if pdf_bytes:
                                        safe_name = re.sub(r'[^a-zA-Z0-9_ -]', '_', title) + ".pdf"
                                        await context.bot.send_document(
                                            chat_id=message.chat_id,
                                            document=io.BytesIO(pdf_bytes),
                                            filename=safe_name,
                                            caption=f"📄 {result['title']}"
                                        )
                                    else:
                                        await context.bot.send_document(
                                            chat_id=message.chat_id,
                                            document=result['public_url'],
                                            caption=f"📄 {result['title']}"
                                        )
                                    func_response = f"PDF '{title}' créé et envoyé avec succès!"
                                except Exception as e:
                                    logger.warning(f"Could not send PDF to user: {e}")
                                    func_response = f"PDF créé mais erreur d'envoi: {e}"
                            elif result and result.get("error"):
                                func_response = f"Erreur: {result['error']}"
                                await message.reply_text(f"❌ {result['error']}")
                            else:
                                func_response = "Erreur inconnue lors de la création du PDF"
                    
                    elif func_name == "delete_pdf":
                        title_query = args.get("title_query", "")
                        confirmed = args.get("confirmed", False)
                        
                        if not confirmed:
                            # AI should ask for confirmation first
                            pdf = self.pdf_manager.get_pdf_by_title(title_query)
                            if pdf:
                                func_response = f"PDF trouvé : '{pdf['title']}'. Demande confirmation à l'utilisateur avant de supprimer."
                            else:
                                func_response = f"Aucun PDF trouvé pour '{title_query}'"
                        else:
                            result = self.pdf_manager.delete_pdf(title_query)
                            if result and result.get("success"):
                                func_response = result["message"]
                            elif result and result.get("error"):
                                func_response = f"Erreur: {result['error']}"
                            else:
                                func_response = "Erreur lors de la suppression"
                    
                    # ===== HOMEWORK TOOLS =====
                    elif func_name == "add_homework":
                        result = self.homework.add(
                            user_id=user.id,
                            subject=args.get("subject", ""),
                            description=args.get("description", ""),
                            due_date=args.get("due_date", "")
                        )
                        func_response = result.get("message") or result.get("error", "Erreur")
                    
                    elif func_name == "list_homework":
                        result = self.homework.list_all(user_id=user.id)
                        func_response = result.get("message") or result.get("error", "Erreur")
                    
                    elif func_name == "mark_homework_done":
                        result = self.homework.mark_done(
                            homework_id=args.get("homework_id", 0),
                            user_id=user.id
                        )
                        func_response = result.get("message") or result.get("error", "Erreur")
                    
                    elif func_name == "delete_homework":
                        result = self.homework.delete(
                            homework_id=args.get("homework_id", 0),
                            user_id=user.id
                        )
                        func_response = result.get("message") or result.get("error", "Erreur")

                    else:
                        func_response = "Fonction inconnue"
                    
                    messages.append(response_dict)
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "content": func_response
                    })
                
                final_response = await self.ollama.chat(messages, tools=None)
                ai_text = final_response.get("content", func_response) if func_response else final_response.get("content", "")
            else:
                ai_text = response_dict.get("content", "Désolé, je n'ai pas pu formuler de réponse.")
            
            if not ai_text:
                ai_text = "Désolé, je n'ai pas pu traiter votre demande."
            
            self.conversations.add_assistant_message(user.id, ai_text)
            await self._send_long_message(message, ai_text)
            
            recent_history = self.conversations.get_messages(user.id)[-4:]
            asyncio.create_task(self._process_passive_memory(user.id, recent_history, user_memories, user_text))

        except OllamaError as e:
            if len(self.conversations._conversations[user.id]) > 0:
                self.conversations._conversations[user.id].pop()
            await message.reply_text(str(e))

        except Exception as e:
            logger.error(f"Unexpected error handling message: {e}", exc_info=True)
            if len(self.conversations._conversations[user.id]) > 0:
                self.conversations._conversations[user.id].pop()
            await message.reply_text("❌ Une erreur inattendue s'est produite. Réessayez plus tard.")


    async def _process_passive_memory(self, user_id: int, recent_history: list[dict], current_memories: str, last_user_message: str):
        """Silently analyzes recent conversation to extract personal facts and study plans."""
        try:
            analysis_prompt = (
                "Tu es un agent d'analyse d'arrière-plan analysant une conversation entre un utilisateur et son coéquipier IA.\n"
                "La mémoire de l'utilisateur contient déjà :\n"
                f"{current_memories}\n\n"
                "Ta mission est d'extraire DEUX choses : \n"
                "1. Si l'utilisateur donne une NOUVELLE information personnelle (identité, préférences, etc.), "
                "déclare-la sur une ligne commençant par 'FAIT: ' (ex: 'FAIT: L'utilisateur fait du sport le jeudi'). \n"
                "2. Si l'utilisateur vient de VALIDER ou D'ACCEPTER un programme de révision proposé par l'IA ou lui-même (ex: date d'examen ou sessions planifiées), "
                "extrais-le et déclare-le sur une ligne commençant par 'PLANNING: ' (ex: 'PLANNING: Révision de Mathématiques (Chap 1-2) le 12 Mars à 18h').\n"
                "S'il n'y a rien de pertinent ou de nouveau, réponds uniquement 'NONE'. Ne réponds rien d'autre."
            )
            
            # Format recent history into string for context
            history_str = ""
            for msg in recent_history:
                if msg["role"] != "system":
                    role = "Utilisateur" if msg["role"] == "user" else "IA"
                    history_str += f"{role}: {msg['content']}\n\n"
            
            messages = [
                {"role": "system", "content": analysis_prompt},
                {"role": "user", "content": f"Voici les derniers échanges à analyser :\n{history_str}"}
            ]
            
            resp = await self.ollama.chat(messages, max_tokens=250)
            analysis = resp.get("content", "").strip()
            
            logger.debug(f"Passive analysis for user {user_id}:\n{analysis}")
            
            if analysis and analysis.upper() != "NONE":
                for line in analysis.split("\n"):
                    line = line.strip()
                    if line.upper().startswith("FAIT:"):
                        fact = line[5:].strip()
                        if fact:
                            logger.info(f"Learned fact: {fact}")
                            self.memory.add_memory(user_id, fact)
                    elif line.upper().startswith("PLANNING:"):
                        plan = line[9:].strip()
                        if plan:
                            logger.info(f"Learned study plan: {plan}")
                            self.memory.add_study_plan(user_id, plan)
                
        except Exception as e:
            logger.error(f"Failed passive memory processing: {e}", exc_info=True)


    async def _send_long_message(self, message, text: str) -> None:
        max_len = self.config.max_response_length
        try:
            if len(text) <= max_len:
                await message.reply_text(text, parse_mode=ParseMode.HTML)
                return

            parts = self._split_text(text, max_len)
            for i, part in enumerate(parts):
                prefix = f"📄 ({i+1}/{len(parts)})\n\n" if len(parts) > 1 else ""
                await message.reply_text(prefix + part, parse_mode=ParseMode.HTML)
        except Exception as e:
            logger.warning(f"HTML parsing failed, falling back to plain text: {e}")
            if len(text) <= max_len:
                await message.reply_text(text)
            else:
                parts = self._split_text(text, max_len)
                for i, part in enumerate(parts):
                    await message.reply_text(part)

    def _split_text(self, text: str, max_len: int) -> list[str]:
        parts = []
        current = ""
        for line in text.split("\n"):
            if len(current) + len(line) + 1 > max_len:
                if current: parts.append(current.strip())
                current = line
            else:
                current += "\n" + line if current else line
        if current.strip(): parts.append(current.strip())
        return parts

    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        logger.error(f"Update {update} caused error: {context.error}", exc_info=context.error)
