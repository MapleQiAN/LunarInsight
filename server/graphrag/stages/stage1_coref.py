"""
阶段 1: 指代消解 (Coreference Resolution)

解析代词与指代关系，生成别名映射
采用"先评估、再决策、再应用"的质量门控范式

架构：
- CoreferenceResolver: 主入口，负责模式选择和路由
- RuleBasedResolver: 规则模式实现
- LLMResolver: LLM模式实现
"""

import logging
import re
import json
from typing import Dict, Tuple, List, Optional, Literal, Any
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod
from graphrag.models.chunk import ChunkMetadata
from graphrag.config import get_config
from infra.ai_providers import AIProviderFactory, BaseAIClient
from services.config_service import config_service

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
    mode: Literal["rewrite", "local", "alias_only", "skip", "llm"]  # 决策模式
    coverage: float              # 覆盖率
    conflict: float              # 冲突率
    metrics: Dict[str, Any]      # 分桶统计
    provenance: List[Dict[str, Any]]  # 证据链
    matches: List[Match] = field(default_factory=list)  # 所有匹配
    resolver_type: str = "unknown"  # 解析器类型 (rule/llm)
    
    def __iter__(self):
        """向后兼容：支持解包为 (resolved_text, alias_map)"""
        return iter((self.resolved_text, self.alias_map))


# ============================================================================
# 基础解析器抽象类
# ============================================================================

