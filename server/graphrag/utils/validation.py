"""
数据校验工具

验证 Chunk、Claim、Concept 等数据的完整性与合法性
"""

from typing import Dict, Any, List, Optional, Tuple
from graphrag.config import get_config


class ValidationError(Exception):
    """数据校验异常"""
    pass


def validate_chunk(chunk: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    验证 Chunk 数据
    
    Args:
        chunk: Chunk 字典
    
    Returns:
        (is_valid, errors)
    """
    errors = []
    
    # 必需字段
    required_fields = ["id", "doc_id", "text", "chunk_index", "window_start", "window_end"]
    for field in required_fields:
        if field not in chunk:
            errors.append(f"Missing required field: {field}")
    
    # 文本长度
    config = get_config()
    min_length = config.thresholds.get("chunking", "chunk_min_length", 50)
    max_length = config.thresholds.get("chunking", "chunk_max_length", 2000)
    
    if "text" in chunk:
        text_length = len(chunk["text"])
        if text_length < min_length:
            errors.append(f"Text too short: {text_length} < {min_length}")
        if text_length > max_length:
            errors.append(f"Text too long: {text_length} > {max_length}")
    
    # 窗口索引
    if "window_start" in chunk and "window_end" in chunk:
        if chunk["window_start"] > chunk["window_end"]:
            errors.append(f"Invalid window: start {chunk['window_start']} > end {chunk['window_end']}")
    
    # 嵌入维度（如果有）
    if "embedding" in chunk and chunk["embedding"]:
        expected_dim = config.thresholds.get("embedding", "dimension", 1536)
        if len(chunk["embedding"]) != expected_dim:
            errors.append(f"Invalid embedding dimension: {len(chunk['embedding'])} != {expected_dim}")
    
    return len(errors) == 0, errors


def validate_claim(claim: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    验证 Claim 数据
    
    Args:
        claim: Claim 字典
    
    Returns:
        (is_valid, errors)
    """
    errors = []
    
    # 必需字段
    required_fields = ["id", "text", "doc_id", "chunk_id", "claim_type", "confidence"]
    for field in required_fields:
        if field not in claim:
            errors.append(f"Missing required field: {field}")
    
    # 文本长度
    config = get_config()
    min_length = config.thresholds.get("claim_extraction", "min_length", 20)
    max_length = config.thresholds.get("claim_extraction", "max_length", 500)
    
    if "text" in claim:
        text_length = len(claim["text"])
        if text_length < min_length:
            errors.append(f"Text too short: {text_length} < {min_length}")
        if text_length > max_length:
            errors.append(f"Text too long: {text_length} > {max_length}")
    
    # 置信度
    if "confidence" in claim:
        confidence = claim["confidence"]
        if not (0.0 <= confidence <= 1.0):
            errors.append(f"Invalid confidence: {confidence} not in [0.0, 1.0]")
        
        min_confidence = config.thresholds.get("claim_extraction", "min_confidence", 0.7)
        if confidence < min_confidence:
            errors.append(f"Confidence too low: {confidence} < {min_confidence}")
    
    # 类型
    if "claim_type" in claim:
        valid_types = ["fact", "hypothesis", "conclusion"]
        if claim["claim_type"] not in valid_types:
            errors.append(f"Invalid claim_type: {claim['claim_type']} not in {valid_types}")
    
    return len(errors) == 0, errors


def validate_concept(concept: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    验证 Concept 数据
    
    Args:
        concept: Concept 字典
    
    Returns:
        (is_valid, errors)
    """
    errors = []
    
    # 使用本体配置验证
    config = get_config()
    
    # 节点类型
    if "type" not in concept:
        errors.append("Missing required field: type")
        return False, errors
    
    node_type = concept["type"]
    is_valid, node_errors = config.ontology.validate_node(node_type, concept)
    
    if not is_valid:
        errors.extend(node_errors)
    
    # 概念名称长度
    if "name" in concept:
        name_length = len(concept["name"])
        min_length = config.ontology.quality_constraints.get("concept_name_min_length", 2)
        max_length = config.ontology.quality_constraints.get("concept_name_max_length", 100)
        
        if name_length < min_length:
            errors.append(f"Name too short: {name_length} < {min_length}")
        if name_length > max_length:
            errors.append(f"Name too long: {name_length} > {max_length}")
    
    # 描述长度（如果有）
    if "description" in concept and concept["description"]:
        desc_length = len(concept["description"])
        min_length = config.ontology.quality_constraints.get("description_min_length", 10)
        max_length = config.ontology.quality_constraints.get("description_max_length", 1000)
        
        if desc_length < min_length:
            errors.append(f"Description too short: {desc_length} < {min_length}")
        if desc_length > max_length:
            errors.append(f"Description too long: {desc_length} > {max_length}")
    
    # 领域（如果有）
    if "domain" in concept and concept["domain"]:
        allowed_domains = config.ontology.get_allowed_domains()
        if concept["domain"] not in allowed_domains:
            errors.append(f"Invalid domain: {concept['domain']} not in {allowed_domains}")
    
    return len(errors) == 0, errors


def validate_relation(relation: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    验证关系数据
    
    Args:
        relation: 关系字典（需包含 source_type, predicate, target_type）
    
    Returns:
        (is_valid, errors)
    """
    errors = []
    
    # 必需字段
    required_fields = ["source_type", "predicate", "target_type"]
    for field in required_fields:
        if field not in relation:
            errors.append(f"Missing required field: {field}")
            return False, errors
    
    # 谓词验证
    config = get_config()
    predicate = relation["predicate"]
    
    # 检查是否为标准谓词或可映射谓词
    if not config.predicates.is_standard_predicate(predicate):
        normalized = config.predicates.normalize_predicate(predicate)
        if not normalized:
            errors.append(f"Unknown predicate: {predicate}")
    
    # 类型约束验证
    source_type = relation["source_type"]
    target_type = relation["target_type"]
    
    is_valid_constraint = config.predicates.validate_type_constraint(
        source_type, predicate, target_type
    )
    
    if not is_valid_constraint:
        errors.append(
            f"Type constraint violation: {source_type} -{predicate}-> {target_type}"
        )
    
    # 置信度（如果有）
    if "confidence" in relation:
        confidence = relation["confidence"]
        if not (0.0 <= confidence <= 1.0):
            errors.append(f"Invalid confidence: {confidence} not in [0.0, 1.0]")
    
    return len(errors) == 0, errors


__all__ = [
    "ValidationError",
    "validate_chunk",
    "validate_claim",
    "validate_concept",
    "validate_relation"
]

