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
    """Get PDF send tool definition."""
    return {
        "type": "function",
        "function": {
            "name": "send_pdf",
            "description": "Recherche et envoie un document PDF existant de la bibliothèque à l'utilisateur.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Mot-clé ou titre pour identifier quel PDF existant envoyer"
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
            "description": "Crée un nouveau document PDF structuré (cours, fiche, exercices). Tout le contenu doit être mis dans text_content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Titre du document PDF"
                    },
                    "text_content": {
                        "type": "string",
                        "description": "Contenu complet, détaillé et structuré en Markdown avec LaTeX et tableaux."
                    }
                },
                "required": ["title", "text_content"]
            }
        }
    }


def get_delete_pdf_tool_definition(available_pdfs: list = None) -> dict:
    """Get the delete_pdf tool definition."""
    return {
        "type": "function",
        "function": {
            "name": "delete_pdf",
            "description": "Supprime un document PDF de la bibliothèque par son titre ou un mot-clé.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title_query": {
                        "type": "string",
                        "description": "Titre ou mot-clé du PDF à supprimer"
                    },
                    "confirmed": {
                        "type": "boolean",
                        "description": "True si l'utilisateur a explicitement confirmé la suppression"
                    }
                },
                "required": ["title_query", "confirmed"]
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

    def _render_formula(self, pdf: FPDF, formula: str, is_block: bool = True):
        """Render a LaTeX formula using CodeCogs API and insert as image."""
        import urllib.parse
        import urllib.request
        import io
        
        # Cleanup formula
        formula = formula.strip()
        if formula.startswith('$$') and formula.endswith('$$'):
            formula = formula[2:-2].strip()
        elif formula.startswith('$') and formula.endswith('$'):
            formula = formula[1:-1].strip()
            
        try:
            # CodeCogs URL for PNG rendering (300 DPI for high quality)
            # Using \bg_white to ensure visibility on white PDF
            encoded_formula = urllib.parse.quote(r"\bg_white \huge " + formula)
            url = f"https://latex.codecogs.com/png.latex?{encoded_formula}"
            
            with urllib.request.urlopen(url, timeout=5) as response:
                img_data = response.read()
                img_file = io.BytesIO(img_data)
                
                # If block formula, center it
                if is_block:
                    pdf.ln(2)
                    # We don't know the image size yet, fpdf2 handles it
                    # To center, we calculate width after placing or use a fixed width approach
                    # Simpler: just use multi_cell alignment or manual x calculation
                    curr_y = pdf.get_y()
                    # Check if we need a new page
                    if curr_y > 250: pdf.add_page()
                    
                    # Try to center the image (rough estimation)
                    pdf.image(img_file, x=pdf.w/2 - 20, w=40) 
                    pdf.ln(2)
                else:
                    # Inline formula - more complex with fpdf2, we'll just treat them as small blocks for now
                    pdf.image(img_file, h=pdf.font_size * 0.8)
        except Exception as e:
            logger.warning(f"Formula rendering failed: {e}")
            pdf.set_font("Courier", "I", 10)
            pdf.cell(0, 10, f" [Eq: {formula}] ", ln=True)

    def _write_rich_line(self, pdf: FPDF, text: str, font_family: str = "Serif", 
                          font_size: int = 10, max_width: float = None):
        """Write a single line/paragraph with **bold**, *italic* and $inline math$."""
        if max_width is None:
            max_width = pdf.w - pdf.l_margin - pdf.r_margin
        
        # Detect inline math $...$
        # Regex to split by bold, italic AND inline math
        parts = re.split(r'(\*\*\*.*?\*\*\*|\*\*.*?\*\*|\*.*?\*|\$.*?\$)', text)
        
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
            elif part.startswith('$') and part.endswith('$'):
                # Inline Math - Render as image if possible, or just Courier
                self._render_formula(pdf, part, is_block=False)
                current_x = pdf.get_x()
                continue
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
        """Convert Markdown text to a clean academic-style PDF with Math and Tables."""
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
                
                # Block Formula: $$ ... $$
                if stripped.startswith('$$') and stripped.endswith('$$'):
                    self._render_formula(pdf, stripped, is_block=True)
                    i += 1
                    continue
                
                # Multi-line Block Formula
                if stripped.startswith('$$') and not stripped.endswith('$$'):
                    formula_lines = [stripped]
                    i += 1
                    while i < len(lines) and not lines[i].strip().endswith('$$'):
                        formula_lines.append(lines[i].strip())
                        i += 1
                    if i < len(lines):
                        formula_lines.append(lines[i].strip())
                        i += 1
                    self._render_formula(pdf, "\n".join(formula_lines), is_block=True)
                    continue

                # Tables: | col | col |
                if stripped.startswith('|') and i + 1 < len(lines) and '|---' in lines[i+1]:
                    # Table detection
                    table_data = []
                    # Header
                    headers = [c.strip() for c in stripped.split('|') if c.strip()]
                    table_data.append(headers)
                    # Skip separator line
                    i += 2
                    # Rows
                    while i < len(lines) and lines[i].strip().startswith('|'):
                        row = [c.strip() for c in lines[i].split('|') if c.strip()]
                        if row: table_data.append(row)
                        i += 1
                    
                    # Render Table using fpdf2 table()
                    pdf.ln(4)
                    with pdf.table(
                        borders_layout="HORIZONTAL_LINES",
                        cell_fill_color=245,
                        cell_fill_mode="ROWS",
                        line_height=pdf.font_size * 1.5,
                        text_align="CENTER",
                        width=content_width
                    ) as t:
                        for row_data in table_data:
                            row = t.row()
                            for datum in row_data:
                                row.cell(datum)
                    pdf.ln(4)
                    continue

                # Horizontal rule: ---
                if stripped in ('---', '***', '___'):
                    pdf.ln(2)
                    self._draw_hr(pdf, 0.3)
                    pdf.ln(1)
                    i += 1
                    continue
                
                # H1: # Title
                if stripped.startswith('# ') and not stripped.startswith('## '):
                    heading = stripped[2:].strip()
                    heading = re.sub(r'\*\*(.*?)\*\*', r'\1', heading)
                    
                    if not first_h1_done:
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
                
                # H2: ## SECTION TITLE
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
                
                # H3: ### Sub-title
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

    def delete_pdf(self, title_query: str) -> dict:
        """Delete a PDF from storage and database by title."""
        if not self.enabled:
            return {"error": "Supabase non configuré"}

        pdf = self.get_pdf_by_title(title_query)
        if not pdf:
            return {"error": f"Aucun PDF trouvé pour '{title_query}'"}

        title = pdf['title']
        file_path = pdf['file_path']
        errors = []

        # Delete from storage
        try:
            self.client_admin.storage.from_(self.bucket_name).remove([file_path])
            logger.info(f"Deleted from storage: {file_path}")
        except Exception as e:
            logger.error(f"Error deleting from storage: {e}")
            errors.append(f"storage: {e}")

        # Delete from pdfs table
        try:
            self.client_admin.table("pdfs").delete().eq("file_path", file_path).execute()
            logger.info(f"Deleted from pdfs table: {file_path}")
        except Exception as e:
            logger.error(f"Error deleting from table: {e}")
            errors.append(f"table: {e}")

        if errors:
            return {"success": True, "title": title, "message": f"PDF '{title}' supprimé (avec avertissements: {', '.join(errors)})"}

        return {"success": True, "title": title, "message": f"PDF '{title}' supprimé de la bibliothèque"}