class BaseResolver(ABC):
    """指代消解器基类"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.quality_gates = config.get("quality_gates", {})
        self.candidate_gen = config.get("candidate_generation", {})
        self.context_window = self.candidate_gen.get("context_window", 3)
        self.max_candidates = self.candidate_gen.get("max_candidates_per_mention", 5)
    
    @abstractmethod
    def resolve(self, chunk: ChunkMetadata) -> Optional[CorefResult]:
        """执行指代消解"""
        pass
    
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
        sentences = [s.strip() for s in sentences if s.strip()]
        if len(sentences) > 3 and all(len(s) < 30 for s in sentences[:3]):
            logger.debug(f"[Stage1] 跳过: 检测到对话模式 (前3句平均长度 < 30)")
            return True
        
        return False
    
    def _split_sentences(self, text: str) -> List[str]:
        """分割句子"""
        pattern = r'[。！？\.\!\?]+'
        sentences = re.split(pattern, text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _get_sentence_index_from_position(self, text: str, position: int) -> int:
        """根据文本位置获取句子索引"""
        sentences = self._split_sentences(text)
        current_pos = 0
        for i, sentence in enumerate(sentences):
            sentence_start = text.find(sentence, current_pos)
            sentence_end = sentence_start + len(sentence)
            
            if sentence_start <= position < sentence_end:
                return i
            
            current_pos = sentence_end
        
        return len(sentences) - 1 if sentences else 0
    
    def _extract_parenthesis_aliases(self, text: str) -> Dict[str, str]:
        """提取括号别名（强约束）"""
        aliases = {}
        pattern = r'([^（(]+)[（(]([^）)]+)[）)]'
        matches = re.finditer(pattern, text)
        
        for match in matches:
            full_name = match.group(1).strip()
            alias_text = match.group(2).strip()
            alias_parts = [a.strip() for a in alias_text.split(',')]
            
            for alias in alias_parts:
                if alias and full_name:
                    if len(alias_parts) > 1 and alias == alias_parts[-1]:
                        aliases[alias] = full_name
                    elif len(alias_parts) == 1:
                        aliases[alias] = full_name
        
        return aliases
    
    def _detect_mentions(self, text: str) -> List[Mention]:
        """检测提及"""
        mentions = []
        sentences = self._split_sentences(text)
        
        pronouns_zh = ['它', '他', '她', '它们', '他们', '她们', '其', '它们']
        pronouns_en = ['this', 'that', 'these', 'those', 'it', 'they', 'them']
        demonstratives = ['该', '此', '其', '前者', '后者', '上述', '下述']
        exclude_patterns = [
            '其他', '其它', '除此之外', '其中', '其实', '其余',
            '极其', '其中', '其实', '其它'
        ]
        
        for sent_idx, sentence in enumerate(sentences):
            sent_start = text.find(sentence)
            if sent_start == -1:
                continue
            
            # 检测代词（中文）
            for pronoun in pronouns_zh:
                pattern = re.escape(pronoun)
                for match in re.finditer(pattern, sentence):
                    pos = sent_start + match.start()
                    
                    if pronoun == '其':
                        context_start = max(0, pos - 2)
                        context_end = min(len(text), pos + len(pronoun) + 2)
                        context = text[context_start:context_end]
                        
                        should_exclude = any(exclude in context for exclude in exclude_patterns)
                        if should_exclude:
                            logger.debug(f"[Stage1] 跳过复合词中的'其': context='{context}'")
                            continue
                    
                    mentions.append(Mention(
                        text=pronoun,
                        type=MentionType.PRONOUN,
                        position=pos,
                        sentence_idx=sent_idx,
                        span=(pos, pos + len(pronoun))
                    ))
            
            # 检测代词（英文）
            for pronoun in pronouns_en:
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
                    
                    if demo == '其':
                        context_start = max(0, pos - 2)
                        context_end = min(len(text), pos + len(demo) + 2)
                        context = text[context_start:context_end]
                        
                        should_exclude = any(exclude in context for exclude in exclude_patterns)
                        if should_exclude:
                            logger.debug(f"[Stage1] 跳过复合词中的指示词'其': context='{context}'")
                            continue
                    
                    mentions.append(Mention(
                        text=demo,
                        type=MentionType.DEMONSTRATIVE,
                        position=pos,
                        sentence_idx=sent_idx,
                        span=(pos, pos + len(demo))
                    ))
        
        return mentions
    
    def _generate_antecedents(self, text: str, mentions: List[Mention]) -> List[Antecedent]:
        """生成候选先行词"""
        antecedents = []
        sentences = self._split_sentences(text)
        
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
                word = match.group(1)
                if word not in ['这个', '那个', '这些', '那些', '它们', '他们']:
                    antecedents.append(Antecedent(
                        text=word,
                        position=pos,
                        sentence_idx=sent_idx,
                        span=(pos, pos + len(word))
                    ))
        
        return antecedents


# ============================================================================
# 规则模式解析器
# ============================================================================

class RuleBasedResolver(BaseResolver):
    """基于规则的指代消解器"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.scoring_weights = config.get("scoring_weights", {})
        self.consistency_cfg = config.get("consistency", {})
    
    def resolve(self, chunk: ChunkMetadata) -> CorefResult:
        """执行规则模式的指代消解"""
        logger.info(f"[Stage1-Rule] ========== 开始规则模式指代消解 ==========")
        logger.info(f"[Stage1-Rule] Chunk ID: {chunk.id}")
        logger.info(f"[Stage1-Rule] 文本长度: {len(chunk.text)} 字符")
        
        text = chunk.text
        
        # 0. 噪声过滤
        if self._should_skip(text):
            logger.debug(f"[Stage1-Rule] 跳过噪声文本: chunk_id={chunk.id}")
            return CorefResult(
                resolved_text=None,
                alias_map={},
                mode="skip",
                coverage=0.0,
                conflict=0.0,
                metrics={},
                provenance=[],
                resolver_type="rule"
            )
        
        # 1. 检测提及
        mentions = self._detect_mentions(text)
        logger.info(f"[Stage1-Rule] 检测到 {len(mentions)} 个提及")
        
        if not mentions:
            logger.info(f"[Stage1-Rule] 未检测到提及，跳过消解")
            return CorefResult(
                resolved_text=text,
                alias_map={},
                mode="skip",
                coverage=0.0,
                conflict=0.0,
                metrics={},
                provenance=[],
                resolver_type="rule"
            )
        
        # 2. 提取括号别名
        parenthesis_aliases = self._extract_parenthesis_aliases(text)
        logger.info(f"[Stage1-Rule] 提取到 {len(parenthesis_aliases)} 个括号别名")
        
        # 3. 生成候选先行词
        antecedents = self._generate_antecedents(text, mentions)
        logger.info(f"[Stage1-Rule] 生成 {len(antecedents)} 个候选先行词")
        
        # 4. 匹配打分
        matches = self._match_and_score(mentions, antecedents, parenthesis_aliases)
        logger.info(f"[Stage1-Rule] 生成 {len(matches)} 个匹配")
        
        # 5. 一致性校验
        validated_matches = self._validate_consistency(matches, parenthesis_aliases)
        logger.info(f"[Stage1-Rule] 一致性校验后剩余 {len(validated_matches)} 个匹配")
        
        # 6. 计算质量指标
        coverage, conflict, metrics = self._compute_quality_metrics(mentions, validated_matches)
        logger.info(f"[Stage1-Rule] 质量指标: 覆盖率={coverage:.2%}, 冲突率={conflict:.2%}")
        
        # 7. 决策路由
        mode = self._decide_mode(coverage, conflict)
        logger.info(f"[Stage1-Rule] 决策模式: {mode}")
        
        # 8. 生成产物
        resolved_text, alias_map, provenance = self._generate_artifacts(
            text, validated_matches, mode, parenthesis_aliases
        )
        
        logger.info(f"[Stage1-Rule] ========== 规则模式消解完成 ==========")
        
        return CorefResult(
            resolved_text=resolved_text,
            alias_map=alias_map,
            mode=mode,
            coverage=coverage,
            conflict=conflict,
            metrics=metrics,
            provenance=provenance,
            matches=validated_matches,
            resolver_type="rule"
        )
    
    def _get_candidates(self, mention: Mention, antecedents: List[Antecedent]) -> List[Antecedent]:
        """获取候选先行词"""
        candidates = []
        
        is_demonstrative_near = (
            mention.type == MentionType.DEMONSTRATIVE and 
            mention.text in ['该', '此', '其']
        )
        max_distance = 1 if is_demonstrative_near else self.context_window
        
        for ant in antecedents:
            if ant.position >= mention.position:
                continue
            
            sentence_distance = mention.sentence_idx - ant.sentence_idx
            if sentence_distance > max_distance:
                continue
            
            if not self._is_type_compatible(mention, ant):
                continue
            
            candidates.append(ant)
        
        return candidates
    
    def _match_and_score(
        self,
        mentions: List[Mention],
        antecedents: List[Antecedent],
        parenthesis_aliases: Dict[str, str]
    ) -> List[Match]:
        """匹配打分"""
        matches = []
        
        for mention in mentions:
            candidates = self._get_candidates(mention, antecedents)
            
            if not candidates:
                logger.debug(f"[Stage1-Rule] 提及 '{mention.text}' 无候选先行词")
                continue
            
            scored_candidates = []
            for candidate in candidates:
                score = self._score_match(mention, candidate, parenthesis_aliases)
                scored_candidates.append((candidate, score))
            
            scored_candidates.sort(key=lambda x: x[1], reverse=True)
            top_candidates = scored_candidates[:self.max_candidates]
            
            # 检查多解风险
            is_multi_solution = False
            if len(top_candidates) >= 3:
                scores = [s for _, s in top_candidates[:3]]
                if scores[0] - scores[2] < 0.1:
                    is_multi_solution = True
            
            min_score = 0.3
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
        
        return matches
    
    def _score_match(
        self,
        mention: Mention,
        antecedent: Antecedent,
        parenthesis_aliases: Dict[str, str]
    ) -> float:
        """匹配打分（多维度）"""
        score = 0.0
        
        # 1. 句距衰减
        sentence_distance = abs(mention.sentence_idx - antecedent.sentence_idx)
        distance_score = max(0, 1.0 - sentence_distance * 0.2)
        weight = self.scoring_weights.get("distance_decay", 0.4)
        score += distance_score * weight
        
        # 跨段长距离惩罚
        if sentence_distance > self.context_window:
            penalty = 0.5
            score *= (1.0 - penalty)
        
        # 2. 括号简称强约束
        if mention.text in parenthesis_aliases:
            canonical = parenthesis_aliases[mention.text]
            if antecedent.text == canonical:
                boost = self.scoring_weights.get("parenthesis_boost", 0.8)
                score += boost
        
        # 3. 类型一致性
        type_score = self._check_type_consistency(mention, antecedent)
        weight = self.scoring_weights.get("type_consistency", 0.2)
        score += type_score * weight
        
        # 4. 语言匹配
        lang_score = self._check_language_match(mention, antecedent)
        score += lang_score * 0.1
        
        # 5. 并列结构处理
        if mention.text in ['前者', '后者']:
            parallel_score = self._check_parallel_structure(mention, antecedent)
            score += parallel_score * 0.3
        
        return min(score, 1.0)
    
    def _is_type_compatible(self, mention: Mention, antecedent: Antecedent) -> bool:
        """检查类型兼容性"""
        ant_text = antecedent.text
        ant_type = antecedent.entity_type
        
        if ant_type:
            if ant_type == "PERSON" and mention.text in ['它', '它们', 'it', 'they']:
                return False
            if ant_type == "ORG" and mention.text in ['他', '她', '他们', '她们', 'he', 'she', 'they']:
                return False
            if ant_type == "TIME" and mention.text in ['它', '它们', 'it', 'they']:
                if re.search(r'(技术|算法|模型|系统|框架)', ant_text):
                    return False
        
        if re.match(r'^[王李张刘陈杨黄赵吴周徐孙马朱胡郭何高林罗郑梁谢宋唐许韩冯邓曹彭曾肖田董袁潘于蒋蔡余杜叶程苏魏吕丁任沈姚卢姜崔钟谭陆汪范金石廖贾夏韦付方白邹孟熊秦邱江尹薛闫段雷侯龙史陶黎贺顾毛郝龚邵万钱严覃武戴莫孔向汤]', ant_text):
            if mention.text in ['它', '它们', 'it', 'they']:
                return False
        
        if re.search(r'(公司|集团|大学|学院|机构|组织|部门|中心)', ant_text):
            if mention.text in ['他', '她', '他们', '她们', 'he', 'she', 'they']:
                return False
        
        return True
    
    def _check_type_consistency(self, mention: Mention, antecedent: Antecedent) -> float:
        """检查类型一致性"""
        if not self._is_type_compatible(mention, antecedent):
            return 0.0
        
        if mention.type == MentionType.PRONOUN:
            if re.match(r'^[\u4e00-\u9fff]{2,4}$', antecedent.text):
                return 0.8
            if re.match(r'^[A-Z][a-z]+$', antecedent.text):
                return 0.8
        
        return 0.5
    
    def _get_evidence_type(
        self,
        mention: Mention,
        antecedent: Antecedent,
        parenthesis_aliases: Dict[str, str]
    ) -> str:
        """获取证据类型"""
        if mention.text in parenthesis_aliases:
            return "parenthesis"
        
        if mention.text in ["模型", "算法", "方法", "技术", "系统", "框架", "架构"]:
            return "abbreviation"
        
        sentence_distance = abs(mention.sentence_idx - antecedent.sentence_idx)
        
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
        alias_map = {}
        
        # 别名一致性
        for match in matches:
            if match.mention.text in parenthesis_aliases:
                canonical = parenthesis_aliases[match.mention.text]
                if match.mention.text not in alias_map:
                    alias_map[match.mention.text] = canonical
                elif alias_map[match.mention.text] != canonical:
                    match.is_conflict = True
                    continue
            
            validated.append(match)
        
        # 窗口内一致性
        mention_groups: Dict[str, List[Match]] = {}
        for match in validated:
            key = match.mention.text
            if key not in mention_groups:
                mention_groups[key] = []
            mention_groups[key].append(match)
        
        final_validated = []
        for key, group in mention_groups.items():
            if len(group) == 1:
                final_validated.append(group[0])
            else:
                group.sort(key=lambda m: m.score, reverse=True)
                best_match = group[0]
                final_validated.append(best_match)
                for m in group[1:]:
                    m.is_conflict = True
                    final_validated.append(m)
        
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
        
        resolved_mentions = set()
        for match in matches:
            if not match.is_conflict:
                resolved_mentions.add(match.mention.text)
        
        coverage = len(resolved_mentions) / total_mentions if total_mentions > 0 else 0.0
        
        conflict_matches = sum(1 for m in matches if m.is_conflict)
        conflict = conflict_matches / len(matches) if matches else 0.0
        
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
        
        rewrite_coverage_min = gates.get("rewrite_coverage_min", 0.6)
        rewrite_conflict_max = gates.get("rewrite_conflict_max", 0.15)
        if coverage >= rewrite_coverage_min and conflict <= rewrite_conflict_max:
            return "rewrite"
        
        local_coverage_min = gates.get("local_coverage_min", 0.3)
        local_conflict_max = gates.get("local_conflict_max", 0.25)
        if coverage >= local_coverage_min and conflict <= local_conflict_max:
            return "local"
        
        alias_only_coverage_min = gates.get("alias_only_coverage_min", 0.1)
        if coverage >= alias_only_coverage_min:
            return "alias_only"
        
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
        
        alias_map.update(parenthesis_aliases)
        
        if mode == "rewrite":
            resolved_text = text
            for match in matches:
                if not match.is_conflict:
                    pattern = r'\b' + re.escape(match.mention.text) + r'\b'
                    resolved_text = re.sub(pattern, match.antecedent.text, resolved_text)
        elif mode == "local":
            resolved_text = text
            for match in matches:
                if not match.is_conflict and match.sentence_distance <= 1:
                    pattern = r'\b' + re.escape(match.mention.text) + r'\b'
                    resolved_text = re.sub(pattern, match.antecedent.text, resolved_text)
        
        return resolved_text, alias_map, provenance
    
    def _check_language_match(self, mention: Mention, antecedent: Antecedent) -> float:
        """检查语言匹配"""
        mention_is_en = bool(re.search(r'[a-zA-Z]', mention.text))
        ant_is_en = bool(re.search(r'[a-zA-Z]', antecedent.text))
        
        if mention_is_en and ant_is_en:
            return 0.8
        if not mention_is_en and not ant_is_en:
            return 0.8
        
        return 0.3
    
    def _check_parallel_structure(self, mention: Mention, antecedent: Antecedent) -> float:
        """检查并列结构"""
        if mention.text == '前者':
            sentence_distance = mention.sentence_idx - antecedent.sentence_idx
            if sentence_distance >= 2:
                return 0.6
        elif mention.text == '后者':
            sentence_distance = mention.sentence_idx - antecedent.sentence_idx
            if sentence_distance <= 2:
                return 0.6
        
        return 0.3


