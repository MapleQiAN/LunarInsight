"""
证据对齐工具

实现证据硬对齐：子串匹配 + LCS 纠偏机制
"""

import logging
import re
from typing import Optional, Tuple, List
from difflib import SequenceMatcher

logger = logging.getLogger("graphrag.evidence_aligner")


def normalize_text(text: str) -> str:
    """
    规范化文本（用于匹配）
    
    移除标点、空格、大小写差异
    """
    # 移除标点符号
    text = re.sub(r'[^\w\s]', '', text)
    # 转小写
    text = text.lower()
    # 移除多余空格
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def find_substring_match(
    claim_text: str,
    source_text: str,
    window_start: int = 0,
    window_end: Optional[int] = None
) -> Optional[Tuple[int, int]]:
    """
    子串匹配：在源文本中查找论断文本的最短覆盖区间
    
    Args:
        claim_text: 论断文本
        source_text: 源文本（Chunk 文本）
        window_start: 搜索窗口起始位置（字符偏移）
        window_end: 搜索窗口结束位置（字符偏移），None 表示到文本末尾
    
    Returns:
        (start_char, end_char) 或 None（未找到）
    """
    if not claim_text or not source_text:
        return None
    
    # 规范化文本用于匹配
    normalized_claim = normalize_text(claim_text)
    if not normalized_claim:
        return None
    
    # 确定搜索窗口
    search_text = source_text[window_start:window_end] if window_end else source_text[window_start:]
    search_start = window_start
    
    # 尝试精确匹配（规范化后）
    normalized_source = normalize_text(search_text)
    
    # 查找规范化后的子串位置
    idx = normalized_source.find(normalized_claim)
    if idx != -1:
        # 找到匹配，需要映射回原始文本位置
        # 由于规范化移除了标点，需要近似映射
        # 简化处理：使用字符位置近似
        original_start = search_start + idx
        original_end = original_start + len(claim_text)
        
        # 确保不超出源文本范围
        if original_end <= len(source_text):
            return (original_start, original_end)
    
    # 如果精确匹配失败，尝试部分匹配（至少匹配 70% 的字符）
    min_match_ratio = 0.7
    best_match = None
    best_ratio = 0.0
    
    # 滑动窗口匹配
    claim_len = len(normalized_claim)
    for i in range(len(normalized_source) - claim_len + 1):
        window = normalized_source[i:i + claim_len]
        ratio = SequenceMatcher(None, normalized_claim, window).ratio()
        
        if ratio >= min_match_ratio and ratio > best_ratio:
            best_ratio = ratio
            # 映射回原始位置（近似）
            original_start = search_start + i
            original_end = original_start + len(claim_text)
            if original_end <= len(source_text):
                best_match = (original_start, original_end)
    
    if best_match:
        logger.debug(f"部分匹配找到证据: ratio={best_ratio:.3f}, span={best_match}")
        return best_match
    
    return None


def lcs_align(
    claim_text: str,
    source_text: str,
    candidate_span: Optional[Tuple[int, int]] = None
) -> Optional[Tuple[int, int]]:
    """
    LCS（最长公共子序列）纠偏
    
    当子串匹配失败或匹配度较低时，使用 LCS 算法找到最佳对齐位置
    
    Args:
        claim_text: 论断文本
        source_text: 源文本
        candidate_span: 候选区间（如果已有）
    
    Returns:
        (start_char, end_char) 或 None
    """
    if not claim_text or not source_text:
        return None
    
    # 如果已有候选区间，在其附近搜索
    if candidate_span:
        start, end = candidate_span
        # 扩展搜索窗口（前后各 100 字符）
        window_start = max(0, start - 100)
        window_end = min(len(source_text), end + 100)
        search_text = source_text[window_start:window_end]
        offset = window_start
    else:
        search_text = source_text
        offset = 0
    
    # 使用 SequenceMatcher 找到最长匹配子串
    matcher = SequenceMatcher(None, claim_text, search_text)
    match = matcher.find_longest_match(0, len(claim_text), 0, len(search_text))
    
    if match.size >= len(claim_text) * 0.6:  # 至少匹配 60%
        start_char = offset + match.b
        end_char = start_char + match.size
        logger.debug(f"LCS 对齐找到证据: span=({start_char}, {end_char}), size={match.size}")
        return (start_char, end_char)
    
    return None


