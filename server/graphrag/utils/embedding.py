"""
向量化工具

文本嵌入、相似度计算
"""

import os
import logging
import numpy as np
from typing import List, Optional
from functools import lru_cache
from openai import OpenAI

logger = logging.getLogger("graphrag.embedding")


def get_embedding(text: str, model: str = "text-embedding-3-small") -> List[float]:
    """
    获取文本的向量表示
    
    Args:
        text: 输入文本
        model: 嵌入模型名称
    
    Returns:
        向量表示（1536 维）
    """
    if not text or not text.strip():
        logger.warning("Empty text provided for embedding")
        return [0.0] * 1536
    
    try:
        # 从环境变量或配置服务获取 API key
        api_key = os.getenv("OPENAI_API_KEY") or os.getenv("AI_API_KEY")
        
        if not api_key:
            logger.warning("No OpenAI API key found, returning zero vector")
            return [0.0] * 1536
        
        # 创建 OpenAI 客户端
        base_url = os.getenv("OPENAI_BASE_URL") or os.getenv("AI_BASE_URL")
        client = OpenAI(
            api_key=api_key,
            base_url=base_url
        )
        
        # 调用 embeddings API
        response = client.embeddings.create(
            input=text,
            model=model
        )
        
        embedding = response.data[0].embedding
        logger.debug(f"Generated embedding for text (length={len(text)}, dim={len(embedding)})")
        return embedding
        
    except Exception as e:
        logger.error(f"Failed to generate embedding: {e}")
        # 返回零向量作为回退
        return [0.0] * 1536


def batch_embed(
    texts: List[str],
    model: str = "text-embedding-3-small",
    batch_size: int = 100
) -> List[List[float]]:
    """
    批量向量化
    
    Args:
        texts: 文本列表
        model: 嵌入模型名称
        batch_size: 批量大小（OpenAI API 支持最多 2048 个文本）
    
    Returns:
        向量列表
    """
    if not texts:
        return []
    
    embeddings = []
    
    try:
        # 从环境变量获取 API key
        api_key = os.getenv("OPENAI_API_KEY") or os.getenv("AI_API_KEY")
        
        if not api_key:
            logger.warning("No OpenAI API key found, returning zero vectors")
            return [[0.0] * 1536 for _ in texts]
        
        # 创建 OpenAI 客户端
        base_url = os.getenv("OPENAI_BASE_URL") or os.getenv("AI_BASE_URL")
        client = OpenAI(
            api_key=api_key,
            base_url=base_url
        )
        
        # 批量调用 API（OpenAI 支持批量 embedding）
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            
            # 过滤空文本
            valid_batch = [(idx, text) for idx, text in enumerate(batch) if text and text.strip()]
            
            if not valid_batch:
                # 如果整个批次都是空文本，返回零向量
                embeddings.extend([[0.0] * 1536 for _ in batch])
                continue
            
            # 提取有效文本
            valid_texts = [text for _, text in valid_batch]
            valid_indices = [idx for idx, _ in valid_batch]
            
            try:
                response = client.embeddings.create(
                    input=valid_texts,
                    model=model
                )
                
                # 构建结果映射
                result_map = {idx: emb.embedding for idx, emb in enumerate(response.data)}
                
                # 按原始顺序填充结果
                batch_embeddings = []
                for orig_idx in range(len(batch)):
                    if orig_idx in valid_indices:
                        result_idx = valid_indices.index(orig_idx)
                        batch_embeddings.append(result_map[result_idx])
                    else:
                        batch_embeddings.append([0.0] * 1536)
                
                embeddings.extend(batch_embeddings)
                
            except Exception as e:
                logger.error(f"Failed to generate batch embeddings: {e}")
                # 回退：为整个批次返回零向量
                embeddings.extend([[0.0] * 1536 for _ in batch])
        
        return embeddings
        
    except Exception as e:
        logger.error(f"Failed to batch embed: {e}")
        return [[0.0] * 1536 for _ in texts]


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """
    计算余弦相似度
    
    Args:
        vec1: 向量 1
        vec2: 向量 2
    
    Returns:
        相似度 [0, 1]
    """
    v1 = np.array(vec1)
    v2 = np.array(vec2)
    
    dot_product = np.dot(v1, v2)
    norm1 = np.linalg.norm(v1)
    norm2 = np.linalg.norm(v2)
    
    if norm1 == 0 or norm2 == 0:
        return 0.0
    
    return float(dot_product / (norm1 * norm2))


def euclidean_distance(vec1: List[float], vec2: List[float]) -> float:
    """
    计算欧氏距离
    
    Args:
        vec1: 向量 1
        vec2: 向量 2
    
    Returns:
        距离
    """
    v1 = np.array(vec1)
    v2 = np.array(vec2)
    
    return float(np.linalg.norm(v1 - v2))


def top_k_similar(
    query_vec: List[float],
    candidate_vecs: List[List[float]],
    k: int = 10
) -> List[tuple[int, float]]:
    """
    找出最相似的 K 个向量
    
    Args:
        query_vec: 查询向量
        candidate_vecs: 候选向量列表
        k: Top-K
    
    Returns:
        [(index, similarity)] 列表，按相似度降序
    """
    similarities = [
        (i, cosine_similarity(query_vec, vec))
        for i, vec in enumerate(candidate_vecs)
    ]
    
    # 按相似度降序排序
    similarities.sort(key=lambda x: x[1], reverse=True)
    
    return similarities[:k]


@lru_cache(maxsize=1000)
def cached_embedding(text: str, model: str = "text-embedding-3-small") -> tuple:
    """
    带缓存的向量化（用于相同文本的重复查询）
    
    Args:
        text: 输入文本
        model: 嵌入模型名称
    
    Returns:
        向量 tuple（用于缓存）
    """
    embedding = get_embedding(text, model)
    return tuple(embedding)


__all__ = [
    "get_embedding",
    "batch_embed",
    "cosine_similarity",
    "euclidean_distance",
    "top_k_similar",
    "cached_embedding"
]

