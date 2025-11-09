"""
GraphRAG 工具函数

文本处理、向量化、数据校验等通用工具
"""

from graphrag.utils.text_processing import (
    split_sentences,
    extract_sections,
    sliding_window
)
from graphrag.utils.embedding import (
    get_embedding,
    batch_embed,
    cosine_similarity
)

# P0 新增工具
from graphrag.utils.evidence_aligner import (
    align_evidence,
    extract_evidence_quote
)

from graphrag.utils.claim_deduplicator import (
    deduplicate_claims,
    compute_text_hash
)
from graphrag.utils.validation import (
    validate_chunk,
    validate_claim,
    validate_concept
)

__all__ = [
    "split_sentences",
    "extract_sections",
    "sliding_window",
    "get_embedding",
    "batch_embed",
    "cosine_similarity",
    "validate_chunk",
    "validate_claim",
    "validate_concept",
    # P0 新增
    "align_evidence",
    "extract_evidence_quote",
    "deduplicate_claims",
    "compute_text_hash"
]

