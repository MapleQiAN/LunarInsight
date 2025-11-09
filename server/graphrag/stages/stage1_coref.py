"""
阶段 1: 指代消解 (Coreference Resolution)

解析代词与指代关系，生成别名映射
采用"先评估、再决策、再应用"的质量门控范式
"""

import logging
import re
from typing import Dict, Tuple, List, Optional, Literal, Any
from dataclasses import dataclass, field
from enum import Enum
from server.graphrag.models.chunk import ChunkMetadata
from server.graphrag.config import get_config

logger = logging.getLogger("graphrag.stage1")


class MentionType(Enum):
    """提及类型"""
    PRONOUN = "pronoun"          # 代词（它、他、她、this、that）
    DEMONSTRATIVE = "demonstrative"  # 指示词（该、此、其、前者、后者）
    ABBREVIATION = "abbreviation"    # 简称（括号引入的别名）
    NOMINAL = "nominal"          # 名词性省略


@dataclass
class Mention:
    """提及（需要消解的指代）"""
    text: str                    # 提及文本
    type: MentionType           # 提及类型
    position: int               # 在文本中的位置
    sentence_idx: int          # 所在句子索引
    span: Tuple[int, int]      # 字符范围 (start, end)


@dataclass
class Antecedent:
    """先行词（候选实体）"""
    text: str                    # 实体文本
    position: int               # 在文本中的位置
    sentence_idx: int          # 所在句子索引
    span: Tuple[int, int]      # 字符范围 (start, end)
    entity_type: Optional[str] = None  # 实体类型（如有 NER）


@dataclass
class Match:
    """匹配结果（提及→先行词）"""
    mention: Mention
    antecedent: Antecedent
    score: float                # 匹配分数
    confidence: float           # 置信度
    evidence_type: str          # 证据类型（parenthesis/abbreviation/distance/type/semantic）
    sentence_distance: int      # 句距
    is_conflict: bool = False   # 是否冲突


@dataclass
class CorefResult:
    """指代消解结果"""
    resolved_text: Optional[str]  # 消解后的文本（可能为 None）
    alias_map: Dict[str, str]     # 别名映射 {surface: canonical}
    mode: Literal["rewrite", "local", "alias_only", "skip"]  # 决策模式
    coverage: float              # 覆盖率
    conflict: float              # 冲突率
    metrics: Dict[str, Any]      # 分桶统计
    provenance: List[Dict[str, Any]]  # 证据链
    matches: List[Match] = field(default_factory=list)  # 所有匹配
    
    def __iter__(self):
        """向后兼容：支持解包为 (resolved_text, alias_map)"""
        return iter((self.resolved_text, self.alias_map))


