"""
阶段 1: 指代消解 (Coreference Resolution)

解析代词与指代关系，生成别名映射
采用"先评估、再决策、再应用"的质量门控范式
"""

import logging
import re
import json
from typing import Dict, Tuple, List, Optional, Literal, Any
from dataclasses import dataclass, field
from enum import Enum
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
    4. 根据阈值决定替换模式（rewrite/local/alias_only/skip/llm）
    
    支持 LLM 模式：默认尝试使用大模型进行指代消解，失败则回退到规则方法
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
        
        # 初始化 LLM 客户端（如果可用）
        self.llm_client: Optional[BaseAIClient] = None
        self.llm_enabled = False
        try:
            ai_config = config_service.get_ai_provider_config()
            provider = ai_config["provider"]
            api_key = ai_config["api_key"]
            model = ai_config["model"]
            base_url = ai_config["base_url"]
            
            # Mock 模式不需要 API key
            if provider == "mock":
                api_key = api_key or "mock"
            
            # 尝试创建 AI 客户端（包括 mock 模式）
            try:
                self.llm_client = AIProviderFactory.create_client(
                    provider=provider,
                    api_key=api_key,
                    model=model,
                    base_url=base_url
                )
                self.llm_enabled = True
                logger.info(f"CoreferenceResolver: LLM 模式已启用 (provider={provider}, model={model})")
            except ValueError as ve:
                # 如果是因为缺少 API key 等配置问题，记录但不启用
                logger.info(f"CoreferenceResolver: LLM 模式未启用（配置不完整: {ve}）")
                self.llm_client = None
                self.llm_enabled = False
        except Exception as e:
            logger.warning(f"CoreferenceResolver: LLM 客户端初始化失败，将使用规则方法: {e}")
            self.llm_client = None
            self.llm_enabled = False
        
        logger.info("CoreferenceResolver initialized with quality gates")
    
    def resolve(self, chunk: ChunkMetadata) -> CorefResult:
        """
        消解 Chunk 中的指代关系
        
        策略：
        1. 先使用规则方法快速评估
        2. 如果规则方法覆盖率低（< 0.3）且 LLM 可用，则尝试 LLM 模式
        3. 否则返回规则方法的结果
        
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
        
        # 1. 先使用规则方法快速评估
        logger.info(f"[Stage1] 使用规则方法进行初步评估")
        rules_result = self._resolve_with_rules(chunk)
        
        # 2. 如果规则方法覆盖率低且 LLM 可用，尝试 LLM 模式
        if self.llm_enabled and self.llm_client and rules_result.coverage < 0.3:
            logger.info(f"[Stage1] 规则方法覆盖率较低 ({rules_result.coverage:.2%})，尝试 LLM 模式")
            try:
                llm_result = self._resolve_with_llm(chunk)
                if llm_result and llm_result.coverage > rules_result.coverage:
                    logger.info(f"[Stage1] LLM 模式覆盖率更高 ({llm_result.coverage:.2%})，使用 LLM 结果")
                    return llm_result
                else:
                    logger.info(f"[Stage1] LLM 模式覆盖率未改善，使用规则方法结果")
            except Exception as e:
                logger.warning(f"[Stage1] LLM 模式失败，继续使用规则方法: {e}")
        
        # 3. 返回规则方法的结果
        logger.info(f"[Stage1] 使用规则方法的结果")
        return rules_result
    
    def _resolve_with_rules(self, chunk: ChunkMetadata) -> CorefResult:
        """
        使用规则方法进行指代消解（原有实现）
        """
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
        sentences = [s.strip() for s in sentences if s.strip()]  # 过滤空字符串
        if len(sentences) > 3 and all(len(s) < 30 for s in sentences[:3]):
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
        
        # 需要避免误检测的复合词（包含"其"但不应拆解）
        exclude_patterns = [
            '其他', '其它', '除此之外', '其中', '其实', '其它', '其余', '其中',
            '极其', '其中', '其实', '其它', '其它', '其它', '其它'
        ]
        
        for sent_idx, sentence in enumerate(sentences):
            sent_start = text.find(sentence)
            if sent_start == -1:
                continue
            
            # 检测代词（中文不使用单词边界，英文使用）
            for pronoun in pronouns_zh:
                # 中文代词直接匹配，不使用 \b（因为中文没有空格分隔）
                pattern = re.escape(pronoun)
                for match in re.finditer(pattern, sentence):
                    pos = sent_start + match.start()
                    
                    # 特殊处理：如果是"其"，检查是否在复合词中
                    if pronoun == '其':
                        # 获取匹配位置前后各2个字符的上下文
                        context_start = max(0, pos - 2)
                        context_end = min(len(text), pos + len(pronoun) + 2)
                        context = text[context_start:context_end]
                        
                        # 如果上下文包含排除模式，跳过
                        should_exclude = False
                        for exclude in exclude_patterns:
                            if exclude in context:
                                should_exclude = True
                                break
                        
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
            
            for pronoun in pronouns_en:
                # 英文代词使用单词边界
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
                    
                    # 特殊处理：如果是"其"，同样检查复合词
                    if demo == '其':
                        context_start = max(0, pos - 2)
                        context_end = min(len(text), pos + len(demo) + 2)
                        context = text[context_start:context_end]
                        
                        should_exclude = False
                        for exclude in exclude_patterns:
                            if exclude in context:
                                should_exclude = True
                                break
                        
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
        
        # 停用词列表（更完整）
        stopwords = {
            '这个', '那个', '这些', '那些', '它们', '他们', '她们',
            '什么', '哪个', '哪些', '如何', '为什么', '怎样',
            '一个', '两个', '三个', '很多', '所有', '没有',
            '可以', '应该', '需要', '想要', '能够', '开始',
            '继续', '完成', '结束', '发生', '出现', '存在',
            '是的', '不是', '对的', '错的', '好的', '坏的',
            '大的', '小的', '长的', '短的', '高的', '低的',
            '新的', '旧的', '多的', '少的', '快的', '慢的',
            '真的', '假的', '强的', '弱的', '美的', '丑的'
        }
        
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
            
            # 中文名词短语（2-6 字）- 更精准的提取
            # 优先提取括号内的全称（如"人工智能"）
            pattern_zh = r'([\u4e00-\u9fff]{2,6})'
            for match in re.finditer(pattern_zh, sentence):
                pos = sent_start + match.start()
                word = match.group(1)
                
                # 过滤停用词
                if word in stopwords:
                    continue
                
                # 过滤代词和指示词
                if word in ['它', '他', '她', '它们', '他们', '她们', '其', '该', '此', '这', '那', '前者', '后者']:
                    continue
                
                # 过滤虚词
                if re.search(r'^(的|了|在|和|或|但|因|所|被|把|给|向|对|跟|同|比|从|到|为|于)$', word):
                    continue

                antecedents.append(Antecedent(
                    text=word,
                    position=pos,
                    sentence_idx=sent_idx,
                    span=(pos, pos + len(word))
                ))
            


    
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
        
        # 如果超出范围，返回最后一个句子索引
        return len(sentences) - 1 if sentences else 0


__all__ = ["CoreferenceResolver", "CorefResult"]