"""Document parsing services."""
import re
from typing import List, Dict, Any
from pathlib import Path
import fitz  # PyMuPDF
from models.document import Chunk


class Parser:
    """Base parser class."""
    
    def __init__(self, chunk_size: int = 2000):
        """
        Initialize parser with chunk size.
        
        Args:
            chunk_size: Maximum characters per chunk (default: 2000)
        """
        self.chunk_size = chunk_size
    
    def parse(self, file_path: str) -> tuple[str, List[Chunk]]:
        """
        Parse document and return (text, chunks).
        
        Returns:
            Tuple of (full_text, list_of_chunks)
        """
        raise NotImplementedError
    
    def _smart_chunk(self, text: str, doc_id: str, base_chunk_id: str, meta: Dict[str, Any]) -> List[Chunk]:
        """
        Intelligently chunk text by size while preserving paragraph boundaries.
        
        Args:
            text: Text to chunk
            doc_id: Document ID
            base_chunk_id: Base chunk ID prefix
            meta: Base metadata for chunks
            
        Returns:
            List of Chunk objects
        """
        if not text.strip():
            return []
        
        chunks = []
        
        # If text is smaller than chunk_size, return as single chunk
        if len(text) <= self.chunk_size:
            return [Chunk(
                doc_id=doc_id,
                chunk_id=base_chunk_id,
                text=text.strip(),
                meta=meta.copy()
            )]
        
        # Split by paragraphs first
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip() and len(p.strip()) >= 10]
        
        if not paragraphs:
            # Fallback: split by sentences if no paragraphs
            import re
            sentences = re.split(r'[.!?。！？]\s+', text)
            paragraphs = [s.strip() for s in sentences if s.strip() and len(s.strip()) >= 10]
        
        current_chunk = []
        current_size = 0
        chunk_idx = 0
        
        for para in paragraphs:
            para_size = len(para)
            
            # If single paragraph exceeds chunk_size, split it
            if para_size > self.chunk_size:
                # Save current chunk if exists
                if current_chunk:
                    chunks.append(Chunk(
                        doc_id=doc_id,
                        chunk_id=f"{base_chunk_id}_{chunk_idx}",
                        text="\n\n".join(current_chunk),
                        meta=meta.copy()
                    ))
                    chunk_idx += 1
                    current_chunk = []
                    current_size = 0
                
                # Split large paragraph by sentences
                import re
                sentences = re.split(r'[.!?。！？]\s+', para)
                for sent in sentences:
                    sent = sent.strip()
                    if not sent or len(sent) < 10:
                        continue
                    
                    if len(sent) > self.chunk_size:
                        # Even sentence is too long, split by words
                        words = sent.split()
                        current_sent = []
                        current_sent_size = 0
                        
                        for word in words:
                            word_size = len(word) + 1  # +1 for space
                            if current_sent_size + word_size > self.chunk_size and current_sent:
                                chunks.append(Chunk(
                                    doc_id=doc_id,
                                    chunk_id=f"{base_chunk_id}_{chunk_idx}",
                                    text=" ".join(current_sent),
                                    meta=meta.copy()
                                ))
                                chunk_idx += 1
                                current_sent = []
                                current_sent_size = 0
                            
                            current_sent.append(word)
                            current_sent_size += word_size
                        
                        if current_sent:
                            current_chunk.append(" ".join(current_sent))
                            current_size += current_sent_size
                    else:
                        # Sentence fits, add to current chunk
                        if current_size + len(sent) + 2 > self.chunk_size and current_chunk:
                            chunks.append(Chunk(
                                doc_id=doc_id,
                                chunk_id=f"{base_chunk_id}_{chunk_idx}",
                                text="\n\n".join(current_chunk),
                                meta=meta.copy()
                            ))
                            chunk_idx += 1
                            current_chunk = [sent]
                            current_size = len(sent)
                        else:
                            current_chunk.append(sent)
                            current_size += len(sent) + 2  # +2 for \n\n
            else:
                # Check if adding this paragraph would exceed chunk_size
                if current_size + para_size + 2 > self.chunk_size and current_chunk:
                    chunks.append(Chunk(
                        doc_id=doc_id,
                        chunk_id=f"{base_chunk_id}_{chunk_idx}",
                        text="\n\n".join(current_chunk),
                        meta=meta.copy()
                    ))
                    chunk_idx += 1
                    current_chunk = [para]
                    current_size = para_size
                else:
                    current_chunk.append(para)
                    current_size += para_size + 2  # +2 for \n\n
        
        # Add remaining chunk
        if current_chunk:
            chunks.append(Chunk(
                doc_id=doc_id,
                chunk_id=f"{base_chunk_id}_{chunk_idx}",
                text="\n\n".join(current_chunk),
                meta=meta.copy()
            ))
        
        return chunks


