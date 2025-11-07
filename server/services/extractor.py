"""Triplet extraction service using LLM."""
import json
from typing import List, Optional
from openai import OpenAI
from infra.config import settings
from models.document import Triplet, Chunk


class TripletExtractor:
    """Extract triplets from text using LLM."""
    
    def __init__(self):
        self.client = None
        if settings.openai_api_key:
            self.client = OpenAI(api_key=settings.openai_api_key)
        else:
            print("Warning: OPENAI_API_KEY not set. Triplet extraction will use mock mode.")
    
    def extract(self, chunk: Chunk) -> List[Triplet]:
        """
        Extract triplets from a text chunk.
        
        Args:
            chunk: Text chunk to extract from
            
        Returns:
            List of Triplet objects
        """
        if not self.client:
            # Mock mode: return empty list or simple extraction
            return self._mock_extract(chunk)
        
        prompt = self._build_prompt(chunk.text)
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a knowledge extraction expert. Extract subject-predicate-object triplets from the given text. Return only valid JSON array."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            triplets = result.get("triplets", [])
            
            return [
                Triplet(
                    subject=t.get("subject", ""),
                    predicate=t.get("predicate", ""),
                    object=t.get("object", ""),
                    confidence=t.get("confidence", 0.8),
                    evidence={
                        "docId": chunk.doc_id,
                        "chunkId": chunk.chunk_id,
                        "page": chunk.meta.get("page"),
                        "offset": chunk.meta.get("offset"),
                        "text": chunk.text[:200]  # Preview
                    },
                    doc_id=chunk.doc_id,
                    chunk_id=chunk.chunk_id
                )
                for t in triplets
                if t.get("subject") and t.get("predicate") and t.get("object")
            ]
        except Exception as e:
            print(f"Error extracting triplets: {e}")
            return []
    
    def _build_prompt(self, text: str) -> str:
        """Build extraction prompt."""
        return f"""Extract knowledge triplets (subject-predicate-object) from the following text.

Text:
{text}

Return a JSON object with this structure:
{{
  "triplets": [
    {{
      "subject": "entity or concept name",
      "predicate": "relationship type (e.g., is_a, has_property, relates_to, mentions)",
      "object": "target entity or value",
      "confidence": 0.0-1.0
    }}
  ]
}}

Focus on:
- Concepts and their relationships
- Definitions and classifications
- Properties and attributes
- Causal or logical connections

Return only the JSON object, no additional text."""

    def _mock_extract(self, chunk: Chunk) -> List[Triplet]:
        """Mock extraction for testing without OpenAI API."""
        # Simple rule-based extraction as fallback
        triplets = []
        text = chunk.text
        
        # Look for "X is Y" patterns
        import re
        is_pattern = re.compile(r'([A-Z][a-zA-Z\s]+?)\s+is\s+(?:a\s+)?([a-zA-Z\s]+?)(?:\.|,|$)')
        for match in is_pattern.finditer(text):
            triplets.append(Triplet(
                subject=match.group(1).strip(),
                predicate="is_a",
                object=match.group(2).strip(),
                confidence=0.7,
                evidence={
                    "docId": chunk.doc_id,
                    "chunkId": chunk.chunk_id,
                    "page": chunk.meta.get("page"),
                    "offset": chunk.meta.get("offset"),
                    "text": chunk.text[:200]
                },
                doc_id=chunk.doc_id,
                chunk_id=chunk.chunk_id
            ))
        
        return triplets