def align_evidence(
    claim_text: str,
    source_text: str,
    llm_span: Optional[Tuple[int, int]] = None,
    min_match_ratio: float = 0.6
) -> Tuple[Optional[Tuple[int, int]], float]:
    """
    证据硬对齐（主函数）
    
    结合子串匹配和 LCS 纠偏，返回最佳证据区间
    
    Args:
        claim_text: 论断文本
        source_text: 源文本（Chunk 文本）
        llm_span: LLM 返回的证据区间（可选）
        min_match_ratio: 最小匹配度阈值
    
    Returns:
        (evidence_span, match_ratio)
        - evidence_span: (start_char, end_char) 或 None
        - match_ratio: 匹配度 [0.0-1.0]
    """
    if not claim_text or not source_text:
        return None, 0.0
    
    # 1. 如果 LLM 提供了 span，先验证其准确性
    if llm_span:
        start, end = llm_span
        if 0 <= start < end <= len(source_text):
            # 提取 LLM 标注的文本片段
            llm_text = source_text[start:end]
            # 计算匹配度
            matcher = SequenceMatcher(None, normalize_text(claim_text), normalize_text(llm_text))
            ratio = matcher.ratio()
            
            if ratio >= min_match_ratio:
                logger.debug(f"LLM span 验证通过: ratio={ratio:.3f}, span={llm_span}")
                return llm_span, ratio
            else:
                logger.debug(f"LLM span 验证失败: ratio={ratio:.3f}, 需要重新对齐")
    
    # 2. 尝试子串匹配
    match_span = find_substring_match(claim_text, source_text)
    if match_span:
        # 验证匹配度
        matched_text = source_text[match_span[0]:match_span[1]]
        matcher = SequenceMatcher(None, normalize_text(claim_text), normalize_text(matched_text))
        ratio = matcher.ratio()
        
        if ratio >= min_match_ratio:
            return match_span, ratio
    
    # 3. 尝试 LCS 纠偏
    lcs_span = lcs_align(claim_text, source_text, llm_span)
    if lcs_span:
        matched_text = source_text[lcs_span[0]:lcs_span[1]]
        matcher = SequenceMatcher(None, normalize_text(claim_text), normalize_text(matched_text))
        ratio = matcher.ratio()
        
        if ratio >= min_match_ratio:
            return lcs_span, ratio
    
    # 4. 所有方法都失败
    logger.warning(f"证据对齐失败: claim_text='{claim_text[:50]}...', 匹配度低于阈值 {min_match_ratio}")
    return None, 0.0


def extract_evidence_quote(
    source_text: str,
    evidence_span: Tuple[int, int],
    context_chars: int = 20
) -> str:
    """
    提取证据引用片段（带上下文）
    
    Args:
        source_text: 源文本
        evidence_span: 证据区间
        context_chars: 上下文字符数
    
    Returns:
        带上下文的引用片段
    """
    start, end = evidence_span
    quote_start = max(0, start - context_chars)
    quote_end = min(len(source_text), end + context_chars)
    
    quote = source_text[quote_start:quote_end]
    # 标记实际证据区间（如果可能）
    if quote_start < start:
        prefix = quote[:start - quote_start]
        evidence = quote[start - quote_start:end - quote_start]
        suffix = quote[end - quote_start:]
        return f"{prefix}[{evidence}]{suffix}"
    
    return quote


__all__ = [
    "align_evidence",
    "extract_evidence_quote",
    "normalize_text"
]

