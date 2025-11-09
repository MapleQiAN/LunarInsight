"""
阶段 2: 实体链接 (Entity Linking)

优化版本：多路召回 + 精排 + NIL 检测
- 别名词典召回（复用 stage1 的 alias_map）
- BM25 + 向量检索候选生成
- 5维特征精排（词形、语义、上下文、类型、频次）
- NIL 检测与新概念创建
- 分类型阈值（Person/Organization vs Method/Tool）
"""

import logging
import re
import hashlib
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from server.graphrag.models.chunk import ChunkMetadata
from server.graphrag.config import get_config
from server.infra.neo4j_client import neo4j_client
from server.infra.config import settings
from server.services.config_service import config_service
from server.graphrag.utils.embedding import get_embedding, cosine_similarity

logger = logging.getLogger("graphrag.stage2")


@dataclass
class EntityCandidate:
    """实体候选"""
    concept_id: str
    concept_name: str
    mention_text: str  # 文本中的提及
    description: Optional[str] = None
    domain: Optional[str] = None
    node_type: Optional[str] = None  # Concept/Person/Method/Tool
    aliases: List[str] = None
    score: float = 0.0  # 精排分数
    features: Dict[str, float] = None  # 特征向量
    match_type: str = "unknown"  # exact/alias/bm25/vector
    
    def __post_init__(self):
        if self.aliases is None:
            self.aliases = []
        if self.features is None:
            self.features = {}


@dataclass
class LinkingResult:
    """链接结果"""
    concept_id: Optional[str]  # None 表示 NIL（新概念）
    concept_name: str
    mention_text: str
    confidence: float
    is_nil: bool = False
    is_review: bool = False  # 是否需要复核
    evidence: Dict[str, Any] = None  # 证据信息
    
    def __post_init__(self):
        if self.evidence is None:
            self.evidence = {}