# ============================================================================
# LLM 模式解析器
# ============================================================================

class LLMResolver(BaseResolver):
    """基于 LLM 的指代消解器"""
    
    def __init__(self, config: Dict[str, Any], llm_client: BaseAIClient):
        super().__init__(config)
        self.llm_client = llm_client
    
    def resolve(self, chunk: ChunkMetadata) -> Optional[CorefResult]:
        """执行 LLM 模式的指代消解"""
        logger.info(f"[Stage1-LLM] ========== 开始 LLM 模式指代消解 ==========")
        logger.info(f"[Stage1-LLM] Chunk ID: {chunk.id}")
        
        text = chunk.text
        
        # 0. 噪声过滤
        if self._should_skip(text):
            logger.debug(f"[Stage1-LLM] 跳过噪声文本: chunk_id={chunk.id}")
            return None
        
        # 1. 检测提及和候选先行词
        mentions = self._detect_mentions(text)
        if not mentions:
            logger.info(f"[Stage1-LLM] 未检测到提及，回退到规则方法")
            return None
        
        # 2. 提取括号别名
        parenthesis_aliases = self._extract_parenthesis_aliases(text)
        logger.info(f"[Stage1-LLM] 提取到 {len(parenthesis_aliases)} 个括号别名")
        
        # 3. 生成候选先行词
        antecedents = self._generate_antecedents(text, mentions)
        logger.info(f"[Stage1-LLM] 生成 {len(antecedents)} 个候选先行词")
        
        # 4. 构造 LLM prompt
        prompt = self._build_llm_prompt(text, mentions, antecedents, parenthesis_aliases)
        
        try:
            # 5. 调用 LLM
            logger.info(f"[Stage1-LLM] 调用 LLM...")
            messages = [
                {
                    "role": "system",
                    "content": "你是一个专业的中文指代消解助手。请根据给定的文本、提及和候选先行词，为每个提及选择最合理的先行词。"
                },
                {"role": "user", "content": prompt}
            ]
            
            response = self.llm_client.chat_completion(
                messages=messages,
                temperature=0.3,
                json_mode=True
            )
            
            logger.info(f"[Stage1-LLM] ✓ LLM 返回响应")
            
            if not response or not response.strip():
                logger.warning(f"[Stage1-LLM] LLM 返回空响应，回退到规则方法")
                return None
            
            # 6. 解析 LLM 响应
            logger.info(f"[Stage1-LLM] 解析 LLM JSON 响应...")
            llm_result = self._parse_llm_json_response(response)
            if not llm_result:
                logger.warning(f"[Stage1-LLM] LLM结果解析失败，回退到规则方法")
                return None
            
            # 7. 转换为 CorefResult
            logger.info(f"[Stage1-LLM] 转换为 CorefResult...")
            result = self._parse_llm_result(text, mentions, antecedents, parenthesis_aliases, llm_result)
            logger.info(f"[Stage1-LLM] ✓ LLM 模式完成: mode={result.mode}, coverage={result.coverage:.2%}")
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"[Stage1-LLM] JSON 解析失败: {e}")
            return None
        except Exception as e:
            logger.error(f"[Stage1-LLM] LLM 调用失败: {e}")
            return None
    
    def _build_llm_prompt(
        self,
        text: str,
        mentions: List[Mention],
        antecedents: List[Antecedent],
        parenthesis_aliases: Dict[str, str]
    ) -> str:
        """构造 LLM prompt"""
        mentions_list = []
        for i, m in enumerate(mentions, 1):
            mentions_list.append({
                "id": i,
                "text": m.text,
                "type": m.type.value,
                "position": m.position
            })
        
        prompt = f"""请对以下中文文本进行指代消解。

文本内容：
{text}

检测到的提及（需要消解的指代词）：
{json.dumps(mentions_list, ensure_ascii=False, indent=2)}

括号别名映射（强约束，必须遵守）：
{json.dumps(parenthesis_aliases, ensure_ascii=False, indent=2)}

请为每个提及选择最合理的先行词。要求：
1. 先行词必须在原文中存在，且在提及之前出现
2. 必须遵守括号别名映射（如果提及是括号别名，必须映射到对应的全称）
3. 如果无法确定，可以返回 null
4. 考虑语义一致性、句法一致性、距离等因素
5. 请仔细阅读整段文字，理解上下文关系后进行判断

请以 JSON 格式返回结果，格式如下：
{{
  "resolutions": [
    {{
      "mention_id": 1,
      "mention_text": "它",
      "antecedent_text": "人工智能",
      "confidence": 0.9,
      "rationale": "理由说明"
    }}
  ]
}}

只返回 JSON，不要其他内容。"""
        
        return prompt
    
    def _parse_llm_json_response(self, response: str) -> Optional[Dict[str, Any]]:
        """解析 LLM 返回的 JSON 响应"""
        logger.debug(f"[Stage1-LLM] 尝试解析JSON响应: {response[:200]}...")
        
        try:
            result = json.loads(response)
            logger.debug(f"[Stage1-LLM] 直接JSON解析成功")
            return result
        except json.JSONDecodeError as e:
            logger.debug(f"[Stage1-LLM] 直接JSON解析失败: {e}")
            
            # 尝试提取 JSON 代码块
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
            if json_match:
                logger.debug(f"[Stage1-LLM] 找到JSON代码块")
                try:
                    result = json.loads(json_match.group(1))
                    logger.debug(f"[Stage1-LLM] 代码块JSON解析成功")
                    return result
                except json.JSONDecodeError:
                    pass
            
            # 尝试提取第一个 { ... } 块
            brace_match = re.search(r'\{.*\}', response, re.DOTALL)
            if brace_match:
                logger.debug(f"[Stage1-LLM] 找到大括号块")
                try:
                    result = json.loads(brace_match.group(0))
                    logger.debug(f"[Stage1-LLM] 大括号块JSON解析成功")
                    return result
                except json.JSONDecodeError:
                    pass
            
            logger.error(f"[Stage1-LLM] 无法解析 JSON 响应")
            return None
    
    def _parse_llm_result(
        self,
        text: str,
        mentions: List[Mention],
        antecedents: List[Antecedent],
        parenthesis_aliases: Dict[str, str],
        llm_result: Dict[str, Any]
    ) -> CorefResult:
        """解析 LLM 返回结果并转换为 CorefResult"""
        alias_map = {}
        provenance = []
        matches = []
        
        resolved_mentions = set()
        mention_dict = {i+1: m for i, m in enumerate(mentions)}
        
        # 处理 LLM 返回的 resolutions
        resolutions = llm_result.get("resolutions", [])
        
        for res in resolutions:
            mention_id = res.get("mention_id")
            mention_text = res.get("mention_text")
            antecedent_text = res.get("antecedent_text")
            confidence = res.get("confidence", 0.5)
            rationale = res.get("rationale", "")
            
            if not mention_id or mention_id not in mention_dict:
                logger.debug(f"[Stage1-LLM] 跳过无效的mention_id: {mention_id}")
                continue
            
            mention = mention_dict[mention_id]
            
            # 如果LLM返回null，跳过
            if not antecedent_text or antecedent_text.lower() == 'null':
                logger.debug(f"[Stage1-LLM] LLM返回null，跳过: {mention_text}")
                continue
            
            # 检查括号别名约束
            if mention_text in parenthesis_aliases:
                canonical = parenthesis_aliases[mention_text]
                if antecedent_text != canonical:
                    logger.warning(f"[Stage1-LLM] 括号别名约束冲突，使用括号别名")
                    antecedent_text = canonical
            
            # 验证先行词是否在原文中存在
            pattern = re.compile(re.escape(antecedent_text))
            matches_in_text = list(pattern.finditer(text))
            valid_positions = [m.start() for m in matches_in_text if m.start() < mention.position]
            
            if valid_positions:
                closest_pos = max(valid_positions)
                
                virtual_antecedent = Antecedent(
                    text=antecedent_text,
                    position=closest_pos,
                    entity_type="llm_identified",
                    sentence_idx=self._get_sentence_index_from_position(text, closest_pos)
                )
                
                alias_map[mention_text] = antecedent_text
                resolved_mentions.add(mention_text)
                
                sentence_distance = abs(mention.sentence_idx - virtual_antecedent.sentence_idx)
                match = Match(
                    mention=mention,
                    antecedent=virtual_antecedent,
                    score=confidence,
                    confidence=confidence,
                    evidence_type="llm_direct",
                    sentence_distance=sentence_distance,
                    is_conflict=False
                )
                matches.append(match)
                
                provenance.append({
                    "mention": mention_text,
                    "canonical": antecedent_text,
                    "confidence": confidence,
                    "evidence_type": "llm_direct",
                    "rationale": f"LLM直接识别: {rationale}",
                    "sentence_distance": sentence_distance,
                    "mention_position": mention.position,
                    "antecedent_position": closest_pos
                })
                
                logger.info(f"[Stage1-LLM] LLM直接识别成功: '{mention_text}' -> '{antecedent_text}'")
            else:
                logger.warning(f"[Stage1-LLM] LLM返回的先行词不在原文中或在提及之后，跳过")
        
        # 添加括号别名
        alias_map.update(parenthesis_aliases)
        
        # 计算质量指标
        total_mentions = len(mentions)
        coverage = len(resolved_mentions) / total_mentions if total_mentions > 0 else 0.0
        conflict = 0.0
        
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
            "conflict_matches": 0
        }
        
        logger.info(f"[Stage1-LLM] ========== LLM 模式消解完成 ==========")
        
        return CorefResult(
            resolved_text=None,
            alias_map=alias_map,
            mode="llm",
            coverage=coverage,
            conflict=conflict,
            metrics=metrics,
            provenance=provenance,
            matches=matches,
            resolver_type="llm"
        )


