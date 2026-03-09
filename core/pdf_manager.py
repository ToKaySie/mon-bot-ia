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
- Utilise $...$ pour les maths en ligne et $$...$$ pour les blocs
"""
    if user_memories: context += f"\nPROFIL DE L'UTILISATEUR:\n{user_memories}\n"
    if study_plans: context += f"\nPLANNINGS DE RÉVISION:\n{study_plans}\n"
    return context

class AcademicPDF(FPDF):
    """PDF with clean academic style."""
    def __init__(self):
        super().__init__()
        # Use DejaVu (already in the project) to ensure stability
        self.add_font("Serif", "", os.path.join(FONTS_DIR, "DejaVuSerif.ttf"), uni=True)
        self.add_font("Serif", "B", os.path.join(FONTS_DIR, "DejaVuSerif-Bold.ttf"), uni=True)
        self.add_font("Sans", "", os.path.join(FONTS_DIR, "DejaVuSans.ttf"), uni=True)
        self.add_font("Sans", "B", os.path.join(FONTS_DIR, "DejaVuSans-Bold.ttf"), uni=True)

    def header(self): pass
    def footer(self):
        self.set_y(-15)
        self.set_font("Serif", "", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"Page {self.page_no()} / {{nb}}", align="C")

class PDFManager:
    def __init__(self, supabase_url: str, supabase_key: str, service_key: str = None):
        self.supabase_url = supabase_url
        self.supabase_key = supabase_key
        self.service_key = service_key
        self.bucket_name = "pdfs"
        self.enabled = bool(supabase_url and supabase_key)
        if self.enabled:
            self.client: Client = create_client(supabase_url, supabase_key)
            self.client_admin = create_client(supabase_url, service_key) if service_key else self.client
        else:
            self.client = self.client_admin = None

    def _get_public_url(self, file_path: str) -> str:
        return f"{self.supabase_url}/storage/v1/object/public/{self.bucket_name}/{file_path}"

    def _safe_filename(self, title: str) -> str:
        safe = unicodedata.normalize('NFKD', title).encode('ascii', 'ignore').decode('ascii')
        safe = re.sub(r'[^a-zA-Z0-9_-]', '_', safe)
        return re.sub(r'_+', '_', safe).strip('_') or "document"

    def _render_formula(self, pdf: FPDF, formula: str, is_block: bool = True):
        import urllib.parse, urllib.request, io
        formula = formula.strip().strip('$').strip()
        try:
            encoded = urllib.parse.quote(r"\bg_white \huge " + formula)
            url = f"https://latex.codecogs.com/png.latex?{encoded}"
            with urllib.request.urlopen(url, timeout=5) as resp:
                img_file = io.BytesIO(resp.read())
                if is_block:
                    pdf.ln(2)
                    if pdf.get_y() > 250: pdf.add_page()
                    pdf.image(img_file, x=pdf.w/2 - 20, w=40)
                    pdf.ln(2)
                else:
                    pdf.image(img_file, h=pdf.font_size * 0.8)
        except Exception as e:
            pdf.set_font("Courier", "", 10)
            pdf.write(pdf.font_size, f" [{formula}] ")

    def _write_rich_line(self, pdf: FPDF, text: str, font_size: int = 10, max_width: float = None):
        if max_width is None: max_width = pdf.w - pdf.l_margin - pdf.r_margin
        parts = re.split(r'(\*\*.*?\*\*|\*.*?\*|\$.*?\$)', text)
        line_height = font_size * 0.6
        for part in parts:
            if not part: continue
            if part.startswith('**'):
                pdf.set_font("Serif", "B", font_size); part = part[2:-2]
            elif part.startswith('*'):
                pdf.set_font("Serif", "I", font_size); part = part[1:-1]
            elif part.startswith('$'):
                self._render_formula(pdf, part, is_block=False); continue
            else:
                pdf.set_font("Serif", "", font_size)
            pdf.write(line_height, part)
        pdf.ln(line_height + 1)

    def _markdown_to_pdf(self, text: str, title: str) -> bytes | None:
        try:
            pdf = AcademicPDF()
            pdf.alias_nb_pages()
            pdf.set_auto_page_break(True, 20)
            pdf.add_page()
            content_width = pdf.w - pdf.l_margin - pdf.r_margin

            # Title
            pdf.set_font("Serif", "B", 22)
            pdf.multi_cell(content_width, 12, title, align="L")
            pdf.ln(5)

            lines = text.strip().split('\n')
            i = 0
            while i < len(lines):
                line = lines[i].strip()
                if not line: pdf.ln(2); i += 1; continue
                
                if line.startswith('$$'):
                    self._render_formula(pdf, line, True); i += 1; continue
                
                if line.startswith('|') and i+1 < len(lines) and '|---' in lines[i+1]:
                    # Simple table
                    table_data = []
                    while i < len(lines) and line.startswith('|'):
                        if '|---' not in line:
                            table_data.append([c.strip() for c in line.split('|') if c.strip()])
                        i += 1; line = lines[i].strip() if i < len(lines) else ""
                    pdf.ln(2)
                    with pdf.table(borders_layout="HORIZONTAL_LINES", line_height=7, width=content_width) as t:
                        for row in table_data:
                            r = t.row()
                            for c in row: r.cell(c)
                    pdf.ln(2); continue

                if line.startswith('# '):
                    pdf.set_font("Sans", "B", 16); pdf.multi_cell(content_width, 10, line[2:]); pdf.ln(2)
                elif line.startswith('## '):
                    pdf.set_font("Sans", "B", 14); pdf.multi_cell(content_width, 9, line[3:]); pdf.ln(2)
                else:
                    self._write_rich_line(pdf, line, 10, content_width)
                i += 1
            return bytes(pdf.output())
        except Exception as e:
            logger.error(f"PDF Error: {e}", exc_info=True); return None

    def create_pdf(self, title: str, latex_content: str = None, text_content: str = None) -> dict | None:
        content = text_content or latex_content or ""
        pdf_bytes = self._markdown_to_pdf(content, title)
        if not pdf_bytes: return {"error": "Échec de la génération"}
        try:
            file_path = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{self._safe_filename(title)}.pdf"
            self.client_admin.storage.from_(self.bucket_name).upload(pdf_bytes, file_path, {"content-type": "application/pdf"})
            url = self._get_public_url(file_path)
            self.client_admin.table("pdfs").insert({"title": title, "file_path": file_path, "public_url": url}).execute()
            return {"success": True, "title": title, "public_url": url, "pdf_bytes": pdf_bytes}
        except Exception as e:
            return {"error": f"Upload Error: {e}"}

    def search_pdfs(self, query: str = ""):
        try:
            res = self.client_admin.storage.from_(self.bucket_name).list()
            return [{"title": f.get("name"), "public_url": self._get_public_url(f.get("name"))} for f in res if query.lower() in f.get("name").lower()]
        except: return []

    def get_pdf_by_id(self, pdf_id): return None # Simplified for now
    def get_pdf_by_title(self, title): return None
    def delete_pdf(self, title): return {"error": "Non implémenté"}
    def get_all_pdfs(self): return []
