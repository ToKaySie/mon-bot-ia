from supabase import create_client, Client
import re
import logging
import unicodedata
import os
from datetime import datetime
from fpdf import FPDF

logger = logging.getLogger(__name__)

FONTS_DIR = os.path.join(os.path.dirname(__file__), "..", "fonts")


def get_pdf_tool_definition(available_pdfs: list = None) -> dict:
    """Get PDF send tool definition with available PDFs."""
    
    if available_pdfs:
        pdf_list = "\n".join([f"- {p['title']}" for p in available_pdfs])
        send_desc = f"""Recherche et envoie un document PDF existant à l'utilisateur.

Documents disponibles:
{pdf_list}

Utilise cette fonction quand l'utilisateur demande un PDF existant."""
    else:
        send_desc = """Recherche et envoie un document PDF à l'utilisateur."""

    return {
        "type": "function",
        "function": {
            "name": "send_pdf",
            "description": send_desc,
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Mot-clé pour identifier quel PDF existant envoyer"
                    }
                },
                "required": ["query"]
            }
        }
    }


def get_create_pdf_tool_definition() -> dict:
    """Get the create_pdf tool definition."""
    return {
        "type": "function",
        "function": {
            "name": "create_pdf",
            "description": """Crée un nouveau document PDF. UTILISE TOUJOURS cette fonction quand l'utilisateur demande de créer un PDF, un cours, une fiche ou un document.

RÈGLES STRICTES:
1. APPELLE TOUJOURS cette fonction - NE JAMAIS écrire le contenu dans ta réponse
2. Mets TOUT le contenu dans text_content, RIEN dans ta réponse texte
3. Après l'appel, réponds juste "📄 PDF créé et envoyé !"

FORMAT DU CONTENU (text_content):
Utilise ce formatage Markdown précis:
- # Titre principal (sera en gros, gras)
- ## SECTION EN MAJUSCULES (sera avec une ligne de séparation)
- ### Sous-titre (sera en gras normal)
- **Mot-clé** : description (pour les métadonnées, définitions)
- Texte normal pour les paragraphes
- - pour les listes à puces
- 1. pour les listes numérotées
- --- pour une ligne de séparation horizontale
- Lignes vides pour séparer les paragraphes

QUALITÉ DU CONTENU:
- Le contenu doit être APPROFONDI, DÉTAILLÉ et STRUCTURÉ
- Pas de généralités superficielles : va en profondeur
- Inclus des exemples concrets, des citations, des analyses
- Structure logique avec parties et sous-parties claires
- Adapte le niveau au profil de l'utilisateur""",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Titre du document PDF"
                    },
                    "text_content": {
                        "type": "string",
                        "description": "Contenu complet et détaillé du document en Markdown"
                    }
                },
                "required": ["title", "text_content"]
            }
        }
    }


def get_pdf_system_context(user_memories: str = "", study_plans: str = "") -> str:
    """Build a system context for PDF generation based on user info."""
    context = """
INSTRUCTIONS POUR LA CRÉATION DE PDF:
Tu es un expert pédagogue. Quand on te demande un PDF/cours/fiche/document, tu DOIS:

1. APPELER la fonction create_pdf avec un contenu COMPLET et APPROFONDI
2. NE JAMAIS copier le contenu dans ta réponse - tout va dans create_pdf
3. Répondre simplement "📄 PDF créé et envoyé !" après l'appel

QUALITÉ ATTENDUE:
- Contenu académique de haut niveau, pas de survol superficiel
- Structure claire avec titres, sous-titres, paragraphes développés
- Exemples concrets, citations pertinentes, analyses détaillées
- Définitions précises des termes clés
- Synthèses et points à retenir
- Adapté au niveau et aux besoins de l'utilisateur
"""
    
    if user_memories:
        context += f"""
PROFIL DE L'UTILISATEUR (adapte le contenu en conséquence):
{user_memories}
"""
    
    if study_plans:
        context += f"""
PLANNINGS DE RÉVISION EN COURS:
{study_plans}
"""
    
    return context