class CoreferenceResolver:
    """
    指代消解器
    
    采用质量门控范式：
    1. 检测提及与候选先行词
    2. 匹配打分与一致性校验
    3. 计算质量指标（coverage, conflict）
    4. 根据阈值决定替换模式（rewrite/local/alias_only/skip）
    """
    
    def __init__(self):
        self.config = get_config()
        self.thresholds = self.config.thresholds.coreference
        
        # 获取配置参数
        self.quality_gates = self.thresholds.get("quality_gates", {})
        self.scoring_weights = self.thresholds.get("scoring_weights", {})
        self.candidate_gen = self.thresholds.get("candidate_generation", {})
        self.consistency_cfg = self.thresholds.get("consistency", {})
        
        # 默认值
        self.context_window = self.candidate_gen.get("context_window", 3)
        self.max_candidates = self.candidate_gen.get("max_candidates_per_mention", 5)
        
        logger.info("CoreferenceResolver initialized with quality gates")
    
    def resolve(self, chunk: ChunkMetadata) -> CorefResult:
        """
        消解 Chunk 中的指代关系
        
        Args:
            chunk: 输入 Chunk
        
        Returns:
            CorefResult: 包含 resolved_text、alias_map、质量指标等
        """
        logger.info(f"[Stage1] ========== 开始指代消解 ==========")
        logger.info(f"[Stage1] Chunk ID: {chunk.id}")
        logger.info(f"[Stage1] 文本长度: {len(chunk.text)} 字符")
        logger.debug(f"[Stage1] 文本预览: {chunk.text[:200]}..." if len(chunk.text) > 200 else f"[Stage1] 文本: {chunk.text}")
        
        text = chunk.text
        
        # 0. 噪声过滤（表格、代码块、短句对话）
        if self._should_skip(text):
            logger.debug(f"跳过噪声文本: chunk_id={chunk.id}")
            return CorefResult(
                resolved_text=None,
                alias_map={},
                mode="skip",
                coverage=0.0,
                conflict=0.0,
                metrics={},
                provenance=[]
            )
        
        # 1. 检测提及
        mentions = self._detect_mentions(text)
        logger.info(f"[Stage1] 检测到 {len(mentions)} 个提及")
        if mentions:
            for i, m in enumerate(mentions, 1):
                logger.info(f"  提及 {i}: '{m.text}' (类型={m.type.value}, 位置={m.position}, 句索引={m.sentence_idx})")
        
        if not mentions:
            logger.info(f"[Stage1] 未检测到提及，跳过消解")
            return CorefResult(
                resolved_text=text,
                alias_map={},
                mode="skip",
                coverage=0.0,
                conflict=0.0,
                metrics={},
                provenance=[]
            )
        
        # 2. 提取括号别名（强约束）
        parenthesis_aliases = self._extract_parenthesis_aliases(text)
        logger.info(f"[Stage1] 提取到 {len(parenthesis_aliases)} 个括号别名")
        if parenthesis_aliases:
            for alias, canonical in parenthesis_aliases.items():
                logger.info(f"  别名映射: '{alias}' → '{canonical}'")
        
        # 3. 生成候选先行词
        antecedents = self._generate_antecedents(text, mentions)
        logger.info(f"[Stage1] 生成 {len(antecedents)} 个候选先行词")
        if antecedents:
            # 只显示前10个，避免日志过长
            display_count = min(10, len(antecedents))
            for i, ant in enumerate(antecedents[:display_count], 1):
                logger.info(f"  候选 {i}: '{ant.text}' (位置={ant.position}, 句索引={ant.sentence_idx}, 类型={ant.entity_type})")
            if len(antecedents) > display_count:
                logger.info(f"  ... 还有 {len(antecedents) - display_count} 个候选")
        
        # 4. 匹配打分
        matches = self._match_and_score(mentions, antecedents, parenthesis_aliases)
        logger.info(f"[Stage1] 生成 {len(matches)} 个匹配")
        if matches:
            for i, match in enumerate(matches, 1):
                conflict_mark = " [冲突]" if match.is_conflict else ""
                logger.info(f"  匹配 {i}: '{match.mention.text}' → '{match.antecedent.text}' "
                          f"(分数={match.score:.3f}, 置信度={match.confidence:.3f}, "
                          f"句距={match.sentence_distance}, 证据={match.evidence_type}){conflict_mark}")
        
        # 5. 一致性校验
        validated_matches = self._validate_consistency(matches, parenthesis_aliases)
        conflict_count = sum(1 for m in validated_matches if m.is_conflict)
        logger.info(f"[Stage1] 一致性校验后剩余 {len(validated_matches)} 个匹配 (其中 {conflict_count} 个冲突)")
        
        # 6. 计算质量指标
        coverage, conflict, metrics = self._compute_quality_metrics(
            mentions, validated_matches
        )
        logger.info(f"[Stage1] 质量指标: 覆盖率={coverage:.2%}, 冲突率={conflict:.2%}")
        logger.info(f"[Stage1] 分桶统计: 总提及={metrics.get('total_mentions', 0)}, "
                   f"已消解={metrics.get('resolved_mentions', 0)}, "
                   f"代词覆盖率={metrics.get('pronoun_coverage', 0):.2%}, "
                   f"简称覆盖率={metrics.get('abbrev_coverage', 0):.2%}")
        
        # 7. 决策路由
        mode = self._decide_mode(coverage, conflict)
        logger.info(f"[Stage1] 决策模式: {mode} (覆盖率={coverage:.2%}, 冲突率={conflict:.2%})")
        
        # 8. 生成产物
        resolved_text, alias_map, provenance = self._generate_artifacts(
            text, validated_matches, mode, parenthesis_aliases
        )
        logger.info(f"[Stage1] 生成产物: alias_map包含{len(alias_map)}个映射, provenance包含{len(provenance)}条记录")
        if alias_map:
            logger.info(f"[Stage1] 别名映射表:")
            for surface, canonical in alias_map.items():
                logger.info(f"  '{surface}' → '{canonical}'")
        if resolved_text and resolved_text != text:
            logger.info(f"[Stage1] 文本已替换 (原文长度={len(text)}, 替换后长度={len(resolved_text)})")
            # 显示替换前后的对比（前100字符）
            preview_len = min(100, len(text))
            logger.debug(f"[Stage1] 原文预览: {text[:preview_len]}...")
            logger.debug(f"[Stage1] 替换后预览: {resolved_text[:preview_len]}...")
        elif resolved_text is None:
            logger.info(f"[Stage1] 未生成resolved_text (模式={mode})")
        
        logger.info(f"[Stage1] ========== 指代消解完成 ==========")
        logger.info(f"[Stage1] 最终结果: 模式={mode}, 覆盖率={coverage:.2%}, 冲突率={conflict:.2%}, "
                   f"别名映射数={len(alias_map)}, 证据链数={len(provenance)}")
        
        return CorefResult(
            resolved_text=resolved_text,
            alias_map=alias_map,
            mode=mode,
            coverage=coverage,
            conflict=conflict,
            metrics=metrics,
            provenance=provenance,
            matches=validated_matches
        )
    
    def _should_skip(self, text: str) -> bool:
        """判断是否应该跳过（噪声场景）"""
        # 短文本（可能是标题、列表项）
        if len(text.strip()) < 50:
            logger.debug(f"[Stage1] 跳过: 文本太短 ({len(text.strip())} 字符 < 50)")
            return True
        
        # 表格标记
        if re.search(r'\|.*\|', text) and text.count('|') > 4:
            logger.debug(f"[Stage1] 跳过: 检测到表格标记 (包含 {text.count('|')} 个 '|')")
            return True
        
        # 代码块标记
        if re.search(r'```|`.*`', text):
            logger.debug(f"[Stage1] 跳过: 检测到代码块标记")
            return True
        
        # 对话模式（短句 + 引号）
        sentences = re.split(r'[。！？\.\!\?]', text)
        if len(sentences) > 3 and all(len(s.strip()) < 30 for s in sentences[:3]):
            logger.debug(f"[Stage1] 跳过: 检测到对话模式 (前3句平均长度 < 30)")
            return True
        
        return False
    
    def _detect_mentions(self, text: str) -> List[Mention]:
        """检测提及"""
        mentions = []
        sentences = self._split_sentences(text)
        
        # 代词列表
        pronouns_zh = ['它', '他', '她', '它们', '他们', '她们', '其', '它们']
        pronouns_en = ['this', 'that', 'these', 'those', 'it', 'they', 'them']
        
        # 指示词
        demonstratives = ['该', '此', '其', '前者', '后者', '上述', '下述']
        
        for sent_idx, sentence in enumerate(sentences):
            sent_start = text.find(sentence)
            if sent_start == -1:
                continue
            
            # 检测代词
            for pronoun in pronouns_zh + pronouns_en:
                pattern = r'\b' + re.escape(pronoun) + r'\b'
                for match in re.finditer(pattern, sentence, re.IGNORECASE):
                    pos = sent_start + match.start()
                    mentions.append(Mention(
                        text=pronoun,
                        type=MentionType.PRONOUN,
                        position=pos,
                        sentence_idx=sent_idx,
                        span=(pos, pos + len(pronoun))
                    ))
            
            # 检测指示词
            for demo in demonstratives:
                if demo in sentence:
                    pos = sent_start + sentence.find(demo)
                    mentions.append(Mention(
                        text=demo,
                        type=MentionType.DEMONSTRATIVE,
                        position=pos,
                        sentence_idx=sent_idx,
                        span=(pos, pos + len(demo))
                    ))
        
        return mentions
    
    def _extract_parenthesis_aliases(self, text: str) -> Dict[str, str]:
        """
        提取括号别名（强约束）
        
        支持格式：
        - "人工智能（AI）" → {AI: 人工智能}
        - "自然语言处理（Natural Language Processing, NLP）" → {NLP: 自然语言处理}
        """
        aliases = {}
        
        # 匹配中文括号：X（Y）或 X（Y, Z）
        pattern = r'([^（(]+)[（(]([^）)]+)[）)]'
        matches = re.finditer(pattern, text)
        
        for match in matches:
            full_name = match.group(1).strip()
            alias_text = match.group(2).strip()
            
            # 处理多个别名（逗号分隔）
            alias_parts = [a.strip() for a in alias_text.split(',')]
            
            for alias in alias_parts:
                if alias and full_name:
                    # 取最后一个作为主要别名（通常是缩写）
                    if len(alias_parts) > 1 and alias == alias_parts[-1]:
                        aliases[alias] = full_name
                    elif len(alias_parts) == 1:
                        aliases[alias] = full_name
        
        return aliases
    
    def _generate_antecedents(self, text: str, mentions: List[Mention]) -> List[Antecedent]:
        """生成候选先行词"""
        antecedents = []
        sentences = self._split_sentences(text)
        
        # 提取可能的实体（大写开头、中文名词短语）
        for sent_idx, sentence in enumerate(sentences):
            sent_start = text.find(sentence)
            if sent_start == -1:
                continue
            
            # 英文专有名词（大写开头）
            pattern_en = r'\b([A-Z][a-zA-Z0-9]+)\b'
            for match in re.finditer(pattern_en, sentence):
                pos = sent_start + match.start()
                antecedents.append(Antecedent(
                    text=match.group(1),
                    position=pos,
                    sentence_idx=sent_idx,
                    span=(pos, pos + len(match.group(1)))
                ))
            
            # 中文名词短语（2-6 字）
            pattern_zh = r'([\u4e00-\u9fff]{2,6})'
            for match in re.finditer(pattern_zh, sentence):
                pos = sent_start + match.start()
                # 过滤常见停用词
                word = match.group(1)
                if word not in ['这个', '那个', '这些', '那些', '它们', '他们']:
                    antecedents.append(Antecedent(
                        text=word,
                        position=pos,
                        sentence_idx=sent_idx,
                        span=(pos, pos + len(word))
                    ))
        
        return antecedents
    
    def _match_and_score(
        self,
        mentions: List[Mention],
        antecedents: List[Antecedent],
        parenthesis_aliases: Dict[str, str]
    ) -> List[Match]:
        """匹配打分"""
        matches = []
        
        for mention in mentions:
            # 获取候选先行词（在语境窗口内）
            candidates = self._get_candidates(mention, antecedents)
            
            if not candidates:
                logger.debug(f"[Stage1] 提及 '{mention.text}' 无候选先行词")
                continue
            
            logger.debug(f"[Stage1] 提及 '{mention.text}' 有 {len(candidates)} 个候选先行词")
            
            # 为每个候选打分
            scored_candidates = []
            for candidate in candidates:
                score = self._score_match(mention, candidate, parenthesis_aliases)
                scored_candidates.append((candidate, score))
                logger.debug(f"    候选 '{candidate.text}': 分数={score:.3f}")
            
            # 排序，取 Top-K
            scored_candidates.sort(key=lambda x: x[1], reverse=True)
            top_candidates = scored_candidates[:self.max_candidates]
            
            # 检查多解风险（前三名分差过小）
            is_multi_solution = False
            if len(top_candidates) >= 3:
                scores = [s for _, s in top_candidates[:3]]
                if scores[0] - scores[2] < 0.1:  # 分差小于 0.1
                    is_multi_solution = True
                    logger.debug(f"    多解风险: 前三名分差={scores[0] - scores[2]:.3f} < 0.1")
            
            # 生成匹配（只取通过阈值的）
            min_score = 0.3  # 最低分数阈值
            valid_matches = []
            for candidate, score in top_candidates:
                if score >= min_score:
                    sentence_distance = abs(mention.sentence_idx - candidate.sentence_idx)
                    match = Match(
                        mention=mention,
                        antecedent=candidate,
                        score=score,
                        confidence=min(score, 1.0),
                        evidence_type=self._get_evidence_type(mention, candidate, parenthesis_aliases),
                        sentence_distance=sentence_distance,
                        is_conflict=is_multi_solution
                    )
                    matches.append(match)
                    valid_matches.append((candidate.text, score))
                else:
                    logger.debug(f"    候选 '{candidate.text}' 分数 {score:.3f} < 阈值 {min_score}，跳过")
            
            if valid_matches:
                logger.debug(f"    有效匹配: {valid_matches}")
        
        return matches
    
    def _get_candidates(self, mention: Mention, antecedents: List[Antecedent]) -> List[Antecedent]:
        """获取候选先行词（在语境窗口内，且在提及之前）"""
        candidates = []
        
        # 指示词"该/此/其"只允许回指最近一句
        is_demonstrative_near = (
            mention.type == MentionType.DEMONSTRATIVE and 
            mention.text in ['该', '此', '其']
        )
        max_distance = 1 if is_demonstrative_near else self.context_window
        
        for ant in antecedents:
            # 必须在提及之前
            if ant.position >= mention.position:
                continue
            
            # 必须在语境窗口内（指示词特殊约束）
            sentence_distance = mention.sentence_idx - ant.sentence_idx
            if sentence_distance > max_distance:
                continue
            
            # 跨类回指禁止：检查类型兼容性
            if not self._is_type_compatible(mention, ant):
                continue
            
            candidates.append(ant)
        
        return candidates
    
    def _score_match(
        self,
        mention: Mention,
        antecedent: Antecedent,
        parenthesis_aliases: Dict[str, str]
    ) -> float:
        """匹配打分"""
        score = 0.0
        
        # 1. 句距衰减（越近越高）
        sentence_distance = abs(mention.sentence_idx - antecedent.sentence_idx)
        distance_score = max(0, 1.0 - sentence_distance * 0.2)
        weight = self.scoring_weights.get("distance_decay", 0.4)
        score += distance_score * weight
        
        # 跨段长距离惩罚（超过窗口上限时大幅降分）
        if sentence_distance > self.context_window:
            # 跨段长距离：统一降级，降低置信度
            penalty = 0.5  # 大幅降分
            score *= (1.0 - penalty)
        
        # 2. 括号简称强约束（最高优先级）
        if mention.text in parenthesis_aliases:
            canonical = parenthesis_aliases[mention.text]
            if antecedent.text == canonical:
                boost = self.scoring_weights.get("parenthesis_boost", 0.8)
                score += boost
        
        # 3. 类型一致性（简化版：基于文本特征）
        type_score = self._check_type_consistency(mention, antecedent)
        weight = self.scoring_weights.get("type_consistency", 0.2)
        score += type_score * weight
        
        # 4. 语义相似度（可选，当前简化）
        # 如果有向量模型，可以计算余弦相似度
        semantic_weight = self.scoring_weights.get("semantic_similarity", 0.0)
        if semantic_weight > 0:
            semantic_score = self._compute_semantic_similarity(mention, antecedent)
            score += semantic_score * semantic_weight
        
        # 5. 句法一致性（可选，当前简化）
        # 需要句法解析，当前跳过
        syntactic_weight = self.scoring_weights.get("syntactic_consistency", 0.0)
        if syntactic_weight > 0:
            syntactic_score = self._compute_syntactic_consistency(mention, antecedent)
            score += syntactic_score * syntactic_weight
        
        # 6. 语言匹配（英文代词在中英混排时优先匹配英文实体）
        lang_score = self._check_language_match(mention, antecedent)
        score += lang_score * 0.1  # 小权重
        
        # 7. 并列结构处理（"前者/后者"）
        if mention.text in ['前者', '后者']:
            parallel_score = self._check_parallel_structure(mention, antecedent)
            score += parallel_score * 0.3
        
        return min(score, 1.0)
    
    def _is_type_compatible(self, mention: Mention, antecedent: Antecedent) -> bool:
        """
        检查类型兼容性（跨类回指禁止）
        
        规则：
        - Person 不可回指 ORG
        - 时间词不可回技术概念
        - 机构名不可回人名
        """
        ant_text = antecedent.text
        ant_type = antecedent.entity_type
        
        # 如果有 NER 类型，严格检查
        if ant_type:
            if ant_type == "PERSON" and mention.text in ['它', '它们', 'it', 'they']:
                # 代词"它"不能回指人名
                return False
            if ant_type == "ORG" and mention.text in ['他', '她', '他们', '她们', 'he', 'she', 'they']:
                # 人称代词不能回指机构
                return False
            if ant_type == "TIME" and mention.text in ['它', '它们', 'it', 'they']:
                # 时间词不能回指技术概念（简化：通过文本特征判断）
                if re.search(r'(技术|算法|模型|系统|框架)', ant_text):
                    return False
        
        # 基于文本特征的启发式规则
        # 中文人名（2-4字，常见姓氏）
        if re.match(r'^[王李张刘陈杨黄赵吴周徐孙马朱胡郭何高林罗郑梁谢宋唐许韩冯邓曹彭曾肖田董袁潘于蒋蔡余杜叶程苏魏吕丁任沈姚卢姜崔钟谭陆汪范金石廖贾夏韦付方白邹孟熊秦邱江尹薛闫段雷侯龙史陶黎贺顾毛郝龚邵万钱严覃武戴莫孔向汤]', ant_text):
            if mention.text in ['它', '它们', 'it', 'they']:
                return False  # 人名不能用"它"回指
        
        # 机构名特征（包含"公司"、"集团"、"大学"等）
        if re.search(r'(公司|集团|大学|学院|机构|组织|部门|中心)', ant_text):
            if mention.text in ['他', '她', '他们', '她们', 'he', 'she', 'they']:
                return False  # 机构不能用"他/她"回指
        
        # 时间词特征
        if re.search(r'(\d{4}年|\d{1,2}月|昨天|今天|明天|去年|今年|明年)', ant_text):
            if mention.text in ['它', '它们', 'it', 'they']:
                # 时间词不能回指技术概念（简化判断）
                return True  # 时间词本身可以作为先行词，但需要进一步检查
        
        return True
    
    def _check_type_consistency(self, mention: Mention, antecedent: Antecedent) -> float:
        """检查类型一致性（用于打分）"""
        # 如果类型不兼容，直接返回 0
        if not self._is_type_compatible(mention, antecedent):
            return 0.0
        
        # 如果提及是代词，检查先行词是否是人名/机构名
        if mention.type == MentionType.PRONOUN:
            # 中文人名通常 2-4 字
            if re.match(r'^[\u4e00-\u9fff]{2,4}$', antecedent.text):
                return 0.8
            # 英文专有名词
            if re.match(r'^[A-Z][a-z]+$', antecedent.text):
                return 0.8
        
        return 0.5  # 默认中等一致性
    
    def _get_evidence_type(
        self,
        mention: Mention,
        antecedent: Antecedent,
        parenthesis_aliases: Dict[str, str]
    ) -> str:
        """获取证据类型"""
        if mention.text in parenthesis_aliases:
            return "parenthesis"
        
        # 检查是否是简称映射
        if mention.text in ["模型", "算法", "方法", "技术", "系统", "框架", "架构"]:
            return "abbreviation"
        
        sentence_distance = abs(mention.sentence_idx - antecedent.sentence_idx)
        
        # 跨段长距离标记
        if sentence_distance > self.context_window:
            return "cross_segment_long_distance"
        
        if sentence_distance == 0:
            return "same_sentence"
        elif sentence_distance <= 2:
            return "near_distance"
        else:
            return "far_distance"
    
    def _validate_consistency(
        self,
        matches: List[Match],
        parenthesis_aliases: Dict[str, str]
    ) -> List[Match]:
        """一致性校验"""
        validated = []
        alias_conflicts = 0
        
        # 1. 别名一致性：括号别名必须一致
        alias_map = {}  # {mention_text: canonical}
        for match in matches:
            if match.mention.text in parenthesis_aliases:
                canonical = parenthesis_aliases[match.mention.text]
                if match.mention.text not in alias_map:
                    alias_map[match.mention.text] = canonical
                    logger.debug(f"[Stage1] 别名一致性: '{match.mention.text}' → '{canonical}'")
                elif alias_map[match.mention.text] != canonical:
                    # 冲突：跳过此匹配
                    match.is_conflict = True
                    alias_conflicts += 1
                    logger.debug(f"[Stage1] 别名冲突: '{match.mention.text}' 已映射到 '{alias_map[match.mention.text]}', "
                               f"但匹配到 '{canonical}', 标记为冲突")
                    continue
            
            validated.append(match)
        
        if alias_conflicts > 0:
            logger.debug(f"[Stage1] 别名一致性校验: 发现 {alias_conflicts} 个冲突")
        
        # 2. 窗口内一致性（简化版：同一提及在同一窗口应指向同一先行词）
        # 按提及文本分组
        mention_groups: Dict[str, List[Match]] = {}
        for match in validated:
            key = match.mention.text
            if key not in mention_groups:
                mention_groups[key] = []
            mention_groups[key].append(match)
        
        # 检查每组内的冲突
        final_validated = []
        window_conflicts = 0
        for key, group in mention_groups.items():
            if len(group) == 1:
                final_validated.append(group[0])
            else:
                # 多个匹配：选择分数最高的，其他标记为冲突
                group.sort(key=lambda m: m.score, reverse=True)
                best_match = group[0]
                final_validated.append(best_match)
                logger.debug(f"[Stage1] 窗口一致性: 提及 '{key}' 有 {len(group)} 个匹配, "
                           f"选择最高分 '{best_match.antecedent.text}' (分数={best_match.score:.3f})")
                # 其他标记为冲突（但不丢弃，用于计算冲突率）
                for m in group[1:]:
                    m.is_conflict = True
                    window_conflicts += 1
                    final_validated.append(m)
                    logger.debug(f"[Stage1]  标记冲突: '{m.antecedent.text}' (分数={m.score:.3f})")
        
        if window_conflicts > 0:
            logger.debug(f"[Stage1] 窗口一致性校验: 发现 {window_conflicts} 个冲突")
        
        return final_validated
    
    def _compute_quality_metrics(
        self,
        mentions: List[Mention],
        matches: List[Match]
    ) -> Tuple[float, float, Dict[str, Any]]:
        """计算质量指标"""
        total_mentions = len(mentions)
        if total_mentions == 0:
            return 0.0, 0.0, {}
        
        # 覆盖率：已消解的提及数 / 总提及数
        resolved_mentions = set()
        for match in matches:
            if not match.is_conflict:
                resolved_mentions.add(match.mention.text)
        
        coverage = len(resolved_mentions) / total_mentions if total_mentions > 0 else 0.0
        
        # 冲突率：冲突匹配数 / 总匹配数
        conflict_matches = sum(1 for m in matches if m.is_conflict)
        conflict = conflict_matches / len(matches) if matches else 0.0
        
        # 分桶统计
        pronoun_mentions = [m for m in mentions if m.type == MentionType.PRONOUN]
        abbrev_mentions = [m for m in mentions if m.type == MentionType.ABBREVIATION]
        
        pronoun_resolved = sum(1 for m in pronoun_mentions if m.text in resolved_mentions)
        abbrev_resolved = sum(1 for m in abbrev_mentions if m.text in resolved_mentions)
        
        pronoun_coverage = pronoun_resolved / len(pronoun_mentions) if pronoun_mentions else 0.0
        abbrev_coverage = abbrev_resolved / len(abbrev_mentions) if abbrev_mentions else 0.0
        
        metrics = {
            "pronoun_coverage": pronoun_coverage,
            "abbrev_coverage": abbrev_coverage,
            "total_mentions": total_mentions,
            "resolved_mentions": len(resolved_mentions),
            "total_matches": len(matches),
            "conflict_matches": conflict_matches
        }
        
        return coverage, conflict, metrics
    
    def _decide_mode(self, coverage: float, conflict: float) -> Literal["rewrite", "local", "alias_only", "skip"]:
        """决策路由"""
        gates = self.quality_gates
        
        logger.debug(f"[Stage1] 决策路由: 覆盖率={coverage:.2%}, 冲突率={conflict:.2%}")
        
        # rewrite 模式
        rewrite_coverage_min = gates.get("rewrite_coverage_min", 0.6)
        rewrite_conflict_max = gates.get("rewrite_conflict_max", 0.15)
        logger.debug(f"  检查 rewrite 模式: 需要覆盖率>={rewrite_coverage_min:.2%} 且 冲突率<={rewrite_conflict_max:.2%}")
        if coverage >= rewrite_coverage_min and conflict <= rewrite_conflict_max:
            logger.debug(f"  ✓ 满足 rewrite 条件")
            return "rewrite"
        else:
            logger.debug(f"  ✗ 不满足 rewrite 条件 (覆盖率{'满足' if coverage >= rewrite_coverage_min else '不足'}, "
                       f"冲突率{'满足' if conflict <= rewrite_conflict_max else '过高'})")
        
        # local 模式
        local_coverage_min = gates.get("local_coverage_min", 0.3)
        local_conflict_max = gates.get("local_conflict_max", 0.25)
        logger.debug(f"  检查 local 模式: 需要覆盖率>={local_coverage_min:.2%} 且 冲突率<={local_conflict_max:.2%}")
        if coverage >= local_coverage_min and conflict <= local_conflict_max:
            logger.debug(f"  ✓ 满足 local 条件")
            return "local"
        else:
            logger.debug(f"  ✗ 不满足 local 条件 (覆盖率{'满足' if coverage >= local_coverage_min else '不足'}, "
                       f"冲突率{'满足' if conflict <= local_conflict_max else '过高'})")
        
        # alias_only 模式
        alias_only_coverage_min = gates.get("alias_only_coverage_min", 0.1)
        logger.debug(f"  检查 alias_only 模式: 需要覆盖率>={alias_only_coverage_min:.2%}")
        if coverage >= alias_only_coverage_min:
            logger.debug(f"  ✓ 满足 alias_only 条件")
            return "alias_only"
        else:
            logger.debug(f"  ✗ 不满足 alias_only 条件 (覆盖率不足)")
        
        # skip 模式
        logger.debug(f"  → 选择 skip 模式")
        return "skip"
    
    def _generate_artifacts(
        self,
        text: str,
        matches: List[Match],
        mode: Literal["rewrite", "local", "alias_only", "skip"],
        parenthesis_aliases: Dict[str, str]
    ) -> Tuple[Optional[str], Dict[str, str], List[Dict[str, Any]]]:
        """生成产物"""
        alias_map = {}
        provenance = []
        resolved_text = None
        
        # 构建别名映射
        for match in matches:
            if not match.is_conflict:
                alias_map[match.mention.text] = match.antecedent.text
                provenance.append({
                    "mention": match.mention.text,
                    "canonical": match.antecedent.text,
                    "confidence": match.confidence,
                    "evidence_type": match.evidence_type,
                    "sentence_distance": match.sentence_distance,
                    "mention_position": match.mention.position,
                    "antecedent_position": match.antecedent.position
                })
        
        # 添加括号别名
        alias_map.update(parenthesis_aliases)
        
        # 根据模式决定是否替换文本
        if mode == "rewrite":
            # 强替换：替换所有非冲突的匹配
            resolved_text = text
            for match in matches:
                if not match.is_conflict:
                    pattern = r'\b' + re.escape(match.mention.text) + r'\b'
                    resolved_text = re.sub(pattern, match.antecedent.text, resolved_text)
        elif mode == "local":
            # 局部替换：只替换近距离的匹配
            resolved_text = text
            for match in matches:
                if not match.is_conflict and match.sentence_distance <= 1:
                    pattern = r'\b' + re.escape(match.mention.text) + r'\b'
                    resolved_text = re.sub(pattern, match.antecedent.text, resolved_text)
        # alias_only 和 skip 模式不替换文本
        
        return resolved_text, alias_map, provenance
    
    def _compute_semantic_similarity(self, mention: Mention, antecedent: Antecedent) -> float:
        """
        计算语义相似度（占位实现）
        
        后续可接入：
        - 向量模型（sentence-transformers）
        - 词向量（Word2Vec/GloVe）
        - 预训练语言模型（BERT/RoBERTa）
        """
        # 当前简化：基于文本重叠
        if mention.text.lower() in antecedent.text.lower() or antecedent.text.lower() in mention.text.lower():
            return 0.6
        return 0.3
    
    def _compute_syntactic_consistency(self, mention: Mention, antecedent: Antecedent) -> float:
        """
        计算句法一致性（占位实现）
        
        后续可接入：
        - 句法解析器（spaCy/NLTK）
        - 数/性/人称匹配
        - 语法角色一致性
        """
        # 当前简化：基于文本特征
        # 英文：单复数匹配
        if mention.text in ['it', 'this', 'that'] and antecedent.text.endswith('s'):
            return 0.4  # 单数代词匹配复数名词，降分
        if mention.text in ['they', 'these', 'those'] and not antecedent.text.endswith('s'):
            return 0.4  # 复数代词匹配单数名词，降分
        
        return 0.5  # 默认中等一致性
    
    def _check_language_match(self, mention: Mention, antecedent: Antecedent) -> float:
        """
        检查语言匹配（英文代词在中英混排时优先匹配英文实体）
        """
        mention_is_en = bool(re.search(r'[a-zA-Z]', mention.text))
        ant_is_en = bool(re.search(r'[a-zA-Z]', antecedent.text))
        
        if mention_is_en and ant_is_en:
            return 0.8  # 英文匹配英文，加分
        if not mention_is_en and not ant_is_en:
            return 0.8  # 中文匹配中文，加分
        
        return 0.3  # 跨语言匹配，降分
    
    def _check_parallel_structure(self, mention: Mention, antecedent: Antecedent) -> float:
        """
        检查并列结构（"前者/后者"处理）
        
        规则：
        - "前者"应匹配并列结构中的第一个实体
        - "后者"应匹配并列结构中的第二个实体
        """
        # 当前简化：基于位置和文本特征
        # 后续可接入句法解析器检测并列结构
        
        if mention.text == '前者':
            # "前者"通常指向更早出现的实体
            # 如果 antecedent 在 mention 之前较远，可能是并列的第一个
            sentence_distance = mention.sentence_idx - antecedent.sentence_idx
            if sentence_distance >= 2:
                return 0.6
        elif mention.text == '后者':
            # "后者"通常指向较近的实体
            sentence_distance = mention.sentence_idx - antecedent.sentence_idx
            if sentence_distance <= 2:
                return 0.6
        
        return 0.3  # 默认较低分数
    
    def _split_sentences(self, text: str) -> List[str]:
        """分割句子"""
        # 按中英文句号、问号、感叹号分割
        pattern = r'[。！？\.\!\?]+'
        sentences = re.split(pattern, text)
        return [s.strip() for s in sentences if s.strip()]


__all__ = ["CoreferenceResolver", "CorefResult"]
