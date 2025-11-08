"""Document parsing services."""
import re
from typing import List, Dict, Any
from pathlib import Path
import fitz  # PyMuPDF
from models.document import Chunk


class Parser:
    """Base parser class."""
    
    def parse(self, file_path: str) -> tuple[str, List[Chunk]]:
        """
        Parse document and return (text, chunks).
        
        Returns:
            Tuple of (full_text, list_of_chunks)
        """
        raise NotImplementedError


class PDFParser(Parser):
    """PDF parser using PyMuPDF."""
    
    def parse(self, file_path: str) -> tuple[str, List[Chunk]]:
        """Parse PDF file."""
        doc = fitz.open(file_path)
        chunks = []
        full_text_parts = []
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()
            
            if not text.strip():
                continue
            
            full_text_parts.append(text)
            
            # Simple chunking: split by paragraphs
            paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
            
            for idx, para in enumerate(paragraphs):
                if len(para) < 10:  # Skip very short paragraphs
                    continue
                
                chunk_id = f"c_{page_num}_{idx}"
                chunks.append(Chunk(
                    doc_id=Path(file_path).stem,
                    chunk_id=chunk_id,
                    text=para,
                    meta={
                        "page": page_num + 1,
                        "section": None,
                        "offset": [0, len(para)]
                    }
                ))
        
        doc.close()
        full_text = "\n\n".join(full_text_parts)
        return full_text, chunks


class MarkdownParser(Parser):
    """Markdown parser."""
    
    def parse(self, file_path: str) -> tuple[str, List[Chunk]]:
        """Parse Markdown file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        chunks = []
        
        # Split by headers and paragraphs
        sections = re.split(r'\n(#{1,6}\s+.+?)\n', content)
        
        current_section = None
        chunk_idx = 0
        
        for i, section in enumerate(sections):
            if i == 0:
                # First section might be content without header
                if section.strip():
                    chunks.append(Chunk(
                        doc_id=Path(file_path).stem,
                        chunk_id=f"c_0",
                        text=section.strip(),
                        meta={
                            "page": 1,
                            "section": None,
                            "offset": [0, len(section)]
                        }
                    ))
                continue
            
            if section.startswith('#'):
                # This is a header
                current_section = section.strip()
            else:
                # This is content
                if section.strip():
                    # Split into paragraphs
                    paragraphs = [p.strip() for p in section.split('\n\n') if p.strip()]
                    for para in paragraphs:
                        if len(para) < 10:
                            continue
                        chunks.append(Chunk(
                            doc_id=Path(file_path).stem,
                            chunk_id=f"c_{chunk_idx}",
                            text=para,
                            meta={
                                "page": 1,
                                "section": current_section,
                                "offset": [0, len(para)]
                            }
                        ))
                        chunk_idx += 1
        
        return content, chunks


class TxtParser(Parser):
    """Plain text parser."""
    
    def parse(self, file_path: str) -> tuple[str, List[Chunk]]:
        """Parse TXT file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        chunks = []
        
        # Split by double newlines (paragraphs)
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
        
        for idx, para in enumerate(paragraphs):
            if len(para) < 10:  # Skip very short paragraphs
                continue
            
            chunks.append(Chunk(
                doc_id=Path(file_path).stem,
                chunk_id=f"c_{idx}",
                text=para,
                meta={
                    "page": 1,
                    "section": None,
                    "offset": [0, len(para)]
                }
            ))
        
        return content, chunks


class WordParser(Parser):
    """Word document parser (DOC/DOCX)."""
    
    def parse(self, file_path: str) -> tuple[str, List[Chunk]]:
        """Parse Word document."""
        try:
            import docx
        except ImportError:
            raise ImportError("python-docx is required for Word document parsing. Install with: pip install python-docx")
        
        doc = docx.Document(file_path)
        chunks = []
        full_text_parts = []
        
        chunk_idx = 0
        for para in doc.paragraphs:
            text = para.text.strip()
            if not text or len(text) < 10:
                continue
            
            full_text_parts.append(text)
            
            chunks.append(Chunk(
                doc_id=Path(file_path).stem,
                chunk_id=f"c_{chunk_idx}",
                text=text,
                meta={
                    "page": 1,
                    "section": para.style.name if para.style else None,
                    "offset": [0, len(text)]
                }
            ))
            chunk_idx += 1
        
        full_text = "\n\n".join(full_text_parts)
        return full_text, chunks


class ParserFactory:
    """Factory for creating parsers based on file type."""
    
    @staticmethod
    def create_parser(kind: str) -> Parser:
        """Create parser based on document kind."""
        parsers = {
            "pdf": PDFParser,
            "md": MarkdownParser,
            "markdown": MarkdownParser,
            "txt": TxtParser,
            "word": WordParser,
        }
        
        parser_class = parsers.get(kind.lower())
        if not parser_class:
            raise ValueError(f"Unsupported document kind: {kind}")
        
        return parser_class()