# ============================================================================
# 主入口：指代消解器
# ============================================================================

class CoreferenceResolver:
    """
    指代消解器主入口
    
    支持两种模式：
    1. LLM 模式（优先）：使用大语言模型进行消解
    2. 规则模式（回退）：使用规则方法进行消解
    
    流程：
    - 优先尝试 LLM 模式
    - 如果 LLM 不可用或失败，回退到规则模式
    - 返回统一的 CorefResult 对象
    """
    
    def __init__(self):
        self.config = get_config()
        self.thresholds = self.config.thresholds.coreference
        
        # # 初始化规则模式解析器（已注释，完全依赖 LLM）
        # self.rule_resolver = RuleBasedResolver(self.thresholds)
        
        # 初始化 LLM 模式解析器（必须）
        self.llm_resolver: Optional[LLMResolver] = None
        self.llm_client: Optional[BaseAIClient] = None
        self.llm_enabled = False
        
        try:
            ai_config = config_service.get_ai_provider_config()
            provider = ai_config["provider"]
            api_key = ai_config["api_key"]
            model = ai_config["model"]
            base_url = ai_config["base_url"]
            
            if provider == "mock":
                api_key = api_key or "mock"
            
            try:
                llm_client = AIProviderFactory.create_client(
                    provider=provider,
                    api_key=api_key,
                    model=model,
                    base_url=base_url
                )
                self.llm_client = llm_client
                self.llm_resolver = LLMResolver(self.thresholds, llm_client)
                self.llm_enabled = True
                logger.info(f"CoreferenceResolver: LLM 模式已启用 (provider={provider}, model={model})")
            except ValueError as ve:
                logger.info(f"CoreferenceResolver: LLM 模式未启用（配置不完整: {ve}）")
                self.llm_enabled = False
        except Exception as e:
            logger.warning(f"CoreferenceResolver: LLM 客户端初始化失败，将使用规则方法: {e}")
            self.llm_enabled = False
        
        logger.info("CoreferenceResolver initialized")
    
    def resolve(self, chunk: ChunkMetadata) -> CorefResult:
        """
        执行指代消解
        
        完全依赖 LLM 模式
        
        Args:
            chunk: 输入 Chunk
        
        Returns:
            CorefResult: 包含 resolved_text、alias_map、质量指标等
        """
        logger.info(f"[Stage1] ========== 开始指代消解 ==========")
        logger.info(f"[Stage1] Chunk ID: {chunk.id}")
        logger.info(f"[Stage1] 文本长度: {len(chunk.text)} 字符")
        
        # 完全依赖 LLM 模式
        if self.llm_enabled and self.llm_resolver:
            try:
                logger.info(f"[Stage1] ========== 使用 LLM 模式 ==========")
                result = self.llm_resolver.resolve(chunk)
                if result:
                    logger.info(f"[Stage1] ✓ LLM 模式成功完成指代消解，模式={result.mode}")
                    logger.info(f"[Stage1] ========== 指代消解完成 ==========")
                    return result
                else:
                    logger.error(f"[Stage1] ✗ LLM 模式返回空结果")
                    raise RuntimeError("LLM 模式返回空结果")
            except Exception as e:
                logger.error(f"[Stage1] ✗ LLM 模式异常: {type(e).__name__}: {e}", exc_info=True)
                raise
        else:
            logger.error(f"[Stage1] ✗ LLM 未启用，无法执行指代消解")
            raise RuntimeError("LLM 模式未启用，请配置 LLM 参数")
        
        # # 回退到规则方法（已注释，完全依赖 LLM）
        # logger.info(f"[Stage1] ========== 使用规则方法 ==========")
        # result = self.rule_resolver.resolve(chunk)
        # logger.info(f"[Stage1] ========== 指代消解完成 ==========")
        # return result


__all__ = ["CoreferenceResolver", "CorefResult", "RuleBasedResolver", "LLMResolver"]
