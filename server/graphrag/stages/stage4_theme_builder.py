"""
阶段 4: 主题社区 (Theme Builder)

使用 Louvain 算法构建主题社区，并生成主题摘要
"""

import logging
import json
import hashlib
import math
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from infra.neo4j_client import neo4j_client
from graphrag.models.theme import Theme
from graphrag.config import get_config
from infra.ai_providers import AIProviderFactory, BaseAIClient
from services.config_service import config_service
from graphrag.utils.embedding import cosine_similarity

logger = logging.getLogger("graphrag.stage4")


class ThemeBuilder:
    """
    主题构建器
    
    使用 Neo4j GDS Louvain 算法发现社区，并用 LLM 生成摘要
    """
    
    def __init__(self):
        logger.info("ThemeBuilder initialized")
        self.config = get_config()
        self.thresholds = self.config.thresholds.theme_building
        
        # 初始化 AI 客户端（用于生成主题摘要）
        try:
            ai_config = config_service.get_ai_provider_config()
            provider = ai_config["provider"]
            api_key = ai_config["api_key"]
            model = ai_config["model"]
            base_url = ai_config["base_url"]
            
            if provider == "mock":
                api_key = api_key or "mock"
            
            self.ai_client: Optional[BaseAIClient] = AIProviderFactory.create_client(
                provider=provider,
                api_key=api_key,
                model=model,
                base_url=base_url
            )
            logger.info(f"ThemeBuilder AI client initialized: {provider}")
        except Exception as e:
            logger.warning(f"Failed to initialize AI client for ThemeBuilder: {e}")
            self.ai_client = None
    
    def build(self, doc_id: str, build_version: str) -> List[Theme]:
        """
        为文档构建主题社区
        
        Args:
            doc_id: 文档 ID
            build_version: 构建版本标签
        
        Returns:
            主题列表
        """
        logger.info(f"开始构建主题: doc_id={doc_id}, build_version={build_version}")
        
        # 1. 构建概念关系图（基于 RELATED_TO 关系）
        graph_name = f"concept_graph_{doc_id}_{build_version}"
        self._create_concept_graph(graph_name, doc_id)
        
        # 2. 检查是否启用多尺度检测
        multi_scale_config = self.thresholds.get("multi_scale", {})
        if multi_scale_config.get("enabled", False):
            # 多尺度社区检测（Level 1 + Level 2）
            themes = self._detect_multi_scale_communities(
                graph_name, doc_id, build_version
            )
        else:
            # 单尺度社区检测（原有逻辑）
            communities = self._detect_communities(graph_name, doc_id)
            
            # 为每个社区生成主题摘要
            themes = []
            for community_id, members in communities.items():
                if len(members) < self.thresholds.get("min_community_size", 3):
                    continue
                
                theme = self._create_theme(
                    community_id=community_id,
                    members=members,
                    doc_id=doc_id,
                    build_version=build_version,
                    level=1,
                    parent_theme_id=None
                )
                if theme:
                    themes.append(theme)
                    # 存储到 Neo4j
                    self._store_theme(theme)
        
        # 3. 清理临时图投影
        self._drop_graph(graph_name)
        
        logger.info(f"主题构建完成: doc_id={doc_id}, themes={len(themes)}")
        return themes
    
    def _create_concept_graph(self, graph_name: str, doc_id: str):
        """创建概念关系图投影（用于 GDS 算法）- 带权多源关系融合"""
        logger.debug(f"创建概念图投影: {graph_name}")
        
        try:
            # 如果图已存在，先删除
            self._drop_graph(graph_name)
            
            # 1. 计算并创建带权的 RELATED_TO 关系
            self._build_weighted_relations(doc_id)
            
            # 2. 使用 GDS 投影 RELATED_TO 关系
            query = f"""
            CALL gds.graph.project(
                '{graph_name}',
                {{
                    Concept: {{
                        label: 'Concept',
                        properties: {{}}
                    }}
                }},
                {{
                    RELATED_TO: {{
                        type: 'RELATED_TO',
                        orientation: 'UNDIRECTED',
                        properties: {{
                            weight: {{
                                property: 'weight',
                                defaultValue: 1.0
                            }}
                        }}
                    }}
                }},
                {{
                    nodeQuery: 'MATCH (c:Concept) WHERE EXISTS {{ MATCH (c)-[:RELATED_TO]-(:Concept) }} RETURN id(c) AS id',
                    relationshipQuery: 'MATCH (c1:Concept)-[r:RELATED_TO]-(c2:Concept) WHERE r.weight IS NOT NULL RETURN id(c1) AS source, id(c2) AS target, r.weight AS weight',
                    relationshipProperties: {{
                        weight: {{
                            property: 'weight',
                            defaultValue: 1.0
                        }}
                    }}
                }}
            )
            YIELD graphName, nodeCount, relationshipCount
            """
            
            try:
                neo4j_client.execute_query(query, {"doc_id": doc_id})
                logger.debug(f"GDS 图投影创建成功: {graph_name}")
            except Exception as e:
                logger.warning(f"GDS 投影失败，使用简化方法: {e}")
                # 简化方法：直接在查询时使用 RELATED_TO 关系
        except Exception as e:
            logger.error(f"创建概念图失败: {e}")
            raise
    
    def _build_weighted_relations(self, doc_id: str):
        """
        构建带权多源关系（RELATED_TO）
        
        融合三个权重源：
        1. 共现权重：同一个 Chunk 中 Concept 共现次数
        2. 语义相似度：Concept embedding 的余弦相似度
        3. 论断共现：同一个 Claim 中出现的 Concept
        """
        logger.debug(f"开始构建带权关系: doc_id={doc_id}")
        
        # 获取权重配置
        weight_config = self.thresholds.get("relation_weights", {})
        cooccur_weight = weight_config.get("cooccur_weight", 0.4)
        semantic_weight = weight_config.get("semantic_weight", 0.4)
        claim_weight = weight_config.get("claim_weight", 0.2)
        min_threshold = weight_config.get("min_weight_threshold", 0.1)
        max_edges = weight_config.get("max_edges_per_node", 10)
        
        # 1. 计算共现权重（基于 Chunk 共现）
        logger.debug("计算共现权重...")
        cooccur_query = """
        MATCH (c1:Concept)<-[:MENTIONS]-(ch:Chunk)-[:MENTIONS]->(c2:Concept)
        WHERE c1 <> c2 AND ch.doc_id = $doc_id
        WITH c1, c2, COUNT(*) AS cooccur_count
        RETURN c1.name AS c1_name, c2.name AS c2_name, cooccur_count
        """
        cooccur_results = neo4j_client.execute_query(cooccur_query, {"doc_id": doc_id})
        
        # 归一化共现次数（使用对数归一化）
        cooccur_pairs = {}
        max_cooccur = 0
        for record in cooccur_results:
            c1_name = record.get("c1_name")
            c2_name = record.get("c2_name")
            count = record.get("cooccur_count", 0)
            if c1_name and c2_name:
                # 确保键的顺序一致（小->大）
                key = tuple(sorted([c1_name, c2_name]))
                cooccur_pairs[key] = count
                max_cooccur = max(max_cooccur, count)
        
        # 2. 计算语义相似度（基于 Concept embedding）- 优化：使用向量化批量计算
        logger.debug("计算语义相似度...")
        semantic_query = """
        MATCH (c:Concept)
        WHERE EXISTS {
            MATCH (c)<-[:MENTIONS]-(ch:Chunk)
            WHERE ch.doc_id = $doc_id
        } AND c.embedding IS NOT NULL
        RETURN c.name AS name, c.embedding AS embedding
        """
        semantic_results = neo4j_client.execute_query(semantic_query, {"doc_id": doc_id})
        
        # 构建 embedding 字典
        concept_embeddings = {}
        for record in semantic_results:
            name = record.get("name")
            embedding = record.get("embedding")
            if name and embedding:
                concept_embeddings[name] = embedding
        
        # 优化：使用向量化批量计算所有概念对的语义相似度
        semantic_pairs = {}
        if len(concept_embeddings) > 1:
            # 使用 numpy 向量化计算（比双重循环快得多）
            concept_names = list(concept_embeddings.keys())
            embeddings_matrix = np.array([concept_embeddings[name] for name in concept_names])
            
            # 归一化向量（L2 归一化）
            norms = np.linalg.norm(embeddings_matrix, axis=1, keepdims=True)
            norms[norms == 0] = 1  # 避免除零
            embeddings_normalized = embeddings_matrix / norms
            
            # 计算所有对的余弦相似度（矩阵乘法）
            similarity_matrix = np.dot(embeddings_normalized, embeddings_normalized.T)
            
            # 提取上三角矩阵（避免重复计算和自相似度）
            n = len(concept_names)
            for i in range(n):
                for j in range(i + 1, n):
                    c1_name = concept_names[i]
                    c2_name = concept_names[j]
                    sim = float(similarity_matrix[i, j])
                    # 确保键的顺序一致
                    key = tuple(sorted([c1_name, c2_name]))
                    semantic_pairs[key] = max(semantic_pairs.get(key, 0), sim)
            
            logger.debug(f"向量化计算完成: {len(concept_names)} 个概念, {len(semantic_pairs)} 个相似对")
        
        # 3. 计算论断共现权重（基于 Claim）
        logger.debug("计算论断共现权重...")
        claim_query = """
        MATCH (c1:Concept)<-[:MENTIONS]-(ch:Chunk)-[:CONTAINS_CLAIM]->(cl:Claim)
        MATCH (c2:Concept)<-[:MENTIONS]-(ch)-[:CONTAINS_CLAIM]->(cl)
        WHERE c1 <> c2 AND ch.doc_id = $doc_id
        WITH c1, c2, COUNT(DISTINCT cl) AS claim_cooccur_count
        RETURN c1.name AS c1_name, c2.name AS c2_name, claim_cooccur_count
        """
        claim_results = neo4j_client.execute_query(claim_query, {"doc_id": doc_id})
        
        claim_pairs = {}
        max_claim_cooccur = 0
        for record in claim_results:
            c1_name = record.get("c1_name")
            c2_name = record.get("c2_name")
            count = record.get("claim_cooccur_count", 0)
            if c1_name and c2_name:
                key = tuple(sorted([c1_name, c2_name]))
                claim_pairs[key] = count
                max_claim_cooccur = max(max_claim_cooccur, count)
        
        # 4. 融合权重并归一化（同时保存归一化权重，避免重复计算）
        logger.debug("融合多源权重...")
        all_pairs = set(cooccur_pairs.keys()) | set(semantic_pairs.keys()) | set(claim_pairs.keys())
        
        # 存储归一化权重（用于后续批量写入）
        normalized_weights = {}  # pair -> (cooccur_norm, semantic_norm, claim_norm, final_weight)
        
        weighted_relations = []
        for pair in all_pairs:
            c1_name, c2_name = pair
            
            # 归一化共现权重（对数归一化）
            cooccur_norm = 0.0
            if pair in cooccur_pairs and max_cooccur > 0:
                # 使用对数归一化：log(1 + count) / log(1 + max)
                cooccur_norm = math.log(1 + cooccur_pairs[pair]) / math.log(1 + max_cooccur)
            
            # 语义相似度（已经是 [0, 1]）
            semantic_norm = semantic_pairs.get(pair, 0.0)
            
            # 归一化论断共现权重
            claim_norm = 0.0
            if pair in claim_pairs and max_claim_cooccur > 0:
                claim_norm = math.log(1 + claim_pairs[pair]) / math.log(1 + max_claim_cooccur)
            
            # 加权融合
            final_weight = (
                cooccur_weight * cooccur_norm +
                semantic_weight * semantic_norm +
                claim_weight * claim_norm
            )
            
            if final_weight >= min_threshold:
                weighted_relations.append((c1_name, c2_name, final_weight))
                # 保存归一化权重，避免后续重复计算
                normalized_weights[pair] = (cooccur_norm, semantic_norm, claim_norm, final_weight)
        
        # 5. 对每个节点应用 top-k 限制
        logger.debug(f"应用 top-k 限制 (max_edges={max_edges})...")
        node_edges = {}
        for c1_name, c2_name, weight in weighted_relations:
            if c1_name not in node_edges:
                node_edges[c1_name] = []
            if c2_name not in node_edges:
                node_edges[c2_name] = []
            node_edges[c1_name].append((c2_name, weight))
            node_edges[c2_name].append((c1_name, weight))
        
        # 对每个节点的边按权重排序，只保留 top-k
        filtered_relations = set()
        for node_name, edges in node_edges.items():
            edges.sort(key=lambda x: x[1], reverse=True)
            top_edges = edges[:max_edges]
            for target, weight in top_edges:
                # 确保键的顺序一致
                key = tuple(sorted([node_name, target]))
                filtered_relations.add((key[0], key[1], weight))
        
        # 6. 批量写入 Neo4j（创建或更新 RELATED_TO 关系）
        logger.debug(f"批量写入 Neo4j: {len(filtered_relations)} 条关系")
        
        # 获取批量写入大小配置
        batch_size = self.config.thresholds.get("performance", {}).get("batch_write_size", 100)
        
        # 准备批量写入数据
        relations_data = []
        for c1_name, c2_name, weight in filtered_relations:
            pair = tuple(sorted([c1_name, c2_name]))
            # 从已保存的归一化权重中获取（避免重复计算）
            if pair in normalized_weights:
                cooccur_norm, semantic_norm, claim_norm, _ = normalized_weights[pair]
            else:
                # 如果不在缓存中（理论上不应该发生），重新计算
                cooccur_norm = 0.0
                if pair in cooccur_pairs and max_cooccur > 0:
                    cooccur_norm = math.log(1 + cooccur_pairs[pair]) / math.log(1 + max_cooccur)
                semantic_norm = semantic_pairs.get(pair, 0.0)
                claim_norm = 0.0
                if pair in claim_pairs and max_claim_cooccur > 0:
                    claim_norm = math.log(1 + claim_pairs[pair]) / math.log(1 + max_claim_cooccur)
            
            relations_data.append({
                "c1_name": c1_name,
                "c2_name": c2_name,
                "weight": weight,
                "cooccur_norm": cooccur_norm,
                "semantic_norm": semantic_norm,
                "claim_norm": claim_norm
            })
        
        # 批量写入（使用 UNWIND）
        for i in range(0, len(relations_data), batch_size):
            batch = relations_data[i:i + batch_size]
            
            batch_query = """
            UNWIND $relations AS rel
            MATCH (c1:Concept {name: rel.c1_name})
            MATCH (c2:Concept {name: rel.c2_name})
            MERGE (c1)-[r:RELATED_TO]-(c2)
            SET r.weight = rel.weight,
                r.cooccur_weight = rel.cooccur_norm,
                r.semantic_weight = rel.semantic_norm,
                r.claim_weight = rel.claim_norm,
                r.updated_at = datetime()
            ON CREATE SET
                r.created_at = datetime()
            """
            
            neo4j_client.execute_query(batch_query, {"relations": batch})
            logger.debug(f"批量写入进度: {min(i + batch_size, len(relations_data))}/{len(relations_data)}")
        
        logger.info(f"带权关系构建完成: {len(filtered_relations)} 条关系（批量写入）")
    
    def _detect_communities(self, graph_name: str, doc_id: str) -> Dict[str, List[str]]:
        """使用 Louvain 算法检测社区"""
        logger.debug(f"开始社区检测: {graph_name}")
        
        communities: Dict[str, List[str]] = {}
        
        try:
            # 尝试使用 GDS Louvain 算法
            louvain_config = self.thresholds.get("louvain", {})
            resolution = louvain_config.get("resolution", 1.0)
            
            query = f"""
            CALL gds.louvain.stream('{graph_name}', {{
                resolution: $resolution
            }})
            YIELD nodeId, communityId
            RETURN nodeId, communityId
            """
            
            results = neo4j_client.execute_query(query, {"resolution": resolution})
            
            # 将 nodeId 映射到 Concept name
            for record in results:
                node_id = record.get("nodeId")
                community_id = str(record.get("communityId"))
                
                # 查询 Concept name
                concept_query = """
                MATCH (c:Concept)
                WHERE id(c) = $node_id
                RETURN c.name AS name
                """
                concept_results = neo4j_client.execute_query(concept_query, {"node_id": node_id})
                
                if concept_results:
                    concept_name = concept_results[0].get("name")
                    if concept_name:
                        if community_id not in communities:
                            communities[community_id] = []
                        communities[community_id].append(concept_name)
            
            logger.info(f"社区检测完成: 发现 {len(communities)} 个社区")
            
        except Exception as e:
            logger.warning(f"GDS Louvain 算法失败，使用简化方法: {e}")
            # 简化方法：基于 RELATED_TO 关系的连通分量
            communities = self._detect_communities_simple(doc_id)
        
        return communities
    
    def _detect_communities_simple(self, doc_id: str) -> Dict[str, List[str]]:
        """简化社区检测（基于连通分量）"""
        logger.debug("使用简化社区检测方法")
        
        # 使用弱连通分量（Weakly Connected Components）
        query = """
        MATCH (c:Concept)
        WHERE EXISTS {
            MATCH (c)-[:RELATED_TO]-(:Concept)
        }
        WITH collect(c) AS concepts
        CALL apoc.path.subgraphNodes(concepts[0], {
            relationshipFilter: 'RELATED_TO>',
            minLevel: 0,
            maxLevel: 2
        })
        YIELD node
        RETURN node.name AS name
        """
        
        # 如果 APOC 不可用，使用更简单的方法
        try:
            results = neo4j_client.execute_query(query, {"doc_id": doc_id})
            # 简化：将所有概念归为一个社区
            all_concepts = [r.get("name") for r in results if r.get("name")]
            if all_concepts:
                return {"0": all_concepts}
        except Exception as e:
            logger.warning(f"简化社区检测失败: {e}")
        
        # 最后的回退：基于 RELATED_TO 关系的概念分组
        query = """
        MATCH (c1:Concept)-[:RELATED_TO]-(c2:Concept)
        WHERE c1 <> c2
        RETURN DISTINCT c1.name AS name
        UNION
        MATCH (c:Concept)
        WHERE NOT EXISTS {
            MATCH (c)-[:RELATED_TO]-(:Concept)
        }
        RETURN DISTINCT c.name AS name
        LIMIT 50
        """
        results = neo4j_client.execute_query(query, {"doc_id": doc_id})
        concepts = [r.get("name") for r in results if r.get("name")]
        
        if concepts:
            return {"0": concepts}
        return {}
    
    def _detect_multi_scale_communities(
        self,
        graph_name: str,
        doc_id: str,
        build_version: str
    ) -> List[Theme]:
        """
        多尺度社区检测
        
        1. Level 1: 使用较低分辨率检测粗粒度主题
        2. Level 2: 对每个 Level 1 主题，使用较高分辨率检测细粒度子主题
        
        Returns:
            主题列表（包含 Level 1 和 Level 2）
        """
        logger.info("开始多尺度社区检测")
        multi_scale_config = self.thresholds.get("multi_scale", {})
        
        # Level 1: 粗粒度主题检测
        level1_communities = self._detect_level1_communities(
            graph_name, doc_id, multi_scale_config
        )
        
        if not level1_communities:
            logger.warning("Level 1 社区检测未发现任何社区")
            return []
        
        logger.info(f"Level 1 检测完成: {len(level1_communities)} 个粗粒度主题")
        
        # 为 Level 1 主题创建 Theme 对象
        level1_themes = []
        level1_theme_map = {}  # community_id -> Theme
        
        for community_id, members in level1_communities.items():
            if len(members) < self.thresholds.get("min_community_size", 3):
                continue
            
            theme = self._create_theme(
                community_id=f"L1_{community_id}",
                members=members,
                doc_id=doc_id,
                build_version=build_version,
                level=1,
                parent_theme_id=None
            )
            if theme:
                level1_themes.append(theme)
                level1_theme_map[community_id] = theme
                self._store_theme(theme)
        
        # Level 2: 细粒度子主题检测
        all_themes = level1_themes.copy()
        level2_config = multi_scale_config
        
        for level1_community_id, level1_members in level1_communities.items():
            if level1_community_id not in level1_theme_map:
                continue
            
            parent_theme = level1_theme_map[level1_community_id]
            
            # 在 Level 1 社区内部检测 Level 2 子社区
            level2_communities = self._detect_level2_communities(
                graph_name,
                doc_id,
                level1_members,
                level2_config
            )
            
            if not level2_communities:
                logger.debug(f"Level 1 主题 {level1_community_id} 未发现子主题")
                continue
            
            logger.info(
                f"Level 1 主题 {level1_community_id}: "
                f"发现 {len(level2_communities)} 个子主题"
            )
            
            # 为 Level 2 子主题创建 Theme 对象
            for level2_community_id, level2_members in level2_communities.items():
                if len(level2_members) < level2_config.get("level2_min_themes", 3):
                    continue
                
                theme = self._create_theme(
                    community_id=f"L2_{level1_community_id}_{level2_community_id}",
                    members=level2_members,
                    doc_id=doc_id,
                    build_version=build_version,
                    level=2,
                    parent_theme_id=parent_theme.id
                )
                if theme:
                    all_themes.append(theme)
                    self._store_theme(theme)
        
        logger.info(f"多尺度检测完成: Level 1={len(level1_themes)}, Level 2={len(all_themes) - len(level1_themes)}")
        return all_themes
    
    def _detect_level1_communities(
        self,
        graph_name: str,
        doc_id: str,
        multi_scale_config: Dict[str, Any]
    ) -> Dict[str, List[str]]:
        """
        Level 1 粗粒度社区检测
        
        使用较低分辨率（默认 0.5）运行 Louvain，并验证主题数量限制
        """
        logger.debug("开始 Level 1 社区检测（粗粒度）")
        
        level1_resolution = multi_scale_config.get("level1_resolution", 0.5)
        min_themes = multi_scale_config.get("level1_min_themes", 3)
        max_themes = multi_scale_config.get("level1_max_themes", 8)
        
        communities = {}
        
        try:
            # 使用 GDS Louvain 算法
            query = f"""
            CALL gds.louvain.stream('{graph_name}', {{
                resolution: $resolution
            }})
            YIELD nodeId, communityId
            RETURN nodeId, communityId
            """
            
            results = neo4j_client.execute_query(query, {"resolution": level1_resolution})
            
            # 将 nodeId 映射到 Concept name
            for record in results:
                node_id = record.get("nodeId")
                community_id = str(record.get("communityId"))
                
                concept_query = """
                MATCH (c:Concept)
                WHERE id(c) = $node_id
                RETURN c.name AS name
                """
                concept_results = neo4j_client.execute_query(concept_query, {"node_id": node_id})
                
                if concept_results:
                    concept_name = concept_results[0].get("name")
                    if concept_name:
                        if community_id not in communities:
                            communities[community_id] = []
                        communities[community_id].append(concept_name)
            
            # 验证主题数量限制
            num_communities = len(communities)
            if num_communities < min_themes:
                logger.warning(
                    f"Level 1 主题数量 ({num_communities}) 少于最小值 ({min_themes})，"
                    f"降低分辨率以增加主题数"
                )
                # 降低分辨率（增加主题数）
                adjusted_resolution = level1_resolution * 0.7
                return self._detect_level1_communities_with_resolution(
                    graph_name, doc_id, adjusted_resolution, min_themes, max_themes
                )
            elif num_communities > max_themes:
                logger.warning(
                    f"Level 1 主题数量 ({num_communities}) 超过最大值 ({max_themes})，"
                    f"提高分辨率以减少主题数"
                )
                # 提高分辨率（减少主题数）
                adjusted_resolution = level1_resolution * 1.5
                return self._detect_level1_communities_with_resolution(
                    graph_name, doc_id, adjusted_resolution, min_themes, max_themes
                )
            
            logger.info(f"Level 1 检测完成: {num_communities} 个社区")
            
        except Exception as e:
            logger.warning(f"Level 1 GDS Louvain 算法失败，使用简化方法: {e}")
            communities = self._detect_communities_simple(doc_id)
        
        return communities
    
    def _detect_level1_communities_with_resolution(
        self,
        graph_name: str,
        doc_id: str,
        resolution: float,
        min_themes: int,
        max_themes: int,
        max_iterations: int = 3
    ) -> Dict[str, List[str]]:
        """
        使用指定分辨率检测 Level 1 社区，并迭代调整直到满足数量限制
        """
        for iteration in range(max_iterations):
            communities = {}
            
            try:
                query = f"""
                CALL gds.louvain.stream('{graph_name}', {{
                    resolution: $resolution
                }})
                YIELD nodeId, communityId
                RETURN nodeId, communityId
                """
                
                results = neo4j_client.execute_query(query, {"resolution": resolution})
                
                for record in results:
                    node_id = record.get("nodeId")
                    community_id = str(record.get("communityId"))
                    
                    concept_query = """
                    MATCH (c:Concept)
                    WHERE id(c) = $node_id
                    RETURN c.name AS name
                    """
                    concept_results = neo4j_client.execute_query(concept_query, {"node_id": node_id})
                    
                    if concept_results:
                        concept_name = concept_results[0].get("name")
                        if concept_name:
                            if community_id not in communities:
                                communities[community_id] = []
                            communities[community_id].append(concept_name)
                
                num_communities = len(communities)
                
                if min_themes <= num_communities <= max_themes:
                    logger.info(f"Level 1 分辨率调整成功: resolution={resolution}, themes={num_communities}")
                    return communities
                
                # 继续调整分辨率
                if num_communities < min_themes:
                    resolution *= 0.7  # 降低分辨率，增加主题数
                else:
                    resolution *= 1.5  # 提高分辨率，减少主题数
                
                logger.debug(f"Level 1 迭代 {iteration + 1}: themes={num_communities}, new_resolution={resolution}")
                
            except Exception as e:
                logger.error(f"Level 1 分辨率调整失败: {e}")
                break
        
        # 如果调整失败，返回最后一次的结果
        logger.warning(f"Level 1 分辨率调整未达到目标，返回当前结果")
        return communities if communities else {}
    
    def _detect_level2_communities(
        self,
        graph_name: str,
        doc_id: str,
        level1_members: List[str],
        level2_config: Dict[str, Any]
    ) -> Dict[str, List[str]]:
        """
        Level 2 细粒度社区检测
        
        在 Level 1 社区内部，使用较高分辨率（默认 1.5）运行 Louvain
        """
        logger.debug(f"开始 Level 2 社区检测（细粒度），父社区成员数: {len(level1_members)}")
        
        if len(level1_members) < level2_config.get("level2_min_themes", 3):
            logger.debug("Level 1 社区成员数过少，跳过 Level 2 检测")
            return {}
        
        level2_resolution = level2_config.get("level2_resolution", 1.5)
        min_themes = level2_config.get("level2_min_themes", 3)
        max_themes = level2_config.get("level2_max_themes", 10)
        
        communities = {}
        
        try:
            # 创建子图投影（仅包含 Level 1 社区成员）
            subgraph_name = f"{graph_name}_subgraph_{hashlib.md5('_'.join(sorted(level1_members)).encode()).hexdigest()[:8]}"
            
            # 先查询节点 ID
            node_id_query = """
            MATCH (c:Concept)
            WHERE c.name IN $member_names
            RETURN id(c) AS id
            """
            node_results = neo4j_client.execute_query(
                node_id_query,
                {"member_names": level1_members}
            )
            node_ids = [r.get("id") for r in node_results if r.get("id") is not None]
            
            if not node_ids:
                logger.warning("Level 2 子图投影：未找到节点")
                return {}
            
            # 创建子图投影（使用节点 ID 列表）
            # 注意：GDS graph.project.cypher 不支持参数，需要构建查询字符串
            # 但为了安全，我们使用节点 ID 而不是名称
            node_ids_str = str(node_ids)
            
            create_subgraph_query = f"""
            CALL gds.graph.project.cypher(
                '{subgraph_name}',
                'MATCH (c:Concept) WHERE id(c) IN {node_ids_str} RETURN id(c) AS id',
                'MATCH (c1:Concept)-[r:RELATED_TO]-(c2:Concept)
                 WHERE id(c1) IN {node_ids_str} AND id(c2) IN {node_ids_str}
                 RETURN id(c1) AS source, id(c2) AS target, COALESCE(r.weight, 1.0) AS weight'
            )
            YIELD graphName, nodeCount, relationshipCount
            RETURN graphName, nodeCount, relationshipCount
            """
            
            neo4j_client.execute_query(create_subgraph_query, {})
            
            # 在子图上运行 Louvain
            query = f"""
            CALL gds.louvain.stream('{subgraph_name}', {{
                resolution: $resolution
            }})
            YIELD nodeId, communityId
            RETURN nodeId, communityId
            """
            
            results = neo4j_client.execute_query(query, {"resolution": level2_resolution})
            
            # 将 nodeId 映射到 Concept name
            for record in results:
                node_id = record.get("nodeId")
                community_id = str(record.get("communityId"))
                
                concept_query = """
                MATCH (c:Concept)
                WHERE id(c) = $node_id AND c.name IN $member_names
                RETURN c.name AS name
                """
                concept_results = neo4j_client.execute_query(
                    concept_query,
                    {"node_id": node_id, "member_names": level1_members}
                )
                
                if concept_results:
                    concept_name = concept_results[0].get("name")
                    if concept_name:
                        if community_id not in communities:
                            communities[community_id] = []
                        communities[community_id].append(concept_name)
            
            # 清理子图投影
            self._drop_graph(subgraph_name)
            
            # 验证主题数量限制
            num_communities = len(communities)
            if num_communities < min_themes:
                logger.debug(
                    f"Level 2 主题数量 ({num_communities}) 少于最小值 ({min_themes})，"
                    f"跳过该 Level 1 主题的 Level 2 检测"
                )
                return {}
            elif num_communities > max_themes:
                logger.warning(
                    f"Level 2 主题数量 ({num_communities}) 超过最大值 ({max_themes})，"
                    f"仅保留前 {max_themes} 个最大的社区"
                )
                # 按社区大小排序，保留前 max_themes 个
                sorted_communities = sorted(
                    communities.items(),
                    key=lambda x: len(x[1]),
                    reverse=True
                )
                communities = dict(sorted_communities[:max_themes])
            
            logger.debug(f"Level 2 检测完成: {len(communities)} 个子社区")
            
        except Exception as e:
            logger.warning(f"Level 2 GDS Louvain 算法失败: {e}")
            # 如果子图投影失败，使用简化方法：将 Level 1 社区按概念数量平均分割
            if len(level1_members) >= min_themes * 2:
                chunk_size = len(level1_members) // min_themes
                for i, chunk in enumerate([level1_members[j:j+chunk_size] for j in range(0, len(level1_members), chunk_size)]):
                    if len(chunk) >= min_themes:
                        communities[str(i)] = chunk
                logger.debug(f"Level 2 使用简化分割: {len(communities)} 个子社区")
        
        return communities
    
    def _create_theme(
        self,
        community_id: str,
        members: List[str],
        doc_id: str,
        build_version: str,
        level: int = 1,
        parent_theme_id: Optional[str] = None
    ) -> Optional[Theme]:
        """
        为社区创建 Theme 对象
        
        Args:
            community_id: 社区 ID
            members: 社区成员（概念名称列表）
            doc_id: 文档 ID
            build_version: 构建版本标签
            level: 层级（1=粗粒度，2=细粒度）
            parent_theme_id: 父主题 ID（仅 Level 2 有效）
        """
        logger.debug(f"创建主题: community_id={community_id}, members={len(members)}, level={level}")
        
        # 1. 获取社区的概念和论断
        concepts, claims, relations = self._get_community_content(members, doc_id)
        
        if not concepts:
            logger.warning(f"社区 {community_id} 没有概念，跳过")
            return None
        
        # 2. 使用 LLM 生成主题摘要
        theme_data = self._generate_theme_summary(
            community_id=community_id,
            concepts=concepts,
            claims=claims,
            relations=relations
        )
        
        if not theme_data:
            logger.warning(f"无法生成主题摘要: community_id={community_id}")
            return None
        
        # 3. 构造 Theme 对象
        theme_id = self._generate_theme_id(community_id, doc_id, level)
        
        theme = Theme(
            id=theme_id,
            label=theme_data.get("label", f"主题 {community_id}"),
            summary=theme_data.get("summary", ""),
            level=level,
            keywords=theme_data.get("keywords", []),
            community_id=community_id,
            member_count=len(members),
            concept_ids=members[:10],  # 最多保留10个概念ID
            claim_ids=[c.get("id") for c in claims[:5]],  # 最多保留5个论断ID
            key_evidence=theme_data.get("key_evidence", []),
            parent_theme_id=parent_theme_id,
            build_version=build_version
        )
        
        return theme
    
    def _get_community_content(
        self,
        concept_names: List[str],
        doc_id: str
    ) -> tuple[List[Dict], List[Dict], List[Dict]]:
        """获取社区的概念、论断和关系"""
        concepts = []
        claims = []
        relations = []
        
        # 查询概念
        concept_query = """
        MATCH (c:Concept)
        WHERE c.name IN $concept_names
        RETURN c.name AS name, c.description AS description, c.domain AS domain
        LIMIT 20
        """
        concept_results = neo4j_client.execute_query(
            concept_query,
            {"concept_names": concept_names[:20]}
        )
        concepts = [dict(r) for r in concept_results]
        
        # 查询相关论断
        claim_query = """
        MATCH (c:Concept)<-[:MENTIONS]-(ch:Chunk)-[:CONTAINS_CLAIM]->(cl:Claim)
        WHERE c.name IN $concept_names AND ch.doc_id = $doc_id
        RETURN DISTINCT cl.id AS id, cl.text AS text, cl.confidence AS confidence
        ORDER BY cl.confidence DESC
        LIMIT 10
        """
        claim_results = neo4j_client.execute_query(
            claim_query,
            {"concept_names": concept_names[:20], "doc_id": doc_id}
        )
        claims = [dict(r) for r in claim_results]
        
        # 查询关系（简化：只查询概念间的关系）
        relation_query = """
        MATCH (c1:Concept)-[r]->(c2:Concept)
        WHERE c1.name IN $concept_names AND c2.name IN $concept_names
        RETURN type(r) AS type, c1.name AS source, c2.name AS target
        LIMIT 20
        """
        relation_results = neo4j_client.execute_query(
            relation_query,
            {"concept_names": concept_names[:20]}
        )
        relations = [dict(r) for r in relation_results]
        
        return concepts, claims, relations
    
    def _generate_theme_summary(
        self,
        community_id: str,
        concepts: List[Dict],
        claims: List[Dict],
        relations: List[Dict]
    ) -> Optional[Dict[str, Any]]:
        """使用 LLM 生成主题摘要"""
        if not self.ai_client:
            logger.warning("AI 客户端未初始化，使用默认主题摘要")
            return self._default_theme_summary(concepts, claims)
        
        # 加载 Prompt 模板
        prompt_template_path = Path(__file__).parent.parent / "prompts" / "theme_summary.txt"
        try:
            with open(prompt_template_path, "r", encoding="utf-8") as f:
                prompt_template = f.read()
        except Exception as e:
            logger.error(f"无法加载 Prompt 模板: {e}")
            return self._default_theme_summary(concepts, claims)
        
        # 格式化 Prompt
        concepts_text = "\n".join([
            f"- {c.get('name', '')}: {c.get('description', '无描述')}"
            for c in concepts[:self.thresholds.get("summary", {}).get("max_concepts_per_summary", 10)]
        ])
        
        claims_text = "\n".join([
            f"- \"{c.get('text', '')}\""
            for c in claims[:self.thresholds.get("summary", {}).get("max_claims_per_summary", 5)]
        ])
        
        relations_text = "\n".join([
            f"- {r.get('source', '')} -[{r.get('type', '')}]-> {r.get('target', '')}"
            for r in relations[:10]
        ])
        
        prompt = prompt_template.format(
            community_id=community_id,
            concepts=concepts_text or "无概念",
            claims=claims_text or "无论断",
            relations=relations_text or "无关系"
        )
        
        try:
            # 调用 LLM
            response = self.ai_client.chat_completion(
                messages=[
                    {"role": "system", "content": "你是一个专业的知识图谱分析专家。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            )
            
            # 解析 JSON 响应
            # 尝试提取 JSON 部分
            json_start = response.find("{")
            json_end = response.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                theme_data = json.loads(json_str)
                return theme_data
            else:
                logger.warning("LLM 响应中未找到 JSON，使用默认摘要")
                return self._default_theme_summary(concepts, claims)
                
        except Exception as e:
            logger.error(f"生成主题摘要失败: {e}")
            return self._default_theme_summary(concepts, claims)
    
    def _default_theme_summary(
        self,
        concepts: List[Dict],
        claims: List[Dict]
    ) -> Dict[str, Any]:
        """默认主题摘要（当 LLM 不可用时）"""
        concept_names = [c.get("name", "") for c in concepts[:5]]
        label = "、".join(concept_names[:3]) if concept_names else "未知主题"
        
        summary = f"该主题包含 {len(concepts)} 个核心概念：{', '.join(concept_names[:5])}。"
        if claims:
            summary += f" 相关论断：{claims[0].get('text', '')[:100]}..."
        
        return {
            "label": label,
            "summary": summary,
            "keywords": concept_names[:10],
            "key_evidence": [
                {"claim_text": c.get("text", ""), "importance": c.get("confidence", 0.5)}
                for c in claims[:3]
            ]
        }
    
    def _store_theme(self, theme: Theme):
        """存储 Theme 节点到 Neo4j"""
        logger.debug(f"存储主题: {theme.id}")
        
        query = """
        MERGE (t:Theme {id: $id})
        SET t.label = $label,
            t.summary = $summary,
            t.level = $level,
            t.keywords = $keywords,
            t.community_id = $community_id,
            t.member_count = $member_count,
            t.concept_ids = $concept_ids,
            t.claim_ids = $claim_ids,
            t.key_evidence = $key_evidence,
            t.build_version = $build_version,
            t.updated_at = datetime()
        ON CREATE SET
            t.created_at = datetime()
        """
        
        neo4j_client.execute_query(query, {
            "id": theme.id,
            "label": theme.label,
            "summary": theme.summary,
            "level": theme.level,
            "keywords": theme.keywords,
            "community_id": theme.community_id,
            "member_count": theme.member_count,
            "concept_ids": theme.concept_ids,
            "claim_ids": theme.claim_ids,
            "key_evidence": json.dumps(theme.key_evidence) if theme.key_evidence else None,
            "build_version": theme.build_version
        })
        
        # 创建 BELONGS_TO_THEME 关系
        for concept_id in theme.concept_ids:
            relation_query = """
            MATCH (c:Concept {name: $concept_id})
            MATCH (t:Theme {id: $theme_id})
            MERGE (c)-[:BELONGS_TO_THEME]->(t)
            """
            neo4j_client.execute_query(relation_query, {
                "concept_id": concept_id,
                "theme_id": theme.id
            })
        
        for claim_id in theme.claim_ids:
            relation_query = """
            MATCH (cl:Claim {id: $claim_id})
            MATCH (t:Theme {id: $theme_id})
            MERGE (cl)-[:BELONGS_TO_THEME]->(t)
            """
            neo4j_client.execute_query(relation_query, {
                "claim_id": claim_id,
                "theme_id": theme.id
            })
    
    def _generate_theme_id(self, community_id: str, doc_id: str, level: int = 1) -> str:
        """生成主题 ID"""
        text = f"{doc_id}_{community_id}"
        return hashlib.sha256(text.encode()).hexdigest()[:16]
    
    def _drop_graph(self, graph_name: str):
        """删除图投影"""
        try:
            query = f"CALL gds.graph.drop('{graph_name}') YIELD graphName"
            neo4j_client.execute_query(query)
            logger.debug(f"删除图投影: {graph_name}")
        except Exception as e:
            # 图不存在或 GDS 不可用，忽略错误
            logger.debug(f"删除图投影失败（可能不存在）: {e}")


__all__ = ["ThemeBuilder"]

