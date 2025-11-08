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
        self.provider = settings.ai_provider
        self.model = None
        
        if self.provider == "openai":
            if settings.openai_api_key:
                self.client = OpenAI(
                    api_key=settings.openai_api_key,
                    base_url=settings.openai_base_url
                )
                self.model = settings.openai_model
                print(f"✅ 使用 OpenAI API，模型: {self.model}")
            else:
                print("⚠️  警告: OPENAI_API_KEY 未设置，将使用 mock 模式")
                self.provider = "mock"
        
        elif self.provider == "ollama":
            try:
                # Ollama使用OpenAI兼容的API
                self.client = OpenAI(
                    base_url=f"{settings.ollama_base_url}/v1",
                    api_key="ollama"  # Ollama不需要真实的API key
                )
                self.model = settings.ollama_model
                print(f"✅ 使用 Ollama，地址: {settings.ollama_base_url}，模型: {self.model}")
            except Exception as e:
                print(f"⚠️  警告: 无法连接到 Ollama ({e})，将使用 mock 模式")
                self.provider = "mock"
                self.client = None
        
        else:
            print("ℹ️  使用 mock 模式进行三元组提取")
    
    def extract(self, chunk: Chunk) -> List[Triplet]:
        """
        Extract triplets from a text chunk.
        
        Args:
            chunk: Text chunk to extract from
            
        Returns:
            List of Triplet objects
        """
        if not self.client or self.provider == "mock":
            # Mock mode: return empty list or simple extraction
            return self._mock_extract(chunk)
        
        prompt = self._build_prompt(chunk.text)
        
        try:
            # 根据provider调整参数
            completion_params = {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a knowledge extraction expert. Extract subject-predicate-object triplets from the given text. Return only valid JSON array."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.3,
            }
            
            # OpenAI支持response_format，Ollama可能不支持
            if self.provider == "openai":
                completion_params["response_format"] = {"type": "json_object"}
            
            response = self.client.chat.completions.create(**completion_params)
            
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