class AcademicPDF(FPDF):
    """PDF with clean academic style matching the reference design."""
    
    def __init__(self):
        super().__init__()
        # Serif fonts for academic look
        self.add_font("Serif", "", os.path.join(FONTS_DIR, "DejaVuSerif.ttf"), uni=True)
        self.add_font("Serif", "B", os.path.join(FONTS_DIR, "DejaVuSerif-Bold.ttf"), uni=True)
        self.add_font("Serif", "I", os.path.join(FONTS_DIR, "DejaVuSerif-Italic.ttf"), uni=True)
        self.add_font("Serif", "BI", os.path.join(FONTS_DIR, "DejaVuSerif-BoldItalic.ttf"), uni=True)
        # Sans-serif for headers
        self.add_font("Sans", "", os.path.join(FONTS_DIR, "DejaVuSans.ttf"), uni=True)
        self.add_font("Sans", "B", os.path.join(FONTS_DIR, "DejaVuSans-Bold.ttf"), uni=True)
        self.add_font("Sans", "I", os.path.join(FONTS_DIR, "DejaVuSans-Oblique.ttf"), uni=True)

    def header(self):
        pass

    def footer(self):
        self.set_y(-15)
        self.set_font("Serif", "I", 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 10, f"{self.page_no()} / {{nb}}", align="C")


