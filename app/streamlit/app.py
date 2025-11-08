"""Streamlit frontend for LunarInsight - 水墨留白风格仪表板."""
import streamlit as st
import requests
import json
from typing import List, Dict, Any
import pandas as pd
import os
from pathlib import Path
from i18n.translations import get_translations, get_language, set_language, SUPPORTED_LANGUAGES, t

# Configuration
API_BASE = os.getenv("API_BASE", "http://localhost:8000")

# Initialize translations
translations = get_translations()

st.set_page_config(
    page_title=t("app.page_title"),
    page_icon="🌙",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Load custom CSS
def load_css():
    """Load custom CSS styles."""
    css_path = Path(__file__).parent / "assets" / "style.css"
    if css_path.exists():
        with open(css_path, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

load_css()

# API请求函数
def make_request(method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
    """Make API request."""
    url = f"{API_BASE}{endpoint}"
    try:
        if method == "GET":
            response = requests.get(url, **kwargs)
        elif method == "POST":
            response = requests.post(url, **kwargs)
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {}

# 顶部标题栏
def render_header():
    """渲染顶部标题栏 - 左：项目名，右：用户菜单（语言选择）"""
    lang = get_language()
    lang_display = SUPPORTED_LANGUAGES.get(lang, "中文")
    
    st.markdown(f"""
    <div class="header-container">
        <div>
            <span class="header-title">月悟</span>
            <span class="header-subtitle">LunarInsight</span>
        </div>
        <div class="header-menu">
            <span style="font-size: 0.875rem; color: #8A9BA3;">{lang_display}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

render_header()

# 侧边栏 - 语言选择
with st.sidebar:
    selected_lang = st.selectbox(
        t("common.language"),
        options=list(SUPPORTED_LANGUAGES.keys()),
        format_func=lambda x: SUPPORTED_LANGUAGES[x],
        index=list(SUPPORTED_LANGUAGES.keys()).index(get_language())
    )
    
    if selected_lang != get_language():
        set_language(selected_lang)
        translations = get_translations()
        st.rerun()

# 主内容区
st.markdown("""
<div class="content-container">
""", unsafe_allow_html=True)

# 获取系统统计数据
with st.spinner(t("dashboard.loading_data")):
    nodes_result = make_request("GET", "/graph/nodes?limit=1000")
    edges_result = make_request("GET", "/graph/edges?limit=1000")
    
    # 计算统计
    total_nodes = 0
    total_edges = 0
    concepts_count = 0
    documents_count = 0
    entities_count = 0
    
    if nodes_result and isinstance(nodes_result, list):
        total_nodes = len(nodes_result)
        concepts_count = len([n for n in nodes_result if "Concept" in n.get("labels", [])])
        documents_count = len([n for n in nodes_result if "Document" in n.get("labels", [])])
        entities_count = len([n for n in nodes_result if "Entity" in n.get("labels", [])])
    
    if edges_result and isinstance(edges_result, list):
        total_edges = len(edges_result)

# 关键指标展示区 - 最多4张卡片
st.markdown("""
<div class="content-section">
""", unsafe_allow_html=True)

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-card-label">{t('dashboard.total_nodes')}</div>
        <div class="metric-card-value">{total_nodes:,}</div>
        <div class="metric-card-sublabel">{t('dashboard.total_nodes_en')}</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-card-label">{t('dashboard.total_edges')}</div>
        <div class="metric-card-value">{total_edges:,}</div>
        <div class="metric-card-sublabel">{t('dashboard.total_edges_en')}</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-card-label">{t('dashboard.concepts')}</div>
        <div class="metric-card-value">{concepts_count:,}</div>
        <div class="metric-card-sublabel">{t('dashboard.concepts_en')}</div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-card-label">{t('dashboard.documents')}</div>
        <div class="metric-card-value accent">{documents_count:,}</div>
        <div class="metric-card-sublabel">{t('dashboard.documents_en')}</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)

# 主要内容区 - 1个主图表 + 1个辅助信息面板
st.markdown("""
<div class="content-section">
""", unsafe_allow_html=True)

col_main, col_side = st.columns([2, 1])

with col_main:
    # 主图表
    st.markdown(f"""
    <div class="chart-container">
        <div class="info-panel-title">{t('dashboard.node_distribution')}</div>
    </div>
    """, unsafe_allow_html=True)
    
    if total_nodes > 0:
        type_label = t("dashboard.type")
        count_label = t("dashboard.count")
        distribution_data = {
            type_label: [
                t("dashboard.concept"),
                t("dashboard.document"),
                t("dashboard.entity"),
                t("dashboard.other")
            ],
            count_label: [
                concepts_count,
                documents_count,
                entities_count,
                total_nodes - concepts_count - documents_count - entities_count
            ]
        }
        df_dist = pd.DataFrame(distribution_data)
        st.bar_chart(df_dist.set_index(type_label), use_container_width=True)
    else:
        st.markdown(f"""
        <div style="padding: 2rem; text-align: center; color: #8A9BA3;">
            {t('dashboard.no_data')}
        </div>
        """, unsafe_allow_html=True)

with col_side:
    # 辅助信息面板
    st.markdown(f"""
    <div class="info-panel">
        <div class="info-panel-title">{t('dashboard.system_status')}</div>
        <div class="info-panel-item">
            <div class="info-panel-indicator"></div>
            <span>{t('dashboard.api_service')}</span>
        </div>
        <div class="info-panel-item">
            <div class="info-panel-indicator"></div>
            <span>{t('dashboard.graph_database')}</span>
        </div>
        <div class="info-panel-item">
            <div class="info-panel-indicator"></div>
            <span>{t('dashboard.processing_engine')}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)
