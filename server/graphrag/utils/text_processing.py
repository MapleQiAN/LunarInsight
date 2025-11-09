"""
文本处理工具

句子分割、章节提取、滑动窗口等
"""

import re
from typing import List, Tuple, Optional


def split_sentences(text: str) -> List[str]:
    """
    分割句子（中英文）
    
    Args:
        text: 输入文本
    
    Returns:
        句子列表
    """
    # 简单实现：基于标点符号
    # 中文句号、英文句号、问号、感叹号、省略号
    sentence_endings = r'[。！？\.\!\?]+'
    
    sentences = re.split(sentence_endings, text)
    
    # 过滤空句子
    sentences = [s.strip() for s in sentences if s.strip()]
    
    return sentences


def extract_sections(text: str) -> List[Tuple[str, str, int]]:
    """
    提取章节信息
    
    Args:
        text: 输入文本
    
    Returns:
        章节列表 [(section_path, section_title, start_pos)]
        例如: [("1", "Introduction", 0), ("1.1", "Background", 150), ...]
    """
    sections = []
    
    # 匹配章节标题（支持多种格式）
    # 1. 引言
    # 第一章 背景
    # 1.1 相关工作
    # # Introduction (Markdown)
    
    patterns = [
        r'^([0-9]+(?:\.[0-9]+)*)\s+(.+)$',  # "1.2.3 标题"
        r'^第([0-9一二三四五六七八九十百]+)章\s+(.+)$',  # "第一章 标题"
        r'^(#+)\s+(.+)$',  # "## 标题" (Markdown)
    ]
    
    for i, line in enumerate(text.split('\n')):
        line = line.strip()
        for pattern in patterns:
            match = re.match(pattern, line)
            if match:
                if pattern.startswith('^(#+)'):
                    # Markdown heading
                    level = len(match.group(1))
                    section_path = str(level)
                    title = match.group(2)
                elif '章' in pattern:
                    # 中文章节
                    section_num = match.group(1)
                    title = match.group(2)
                    section_path = section_num
                else:
                    # 数字编号
                    section_path = match.group(1)
                    title = match.group(2)
                
                # 计算起始位置（粗略估计）
                start_pos = text.find(line)
                sections.append((section_path, title, start_pos))
                break
    
    return sections


def sliding_window(
    sentences: List[str],
    window_size: int = 4,
    step_size: int = 2
) -> List[Tuple[str, int, int]]:
    """
    滑动窗口切分
    
    Args:
        sentences: 句子列表
        window_size: 窗口大小（句子数）
        step_size: 步长（句子数）
    
    Returns:
        窗口列表 [(window_text, start_idx, end_idx)]
    """
    windows = []
    
    for i in range(0, len(sentences), step_size):
        window_sentences = sentences[i:i + window_size]
        
        # 如果剩余句子不足一个窗口，仍然保留
        if len(window_sentences) < window_size and windows:
            # 跳过（避免重复）
            continue
        
        window_text = ' '.join(window_sentences)
        start_idx = i
        end_idx = min(i + window_size - 1, len(sentences) - 1)
        
        windows.append((window_text, start_idx, end_idx))
    
    return windows


def extract_context(
    text: str,
    mention_start: int,
    mention_end: int,
    context_window: int = 100
) -> Tuple[str, str, str]:
    """
    提取提及的上下文
    
    Args:
        text: 完整文本
        mention_start: 提及起始位置
        mention_end: 提及结束位置
        context_window: 上下文窗口大小（字符数）
    
    Returns:
        (left_context, mention, right_context)
    """
    left_start = max(0, mention_start - context_window)
    right_end = min(len(text), mention_end + context_window)
    
    left_context = text[left_start:mention_start]
    mention = text[mention_start:mention_end]
    right_context = text[mention_end:right_end]
    
    return left_context, mention, right_context


def normalize_whitespace(text: str) -> str:
    """
    规范化空白字符
    
    Args:
        text: 输入文本
    
    Returns:
        处理后的文本
    """
    # 替换多个空格为一个
    text = re.sub(r'\s+', ' ', text)
    
    # 去除首尾空白
    text = text.strip()
    
    return text


def remove_special_chars(text: str, keep_punctuation: bool = True) -> str:
    """
    移除特殊字符
    
    Args:
        text: 输入文本
        keep_punctuation: 是否保留标点符号
    
    Returns:
        处理后的文本
    """
    if keep_punctuation:
        # 只保留字母、数字、中文、标点
        pattern = r'[^\w\s\u4e00-\u9fff.,!?;:，。！？；：]'
    else:
        # 只保留字母、数字、中文
        pattern = r'[^\w\s\u4e00-\u9fff]'
    
    text = re.sub(pattern, '', text)
    
    return text


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """
    截断文本
    
    Args:
        text: 输入文本
        max_length: 最大长度
        suffix: 截断后缀
    
    Returns:
        截断后的文本
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


__all__ = [
    "split_sentences",
    "extract_sections",
    "sliding_window",
    "extract_context",
    "normalize_whitespace",
    "remove_special_chars",
    "truncate_text"
]

