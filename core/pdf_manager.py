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
    return {
        "type": "function",
        "function": {
            "name": "send_pdf",
            "description": "Envoie un PDF existant.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"]
            }
        }
    }

def get_create_pdf_tool_definition() -> dict:
    return {
        "type": "function",
        "function": {
            "name": "create_pdf",
            "description": "Crée un PDF structuré. Tout le contenu doit être dans text_content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "text_content": {"type": "string"}
                },
                "required": ["title", "text_content"]
            }
        }
    }

def get_delete_pdf_tool_definition(available_pdfs: list = None) -> dict:
    return {
        "type": "function",
        "function": {
            "name": "delete_pdf",
            "description": "Supprime un PDF.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title_query": {"type": "string"},
                    "confirmed": {"type": "boolean"}
                },
                "required": ["title_query", "confirmed"]
            }
        }
    }

def get_pdf_system_context(user_memories: str = "", study_plans: str = "") -> str:
    context = "Tu es un expert. Utilise create_pdf pour les documents. Utilise $...$ pour les maths."
    if user_memories: context += f"\nPROFIL:\n{user_memories}"
    return context

class AcademicPDF(FPDF):
    def __init__(self):
        super().__init__()
        self.add_font("Serif", "", os.path.join(FONTS_DIR, "DejaVuSerif.ttf"), uni=True)
        self.add_font("Serif", "B", os.path.join(FONTS_DIR, "DejaVuSerif-Bold.ttf"), uni=True)
        self.add_font("Serif", "I", os.path.join(FONTS_DIR, "DejaVuSerif-Italic.ttf"), uni=True)
        self.add_font("Serif", "BI", os.path.join(FONTS_DIR, "DejaVuSerif-BoldItalic.ttf"), uni=True)
        self.add_font("Sans", "", os.path.join(FONTS_DIR, "DejaVuSans.ttf"), uni=True)
        self.add_font("Sans", "B", os.path.join(FONTS_DIR, "DejaVuSans-Bold.ttf"), uni=True)

    def header(self): pass
    def footer(self):
        self.set_y(-15)
        self.set_font("Serif", "I", 8)
        self.cell(0, 10, f"{self.page_no()} / {{nb}}", align="C")

class PDFManager:
    def __init__(self, supabase_url: str, supabase_key: str, service_key: str = None):
        self.supabase_url = supabase_url
        self.supabase_key = supabase_key
        self.enabled = bool(supabase_url and supabase_key)
        if self.enabled:
            self.client_admin = create_client(supabase_url, service_key or supabase_key)
        else: self.client_admin = None
        self.bucket_name = "pdfs"

    def _render_formula(self, pdf: FPDF, formula: str, is_block: bool = True):
        import urllib.parse, urllib.request, io
        formula = formula.strip().strip('$').strip()
        try:
            encoded = urllib.parse.quote(r"\bg_white \huge " + formula)
            url = f"https://latex.codecogs.com/png.latex?{encoded}"
            with urllib.request.urlopen(url, timeout=10) as resp:
                img_file = io.BytesIO(resp.read())
                if is_block:
                    pdf.ln(2)
                    pdf.image(img_file, x=pdf.w/2 - 20, w=40)
                    pdf.ln(2)
                else:
                    pdf.image(img_file, h=pdf.font_size * 0.8)
        except Exception as e:
            pdf.write(pdf.font_size, f" [{formula}] ")

    def _write_rich_line(self, pdf: FPDF, text: str, font_size: int = 10):
        parts = re.split(r'(\*\*.*?\*\*|\*.*?\*|\$.*?\$)', text)
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
            pdf.write(font_size * 0.7, part)
        pdf.ln(font_size * 0.8)

    def _markdown_to_pdf(self, text: str, title: str) -> bytes | None:
        try:
            pdf = AcademicPDF()
            pdf.alias_nb_pages()
            pdf.set_auto_page_break(True, 20)
            pdf.add_page()
            pdf.set_font("Serif", "B", 22)
            pdf.multi_cell(0, 12, title)
            pdf.ln(5)
            for line in text.strip().split('\n'):
                line = line.strip()
                if not line: pdf.ln(2); continue
                if line.startswith('$$'): self._render_formula(pdf, line, True); continue
                if line.startswith('# '):
                    pdf.set_font("Sans", "B", 16); pdf.multi_cell(0, 10, line[2:]); pdf.ln(2)
                elif line.startswith('## '):
                    pdf.set_font("Sans", "B", 14); pdf.multi_cell(0, 9, line[3:]); pdf.ln(2)
                else:
                    self._write_rich_line(pdf, line, 10)
            return bytes(pdf.output())
        except Exception as e:
            logger.error(f"PDF CRASH: {e}", exc_info=True); return None

    def create_pdf(self, title: str, text_content: str = None, **kwargs) -> dict:
        content = text_content or ""
        pdf_bytes = self._markdown_to_pdf(content, title)
        if not pdf_bytes: return {"error": "Échec generation PDF"}
        try:
            file_path = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{title[:20].replace(' ','_')}.pdf"
            # FIX: correct argument order path, file
            self.client_admin.storage.from_(self.bucket_name).upload(path=file_path, file=pdf_bytes, file_options={"content-type": "application/pdf"})
            url = f"{self.supabase_url}/storage/v1/object/public/{self.bucket_name}/{file_path}"
            return {"success": True, "title": title, "public_url": url, "pdf_bytes": pdf_bytes}
        except Exception as e:
            logger.error(f"Upload error: {e}"); return {"error": f"Upload fail: {e}"}

    def search_pdfs(self, query: str = ""): return []
    def get_all_pdfs(self): return []
    def get_pdf_by_id(self, id): return None
    def get_pdf_by_title(self, title): return None
    def delete_pdf(self, title): return {"error": "Non implémenté"}
