"""
向量化工具

文本嵌入、相似度计算
"""

import os
import numpy as np
from typing import List, Optional
from functools import lru_cache


# 占位符：实际实现需要集成 OpenAI API 或本地模型
# 这里提供接口定义


def get_embedding(text: str, model: str = "text-embedding-3-small") -> List[float]:
    """
    获取文本的向量表示
    
    Args:
        text: 输入文本
        model: 嵌入模型名称
    
    Returns:
        向量表示（1536 维）
    """
    # TODO: 实现 OpenAI API 调用
    # from openai import OpenAI
    # client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    # response = client.embeddings.create(input=text, model=model)
    # return response.data[0].embedding
    
    # 占位符：返回随机向量
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
        batch_size: 批量大小
    
    Returns:
        向量列表
    """
    embeddings = []
    
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        
        # TODO: 批量调用 API
        # batch_embeddings = [get_embedding(text, model) for text in batch]
        
        # 占位符
        batch_embeddings = [[0.0] * 1536 for _ in batch]
        
        embeddings.extend(batch_embeddings)
    
    return embeddings


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