class PDFManager:
    def __init__(self, supabase_url: str, supabase_key: str, service_key: str = None):
        self.supabase_url = supabase_url
        self.supabase_key = supabase_key
        self.service_key = service_key
        self.bucket_name = "pdfs"
        self.enabled = bool(supabase_url and supabase_key)
        
        if self.enabled:
            self.client: Client = create_client(supabase_url, supabase_key)
            if service_key:
                self.client_admin = create_client(supabase_url, service_key)
            else:
                self.client_admin = self.client
        else:
            self.client = None
            self.client_admin = None

    def _get_public_url(self, file_path: str) -> str:
        return f"{self.supabase_url}/storage/v1/object/public/{self.bucket_name}/{file_path}"

    def _extract_title(self, file_path: str) -> str:
        filename = file_path.split("/")[-1]
        name = re.sub(r'^\d{8}_\d{6}_', '', filename)
        name = name.replace('.pdf', '').replace('_', ' ').replace('-', ' ')
        return name

    def _safe_filename(self, title: str) -> str:
        safe = unicodedata.normalize('NFKD', title).encode('ascii', 'ignore').decode('ascii')
        safe = re.sub(r'[^a-zA-Z0-9_-]', '_', safe)
        safe = re.sub(r'_+', '_', safe).strip('_')
        return safe or "document"

    def _draw_hr(self, pdf: FPDF, thickness: float = 0.3):
        """Draw a horizontal rule."""
        pdf.set_draw_color(60, 60, 60)
        pdf.set_line_width(thickness)
        pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
        pdf.ln(4)

    def _write_rich_line(self, pdf: FPDF, text: str, font_family: str = "Serif", 
                          font_size: int = 10, max_width: float = None):
        """Write a single line/paragraph with **bold** and *italic* inline formatting."""
        if max_width is None:
            max_width = pdf.w - pdf.l_margin - pdf.r_margin
        
        parts = re.split(r'(\*\*\*.*?\*\*\*|\*\*.*?\*\*|\*.*?\*)', text)
        
        x_start = pdf.get_x()
        current_x = x_start
        line_height = font_size * 0.55

        for part in parts:
            if not part:
                continue
            
            if part.startswith('***') and part.endswith('***'):
                pdf.set_font(font_family, "BI", font_size)
                part = part[3:-3]
            elif part.startswith('**') and part.endswith('**'):
                pdf.set_font(font_family, "B", font_size)
                part = part[2:-2]
            elif part.startswith('*') and part.endswith('*'):
                pdf.set_font(font_family, "I", font_size)
                part = part[1:-1]
            else:
                pdf.set_font(font_family, "", font_size)
            
            words = part.split(' ')
            for j, word in enumerate(words):
                if j > 0:
                    word = ' ' + word
                w = pdf.get_string_width(word)
                if current_x + w > x_start + max_width and current_x > x_start:
                    pdf.ln(line_height)
                    pdf.set_x(x_start)
                    current_x = x_start
                    word = word.lstrip()
                    w = pdf.get_string_width(word)
                
                pdf.set_x(current_x)
                pdf.cell(w, line_height, word)
                current_x += w
        
        pdf.ln(line_height)
        pdf.set_font(font_family, "", font_size)

    def _markdown_to_pdf(self, text: str, title: str) -> bytes | None:
        """Convert Markdown text to a clean academic-style PDF."""
        try:
            pdf = AcademicPDF()
            pdf.alias_nb_pages()
            pdf.set_auto_page_break(auto=True, margin=20)
            pdf.set_margins(25, 25, 25)
            pdf.add_page()
            
            TEXT_COLOR = (30, 30, 30)
            BODY_SIZE = 10
            content_width = pdf.w - pdf.l_margin - pdf.r_margin

            # ===== TITLE =====
            pdf.set_text_color(*TEXT_COLOR)
            pdf.set_font("Serif", "B", 22)
            pdf.ln(5)
            pdf.multi_cell(content_width, 11, title, align="L")
            pdf.ln(2)
            
            # ===== PARSE CONTENT =====
            lines = text.strip().split('\n')
            i = 0
            first_h1_done = False
            
            while i < len(lines):
                line = lines[i].rstrip()
                stripped = line.strip()
                
                # Empty line
                if not stripped:
                    pdf.ln(2)
                    i += 1
                    continue
                
                # Horizontal rule: ---
                if stripped in ('---', '***', '___'):
                    pdf.ln(2)
                    self._draw_hr(pdf, 0.3)
                    pdf.ln(1)
                    i += 1
                    continue
                
                # H1: # Title (used as subtitle / section intro)
                if stripped.startswith('# ') and not stripped.startswith('## '):
                    heading = stripped[2:].strip()
                    heading = re.sub(r'\*\*(.*?)\*\*', r'\1', heading)
                    
                    if not first_h1_done:
                        # First H1 = subtitle with guillemets style
                        pdf.set_font("Sans", "I", 13)
                        pdf.set_text_color(*TEXT_COLOR)
                        pdf.multi_cell(content_width, 8, heading, align="L")
                        pdf.ln(3)
                        self._draw_hr(pdf, 0.5)
                        pdf.ln(2)
                        first_h1_done = True
                    else:
                        pdf.ln(4)
                        pdf.set_font("Serif", "B", 16)
                        pdf.set_text_color(*TEXT_COLOR)
                        pdf.multi_cell(content_width, 9, heading, align="L")
                        pdf.ln(2)
                    i += 1
                    continue
                
                # H2: ## SECTION TITLE (uppercase, with line underneath)
                if stripped.startswith('## ') and not stripped.startswith('### '):
                    heading = stripped[3:].strip()
                    heading = re.sub(r'\*\*(.*?)\*\*', r'\1', heading)
                    
                    pdf.ln(6)
                    pdf.set_font("Sans", "B", 13)
                    pdf.set_text_color(*TEXT_COLOR)
                    pdf.multi_cell(content_width, 8, heading, align="L")
                    pdf.ln(1)
                    self._draw_hr(pdf, 0.4)
                    pdf.ln(2)
                    i += 1
                    continue
                
                # H3: ### Sub-title (bold, normal)
                if stripped.startswith('### '):
                    heading = stripped[4:].strip()
                    heading = re.sub(r'\*\*(.*?)\*\*', r'\1', heading)
                    
                    pdf.ln(4)
                    pdf.set_font("Sans", "B", 11)
                    pdf.set_text_color(*TEXT_COLOR)
                    pdf.multi_cell(content_width, 7, heading, align="L")
                    pdf.ln(2)
                    i += 1
                    continue
                
                # Bullet list
                if stripped.startswith(('- ', '* ', '• ')):
                    pdf.set_text_color(*TEXT_COLOR)
                    item_text = stripped[2:].strip()
                    
                    bullet_x = pdf.l_margin + 5
                    text_x = bullet_x + 6
                    item_width = content_width - 11
                    
                    pdf.set_font("Serif", "", BODY_SIZE)
                    pdf.set_x(bullet_x)
                    pdf.cell(5, 5.5, "–")
                    pdf.set_x(text_x)
                    self._write_rich_line(pdf, item_text, "Serif", BODY_SIZE, item_width)
                    pdf.ln(0.5)
                    i += 1
                    continue
                
                # Numbered list
                if re.match(r'^\d+[\.\)] ', stripped):
                    pdf.set_text_color(*TEXT_COLOR)
                    match = re.match(r'^(\d+[\.\)] )(.*)', stripped)
                    number = match.group(1)
                    item_text = match.group(2).strip()
                    
                    num_x = pdf.l_margin + 5
                    text_x = num_x + 8
                    item_width = content_width - 13
                    
                    pdf.set_font("Serif", "B", BODY_SIZE)
                    pdf.set_x(num_x)
                    pdf.cell(8, 5.5, number)
                    pdf.set_font("Serif", "", BODY_SIZE)
                    pdf.set_x(text_x)
                    self._write_rich_line(pdf, item_text, "Serif", BODY_SIZE, item_width)
                    pdf.ln(0.5)
                    i += 1
                    continue
                
                # Regular paragraph
                pdf.set_text_color(*TEXT_COLOR)
                pdf.set_x(pdf.l_margin)
                self._write_rich_line(pdf, stripped, "Serif", BODY_SIZE, content_width)
                pdf.ln(1.5)
                i += 1

            return bytes(pdf.output())
            
        except Exception as e:
            logger.error(f"PDF generation error: {e}", exc_info=True)
            return None

    def create_pdf(self, title: str, latex_content: str = None, text_content: str = None) -> dict | None:
        """Create a PDF from text content and upload to Supabase storage + table."""
        if not self.enabled:
            return {"error": "Supabase non configuré"}
        
        if not text_content and not latex_content:
            return {"error": "Aucun contenu fourni"}
        
        content = text_content or latex_content or ""
        
        logger.info(f"Creating PDF: '{title}' ({len(content)} chars)")
        
        pdf_bytes = self._markdown_to_pdf(content, title)
        
        if not pdf_bytes:
            return {"error": "Échec de la génération du PDF"}
        
        logger.info(f"PDF generated: {len(pdf_bytes)} bytes")
        
        try:
            safe_title = self._safe_filename(title)
            file_path = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{safe_title}.pdf"
            
            self.client_admin.storage.from_(self.bucket_name).upload(
                file=pdf_bytes,
                path=file_path,
                file_options={"content-type": "application/pdf"}
            )
            
            public_url = self._get_public_url(file_path)
            
            try:
                self.client_admin.table("pdfs").insert({
                    "title": title,
                    "description": "Généré par le bot IA",
                    "file_path": file_path,
                    "public_url": public_url,
                    "file_size": len(pdf_bytes),
                    "uploaded_at": datetime.now().isoformat()
                }).execute()
            except Exception as e:
                logger.warning(f"Could not save to pdfs table: {e}")
            
            return {
                "success": True,
                "title": title,
                "file_path": file_path,
                "public_url": public_url,
                "pdf_bytes": pdf_bytes,
                "message": f"PDF '{title}' créé et ajouté à la bibliothèque!"
            }
            
        except Exception as e:
            logger.error(f"Error uploading PDF: {e}", exc_info=True)
            return {"error": f"Erreur lors de l'upload: {str(e)}"}

    def get_all_pdfs(self):
        if not self.enabled:
            return []
        try:
            client = self.client_admin if hasattr(self, 'client_admin') and self.client_admin else self.client
            response = client.storage.from_(self.bucket_name).list()
            if not response:
                return []
            pdfs = []
            for f in response:
                file_path = f.get("name") or f.get("id")
                if file_path and str(file_path).endswith('.pdf'):
                    pdfs.append({
                        "id": f.get("id"),
                        "title": self._extract_title(file_path),
                        "file_path": file_path,
                        "public_url": self._get_public_url(file_path),
                        "file_size": f.get("size", 0),
                    })
            return pdfs
        except Exception as e:
            logger.error(f"Error listing PDFs: {e}")
            return []

    def search_pdfs(self, query: str = "", limit: int = 10):
        all_pdfs = self.get_all_pdfs()
        if not query:
            return all_pdfs[:limit]
        query_lower = query.lower()
        return [p for p in all_pdfs if query_lower in p['title'].lower()][:limit]

    def get_pdf_by_id(self, pdf_id: str):
        for pdf in self.get_all_pdfs():
            if pdf.get("id") == pdf_id:
                return pdf
        return None

    def get_pdf_by_title(self, title_query: str):
        all_pdfs = self.get_all_pdfs()
        if not title_query:
            return all_pdfs[0] if all_pdfs else None
        tq = title_query.lower()
        for pdf in all_pdfs:
            if tq in pdf['title'].lower():
                return pdf
        return None
