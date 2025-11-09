"""
Claim 去重与规范化工具

实现硬去重（哈希）和软聚类（语义相似度）
"""

import logging
import hashlib
import re
from typing import List, Dict, Optional, Tuple
from server.graphrag.models.claim import Claim
from server.graphrag.utils.embedding import get_embedding, cosine_similarity, batch_embed

logger = logging.getLogger("graphrag.deduplicator")


def normalize_claim_text(text: str) -> str:
    """
    规范化论断文本（用于硬去重）
    
    移除标点、空格、统一格式
    """
    # 移除标点符号
    text = re.sub(r'[^\w\s]', '', text)
    # 转小写
    text = text.lower()
    # 移除多余空格
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def compute_text_hash(text: str) -> str:
    """
    计算规范化文本的哈希值（用于硬去重）
    
    Args:
        text: 论断文本
    
    Returns:
        SHA256 哈希值（前 16 位）
    """
    normalized = normalize_claim_text(text)
    return hashlib.sha256(normalized.encode('utf-8')).hexdigest()[:16]


def hard_deduplicate(claims: List[Claim]) -> Tuple[List[Claim], Dict[str, List[str]]]:
    """
    硬去重：基于规范化文本哈希
    
    Args:
        claims: 原始 Claim 列表
    
    Returns:
        (去重后的 Claim 列表, 合并映射 {canonical_id: [merged_ids]})
    """
    seen_hashes: Dict[str, Claim] = {}
    merged_map: Dict[str, List[str]] = {}
    deduplicated: List[Claim] = []
    
    for claim in claims:
        # 计算规范化哈希
        if not claim.normalized_text_hash:
            claim.normalized_text_hash = compute_text_hash(claim.text)
        
        hash_key = claim.normalized_text_hash
        
        if hash_key in seen_hashes:
            # 发现重复，合并到已有 Claim
            canonical_claim = seen_hashes[hash_key]
            
            # 记录合并关系
            if canonical_claim.id not in merged_map:
                merged_map[canonical_claim.id] = []
            merged_map[canonical_claim.id].append(claim.id)
            
            # 合并证据信息（如果新 Claim 有更详细的证据）
            if claim.evidence_span and not canonical_claim.evidence_span:
                canonical_claim.evidence_span = claim.evidence_span
            
            # 合并置信度（取较高者）
            if claim.confidence > canonical_claim.confidence:
                canonical_claim.confidence = claim.confidence
            
            logger.debug(f"硬去重合并: {claim.id} -> {canonical_claim.id}")
        else:
            # 新 Claim，保留
            seen_hashes[hash_key] = claim
            deduplicated.append(claim)
    
    logger.info(f"硬去重完成: {len(claims)} -> {len(deduplicated)}, 合并了 {len(claims) - len(deduplicated)} 个重复项")
    return deduplicated, merged_map


