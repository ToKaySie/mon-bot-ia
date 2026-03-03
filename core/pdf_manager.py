from supabase import create_client, Client
import re
import logging
import unicodedata
import os
import io
from datetime import datetime
from fpdf import FPDF

logger = logging.getLogger(__name__)


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
1. APPELLE TOUJOURS cette fonction quand on te demande un PDF/cours/fiche
2. NE JAMAIS écrire le contenu dans ta réponse texte
3. Mets TOUT le contenu dans text_content
4. Utilise du formatage Markdown dans text_content:
   - # pour les titres principaux
   - ## pour les sous-titres
   - ### pour les sous-sous-titres
   - **gras** pour les mots importants
   - - pour les listes à puces
   - 1. pour les listes numérotées
   - Lignes vides pour séparer les paragraphes
5. Après l'appel, réponds juste "PDF créé et envoyé !"
6. Le contenu doit être complet, détaillé et bien structuré""",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Titre du document PDF"
                    },
                    "text_content": {
                        "type": "string",
                        "description": "Contenu complet du document en Markdown. Inclure titres, sous-titres, paragraphes, listes etc."
                    }
                },
                "required": ["title", "text_content"]
            }
        }
    }


class UnicodePDF(FPDF):
    """PDF with Unicode support and professional formatting."""
    
    def __init__(self):
        super().__init__()
        # Use DejaVu - comes bundled with fpdf2 and supports full Unicode
        self.add_font("DejaVu", "", os.path.join(os.path.dirname(__file__), "..", "fonts", "DejaVuSans.ttf"), uni=True)
        self.add_font("DejaVu", "B", os.path.join(os.path.dirname(__file__), "..", "fonts", "DejaVuSans-Bold.ttf"), uni=True)
        self.add_font("DejaVu", "I", os.path.join(os.path.dirname(__file__), "..", "fonts", "DejaVuSans-Oblique.ttf"), uni=True)
        self.add_font("DejaVu", "BI", os.path.join(os.path.dirname(__file__), "..", "fonts", "DejaVuSans-BoldOblique.ttf"), uni=True)
        self._font_loaded = True

    def header(self):
        pass

    def footer(self):
        self.set_y(-15)
        self.set_font("DejaVu", "I", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")


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
        """Create a safe filename from a title."""
        safe = unicodedata.normalize('NFKD', title).encode('ascii', 'ignore').decode('ascii')
        safe = re.sub(r'[^a-zA-Z0-9_-]', '_', safe)
        safe = re.sub(r'_+', '_', safe).strip('_')
        return safe or "document"

    def _markdown_to_pdf(self, text: str, title: str) -> bytes | None:
        """Convert Markdown-formatted text to a professional PDF using fpdf2 with Unicode support."""
        try:
            pdf = UnicodePDF()
            pdf.alias_nb_pages()
            pdf.set_auto_page_break(auto=True, margin=20)
            pdf.add_page()

            # ===== Title page =====
            pdf.ln(30)
            pdf.set_font("DejaVu", "B", 24)
            pdf.set_text_color(44, 62, 80)
            pdf.multi_cell(0, 12, title, align="C")
            pdf.ln(5)
            
            # Decorative line
            pdf.set_draw_color(52, 152, 219)
            pdf.set_line_width(0.8)
            x_start = pdf.w / 2 - 40
            pdf.line(x_start, pdf.get_y(), x_start + 80, pdf.get_y())
            pdf.ln(5)
            
            # Date
            pdf.set_font("DejaVu", "I", 10)
            pdf.set_text_color(127, 140, 141)
            pdf.cell(0, 8, f"Généré le {datetime.now().strftime('%d/%m/%Y à %Hh%M')}", align="C", new_x="LMARGIN", new_y="NEXT")
            
            # Start content on new page
            pdf.add_page()

            # ===== Parse and render content =====
            lines = text.strip().split('\n')
            in_list = False
            list_indent = 15
            
            i = 0
            while i < len(lines):
                line = lines[i].rstrip()
                
                # Empty line = paragraph break
                if not line.strip():
                    if in_list:
                        in_list = False
                    pdf.ln(4)
                    i += 1
                    continue

                stripped = line.strip()

                # H1: # Title
                if stripped.startswith('# ') and not stripped.startswith('## '):
                    if in_list:
                        in_list = False
                    pdf.ln(6)
                    pdf.set_font("DejaVu", "B", 16)
                    pdf.set_text_color(44, 62, 80)
                    heading_text = stripped[2:].strip()
                    heading_text = re.sub(r'\*\*(.*?)\*\*', r'\1', heading_text)
                    pdf.multi_cell(0, 9, heading_text)
                    # Underline
                    pdf.set_draw_color(52, 152, 219)
                    pdf.set_line_width(0.4)
                    pdf.line(10, pdf.get_y(), pdf.w - 10, pdf.get_y())
                    pdf.ln(4)
                
                # H2: ## Subtitle
                elif stripped.startswith('## ') and not stripped.startswith('### '):
                    if in_list:
                        in_list = False
                    pdf.ln(5)
                    pdf.set_font("DejaVu", "B", 14)
                    pdf.set_text_color(52, 73, 94)
                    heading_text = stripped[3:].strip()
                    heading_text = re.sub(r'\*\*(.*?)\*\*', r'\1', heading_text)
                    pdf.multi_cell(0, 8, heading_text)
                    pdf.ln(2)

                # H3: ### Sub-subtitle
                elif stripped.startswith('### '):
                    if in_list:
                        in_list = False
                    pdf.ln(3)
                    pdf.set_font("DejaVu", "B", 12)
                    pdf.set_text_color(52, 73, 94)
                    heading_text = stripped[4:].strip()
                    heading_text = re.sub(r'\*\*(.*?)\*\*', r'\1', heading_text)
                    pdf.multi_cell(0, 7, heading_text)
                    pdf.ln(2)

                # Bullet list: - item or * item or • item
                elif stripped.startswith(('- ', '* ', '• ')):
                    in_list = True
                    pdf.set_font("DejaVu", "", 11)
                    pdf.set_text_color(51, 51, 51)
                    item_text = stripped[2:].strip()
                    
                    x_bullet = 10 + list_indent
                    pdf.set_x(x_bullet)
                    pdf.cell(5, 6, "•")
                    pdf.set_x(x_bullet + 7)
                    
                    self._write_rich_text(pdf, item_text, pdf.w - x_bullet - 17)
                    pdf.ln(1)

                # Numbered list: 1. item
                elif re.match(r'^\d+[\.\)] ', stripped):
                    in_list = True
                    pdf.set_font("DejaVu", "", 11)
                    pdf.set_text_color(51, 51, 51)
                    match = re.match(r'^(\d+[\.\)] )(.*)', stripped)
                    number = match.group(1)
                    item_text = match.group(2).strip()
                    
                    x_num = 10 + list_indent
                    pdf.set_x(x_num)
                    pdf.set_font("DejaVu", "B", 11)
                    pdf.cell(10, 6, number)
                    pdf.set_font("DejaVu", "", 11)
                    pdf.set_x(x_num + 10)
                    
                    self._write_rich_text(pdf, item_text, pdf.w - x_num - 20)
                    pdf.ln(1)

                # Regular paragraph
                else:
                    if in_list:
                        in_list = False
                        pdf.ln(2)
                    
                    pdf.set_font("DejaVu", "", 11)
                    pdf.set_text_color(51, 51, 51)
                    self._write_rich_text(pdf, stripped, pdf.w - 20)
                    pdf.ln(2)

                i += 1

            return bytes(pdf.output())
            
        except Exception as e:
            logger.error(f"PDF generation error: {e}", exc_info=True)
            return None

    def _write_rich_text(self, pdf: FPDF, text: str, max_width: float):
        """Write text with **bold** and *italic* markdown formatting."""
        # Split text into segments: bold, italic, and normal
        parts = re.split(r'(\*\*\*.*?\*\*\*|\*\*.*?\*\*|\*.*?\*)', text)
        
        x_start = pdf.get_x()
        current_x = x_start
        line_height = 6
        
        for part in parts:
            if not part:
                continue
            
            # Bold+Italic
            if part.startswith('***') and part.endswith('***'):
                pdf.set_font("DejaVu", "BI", 11)
                part = part[3:-3]
            # Bold
            elif part.startswith('**') and part.endswith('**'):
                pdf.set_font("DejaVu", "B", 11)
                part = part[2:-2]
            # Italic
            elif part.startswith('*') and part.endswith('*'):
                pdf.set_font("DejaVu", "I", 11)
                part = part[1:-1]
            else:
                pdf.set_font("DejaVu", "", 11)
            
            # Write text, handling line wraps
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
        pdf.set_font("DejaVu", "", 11)

    def create_pdf(self, title: str, latex_content: str = None, text_content: str = None) -> dict | None:
        """Create a PDF from text content and upload to Supabase storage + table."""
        if not self.enabled:
            return {"error": "Supabase non configuré"}
        
        if not text_content and not latex_content:
            return {"error": "Aucun contenu fourni"}
        
        content = text_content or latex_content or ""
        
        logger.info(f"Creating PDF: '{title}' ({len(content)} chars)")
        
        # Generate PDF bytes
        pdf_bytes = self._markdown_to_pdf(content, title)
        
        if not pdf_bytes:
            return {"error": "Échec de la génération du PDF"}
        
        logger.info(f"PDF generated: {len(pdf_bytes)} bytes")
        
        try:
            safe_title = self._safe_filename(title)
            file_path = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{safe_title}.pdf"
            
            # Upload to storage
            self.client_admin.storage.from_(self.bucket_name).upload(
                file=pdf_bytes,
                path=file_path,
                file_options={"content-type": "application/pdf"}
            )
            
            public_url = self._get_public_url(file_path)
            
            # Save metadata in pdfs table
            try:
                self.client_admin.table("pdfs").insert({
                    "title": title,
                    "description": "Généré par le bot IA",
                    "file_path": file_path,
                    "public_url": public_url,
                    "file_size": len(pdf_bytes),
                    "uploaded_at": datetime.now().isoformat()
                }).execute()
                logger.info(f"PDF metadata saved to 'pdfs' table")
            except Exception as e:
                logger.warning(f"Could not save to pdfs table (continuing): {e}")
            
            logger.info(f"PDF created successfully: {file_path}")
            
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
        """Get all PDFs from storage."""
        if not self.enabled:
            return []
        
        try:
            logger.info(f"Listing all PDFs in bucket '{self.bucket_name}'...")
            
            if hasattr(self, 'client_admin') and self.client_admin:
                response = self.client_admin.storage.from_(self.bucket_name).list()
            else:
                response = self.client.storage.from_(self.bucket_name).list()
            
            if not response:
                logger.warning("No files found in storage bucket")
                return []
            
            pdfs = []
            for f in response:
                file_path = f.get("name") or f.get("id")
                if file_path and str(file_path).endswith('.pdf'):
                    title = self._extract_title(file_path)
                    pdfs.append({
                        "id": f.get("id"),
                        "title": title,
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
        results = []
        for pdf in all_pdfs:
            if query_lower in pdf['title'].lower():
                results.append(pdf)
        
        return results[:limit]

    def get_pdf_by_id(self, pdf_id: str):
        all_pdfs = self.get_all_pdfs()
        
        for pdf in all_pdfs:
            if pdf.get("id") == pdf_id:
                return pdf
        return None

    def get_pdf_by_title(self, title_query: str):
        """Get PDF by title query (fuzzy match)."""
        all_pdfs = self.get_all_pdfs()
        
        if not title_query:
            return all_pdfs[0] if all_pdfs else None
        
        title_query_lower = title_query.lower()
        
        for pdf in all_pdfs:
            if title_query_lower in pdf['title'].lower():
                return pdf
        
        return None
