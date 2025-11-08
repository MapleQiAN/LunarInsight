"""Streamlit frontend for LunarInsight."""
import streamlit as st
import requests
import json
from typing import List, Dict, Any
import networkx as nx
from pyvis.network import Network
import pandas as pd
import os
from pathlib import Path

# Configuration
API_BASE = os.getenv("API_BASE", "http://localhost:8000")  # Default for local dev

st.set_page_config(
    page_title="LunarInsight | 月悟",
    page_icon="🌙",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load custom CSS
def load_css():
    """Load custom CSS styles."""
    css_path = Path(__file__).parent / "assets" / "style.css"
    if css_path.exists():
        with open(css_path, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    else:
        # Fallback inline CSS if file not found
        st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@200;300;400;500;600;700;900&display=swap');
        * { font-family: 'Noto Serif SC', serif !important; }
        </style>
        """, unsafe_allow_html=True)

load_css()

# Header with Chinese styling
st.markdown("""
<div style="text-align: center; padding: 2rem 0;">
    <h1 style="font-size: 3rem; margin-bottom: 0.5rem;">🌙 LunarInsight | 月悟</h1>
    <p style="font-size: 1.2rem; color: #6B4423; font-style: italic; margin-top: 0;">
        静心知识图谱引擎 · A quiet knowledge graph engine for insight
    </p>
</div>
""", unsafe_allow_html=True)


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
        st.error(f"API Error: {e}")
        return {}


def upload_file(uploaded_file) -> Dict[str, Any]:
    """Upload file to API."""
    files = {"file": (uploaded_file.name, uploaded_file.read(), uploaded_file.type)}
    response = requests.post(f"{API_BASE}/uploads", files=files)
    response.raise_for_status()
    return response.json()


def visualize_graph(nodes: List[Dict], edges: List[Dict]):
    """Visualize graph using pyvis with Chinese style colors."""
    # Chinese style background - warm beige/cream
    net = Network(
        height="700px", 
        width="100%", 
        bgcolor="#F5F1E8", 
        font_color="#3D2817",
        font_size=14
    )
    net.barnes_hut()
    
    # Chinese color palette
    colors = {
        "Concept": "#C9A961",      # Gold - concepts
        "Document": "#8B4513",     # Saddle brown - documents
        "Entity": "#D4AF37",       # Golden yellow - entities
        "default": "#B8945F"       # Muted gold - default
    }
    
    # Add nodes with Chinese style colors
    for node in nodes:
        node_id = node.get("id", "")
        labels = node.get("labels", [])
        props = node.get("properties", {})
        label = props.get("name") or props.get("filename") or node_id
        
        # Determine color based on labels
        color = colors["default"]
        border_color = "#6B4423"
        
        if "Concept" in labels:
            color = colors["Concept"]
            border_color = "#8B6914"
        elif "Document" in labels:
            color = colors["Document"]
            border_color = "#654321"
        elif "Entity" in labels:
            color = colors["Entity"]
            border_color = "#B8860B"
        
        net.add_node(
            node_id,
            label=label[:25],  # Truncate long labels
            color=color,
            border=border_color,
            font={"size": 14, "face": "Noto Serif SC, serif"},
            title=json.dumps(props, indent=2, ensure_ascii=False)
        )
    
    # Add edges with Chinese style
    for edge in edges:
        net.add_edge(
            edge.get("source"),
            edge.get("target"),
            label=edge.get("type", ""),
            color="#8B4513",
            width=2,
            title=json.dumps(edge.get("properties", {}), indent=2, ensure_ascii=False)
        )
    
    # Generate HTML with Chinese style physics
    net.set_options("""
    {
      "nodes": {
        "borderWidth": 2,
        "shadow": true,
        "font": {
          "size": 14,
          "face": "Noto Serif SC, serif"
        }
      },
      "edges": {
        "smooth": {
          "type": "continuous",
          "roundness": 0.5
        },
        "shadow": true,
        "font": {
          "size": 12,
          "face": "Noto Serif SC, serif"
        }
      },
      "physics": {
        "enabled": true,
        "stabilization": {
          "enabled": true,
          "iterations": 100,
          "fit": true
        },
        "barnesHut": {
          "gravitationalConstant": -2000,
          "centralGravity": 0.3,
          "springLength": 95,
          "springConstant": 0.04,
          "damping": 0.09
        }
      }
    }
    """)
    
    return net.generate_html()


# Sidebar with Chinese styling
st.sidebar.markdown("""
<div style="text-align: center; padding: 1rem 0; border-bottom: 2px solid #C9A961;">
    <h2 style="color: #F5E6D3; margin: 0;">导航 | Navigation</h2>
</div>
""", unsafe_allow_html=True)

page = st.sidebar.selectbox(
    "选择页面 | Choose a page",
    ["Upload", "Graph Visualization", "Query", "Status"],
    format_func=lambda x: {
        "Upload": "📤 上传文档",
        "Graph Visualization": "🕸️ 图谱可视化",
        "Query": "🔍 图谱查询",
        "Status": "📊 处理状态"
    }.get(x, x)
)

# Main content
if page == "Upload":
    st.markdown("### 📤 上传文档 | Upload Document")
    st.markdown("---")
    
    uploaded_file = st.file_uploader(
        "选择文件 | Choose a file",
        type=["pdf", "md", "markdown"],
        help="支持格式: PDF, Markdown | Supported formats: PDF, Markdown"
    )
    
    if uploaded_file is not None:
        col1, col2 = st.columns([2, 1])
        with col1:
            st.info(f"📄 **文件**: {uploaded_file.name} | **大小**: {uploaded_file.size:,} 字节")
        
        if st.button("📤 上传并处理 | Upload & Process", use_container_width=True):
            with st.spinner("正在上传文件... | Uploading file..."):
                try:
                    result = upload_file(uploaded_file)
                    st.success("✅ 文件上传成功！| File uploaded successfully!")
                    
                    with st.expander("查看上传结果 | View Upload Result", expanded=False):
                        st.json(result)
                    
                    doc_id = result.get("documentId")
                    if doc_id:
                        st.info(f"📋 **文档 ID**: `{doc_id}`")
                        
                        # Trigger ingestion
                        if st.button("🚀 开始处理 | Start Ingestion", use_container_width=True):
                            with st.spinner("正在启动处理流程... | Starting ingestion..."):
                                ingest_result = make_request(
                                    "POST",
                                    f"/ingest/{doc_id}"
                                )
                                if ingest_result:
                                    st.success("✅ 处理已启动！| Ingestion started!")
                                    
                                    with st.expander("查看处理结果 | View Ingestion Result", expanded=False):
                                        st.json(ingest_result)
                                    
                                    st.session_state["job_id"] = ingest_result.get("jobId")
                                    st.session_state["doc_id"] = doc_id
                                    
                                    if st.session_state.get("job_id"):
                                        st.info(f"💼 **任务 ID**: `{st.session_state['job_id']}` - 可在状态页面查看进度")
                except Exception as e:
                    st.error(f"❌ 错误: {e} | Error: {e}")

elif page == "Graph Visualization":
    st.markdown("### 🕸️ 知识图谱可视化 | Knowledge Graph Visualization")
    st.markdown("---")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        limit = st.number_input("节点数量限制 | Node Limit", min_value=10, max_value=500, value=100, step=10)
    with col2:
        st.write("")  # Spacing
        load_button = st.button("🔄 加载图谱 | Load Graph", use_container_width=True)
    
    if load_button:
        with st.spinner("正在加载图谱数据... | Loading graph..."):
            result = make_request("GET", f"/graph/query?limit={limit}")
            
            if result and "nodes" in result:
                nodes = result.get("nodes", [])
                edges = result.get("edges", [])
                
                st.success(f"✅ 已加载 {len(nodes)} 个节点和 {len(edges)} 个关系 | Loaded {len(nodes)} nodes and {len(edges)} relationships")
                
                # Display stats with Chinese labels
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("节点数 | Nodes", len(nodes))
                with col2:
                    st.metric("关系数 | Edges", len(edges))
                with col3:
                    concepts = [n for n in nodes if "Concept" in n.get("labels", [])]
                    st.metric("概念数 | Concepts", len(concepts))
                with col4:
                    documents = [n for n in nodes if "Document" in n.get("labels", [])]
                    st.metric("文档数 | Documents", len(documents))
                
                # Visualize
                if nodes:
                    st.markdown("### 📊 图谱视图 | Graph View")
                    html = visualize_graph(nodes, edges)
                    st.components.v1.html(html, height=700)
                else:
                    st.info("ℹ️ 图谱中未找到节点 | No nodes found in the graph.")
            else:
                st.warning("⚠️ API 未返回数据 | No data returned from API.")

elif page == "Query":
    st.markdown("### 🔍 图谱查询 | Graph Query")
    st.markdown("---")
    
    query_type = st.selectbox(
        "查询类型 | Query Type",
        ["Cypher Query", "Get Nodes", "Get Edges"],
        format_func=lambda x: {
            "Cypher Query": "🔤 Cypher 查询",
            "Get Nodes": "📦 获取节点",
            "Get Edges": "🔗 获取关系"
        }.get(x, x)
    )
    
    if query_type == "Cypher Query":
        st.markdown("#### 🔤 Cypher 查询 | Cypher Query")
        cypher = st.text_area(
            "输入 Cypher 查询语句 | Enter Cypher Query",
            value="MATCH (n) RETURN n LIMIT 10",
            height=120,
            help="使用 Neo4j Cypher 语法查询图谱 | Use Neo4j Cypher syntax to query the graph"
        )
        
        if st.button("▶️ 执行查询 | Execute Query", use_container_width=True):
            with st.spinner("正在执行查询... | Executing query..."):
                import urllib.parse
                encoded_cypher = urllib.parse.quote(cypher)
                result = make_request("GET", f"/graph/query?cypher={encoded_cypher}&limit=100")
                if result:
                    st.success("✅ 查询成功！| Query executed successfully!")
                    
                    with st.expander("查看查询结果 | View Query Result", expanded=True):
                        st.json(result)
                else:
                    st.warning("⚠️ 查询未返回结果 | Query returned no results")
    
    elif query_type == "Get Nodes":
        st.markdown("#### 📦 获取节点 | Get Nodes")
        col1, col2 = st.columns(2)
        with col1:
            label = st.text_input("标签 (可选) | Label (optional)", "", help="筛选特定标签的节点 | Filter nodes by label")
        with col2:
            limit = st.number_input("数量限制 | Limit", min_value=1, max_value=1000, value=100, step=10)
        
        if st.button("📦 获取节点 | Get Nodes", use_container_width=True):
            with st.spinner("正在获取节点... | Fetching nodes..."):
                endpoint = f"/graph/nodes?limit={limit}"
                if label:
                    endpoint += f"&label={label}"
                result = make_request("GET", endpoint)
                if result:
                    st.success(f"✅ 找到 {len(result)} 个节点 | Found {len(result)} nodes")
                    
                    # Display as table
                    if result:
                        df = pd.DataFrame([
                            {
                                "ID": n.get("id"),
                                "标签 | Labels": ", ".join(n.get("labels", [])),
                                "属性 | Properties": json.dumps(n.get("properties", {}), ensure_ascii=False)
                            }
                            for n in result
                        ])
                        st.dataframe(df, use_container_width=True)
                    
                    with st.expander("查看原始 JSON | View Raw JSON", expanded=False):
                        st.json(result)
                else:
                    st.warning("⚠️ 未找到节点 | No nodes found")
    
    elif query_type == "Get Edges":
        st.markdown("#### 🔗 获取关系 | Get Edges")
        col1, col2 = st.columns(2)
        with col1:
            rel_type = st.text_input("关系类型 (可选) | Relationship Type (optional)", "", help="筛选特定类型的关系 | Filter edges by relationship type")
        with col2:
            limit = st.number_input("数量限制 | Limit", min_value=1, max_value=1000, value=100, step=10)
        
        if st.button("🔗 获取关系 | Get Edges", use_container_width=True):
            with st.spinner("正在获取关系... | Fetching edges..."):
                endpoint = f"/graph/edges?limit={limit}"
                if rel_type:
                    endpoint += f"&rel_type={rel_type}"
                result = make_request("GET", endpoint)
                if result:
                    st.success(f"✅ 找到 {len(result)} 个关系 | Found {len(result)} edges")
                    
                    # Display as table
                    if result:
                        df = pd.DataFrame([
                            {
                                "源节点 | Source": e.get("source"),
                                "关系类型 | Type": e.get("type"),
                                "目标节点 | Target": e.get("target"),
                                "属性 | Properties": json.dumps(e.get("properties", {}), ensure_ascii=False)
                            }
                            for e in result
                        ])
                        st.dataframe(df, use_container_width=True)
                    
                    with st.expander("查看原始 JSON | View Raw JSON", expanded=False):
                        st.json(result)
                else:
                    st.warning("⚠️ 未找到关系 | No edges found")

elif page == "Status":
    st.markdown("### 📊 处理状态 | Ingestion Status")
    st.markdown("---")
    
    job_id = st.text_input(
        "任务 ID | Job ID", 
        value=st.session_state.get("job_id", ""),
        help="输入要查询的任务 ID | Enter the job ID to check status"
    )
    
    if job_id:
        if st.button("🔄 检查状态 | Check Status", use_container_width=True):
            with st.spinner("正在检查状态... | Checking status..."):
                result = make_request("GET", f"/ingest/status/{job_id}")
                if result:
                    status = result.get("status", "unknown")
                    progress = result.get("progress", 0)
                    message = result.get("message", "")
                    
                    # Status display with Chinese labels
                    col1, col2 = st.columns([1, 2])
                    with col1:
                        status_emoji = {
                            "completed": "✅",
                            "processing": "⏳",
                            "pending": "⏸️",
                            "failed": "❌",
                            "unknown": "❓"
                        }.get(status.lower(), "❓")
                        st.metric("状态 | Status", f"{status_emoji} {status}")
                    
                    with col2:
                        st.metric("进度 | Progress", f"{progress}%")
                    
                    # Progress bar
                    st.progress(progress / 100 if progress > 0 else 0)
                    
                    if message:
                        st.info(f"💬 {message}")
                    
                    # Statistics section
                    if "stats" in result:
                        st.markdown("#### 📈 统计信息 | Statistics")
                        stats = result["stats"]
                        
                        if isinstance(stats, dict):
                            stats_cols = st.columns(min(len(stats), 4))
                            for idx, (key, value) in enumerate(stats.items()):
                                with stats_cols[idx % len(stats_cols)]:
                                    st.metric(key.replace("_", " ").title(), value)
                        
                        with st.expander("查看详细统计 | View Detailed Statistics", expanded=False):
                            st.json(stats)
                    
                    # Full result
                    with st.expander("查看完整结果 | View Full Result", expanded=False):
                        st.json(result)
                else:
                    st.error("❌ 无法获取状态信息 | Unable to fetch status information")
    else:
        st.info("ℹ️ 请输入任务 ID 或从上传页面获取 | Please enter a job ID or get one from the upload page")