class EntityLinker:
    """
    实体链接器（优化版本）
    
    实现多路召回 + 精排 + NIL 检测流程：
    1. 多路召回：别名词典（stage1 alias_map）+ BM25 + 向量检索
    2. 精排：5 特征融合（词形、语义、上下文、类型、频次）
    3. NIL 检测：动态阈值 + top-1 vs top-2 差距判断
    4. 分类型阈值：Person/Organization 较高，Method/Tool 较低
    """
    
    def __init__(self):
        self.config = get_config()
        self.thresholds = self.config.thresholds.entity_linking
        self.neo4j_graphrag_available = False
        
        # 获取阈值配置
        self.accept_threshold = self.thresholds.get("accept_threshold", 0.85)
        self.review_threshold = self.thresholds.get("review_threshold", 0.65)
        self.reject_threshold = self.thresholds.get("reject_threshold", 0.4)
        
        # 候选生成参数
        self.candidate_cfg = self.thresholds.get("candidate_generation", {})
        self.bm25_top_k = self.candidate_cfg.get("bm25_top_k", 20)
        self.vector_top_k = self.candidate_cfg.get("vector_top_k", 20)
        self.combined_top_k = self.candidate_cfg.get("combined_top_k", 10)
        
        # 精排权重
        self.ranking_weights = self.thresholds.get("ranking_weights", {})
        
        # 分类型阈值（Person/Organization 较高，Method/Tool 较低）
        self.type_thresholds = {
            "Person": {"accept": 0.88, "review": 0.70},
            "Organization": {"accept": 0.88, "review": 0.70},
            "Concept": {"accept": 0.85, "review": 0.65},
            "Method": {"accept": 0.80, "review": 0.60},
            "Tool": {"accept": 0.80, "review": 0.60},
            "Metric": {"accept": 0.82, "review": 0.63},
        }
        
        # 在线学习：错误链接模式（从反馈数据中学习）
        self.error_patterns = {
            "mention_to_concept": {},  # {mention_text: {concept_id: error_count}}
            "chunk_to_concept": {},    # {chunk_id: {concept_id: error_count}}
        }
        
        # 加载反馈数据（在线学习）
        self._load_feedback_data()
        
        # 尝试导入 neo4j-graphrag（作为回退方案）
        try:
            from neo4j_graphrag import KnowledgeGraphBuilder
            from neo4j_graphrag.llm import OpenAILLM
            
            try:
                ai_config = config_service.get_ai_provider_config()
                provider = ai_config["provider"]
                api_key = ai_config["api_key"]
                model = ai_config["model"]
                base_url = ai_config["base_url"]
                
                if provider != "mock" and api_key:
                    self.kg_builder = KnowledgeGraphBuilder(
                        driver=neo4j_client.driver,
                        llm=OpenAILLM(api_key=api_key, model=model),
                        allowed_nodes=settings.allowed_node_types,
                        allowed_relationships=settings.allowed_relations
                    )
                    self.neo4j_graphrag_available = True
                    logger.info("Neo4j GraphRAG KG Builder initialized (fallback mode)")
            except Exception as e:
                logger.warning(f"Failed to initialize Neo4j GraphRAG: {e}")
        except ImportError:
            logger.debug("neo4j-graphrag not available, using optimized implementation")
        
        logger.info("EntityLinker initialized (optimized version)")
    
    def _load_feedback_data(self):
        """
        从 Neo4j 加载反馈数据，用于在线学习
        
        学习错误链接模式，调整阈值和权重
        """
        try:
            # 查询已审核通过的 UnlinkRequest（错误链接）
            query = """
            MATCH (f:UnlinkRequest)
            WHERE f.status = 'approved'
            RETURN f.mention_text AS mention_text,
                   f.chunk_id AS chunk_id,
                   f.linked_concept_id AS linked_concept_id,
                   f.correct_concept_id AS correct_concept_id,
                   f.reason AS reason
            LIMIT 1000
            """
            
            feedbacks = neo4j_client.execute_query(query)
            
            if not feedbacks:
                logger.debug("[Stage2] 未找到反馈数据，使用默认配置")
                return
            
            # 统计错误链接模式
            error_count = 0
            for feedback in feedbacks:
                mention_text = feedback.get("mention_text")
                chunk_id = feedback.get("chunk_id")
                linked_concept_id = feedback.get("linked_concept_id")
                
                if mention_text and linked_concept_id:
                    # 记录 mention -> concept 的错误模式
                    if mention_text not in self.error_patterns["mention_to_concept"]:
                        self.error_patterns["mention_to_concept"][mention_text] = {}
                    
                    if linked_concept_id not in self.error_patterns["mention_to_concept"][mention_text]:
                        self.error_patterns["mention_to_concept"][mention_text][linked_concept_id] = 0
                    
                    self.error_patterns["mention_to_concept"][mention_text][linked_concept_id] += 1
                    error_count += 1
                
                if chunk_id and linked_concept_id:
                    # 记录 chunk -> concept 的错误模式
                    if chunk_id not in self.error_patterns["chunk_to_concept"]:
                        self.error_patterns["chunk_to_concept"][chunk_id] = {}
                    
                    if linked_concept_id not in self.error_patterns["chunk_to_concept"][chunk_id]:
                        self.error_patterns["chunk_to_concept"][chunk_id][linked_concept_id] = 0
                    
                    self.error_patterns["chunk_to_concept"][chunk_id][linked_concept_id] += 1
            
            if error_count > 0:
                logger.info(f"[Stage2] 加载反馈数据: {error_count} 个错误链接模式")
                
                # 根据反馈数据调整阈值（如果错误链接较多，提高阈值）
                if error_count > 50:
                    # 提高接受阈值，减少错误链接
                    self.accept_threshold = min(self.accept_threshold + 0.05, 0.95)
                    logger.info(f"[Stage2] 根据反馈数据调整接受阈值: {self.accept_threshold:.2f}")
        
        except Exception as e:
            logger.warning(f"[Stage2] 加载反馈数据失败: {e}，使用默认配置")
    
    def refresh_feedback_data(self):
        """
        刷新反馈数据（用于运行时更新）
        
        当新的反馈被审核通过后，可以调用此方法重新加载反馈数据
        """
        # 清空现有模式
        self.error_patterns = {
            "mention_to_concept": {},
            "chunk_to_concept": {},
        }
        
        # 重新加载
        self._load_feedback_data()
        logger.info("[Stage2] 反馈数据已刷新")
    
    def _check_error_pattern(self, mention: str, chunk_id: str, concept_id: str) -> float:
        """
        检查是否为已知的错误链接模式
        
        Args:
            mention: 提及文本
            chunk_id: Chunk ID
            concept_id: 概念 ID
        
        Returns:
            错误概率 [0, 1]，越高表示越可能是错误链接
        """
        error_score = 0.0
        
        # 检查 mention -> concept 的错误模式
        if mention in self.error_patterns["mention_to_concept"]:
            if concept_id in self.error_patterns["mention_to_concept"][mention]:
                error_count = self.error_patterns["mention_to_concept"][mention][concept_id]
                # 错误次数越多，错误概率越高（使用 sigmoid 函数）
                error_score = max(error_score, min(error_count / 5.0, 0.9))
        
        # 检查 chunk -> concept 的错误模式
        if chunk_id in self.error_patterns["chunk_to_concept"]:
            if concept_id in self.error_patterns["chunk_to_concept"][chunk_id]:
                error_count = self.error_patterns["chunk_to_concept"][chunk_id][concept_id]
                error_score = max(error_score, min(error_count / 3.0, 0.9))
        
        return error_score
    
    def _apply_feedback_learning(self, candidate: EntityCandidate, mention: str, chunk_id: str) -> float:
        """
        应用反馈学习：根据错误链接模式调整候选分数
        
        Args:
            candidate: 候选
            mention: 提及文本
            chunk_id: Chunk ID
        
        Returns:
            调整后的分数惩罚（0.0 = 无惩罚, 1.0 = 完全惩罚）
        """
        error_prob = self._check_error_pattern(mention, chunk_id, candidate.concept_id)
        
        if error_prob > 0:
            # 如果检测到错误模式，降低分数
            penalty = error_prob * 0.5  # 最多降低 50% 的分数
            logger.debug(
                f"[Stage2] 反馈学习: '{mention}' -> '{candidate.concept_name}' "
                f"错误概率={error_prob:.2f}, 惩罚={penalty:.2f}"
            )
            return penalty
        
        return 0.0
    
    def link_and_extract(self, chunk: ChunkMetadata) -> List[Dict[str, Any]]:
        """
        链接并抽取实体（优化版本）
        
        Args:
            chunk: 输入 Chunk
        
        Returns:
            实体列表 [{concept_id, concept_name, confidence, mention_text, chunk_id, is_nil, is_review}]
        """
        logger.debug(f"[Stage2] 开始实体链接: chunk_id={chunk.id}")
        
        # 根据 coref_mode 决定是否使用 resolved_text
        use_resolved_text = (
            chunk.resolved_text and 
            chunk.coref_mode == "rewrite"
        )
        text_to_use = chunk.resolved_text if use_resolved_text else chunk.text
        
        # 提取实体提及（简单规则：专有名词、中文名词短语）
        mentions = self._extract_mentions(text_to_use)
        if not mentions:
            logger.debug(f"[Stage2] 未检测到实体提及: chunk_id={chunk.id}")
            return []
        
        logger.info(f"[Stage2] 检测到 {len(mentions)} 个实体提及")
        
        # 获取 stage1 的别名映射
        alias_map = chunk.coreference_aliases or {}
        if alias_map:
            logger.debug(f"[Stage2] 使用 stage1 别名映射: {len(alias_map)} 个条目")
        
        # 对每个提及进行链接
        linking_results = []
        for mention in mentions:
            result = self._link_mention(
                mention=mention,
                text=text_to_use,
                chunk=chunk,
                alias_map=alias_map
            )
            if result:
                linking_results.append(result)
        
        # 转换为返回格式
        entities = []
        for result in linking_results:
            entity = {
                "concept_id": result.concept_id,
                "concept_name": result.concept_name,
                "confidence": result.confidence,
                "mention_text": result.mention_text,
                "chunk_id": chunk.id,
                "is_nil": result.is_nil,
                "is_review": result.is_review,
                "evidence": result.evidence
            }
            entities.append(entity)
        
        logger.info(f"[Stage2] 实体链接完成: chunk_id={chunk.id}, entities={len(entities)}")
        return entities
    
    def _extract_mentions(self, text: str) -> List[str]:
        """
        提取实体提及（简单规则）
        
        Args:
            text: 输入文本
        
        Returns:
            提及列表
        """
        mentions = set()
        
        # 1. 英文专有名词（大写开头，2+ 字符）
        proper_nouns = re.findall(r'\b([A-Z][a-zA-Z0-9]{2,})\b', text)
        mentions.update(proper_nouns)
        
        # 2. 中文名词短语（2-5 个字符）
        chinese_nouns = re.findall(r'[\u4e00-\u9fff]{2,5}', text)
        mentions.update(chinese_nouns)
        
        # 过滤停用词
        stopwords = {'这个', '那个', '这些', '那些', '它们', '他们', '我们', '你们', '它们', '它们'}
        mentions = {m for m in mentions if m not in stopwords}
        
        return list(mentions)
    
    def _link_mention(
        self,
        mention: str,
        text: str,
        chunk: ChunkMetadata,
        alias_map: Dict[str, str]
    ) -> Optional[LinkingResult]:
        """
        链接单个提及
        
        Args:
            mention: 提及文本
            text: 完整文本
            chunk: Chunk 元数据
            alias_map: stage1 的别名映射
        
        Returns:
            链接结果
        """
        # 1. 多路召回：别名词典 + BM25 + 向量
        candidates = self._multi_retrieval(mention, text, alias_map, chunk)
        
        if not candidates:
            # NIL：没有候选，创建新概念
            logger.debug(f"[Stage2] NIL: 提及 '{mention}' 无候选，创建新概念")
            return LinkingResult(
                concept_id=None,
                concept_name=mention,
                mention_text=mention,
                confidence=0.5,
                is_nil=True,
                is_review=False,
                evidence={"reason": "no_candidates"}
            )
        
        # 2. 精排：计算特征并排序
        ranked_candidates = self._rerank(candidates, mention, text, chunk)
        
        if not ranked_candidates:
            return None
        
        top_candidate = ranked_candidates[0]
        top_score = top_candidate.score
        
        # 3. NIL 检测：检查 top-1 与 top-2 的差距
        is_nil = False
        if len(ranked_candidates) > 1:
            second_score = ranked_candidates[1].score
            score_gap = top_score - second_score
            # 如果 top-1 分数低且与 top-2 差距小，判定为 NIL
            if top_score < 0.6 and score_gap < 0.15:
                is_nil = True
                logger.debug(f"[Stage2] NIL: 提及 '{mention}' 分数低且差距小 (top={top_score:.3f}, gap={score_gap:.3f})")
        
        # 4. 分类型阈值判断
        node_type = top_candidate.node_type or "Concept"
        type_thresh = self.type_thresholds.get(node_type, {"accept": self.accept_threshold, "review": self.review_threshold})
        accept_thresh = type_thresh["accept"]
        review_thresh = type_thresh["review"]
        
        is_review = False
        if is_nil or top_score < self.reject_threshold:
            # NIL 或拒绝
            return LinkingResult(
                concept_id=None,
                concept_name=mention,
                mention_text=mention,
                confidence=top_score,
                is_nil=True,
                is_review=False,
                evidence={
                    "reason": "nil_or_rejected",
                    "top_score": top_score,
                    "node_type": node_type
                }
            )
        elif top_score < accept_thresh:
            # 需要复核
            is_review = True
        
        # 5. 返回链接结果
        return LinkingResult(
            concept_id=top_candidate.concept_id,
            concept_name=top_candidate.concept_name,
            mention_text=mention,
            confidence=top_score,
            is_nil=False,
            is_review=is_review,
            evidence={
                "match_type": top_candidate.match_type,
                "node_type": node_type,
                "features": top_candidate.features
            }
        )
    
    def _multi_retrieval(
        self,
        mention: str,
        text: str,
        alias_map: Dict[str, str],
        chunk: ChunkMetadata
    ) -> List[EntityCandidate]:
        """
        多路召回：别名词典 + BM25 + 向量检索
        
        Args:
            mention: 提及文本
            text: 完整文本
            alias_map: stage1 的别名映射
            chunk: Chunk 元数据
        
        Returns:
            候选列表
        """
        candidates = []
        candidate_ids = set()  # 去重
        
        # 1. 别名词典召回（复用 stage1 的 alias_map）
        if mention in alias_map:
            canonical = alias_map[mention]
            candidates_from_alias = self._retrieve_by_name_or_alias(canonical)
            for cand in candidates_from_alias:
                if cand.concept_id not in candidate_ids:
                    cand.match_type = "alias"
                    candidates.append(cand)
                    candidate_ids.add(cand.concept_id)
            logger.debug(f"[Stage2] 别名词典召回: '{mention}' -> '{canonical}', 找到 {len(candidates_from_alias)} 个候选")
        
        # 2. 精确匹配召回
        exact_candidates = self._retrieve_by_name_or_alias(mention)
        for cand in exact_candidates:
            if cand.concept_id not in candidate_ids:
                cand.match_type = "exact"
                candidates.append(cand)
                candidate_ids.add(cand.concept_id)
        
        # 3. BM25 召回（简化版：使用 Neo4j 的文本匹配）
        bm25_candidates = self._retrieve_by_bm25(mention, limit=self.bm25_top_k)
        for cand in bm25_candidates:
            if cand.concept_id not in candidate_ids:
                cand.match_type = "bm25"
                candidates.append(cand)
                candidate_ids.add(cand.concept_id)
        
        # 4. 向量检索
        # 优先使用 mention 的 embedding（更精确），如果没有则使用 chunk.embedding
        mention_embedding = None
        if settings.enable_vector_search:
            try:
                # 为 mention 生成 embedding（更精确的匹配）
                mention_embedding = get_embedding(mention, model=settings.embedding_model)
                # 检查是否为有效向量（非全零）
                if mention_embedding and any(x != 0.0 for x in mention_embedding):
                    logger.debug(f"[Stage2] 为 mention '{mention}' 生成 embedding")
                else:
                    # 如果生成失败，尝试使用 chunk.embedding
                    mention_embedding = chunk.embedding
                    if mention_embedding:
                        logger.debug(f"[Stage2] 使用 chunk.embedding 进行向量检索")
            except Exception as e:
                logger.warning(f"[Stage2] 生成 mention embedding 失败: {e}，尝试使用 chunk.embedding")
                mention_embedding = chunk.embedding
        
        if mention_embedding:
            vector_candidates = self._retrieve_by_vector(mention, mention_embedding, limit=self.vector_top_k)
            for cand in vector_candidates:
                if cand.concept_id not in candidate_ids:
                    cand.match_type = "vector"
                    candidates.append(cand)
                    candidate_ids.add(cand.concept_id)
        
        logger.debug(f"[Stage2] 多路召回完成: '{mention}' 共找到 {len(candidates)} 个候选")
        return candidates[:self.combined_top_k]  # 限制总数
    
    def _retrieve_by_name_or_alias(self, name: str) -> List[EntityCandidate]:
        """
        通过名称或别名检索候选
        
        Args:
            name: 名称或别名
        
        Returns:
            候选列表
        """
        query = """
        MATCH (c:Concept)
        WHERE toLower(c.name) = toLower($name)
           OR $name IN coalesce(c.aliases, [])
           OR any(alias IN coalesce(c.aliases, []) WHERE toLower(alias) = toLower($name))
        RETURN c.id AS concept_id,
               c.name AS concept_name,
               c.description AS description,
               c.domain AS domain,
               coalesce(c.aliases, []) AS aliases,
               labels(c) AS labels
        LIMIT 10
        """
        
        result = neo4j_client.execute_query(query, {"name": name})
        candidates = []
        
        for record in result:
            labels = record.get("labels", [])
            node_type = None
            for label in labels:
                if label in ["Person", "Organization", "Method", "Tool", "Metric", "Concept"]:
                    node_type = label
                    break
            
            candidate = EntityCandidate(
                concept_id=record.get("concept_id") or record.get("concept_name"),
                concept_name=record.get("concept_name"),
                mention_text=name,
                description=record.get("description"),
                domain=record.get("domain"),
                node_type=node_type,
                aliases=record.get("aliases", [])
            )
            candidates.append(candidate)
        
        return candidates
    
    def _retrieve_by_bm25(self, mention: str, limit: int = 20) -> List[EntityCandidate]:
        """
        BM25 检索（简化版：使用 Neo4j 的文本匹配）
        
        Args:
            mention: 提及文本
            limit: 返回数量限制
        
        Returns:
            候选列表
        """
        query = """
        MATCH (c:Concept)
        WHERE c.name CONTAINS $mention
           OR $mention CONTAINS c.name
           OR any(alias IN coalesce(c.aliases, []) WHERE alias CONTAINS $mention OR $mention CONTAINS alias)
        RETURN c.id AS concept_id,
               c.name AS concept_name,
               c.description AS description,
               c.domain AS domain,
               coalesce(c.aliases, []) AS aliases,
               labels(c) AS labels
        ORDER BY 
            CASE 
                WHEN toLower(c.name) = toLower($mention) THEN 0
                WHEN c.name CONTAINS $mention OR $mention CONTAINS c.name THEN 1
                ELSE 2
            END
        LIMIT $limit
        """
        
        result = neo4j_client.execute_query(query, {"mention": mention, "limit": limit})
        candidates = []
        
        for record in result:
            labels = record.get("labels", [])
            node_type = None
            for label in labels:
                if label in ["Person", "Organization", "Method", "Tool", "Metric", "Concept"]:
                    node_type = label
                    break
            
            candidate = EntityCandidate(
                concept_id=record.get("concept_id") or record.get("concept_name"),
                concept_name=record.get("concept_name"),
                mention_text=mention,
                description=record.get("description"),
                domain=record.get("domain"),
                node_type=node_type,
                aliases=record.get("aliases", [])
            )
            candidates.append(candidate)
        
        return candidates
    
    def _retrieve_by_vector(self, mention: str, embedding: List[float], limit: int = 20) -> List[EntityCandidate]:
        """
        向量检索（使用 Neo4j 向量索引）
        
        Args:
            mention: 提及文本
            embedding: 向量表示（1536 维）
            limit: 返回数量限制
        
        Returns:
            候选列表
        """
        if not embedding or len(embedding) != 1536:
            logger.debug(f"[Stage2] 向量检索跳过：无效的 embedding (dim={len(embedding) if embedding else 0})")
            return []
        
        if not settings.enable_vector_search:
            logger.debug("[Stage2] 向量检索已禁用")
            return []
        
        candidates = []
        
        try:
            # 使用 Neo4j 向量索引查询
            # Neo4j 5.11+ 支持 db.index.vector.queryNodes
            # queryNodes 已经按相似度降序返回结果，无需再次排序
            query = """
            CALL db.index.vector.queryNodes('concept_embeddings', $topK, $queryVector)
            YIELD node, score
            WHERE node.embedding IS NOT NULL
            RETURN 
                node.name AS name,
                node.id AS id,
                node.domain AS domain,
                node.description AS description,
                node.category AS category,
                labels(node) AS labels,
                coalesce(node.aliases, []) AS aliases,
                score AS vector_score
            """
            
            # 查询更多候选以便后续过滤（应用阈值后可能少于 limit）
            top_k = limit * 2
            result = neo4j_client.execute_query(query, {
                "topK": top_k,
                "queryVector": embedding
            })
            
            # 应用向量相似度阈值
            vector_threshold = settings.vector_search_threshold
            
            for record in result:
                vector_score = record.get("vector_score", 0.0)
                
                # 过滤低相似度结果
                if vector_score < vector_threshold:
                    continue
                
                # 确定节点类型
                labels = record.get("labels", [])
                node_type = None
                for label in labels:
                    if label in ["Person", "Organization", "Method", "Tool", "Metric", "Concept"]:
                        node_type = label
                        break
                if not node_type:
                    node_type = "Concept"
                
                candidate = EntityCandidate(
                    concept_id=record.get("id") or record.get("name"),
                    concept_name=record.get("name"),
                    domain=record.get("domain"),
                    description=record.get("description"),
                    node_type=node_type,
                    aliases=record.get("aliases", []),
                    score=vector_score,  # 初始分数为向量相似度
                    features={
                        "vector_similarity": vector_score,
                        "match_type": "vector_search"
                    }
                )
                candidates.append(candidate)
            
            logger.debug(f"[Stage2] 向量检索 '{mention}': 找到 {len(candidates)} 个候选 (阈值={vector_threshold})")
            
        except Exception as e:
            # 如果向量索引不存在或查询失败，记录警告但不中断流程
            error_msg = str(e).lower()
            if "index" in error_msg and "not found" in error_msg:
                logger.warning(f"[Stage2] 向量索引 'concept_embeddings' 不存在，跳过向量检索")
            else:
                logger.warning(f"[Stage2] 向量检索失败: {e}")
        
        return candidates
    
    def _rerank(
        self,
        candidates: List[EntityCandidate],
        mention: str,
        text: str,
        chunk: ChunkMetadata
    ) -> List[EntityCandidate]:
        """
        精排：计算特征并排序
        
        Args:
            candidates: 候选列表
            mention: 提及文本
            text: 完整文本
            chunk: Chunk 元数据
        
        Returns:
            排序后的候选列表
        """
        logger.debug(
            f"[Stage2] 开始精排: mention='{mention}', candidates={len(candidates)}"
        )
        
        for candidate in candidates:
            # 计算 6 类特征（新增图一致性特征）
            features = {
                "lexical_similarity": self._compute_lexical_similarity(mention, candidate.concept_name, candidate.aliases),
                "semantic_similarity": self._compute_semantic_similarity(mention, candidate, chunk),
                "context_match": self._compute_context_match(mention, candidate, text, chunk),
                "type_consistency": self._compute_type_consistency(candidate),
                "prior_frequency": self._compute_prior_frequency(candidate),
                "graph_consistency": self._compute_graph_consistency(candidate, chunk)
            }
            candidate.features = features
            
            # 加权求和得到总分
            weights = {
                "lexical_similarity": self.ranking_weights.get("lexical_similarity", 0.15),
                "semantic_similarity": self.ranking_weights.get("semantic_similarity", 0.35),
                "context_match": self.ranking_weights.get("context_match", 0.15),
                "type_consistency": self.ranking_weights.get("type_consistency", 0.1),
                "prior_frequency": self.ranking_weights.get("prior_frequency", 0.1),
                "graph_consistency": self.ranking_weights.get("graph_consistency", 0.15)
            }
            
            score = (
                features["lexical_similarity"] * weights["lexical_similarity"] +
                features["semantic_similarity"] * weights["semantic_similarity"] +
                features["context_match"] * weights["context_match"] +
                features["type_consistency"] * weights["type_consistency"] +
                features["prior_frequency"] * weights["prior_frequency"] +
                features["graph_consistency"] * weights["graph_consistency"]
            )
            
            # 应用反馈学习：根据错误链接模式调整分数
            penalty = self._apply_feedback_learning(candidate, mention, chunk.id)
            score_before_penalty = score
            score = score * (1.0 - penalty)
            
            candidate.score = score
            
            logger.debug(
                f"[Stage2] 候选 '{candidate.concept_name}' (id={candidate.concept_id}):\n"
                f"  特征: lexical={features['lexical_similarity']:.3f}, "
                f"semantic={features['semantic_similarity']:.3f}, "
                f"context={features['context_match']:.3f}, "
                f"type={features['type_consistency']:.3f}, "
                f"frequency={features['prior_frequency']:.3f}, "
                f"graph={features['graph_consistency']:.3f}\n"
                f"  权重: {weights}\n"
                f"  得分: {score_before_penalty:.3f} -> {score:.3f} "
                f"(penalty={penalty:.3f}, match_type={candidate.match_type})"
            )
        
        # 按分数降序排序
        ranked = sorted(candidates, key=lambda x: x.score, reverse=True)
        
        top3_scores = [f"{c.concept_name}:{c.score:.3f}" for c in ranked[:3]]
        logger.debug(
            f"[Stage2] 精排完成: top-3 候选分数 = {top3_scores}"
        )
        
        return ranked
    
    def _compute_lexical_similarity(self, mention: str, concept_name: str, aliases: List[str]) -> float:
        """
        计算词形相似度
        
        Args:
            mention: 提及文本
            concept_name: 概念名称
            aliases: 别名列表
        
        Returns:
            相似度分数 [0, 1]
        """
        mention_lower = mention.lower()
        concept_lower = concept_name.lower()
        
        # 精确匹配
        if mention_lower == concept_lower:
            return 1.0
        
        # 别名匹配
        for alias in aliases:
            if mention_lower == alias.lower():
                return 0.95
        
        # 包含关系
        if mention_lower in concept_lower or concept_lower in mention_lower:
            return 0.8
        
        # 字符级相似度（简化版 Jaccard）
        mention_chars = set(mention_lower)
        concept_chars = set(concept_lower)
        if mention_chars and concept_chars:
            jaccard = len(mention_chars & concept_chars) / len(mention_chars | concept_chars)
            return jaccard * 0.6  # 降低权重
        
        return 0.0
    
    def _compute_semantic_similarity(self, mention: str, candidate: EntityCandidate, chunk: ChunkMetadata) -> float:
        """
        计算语义相似度（使用向量余弦相似度）
        
        Args:
            mention: 提及文本
            candidate: 候选
            chunk: Chunk 元数据
        
        Returns:
            相似度分数 [0, 1]
        """
        # 1. 获取 mention 的 embedding
        mention_embedding = None
        try:
            mention_embedding = get_embedding(mention, model=settings.embedding_model)
            # 检查是否为有效向量（非全零）
            if not mention_embedding or all(x == 0.0 for x in mention_embedding):
                mention_embedding = None
        except Exception as e:
            logger.debug(f"[Stage2] 生成 mention embedding 失败: {e}")
        
        # 如果没有 mention embedding，尝试使用 chunk.embedding
        if not mention_embedding and chunk.embedding:
            mention_embedding = chunk.embedding
        
        # 2. 获取 candidate 的 embedding（从 Neo4j 查询）
        candidate_embedding = None
        if settings.enable_vector_search:
            try:
                query = """
                MATCH (c:Concept {id: $concept_id})
                WHERE c.embedding IS NOT NULL
                RETURN c.embedding AS embedding
                LIMIT 1
                """
                result = neo4j_client.execute_query(query, {"concept_id": candidate.concept_id})
                if result and result[0].get("embedding"):
                    candidate_embedding = result[0]["embedding"]
            except Exception as e:
                logger.debug(f"[Stage2] 查询 candidate embedding 失败: {e}")
        
        # 3. 如果两个向量都存在，计算余弦相似度
        if mention_embedding and candidate_embedding:
            try:
                # 确保向量维度一致
                if len(mention_embedding) == len(candidate_embedding):
                    similarity = cosine_similarity(mention_embedding, candidate_embedding)
                    # 余弦相似度范围是 [-1, 1]，归一化到 [0, 1]
                    normalized_similarity = (similarity + 1.0) / 2.0
                    logger.debug(f"[Stage2] 向量相似度: '{mention}' <-> '{candidate.concept_name}' = {normalized_similarity:.3f}")
                    return normalized_similarity
            except Exception as e:
                logger.warning(f"[Stage2] 计算向量相似度失败: {e}")
        
        # 4. 回退：基于描述的文本匹配
        if candidate.description and mention.lower() in candidate.description.lower():
            return 0.5  # 降低回退分数，因为不是真正的语义相似度
        
        # 5. 如果候选来自向量检索，使用已有的 vector_score
        if candidate.features and "vector_similarity" in candidate.features:
            vector_score = candidate.features["vector_similarity"]
            # 归一化到 [0, 1]（Neo4j 返回的 score 可能是距离，需要转换）
            if vector_score >= 0:
                return min(vector_score, 1.0)
        
        return 0.3  # 默认低分
    
    def _compute_context_match(self, mention: str, candidate: EntityCandidate, text: str, chunk: ChunkMetadata) -> float:
        """
        计算上下文一致性
        
        Args:
            mention: 提及文本
            candidate: 候选
            text: 完整文本
            chunk: Chunk 元数据
        
        Returns:
            一致性分数 [0, 1]
        """
        # 简化版：检查领域匹配
        if chunk.section_path and candidate.domain:
            # 如果 section_path 包含 domain 关键词，加分
            if candidate.domain.lower() in chunk.section_path.lower():
                return 0.8
        
        # 检查描述中的关键词是否在上下文中出现
        if candidate.description:
            desc_words = set(candidate.description.lower().split())
            text_words = set(text.lower().split())
            overlap = len(desc_words & text_words)
            if len(desc_words) > 0:
                return min(overlap / len(desc_words), 0.7)
        
        return 0.5
    
    def _compute_type_consistency(self, candidate: EntityCandidate) -> float:
        """
        计算类型一致性
        
        Args:
            candidate: 候选
        
        Returns:
            一致性分数 [0, 1]
        """
        # 简化版：有类型定义则给高分
        if candidate.node_type:
            return 0.9
        return 0.5
    
    def _compute_prior_frequency(self, candidate: EntityCandidate) -> float:
        """
        计算先验频次（概念在图谱中的连接数）
        
        Args:
            candidate: 候选
        
        Returns:
            频次分数 [0, 1]
        """
        # 查询概念的连接数
        query = """
        MATCH (c:Concept {name: $name})-[r]-()
        RETURN count(r) AS degree
        """
        
        result = neo4j_client.execute_query(query, {"name": candidate.concept_name})
        if result:
            degree = result[0].get("degree", 0)
            # 归一化到 [0, 1]（假设最大连接数为 100）
            score = min(degree / 100.0, 1.0)
            logger.debug(
                f"[Stage2] 先验频次: '{candidate.concept_name}' degree={degree}, "
                f"归一化分数={score:.3f}"
            )
            return score
        
        logger.debug(
            f"[Stage2] 先验频次: '{candidate.concept_name}' 未找到连接，返回 0.0"
        )
        return 0.0
    
    def _compute_graph_consistency(self, candidate: EntityCandidate, chunk: ChunkMetadata) -> float:
        """
        计算图一致性特征（接入阶段 4 的主题社区信息）
        
        检查 candidate 是否与 chunk 中其他已链接的实体在同一主题社区
        
        Args:
            candidate: 候选
            chunk: Chunk 元数据
        
        Returns:
            一致性分数 [0, 1]
        """
        try:
            logger.debug(
                f"[Stage2] 计算图一致性: candidate='{candidate.concept_name}' "
                f"(id={candidate.concept_id}), chunk_id={chunk.id}"
            )
            
            # 1. 查询 candidate 所属的主题社区
            candidate_theme_query = """
            MATCH (c:Concept {id: $concept_id})<-[:HAS_MEMBER]-(t:Theme)
            RETURN t.id AS theme_id, t.label AS theme_label, t.level AS level
            ORDER BY t.level ASC
            LIMIT 5
            """
            
            candidate_themes = neo4j_client.execute_query(
                candidate_theme_query,
                {"concept_id": candidate.concept_id}
            )
            
            if not candidate_themes:
                # 如果 candidate 没有主题社区，返回中等分数
                logger.debug(
                    f"[Stage2] candidate '{candidate.concept_name}' 没有主题社区，返回默认分数 0.5"
                )
                return 0.5
            
            candidate_theme_ids = {record.get("theme_id") for record in candidate_themes}
            candidate_theme_labels = [record.get("theme_label", "") for record in candidate_themes]
            logger.debug(
                f"[Stage2] candidate 主题社区: {len(candidate_themes)} 个, "
                f"ids={list(candidate_theme_ids)}, labels={candidate_theme_labels}"
            )
            
            # 2. 查询 chunk 中其他已链接的实体（通过 MENTIONS 关系）
            chunk_entities_query = """
            MATCH (chunk:Chunk {id: $chunk_id})-[:MENTIONS]->(concept:Concept)
            WHERE concept.id <> $exclude_concept_id
            MATCH (concept)<-[:HAS_MEMBER]-(theme:Theme)
            RETURN DISTINCT theme.id AS theme_id, theme.label AS theme_label
            LIMIT 20
            """
            
            chunk_themes = neo4j_client.execute_query(
                chunk_entities_query,
                {
                    "chunk_id": chunk.id,
                    "exclude_concept_id": candidate.concept_id
                }
            )
            
            if not chunk_themes:
                # 如果 chunk 中没有其他实体，返回中等分数
                logger.debug(
                    f"[Stage2] chunk {chunk.id} 中没有其他已链接实体的主题社区，返回默认分数 0.5"
                )
                return 0.5
            
            chunk_theme_ids = {record.get("theme_id") for record in chunk_themes}
            chunk_theme_labels = [record.get("theme_label", "") for record in chunk_themes]
            logger.debug(
                f"[Stage2] chunk 中其他实体的主题社区: {len(chunk_themes)} 个, "
                f"ids={list(chunk_theme_ids)}, labels={chunk_theme_labels}"
            )
            
            # 3. 计算主题社区重叠度
            overlap = len(candidate_theme_ids & chunk_theme_ids)
            total_unique = len(candidate_theme_ids | chunk_theme_ids)
            overlap_ids = list(candidate_theme_ids & chunk_theme_ids)
            
            logger.debug(
                f"[Stage2] 主题重叠计算: 重叠数={overlap}, 总唯一数={total_unique}, "
                f"重叠主题IDs={overlap_ids}"
            )
            
            if total_unique > 0:
                # Jaccard 相似度：重叠度 / 总唯一主题数
                jaccard = overlap / total_unique
                logger.debug(f"[Stage2] Jaccard 相似度: {jaccard:.3f}")
                
                # 如果完全重叠，给高分
                if overlap > 0:
                    consistency_score = 0.7 + 0.3 * jaccard  # [0.7, 1.0]
                    logger.debug(
                        f"[Stage2] 有主题重叠，计算得分: base=0.7, jaccard_weight=0.3*{jaccard:.3f}, "
                        f"最终得分={consistency_score:.3f}"
                    )
                else:
                    # 无重叠，但检查是否有相关的主题（通过主题关键词）
                    logger.debug(
                        f"[Stage2] 无直接主题重叠，检查关键词重叠..."
                    )
                    consistency_score = self._check_theme_keyword_overlap(
                        candidate_themes, chunk_themes
                    )
                
                logger.debug(
                    f"[Stage2] 图一致性最终得分: '{candidate.concept_name}' "
                    f"主题重叠={overlap}/{total_unique}, score={consistency_score:.3f}"
                )
                return consistency_score
            
            logger.debug(f"[Stage2] total_unique=0，返回默认分数 0.5")
            return 0.5
        except Exception as e:
            logger.debug(f"[Stage2] 计算图一致性失败: {e}")
            return 0.5  # 出错时返回中等分数
    
    def _check_theme_keyword_overlap(
        self,
        candidate_themes: List[Dict[str, Any]],
        chunk_themes: List[Dict[str, Any]]
    ) -> float:
        """
        检查主题关键词重叠（当主题社区不直接重叠时）
        
        Args:
            candidate_themes: candidate 的主题列表
            chunk_themes: chunk 中其他实体的主题列表
        
        Returns:
            相似度分数 [0, 1]
        """
        try:
            logger.debug(
                f"[Stage2] 检查主题关键词重叠: candidate_themes={len(candidate_themes)}, "
                f"chunk_themes={len(chunk_themes)}"
            )
            
            # 提取主题标签中的关键词
            candidate_keywords = set()
            for theme in candidate_themes:
                label = theme.get("theme_label", "")
                if label:
                    # 简单分词（按空格和标点）
                    keywords = re.findall(r'\w+', label.lower())
                    candidate_keywords.update(keywords)
            
            chunk_keywords = set()
            for theme in chunk_themes:
                label = theme.get("theme_label", "")
                if label:
                    keywords = re.findall(r'\w+', label.lower())
                    chunk_keywords.update(keywords)
            
            logger.debug(
                f"[Stage2] 提取关键词: candidate={len(candidate_keywords)} 个 "
                f"({list(candidate_keywords)[:10]}), chunk={len(chunk_keywords)} 个 "
                f"({list(chunk_keywords)[:10]})"
            )
            
            if not candidate_keywords or not chunk_keywords:
                logger.debug(
                    f"[Stage2] 关键词为空，返回默认分数 0.4 "
                    f"(candidate={len(candidate_keywords)}, chunk={len(chunk_keywords)})"
                )
                return 0.4
            
            # 计算关键词重叠度
            overlap = len(candidate_keywords & chunk_keywords)
            total = len(candidate_keywords | chunk_keywords)
            overlap_keywords = list(candidate_keywords & chunk_keywords)
            
            logger.debug(
                f"[Stage2] 关键词重叠: 重叠数={overlap}, 总唯一数={total}, "
                f"重叠关键词={overlap_keywords[:10]}"
            )
            
            if total > 0:
                keyword_similarity = overlap / total
                score = 0.4 + 0.2 * keyword_similarity  # [0.4, 0.6]
                logger.debug(
                    f"[Stage2] 关键词相似度: {keyword_similarity:.3f}, "
                    f"最终得分={score:.3f} (base=0.4, weight=0.2*{keyword_similarity:.3f})"
                )
                return score
            
            logger.debug(f"[Stage2] total=0，返回默认分数 0.4")
            return 0.4
            
        except Exception as e:
            logger.debug(f"[Stage2] 检查主题关键词重叠失败: {e}")
            return 0.4
    
    def _fetch_concepts_for_chunk(self, chunk_id: str) -> List[Dict[str, Any]]:
        """
        查询 Chunk 关联的 Concept 节点
        
        Args:
            chunk_id: Chunk ID
        
        Returns:
            实体列表
        """
        query = """
        MATCH (c:Chunk {id: $chunk_id})-[:MENTIONS]->(concept:Concept)
        RETURN DISTINCT concept.id AS concept_id,
               concept.name AS concept_name,
               concept.description AS description,
               concept.domain AS domain
        """
        
        result = neo4j_client.execute_query(query, {"chunk_id": chunk_id})
        
        entities = []
        for record in result:
            entities.append({
                "concept_id": record.get("concept_id"),
                "concept_name": record.get("concept_name"),
                "confidence": 0.85,  # 默认置信度
                "mention_text": record.get("concept_name"),
                "description": record.get("description"),
                "domain": record.get("domain")
            })
        
        return entities
    
    def _basic_extract(self, chunk: ChunkMetadata) -> List[Dict[str, Any]]:
        """
        基础实体抽取（回退方案）
        
        使用简单的规则提取可能的实体（专有名词、大写词等）
        """
        import re
        
        # 根据 coref_mode 决定是否使用 resolved_text
        use_resolved_text = (
            chunk.resolved_text and 
            chunk.coref_mode == "rewrite"
        )
        text = chunk.resolved_text if use_resolved_text else chunk.text
        entities = []
        
        # 提取可能的实体（大写开头的词、中文名词短语）
        # 1. 英文专有名词（大写开头，2+ 字符）
        proper_nouns = re.findall(r'\b([A-Z][a-zA-Z0-9]{2,})\b', text)
        
        # 2. 中文名词短语（2-5 个字符）
        chinese_nouns = re.findall(r'[\u4e00-\u9fff]{2,5}', text)
        
        # 合并并去重
        candidates = list(set(proper_nouns + chinese_nouns))
        
        # 过滤常见停用词
        stopwords = ['这个', '那个', '这些', '那些', '它们', '他们', '我们', '你们']
        candidates = [c for c in candidates if c not in stopwords]
        
        # 生成实体记录
        for candidate in candidates[:10]:  # 限制最多 10 个
            concept_id = hashlib.sha256(candidate.encode()).hexdigest()[:16]
            entities.append({
                "concept_id": concept_id,
                "concept_name": candidate,
                "confidence": 0.6,  # 较低置信度（规则提取）
                "mention_text": candidate,
                "description": None,
                "domain": None
            })
        
        return entities


__all__ = ["EntityLinker"]