class PDFParser(Parser):
    """PDF parser using PyMuPDF."""
    
    def parse(self, file_path: str) -> tuple[str, List[Chunk]]:
        """Parse PDF file."""
        doc = fitz.open(file_path)
        chunks = []
        full_text_parts = []
        doc_id = Path(file_path).stem
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()
            
            if not text.strip():
                continue
            
            full_text_parts.append(text)
            
            # Use smart chunking with page-aware metadata
            page_chunks = self._smart_chunk(
                text=text,
                doc_id=doc_id,
                base_chunk_id=f"c_{page_num}",
                meta={
                    "page": page_num + 1,
                    "section": None,
                    "offset": [0, len(text)]
                }
            )
            chunks.extend(page_chunks)
        
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
        doc_id = Path(file_path).stem
        
        # Split by headers and paragraphs
        sections = re.split(r'\n(#{1,6}\s+.+?)\n', content)
        
        current_section = None
        chunk_idx = 0
        
        for i, section in enumerate(sections):
            if i == 0:
                # First section might be content without header
                if section.strip():
                    section_chunks = self._smart_chunk(
                        text=section.strip(),
                        doc_id=doc_id,
                        base_chunk_id=f"c_{chunk_idx}",
                        meta={
                            "page": 1,
                            "section": None,
                            "offset": [0, len(section)]
                        }
                    )
                    chunks.extend(section_chunks)
                    chunk_idx += len(section_chunks)
                continue
            
            if section.startswith('#'):
                # This is a header
                current_section = section.strip()
            else:
                # This is content
                if section.strip():
                    section_chunks = self._smart_chunk(
                        text=section.strip(),
                        doc_id=doc_id,
                        base_chunk_id=f"c_{chunk_idx}",
                        meta={
                            "page": 1,
                            "section": current_section,
                            "offset": [0, len(section)]
                        }
                    )
                    chunks.extend(section_chunks)
                    chunk_idx += len(section_chunks)
        
        return content, chunks


class TxtParser(Parser):
    """Plain text parser."""
    
    def parse(self, file_path: str) -> tuple[str, List[Chunk]]:
        """Parse TXT file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        doc_id = Path(file_path).stem
        
        # Use smart chunking
        chunks = self._smart_chunk(
            text=content,
            doc_id=doc_id,
            base_chunk_id="c",
            meta={
                "page": 1,
                "section": None,
                "offset": [0, len(content)]
            }
        )
        
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
        doc_id = Path(file_path).stem
        
        # Collect all paragraphs first
        all_text = []
        current_section = None
        
        for para in doc.paragraphs:
            text = para.text.strip()
            if not text or len(text) < 10:
                continue
            
            section = para.style.name if para.style else None
            if section != current_section:
                # Section changed, process accumulated text
                if all_text:
                    section_text = "\n\n".join(all_text)
                    full_text_parts.append(section_text)
                    section_chunks = self._smart_chunk(
                        text=section_text,
                        doc_id=doc_id,
                        base_chunk_id=f"c_{len(chunks)}",
                        meta={
                            "page": 1,
                            "section": current_section,
                            "offset": [0, len(section_text)]
                        }
                    )
                    chunks.extend(section_chunks)
                    all_text = []
                current_section = section
            
            all_text.append(text)
        
        # Process remaining text
        if all_text:
            section_text = "\n\n".join(all_text)
            full_text_parts.append(section_text)
            section_chunks = self._smart_chunk(
                text=section_text,
                doc_id=doc_id,
                base_chunk_id=f"c_{len(chunks)}",
                meta={
                    "page": 1,
                    "section": current_section,
                    "offset": [0, len(section_text)]
                }
            )
            chunks.extend(section_chunks)
        
        full_text = "\n\n".join(full_text_parts)
        return full_text, chunks


class ParserFactory:
    """Factory for creating parsers based on file type."""
    
    @staticmethod
    def create_parser(kind: str, chunk_size: int = 2000) -> Parser:
        """
        Create parser based on document kind.
        
        Args:
            kind: Document type (pdf, md, txt, word)
            chunk_size: Maximum characters per chunk (default: 2000)
        """
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
        
        return parser_class(chunk_size=chunk_size)

