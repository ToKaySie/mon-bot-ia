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


def download_fonts():
    """Download Roboto Slab fonts if they don't exist."""
    import urllib.request
    
    fonts = {
        "RobotoSlab-Regular.ttf": "https://github.com/google/fonts/raw/main/apache/robotoslab/static/RobotoSlab-Regular.ttf",
        "RobotoSlab-Bold.ttf": "https://github.com/google/fonts/raw/main/apache/robotoslab/static/RobotoSlab-Bold.ttf"
    }
    
    if not os.path.exists(FONTS_DIR):
        os.makedirs(FONTS_DIR)
        
    for name, url in fonts.items():
        path = os.path.join(FONTS_DIR, name)
        if not os.path.exists(path):
            try:
                logger.info(f"Downloading font {name}...")
                urllib.request.urlretrieve(url, path)
            except Exception as e:
                logger.error(f"Failed to download font {name}: {e}")

# Call downloader on import
download_fonts()

class AcademicPDF(FPDF):
    """PDF with Roboto Slab academic style."""
    
    def __init__(self):
        super().__init__()
        # Roboto Slab as the new primary font
        reg_path = os.path.join(FONTS_DIR, "RobotoSlab-Regular.ttf")
        bold_path = os.path.join(FONTS_DIR, "RobotoSlab-Bold.ttf")
        
        if os.path.exists(reg_path) and os.path.exists(bold_path):
            self.add_font("Serif", "", reg_path, uni=True)
            self.add_font("Serif", "B", bold_path, uni=True)
            self.add_font("Serif", "I", reg_path, uni=True) # Fallback I to Reg
            self.add_font("Serif", "BI", bold_path, uni=True) # Fallback BI to Bold
        else:
            # Fallback to DejaVu if download failed
            self.add_font("Serif", "", os.path.join(FONTS_DIR, "DejaVuSerif.ttf"), uni=True)
            self.add_font("Serif", "B", os.path.join(FONTS_DIR, "DejaVuSerif-Bold.ttf"), uni=True)
            
        # Sans-serif for headers
        self.add_font("Sans", "", os.path.join(FONTS_DIR, "DejaVuSans.ttf"), uni=True)
        self.add_font("Sans", "B", os.path.join(FONTS_DIR, "DejaVuSans-Bold.ttf"), uni=True)

    def header(self):
        pass

    def footer(self):
        self.set_y(-15)
        self.set_font("Serif", "", 8)
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

    def _render_formula(self, pdf: FPDF, formula: str, is_block: bool = True, custom_h: float = None):
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
            # CodeCogs URL for PNG rendering
            encoded_formula = urllib.parse.quote(r"\bg_white \huge " + formula)
            url = f"https://latex.codecogs.com/png.latex?{encoded_formula}"
            
            with urllib.request.urlopen(url, timeout=5) as response:
                img_data = response.read()
                img_file = io.BytesIO(img_data)
                
                if is_block:
                    pdf.ln(2)
                    curr_y = pdf.get_y()
                    if curr_y > 250: pdf.add_page()
                    # Center
                    pdf.image(img_file, x=pdf.w/2 - 20, w=40) 
                    pdf.ln(2)
                else:
                    # Inline
                    h = custom_h or (pdf.font_size * 0.9)
                    pdf.image(img_file, h=h)
        except Exception as e:
            logger.warning(f"Formula rendering failed: {e}")
            pdf.set_font("Courier", "", 10)
            pdf.write(pdf.font_size, f" [Eq: {formula}] ")

    def _write_rich_line(self, pdf: FPDF, text: str, font_family: str = "Serif", 
                          font_size: int = 10, max_width: float = None, dry_run: bool = False):
        """Write text with **bold**, *italic* and $inline math$. Returns total height used."""
        if max_width is None:
            max_width = pdf.w - pdf.l_margin - pdf.r_margin
        
        parts = re.split(r'(\*\*\*.*?\*\*\*|\*\*.*?\*\*|\*.*?\*|\$.*?\$)', text)
        
        x_start = pdf.get_x()
        current_x = x_start
        line_height = font_size * 0.7
        total_height = line_height

        for part in parts:
            if not part: continue
            
            # Set style
            style = ""
            clean_part = part
            is_math = False
            
            if part.startswith('***') and part.endswith('***'):
                style = "BI"; clean_part = part[3:-3]
            elif part.startswith('**') and part.endswith('**'):
                style = "B"; clean_part = part[2:-2]
            elif part.startswith('*') and part.endswith('*'):
                style = "I"; clean_part = part[1:-1]
            elif part.startswith('$') and part.endswith('$'):
                is_math = True
            
            if is_math:
                if not dry_run:
                    self._render_formula(pdf, part, is_block=False, custom_h=font_size*0.6)
                current_x = pdf.get_x()
                continue
            
            pdf.set_font(font_family, style, font_size)
            words = clean_part.split(' ')
            for j, word in enumerate(words):
                w_str = (' ' if j > 0 else '') + word
                w = pdf.get_string_width(w_str)
                
                if current_x + w > x_start + max_width and current_x > x_start:
                    if not dry_run:
                        pdf.ln(line_height)
                        pdf.set_x(x_start)
                    current_x = x_start
                    total_height += line_height
                    w_str = word.lstrip()
                    w = pdf.get_string_width(w_str)
                
                if not dry_run:
                    pdf.set_x(current_x)
                    pdf.cell(w, line_height, w_str)
                current_x += w
        
        if not dry_run:
            pdf.ln(line_height)
        return total_height

    def _render_rich_table(self, pdf: FPDF, table_data: list, width: float):
        """Custom table renderer that supports LaTeX in cells."""
        if not table_data: return
        
        num_cols = len(table_data[0])
        col_width = width / num_cols
        font_size = 10
        padding = 3
        
        # Calculate row heights
        row_heights = []
        for row in table_data:
            max_h = 0
            for cell in row:
                # Dry run to get height
                pdf.set_x(0) # Temporary
                h = self._write_rich_line(pdf, cell, font_size=font_size, max_width=col_width - 2*padding, dry_run=True)
                max_h = max(max_h, h)
            row_heights.append(max_h + 2*padding)

        # Draw Table
        pdf.set_draw_color(180, 180, 180)
        pdf.set_line_width(0.2)
        
        for i, row in enumerate(table_data):
            h = row_heights[i]
            
            # Page break check
            if pdf.get_y() + h > 270: pdf.add_page()
            
            start_x = pdf.get_x()
            start_y = pdf.get_y()
            
            # Row Background
            if i == 0: pdf.set_fill_color(230, 230, 230) # Header
            elif i % 2 == 1: pdf.set_fill_color(248, 248, 248) # Zebra
            else: pdf.set_fill_color(255, 255, 255)
            
            pdf.rect(start_x, start_y, width, h, 'F')
            
            # Draw Cells
            for j, cell in enumerate(row):
                pdf.set_xy(start_x + j*col_width + padding, start_y + padding)
                self._write_rich_line(pdf, cell, font_size=font_size, max_width=col_width - 2*padding)
                
                # Cell border (vertical)
                pdf.line(start_x + j*col_width, start_y, start_x + j*col_width, start_y + h)
            
            # Last vertical line & horizontal lines
            pdf.line(start_x + width, start_y, start_x + width, start_y + h)
            pdf.line(start_x, start_y, start_x + width, start_y)
            if i == len(table_data) - 1:
                pdf.line(start_x, start_y + h, start_x + width, start_y + h)
            
            pdf.set_xy(start_x, start_y + h)

    def _markdown_to_pdf(self, text: str, title: str) -> bytes | None:
        """Convert Markdown text to a clean academic-style PDF with Math and Rich Tables."""
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
                
                if not stripped:
                    pdf.ln(2); i += 1; continue
                
                # Block Formula
                if stripped.startswith('$$'):
                    f_lines = [stripped]
                    if not stripped.endswith('$$') or len(stripped) == 2:
                        i += 1
                        while i < len(lines) and '$$' not in lines[i]:
                            f_lines.append(lines[i].strip()); i += 1
                        if i < len(lines): f_lines.append(lines[i].strip()); i += 1
                    else: i += 1
                    self._render_formula(pdf, "\n".join(f_lines), is_block=True)
                    continue

                # Rich Tables
                if stripped.startswith('|') and i + 1 < len(lines) and '|---' in lines[i+1]:
                    table_data = []
                    headers = [c.strip() for c in stripped.split('|') if c.strip()]
                    table_data.append(headers)
                    i += 2
                    while i < len(lines) and lines[i].strip().startswith('|'):
                        row = [c.strip() for c in lines[i].split('|') if c.strip()]
                        if row: table_data.append(row)
                        i += 1
                    pdf.ln(2)
                    self._render_rich_table(pdf, table_data, content_width)
                    pdf.ln(2)
                    continue

                # HR
                if stripped in ('---', '***', '___'):
                    pdf.ln(2); self._draw_hr(pdf, 0.3); pdf.ln(1); i += 1; continue
                
                # Headers
                if stripped.startswith('# '):
                    h = stripped[2:].strip()
                    if not first_h1_done:
                        pdf.set_font("Sans", "B", 14); pdf.multi_cell(content_width, 8, h); pdf.ln(2)
                        self._draw_hr(pdf, 0.5); pdf.ln(2); first_h1_done = True
                    else:
                        pdf.ln(4); pdf.set_font("Serif", "B", 16); pdf.multi_cell(content_width, 9, h); pdf.ln(2)
                    i += 1; continue
                
                if stripped.startswith('## '):
                    h = stripped[3:].strip()
                    pdf.ln(6); pdf.set_font("Sans", "B", 13); pdf.multi_cell(content_width, 8, h); pdf.ln(1)
                    self._draw_hr(pdf, 0.4); pdf.ln(2); i += 1; continue
                
                if stripped.startswith('### '):
                    h = stripped[4:].strip(); pdf.ln(4); pdf.set_font("Sans", "B", 11)
                    pdf.multi_cell(content_width, 7, h); pdf.ln(2); i += 1; continue
                
                # Lists
                if stripped.startswith(('- ', '* ', '• ')):
                    pdf.set_font("Serif", "", BODY_SIZE); pdf.set_x(pdf.l_margin + 5)
                    pdf.cell(5, 7, "–"); pdf.set_x(pdf.l_margin + 10)
                    self._write_rich_line(pdf, stripped[2:].strip(), font_size=BODY_SIZE, max_width=content_width-10)
                    i += 1; continue
                
                if re.match(r'^\d+[\.\)] ', stripped):
                    m = re.match(r'^(\d+[\.\)] )(.*)', stripped)
                    pdf.set_font("Serif", "B", BODY_SIZE); pdf.set_x(pdf.l_margin + 5)
                    pdf.cell(8, 7, m.group(1)); pdf.set_x(pdf.l_margin + 13)
                    self._write_rich_line(pdf, m.group(2).strip(), font_size=BODY_SIZE, max_width=content_width-13)
                    i += 1; continue
                
                # Regular paragraph
                pdf.set_x(pdf.l_margin)
                self._write_rich_line(pdf, stripped, font_size=BODY_SIZE, max_width=content_width)
                pdf.ln(1); i += 1

            return bytes(pdf.output())
        except Exception as e:
            logger.error(f"PDF generation error: {e}", exc_info=True); return None

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
