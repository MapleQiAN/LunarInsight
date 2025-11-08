"""Translation management for LunarInsight."""
import json
from pathlib import Path
from typing import Dict, Any
import streamlit as st

# Supported languages
SUPPORTED_LANGUAGES = {
    "zh": "中文",
    "en": "English"
}

# Default language
DEFAULT_LANGUAGE = "zh"

# Translation data
TRANSLATIONS: Dict[str, Dict[str, Any]] = {
    "zh": {
        "app": {
            "title": "月悟·镜",
            "subtitle": "LunarInsight · 智能知识图谱分析平台",
            "page_title": "月悟·镜 | LunarInsight"
        },
        "navigation": {
            "title": "导航",
            "select_page": "选择页面",
            "dashboard": "📊 仪表板",
            "upload": "📤 上传文档",
            "graph_visualization": "🕸️ 图谱可视化",
            "query": "🔍 图谱查询",
            "status": "📈 处理状态"
        },
        "dashboard": {
            "title": "系统概览",
            "key_metrics": "核心指标",
            "total_nodes": "总节点数",
            "total_nodes_en": "Total Nodes",
            "total_edges": "总关系数",
            "total_edges_en": "Total Relationships",
            "concepts": "概念数",
            "concepts_en": "Concepts",
            "documents": "文档数",
            "documents_en": "Documents",
            "loading_data": "正在加载系统数据...",
            "quick_actions": "快速操作",
            "system_status": "系统状态",
            "api_service": "API 服务",
            "graph_database": "图谱数据库",
            "processing_engine": "处理引擎",
            "node_distribution": "节点类型分布",
            "upload_document": "上传文档",
            "view_graph": "查看图谱",
            "execute_query": "执行查询",
            "no_data": "暂无数据，请先上传文档进行处理",
            "concept": "概念",
            "document": "文档",
            "entity": "实体",
            "other": "其他",
            "type": "类型",
            "count": "数量"
        },
        "upload": {
            "title": "上传文档",
            "choose_file": "选择文件",
            "supported_formats": "支持格式: PDF, Markdown",
            "file": "文件",
            "size": "大小",
            "bytes": "字节",
            "upload_process": "上传并处理",
            "uploading": "正在上传文件...",
            "upload_success": "文件上传成功！",
            "view_result": "查看上传结果",
            "document_id": "文档 ID",
            "start_ingestion": "开始处理",
            "starting": "正在启动处理流程...",
            "ingestion_started": "处理已启动！",
            "view_ingestion_result": "查看处理结果",
            "job_id": "任务 ID",
            "check_status": "可在状态页面查看进度",
            "error": "错误"
        },
        "graph": {
            "title": "知识图谱可视化",
            "node_limit": "节点数量限制",
            "load_graph": "加载图谱",
            "loading": "正在加载图谱数据...",
            "loaded": "已加载 {nodes} 个节点和 {edges} 个关系",
            "nodes": "节点数",
            "edges": "关系数",
            "concepts": "概念数",
            "documents": "文档数",
            "graph_view": "图谱视图",
            "no_nodes": "图谱中未找到节点",
            "no_data": "API 未返回数据"
        },
        "query": {
            "title": "图谱查询",
            "query_type": "查询类型",
            "cypher_query": "Cypher 查询",
            "get_nodes": "获取节点",
            "get_edges": "获取关系",
            "enter_cypher": "输入 Cypher 查询语句",
            "cypher_help": "使用 Neo4j Cypher 语法查询图谱",
            "execute": "执行查询",
            "executing": "正在执行查询...",
            "success": "查询成功！",
            "view_result": "查看查询结果",
            "no_results": "查询未返回结果",
            "label_optional": "标签 (可选)",
            "label_help": "筛选特定标签的节点",
            "limit": "数量限制",
            "get_nodes_btn": "获取节点",
            "fetching_nodes": "正在获取节点...",
            "found_nodes": "找到 {count} 个节点",
            "view_raw_json": "查看原始 JSON",
            "no_nodes_found": "未找到节点",
            "rel_type_optional": "关系类型 (可选)",
            "rel_type_help": "筛选特定类型的关系",
            "get_edges_btn": "获取关系",
            "fetching_edges": "正在获取关系...",
            "found_edges": "找到 {count} 个关系",
            "no_edges_found": "未找到关系",
            "source": "源节点",
            "target": "目标节点",
            "type": "关系类型",
            "properties": "属性",
            "labels": "标签"
        },
        "status": {
            "title": "处理状态",
            "job_id": "任务 ID",
            "job_id_help": "输入要查询的任务 ID",
            "check_status": "检查状态",
            "checking": "正在检查状态...",
            "status": "状态",
            "progress": "进度",
            "statistics": "统计信息",
            "view_statistics": "查看详细统计",
            "view_full_result": "查看完整结果",
            "fetch_error": "无法获取状态信息",
            "enter_job_id": "请输入任务 ID 或从上传页面获取",
            "completed": "已完成",
            "processing": "处理中",
            "pending": "等待中",
            "failed": "失败",
            "unknown": "未知"
        },
        "common": {
            "loading": "加载中...",
            "success": "成功",
            "error": "错误",
            "warning": "警告",
            "info": "信息",
            "confirm": "确认",
            "cancel": "取消",
            "save": "保存",
            "delete": "删除",
            "edit": "编辑",
            "view": "查看",
            "close": "关闭",
            "language": "语言"
        }
    },
    "en": {
        "app": {
            "title": "LunarInsight",
            "subtitle": "LunarInsight · Intelligent Knowledge Graph Analysis Platform",
            "page_title": "LunarInsight"
        },
        "navigation": {
            "title": "Navigation",
            "select_page": "Choose a page",
            "dashboard": "📊 Dashboard",
            "upload": "📤 Upload Document",
            "graph_visualization": "🕸️ Graph Visualization",
            "query": "🔍 Graph Query",
            "status": "📈 Ingestion Status"
        },
        "dashboard": {
            "title": "System Overview",
            "key_metrics": "Key Metrics",
            "total_nodes": "Total Nodes",
            "total_nodes_en": "Total Nodes",
            "total_edges": "Total Relationships",
            "total_edges_en": "Total Relationships",
            "concepts": "Concepts",
            "concepts_en": "Concepts",
            "documents": "Documents",
            "documents_en": "Documents",
            "loading_data": "Loading system data...",
            "quick_actions": "Quick Actions",
            "system_status": "System Status",
            "api_service": "API Service",
            "graph_database": "Graph Database",
            "processing_engine": "Processing Engine",
            "node_distribution": "Node Type Distribution",
            "upload_document": "Upload Document",
            "view_graph": "View Graph",
            "execute_query": "Execute Query",
            "no_data": "No data available. Please upload documents first.",
            "concept": "Concept",
            "document": "Document",
            "entity": "Entity",
            "other": "Other",
            "type": "Type",
            "count": "Count"
        },
        "upload": {
            "title": "Upload Document",
            "choose_file": "Choose a file",
            "supported_formats": "Supported formats: PDF, Markdown",
            "file": "File",
            "size": "Size",
            "bytes": "bytes",
            "upload_process": "Upload & Process",
            "uploading": "Uploading file...",
            "upload_success": "File uploaded successfully!",
            "view_result": "View Upload Result",
            "document_id": "Document ID",
            "start_ingestion": "Start Ingestion",
            "starting": "Starting ingestion...",
            "ingestion_started": "Ingestion started!",
            "view_ingestion_result": "View Ingestion Result",
            "job_id": "Job ID",
            "check_status": "Check status on Status page",
            "error": "Error"
        },
        "graph": {
            "title": "Knowledge Graph Visualization",
            "node_limit": "Node Limit",
            "load_graph": "Load Graph",
            "loading": "Loading graph...",
            "loaded": "Loaded {nodes} nodes and {edges} relationships",
            "nodes": "Nodes",
            "edges": "Edges",
            "concepts": "Concepts",
            "documents": "Documents",
            "graph_view": "Graph View",
            "no_nodes": "No nodes found in the graph.",
            "no_data": "No data returned from API."
        },
        "query": {
            "title": "Graph Query",
            "query_type": "Query Type",
            "cypher_query": "Cypher Query",
            "get_nodes": "Get Nodes",
            "get_edges": "Get Edges",
            "enter_cypher": "Enter Cypher Query",
            "cypher_help": "Use Neo4j Cypher syntax to query the graph",
            "execute": "Execute Query",
            "executing": "Executing query...",
            "success": "Query executed successfully!",
            "view_result": "View Query Result",
            "no_results": "Query returned no results",
            "label_optional": "Label (optional)",
            "label_help": "Filter nodes by label",
            "limit": "Limit",
            "get_nodes_btn": "Get Nodes",
            "fetching_nodes": "Fetching nodes...",
            "found_nodes": "Found {count} nodes",
            "view_raw_json": "View Raw JSON",
            "no_nodes_found": "No nodes found",
            "rel_type_optional": "Relationship Type (optional)",
            "rel_type_help": "Filter edges by relationship type",
            "get_edges_btn": "Get Edges",
            "fetching_edges": "Fetching edges...",
            "found_edges": "Found {count} edges",
            "no_edges_found": "No edges found",
            "source": "Source",
            "target": "Target",
            "type": "Type",
            "properties": "Properties",
            "labels": "Labels"
        },
        "status": {
            "title": "Ingestion Status",
            "job_id": "Job ID",
            "job_id_help": "Enter the job ID to check status",
            "check_status": "Check Status",
            "checking": "Checking status...",
            "status": "Status",
            "progress": "Progress",
            "statistics": "Statistics",
            "view_statistics": "View Detailed Statistics",
            "view_full_result": "View Full Result",
            "fetch_error": "Unable to fetch status information",
            "enter_job_id": "Please enter a job ID or get one from the upload page",
            "completed": "Completed",
            "processing": "Processing",
            "pending": "Pending",
            "failed": "Failed",
            "unknown": "Unknown"
        },
        "common": {
            "loading": "Loading...",
            "success": "Success",
            "error": "Error",
            "warning": "Warning",
            "info": "Info",
            "confirm": "Confirm",
            "cancel": "Cancel",
            "save": "Save",
            "delete": "Delete",
            "edit": "Edit",
            "view": "View",
            "close": "Close",
            "language": "Language"
        }
    }
}


def get_language() -> str:
    """Get current language from session state."""
    if "language" not in st.session_state:
        st.session_state["language"] = DEFAULT_LANGUAGE
    return st.session_state["language"]


def set_language(lang: str) -> None:
    """Set current language in session state."""
    if lang in SUPPORTED_LANGUAGES:
        st.session_state["language"] = lang
    else:
        st.session_state["language"] = DEFAULT_LANGUAGE


def get_translations() -> Dict[str, Any]:
    """Get translations for current language."""
    lang = get_language()
    return TRANSLATIONS.get(lang, TRANSLATIONS[DEFAULT_LANGUAGE])


def t(key: str, **kwargs) -> str:
    """Get translated text by key path (e.g., 'dashboard.title')."""
    translations = get_translations()
    keys = key.split(".")
    value = translations
    for k in keys:
        if isinstance(value, dict):
            value = value.get(k)
        else:
            return key
    
    if value is None:
        return key
    
    # Format string if kwargs provided
    if isinstance(value, str) and kwargs:
        try:
            return value.format(**kwargs)
        except KeyError:
            return value
    
    return str(value)