def soft_cluster(
    claims: List[Claim],
    similarity_threshold: float = 0.92,
    batch_size: int = 50
) -> Tuple[List[Claim], Dict[str, List[str]]]:
    """
    软聚类：基于语义相似度合并相似论断
    
    Args:
        claims: 已硬去重的 Claim 列表
        similarity_threshold: 相似度阈值（默认 0.92）
        batch_size: 批量向量化大小
    
    Returns:
        (聚类后的 Claim 列表, 聚类映射 {canonical_id: [member_ids]})
    """
    if len(claims) <= 1:
        return claims, {}
    
    logger.info(f"开始软聚类: {len(claims)} 个 Claim, 阈值={similarity_threshold}")
    
    # 1. 批量向量化
    claim_texts = [claim.text for claim in claims]
    try:
        embeddings = batch_embed(claim_texts, batch_size=batch_size)
        logger.debug(f"批量向量化完成: {len(embeddings)} 个向量")
    except Exception as e:
        logger.warning(f"向量化失败，跳过软聚类: {e}")
        return claims, {}
    
    # 2. 为每个 Claim 设置 embedding（如果还没有）
    for i, claim in enumerate(claims):
        if not claim.embedding:
            claim.embedding = embeddings[i]
    
    # 3. 聚类：贪心算法（简单但有效）
    clusters: List[List[int]] = []  # 每个簇包含 Claim 索引
    cluster_map: Dict[int, int] = {}  # claim_index -> cluster_index
    
    for i, claim in enumerate(claims):
        if i in cluster_map:
            continue  # 已分配到簇
        
        # 创建新簇
        cluster_idx = len(clusters)
        clusters.append([i])
        cluster_map[i] = cluster_idx
        
        # 查找相似 Claim
        for j in range(i + 1, len(claims)):
            if j in cluster_map:
                continue  # 已分配到簇
            
            # 计算相似度
            similarity = cosine_similarity(embeddings[i], embeddings[j])
            
            if similarity >= similarity_threshold:
                # 加入同一簇
                clusters[cluster_idx].append(j)
                cluster_map[j] = cluster_idx
                logger.debug(f"软聚类合并: claim[{i}] <-> claim[{j}], similarity={similarity:.3f}")
    
    # 4. 为每个簇选择代表 Claim（置信度最高者）
    clustered_claims: List[Claim] = []
    canonical_map: Dict[str, List[str]] = {}
    
    for cluster_indices in clusters:
        if len(cluster_indices) == 1:
            # 单元素簇，直接保留
            claim = claims[cluster_indices[0]]
            clustered_claims.append(claim)
        else:
            # 多元素簇，选择代表
            cluster_claims = [claims[idx] for idx in cluster_indices]
            # 按置信度排序，选择最高者作为代表
            representative = max(cluster_claims, key=lambda c: c.confidence)
            representative.canonical_id = representative.id
            
            # 记录成员
            member_ids = [c.id for c in cluster_claims if c.id != representative.id]
            if member_ids:
                canonical_map[representative.id] = member_ids
            
            # 合并证据信息
            for member in cluster_claims:
                if member.id != representative.id:
                    # 合并证据区间（取并集）
                    if member.evidence_span and representative.evidence_span:
                        rep_start, rep_end = representative.evidence_span
                        mem_start, mem_end = member.evidence_span
                        representative.evidence_span = (
                            min(rep_start, mem_start),
                            max(rep_end, mem_end)
                        )
                    elif member.evidence_span:
                        representative.evidence_span = member.evidence_span
            
            clustered_claims.append(representative)
            logger.info(f"软聚类簇: 代表={representative.id}, 成员数={len(cluster_indices)}")
    
    logger.info(f"软聚类完成: {len(claims)} -> {len(clustered_claims)}, 合并了 {len(claims) - len(clustered_claims)} 个相似项")
    return clustered_claims, canonical_map


def deduplicate_claims(
    claims: List[Claim],
    enable_soft_cluster: bool = True,
    similarity_threshold: float = 0.92
) -> Tuple[List[Claim], Dict[str, List[str]]]:
    """
    完整的去重流程：硬去重 + 软聚类
    
    Args:
        claims: 原始 Claim 列表
        enable_soft_cluster: 是否启用软聚类
        similarity_threshold: 软聚类相似度阈值
    
    Returns:
        (去重后的 Claim 列表, 合并映射)
    """
    # 1. 硬去重
    hard_deduped, hard_merged = hard_deduplicate(claims)
    
    # 2. 软聚类（可选）
    if enable_soft_cluster and len(hard_deduped) > 1:
        final_claims, soft_merged = soft_cluster(
            hard_deduped,
            similarity_threshold=similarity_threshold
        )
        
        # 合并映射表
        merged_map = {**hard_merged, **soft_merged}
        return final_claims, merged_map
    else:
        return hard_deduped, hard_merged


__all__ = [
    "deduplicate_claims",
    "compute_text_hash",
    "normalize_claim_text"
]

