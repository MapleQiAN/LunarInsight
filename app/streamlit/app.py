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
    page_title="月悟·镜 | LunarInsight",
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

# Header with professional styling
st.markdown("""
<div style="text-align: center; padding: 2.5rem 0 2rem 0;">
    <h1 style="font-size: 3.5rem; margin-bottom: 0.75rem; font-weight: 700; letter-spacing: -0.02em;">
        月悟·镜
    </h1>
    <p style="font-size: 1.125rem; color: #64748b; font-weight: 400; margin-top: 0.5rem; letter-spacing: 0.05em;">
        LunarInsight · 智能知识图谱分析平台
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
    """Visualize graph using pyvis with professional color scheme."""
    # Professional background - light gray
    net = Network(
        height="700px", 
        width="100%", 
        bgcolor="#f8fafc", 
        font_color="#1e293b",
        font_size=14
    )
    net.barnes_hut()
    
    # Professional color palette
    colors = {
        "Concept": "#0ea5e9",      # Cyan - concepts
        "Document": "#2d3748",     # Dark gray - documents
        "Entity": "#d4af37",       # Gold - entities
        "default": "#64748b"       # Slate gray - default
    }
    
    # Add nodes with professional colors
    for node in nodes:
        node_id = node.get("id", "")
        labels = node.get("labels", [])
        props = node.get("properties", {})
        label = props.get("name") or props.get("filename") or node_id
        
        # Determine color based on labels
        color = colors["default"]
        border_color = "#475569"
        
        if "Concept" in labels:
            color = colors["Concept"]
            border_color = "#0284c7"
        elif "Document" in labels:
            color = colors["Document"]
            border_color = "#1a2332"
        elif "Entity" in labels:
            color = colors["Entity"]
            border_color = "#b8945f"
        
        net.add_node(
            node_id,
            label=label[:25],  # Truncate long labels
            color=color,
            border=border_color,
            font={"size": 14, "face": "Inter, Noto Serif SC, sans-serif"},
            title=json.dumps(props, indent=2, ensure_ascii=False)
        )
    
    # Add edges with professional style
    for edge in edges:
        net.add_edge(
            edge.get("source"),
            edge.get("target"),
            label=edge.get("type", ""),
            color="#94a3b8",
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
          "face": "Inter, Noto Serif SC, sans-serif"
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
          "face": "Inter, Noto Serif SC, sans-serif"
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


# Sidebar with professional styling
st.sidebar.markdown("""
<div style="text-align: center; padding: 1.25rem 0; border-bottom: 1px solid rgba(255, 255, 255, 0.1);">
    <h2 style="color: #ffffff; margin: 0; font-size: 1.125rem; font-weight: 600; letter-spacing: 0.05em;">
        导航 | Navigation
    </h2>
</div>
""", unsafe_allow_html=True)

page = st.sidebar.selectbox(
    "选择页面 | Choose a page",
    ["Dashboard", "Upload", "Graph Visualization", "Query", "Status"],
    format_func=lambda x: {
        "Dashboard": "📊 仪表板",
        "Upload": "📤 上传文档",
        "Graph Visualization": "🕸️ 图谱可视化",
        "Query": "🔍 图谱查询",
        "Status": "📈 处理状态"
    }.get(x, x)
)

# Main content
if page == "Dashboard":
    st.markdown("### 📊 系统概览 | System Overview")
    st.markdown("---")
    
    # Fetch system statistics
    with st.spinner("正在加载系统数据... | Loading system data..."):
        # Get graph statistics with reasonable limits for dashboard
        nodes_result = make_request("GET", "/graph/nodes?limit=1000")
        edges_result = make_request("GET", "/graph/edges?limit=1000")
        
        # Calculate statistics
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
    
    # Key Metrics Row
    st.markdown("#### 核心指标 | Key Metrics")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("""
        <div class="dashboard-card" style="background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%); border-left: 4px solid #3b82f6;">
            <div style="font-size: 0.875rem; color: #1e40af; font-weight: 600; margin-bottom: 0.5rem; text-transform: uppercase; letter-spacing: 0.05em;">
                总节点数
            </div>
            <div style="font-size: 2.5rem; font-weight: 700; color: #1e40af; margin: 0.5rem 0;">
                {total_nodes:,}
            </div>
            <div style="font-size: 0.75rem; color: #64748b;">
                Total Nodes
            </div>
        </div>
        """.format(total_nodes=total_nodes), unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="dashboard-card" style="background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%); border-left: 4px solid #10b981;">
            <div style="font-size: 0.875rem; color: #166534; font-weight: 600; margin-bottom: 0.5rem; text-transform: uppercase; letter-spacing: 0.05em;">
                总关系数
            </div>
            <div style="font-size: 2.5rem; font-weight: 700; color: #166534; margin: 0.5rem 0;">
                {total_edges:,}
            </div>
            <div style="font-size: 0.75rem; color: #64748b;">
                Total Relationships
            </div>
        </div>
        """.format(total_edges=total_edges), unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="dashboard-card" style="background: linear-gradient(135deg, #fffbeb 0%, #fef3c7 100%); border-left: 4px solid #d4af37;">
            <div style="font-size: 0.875rem; color: #92400e; font-weight: 600; margin-bottom: 0.5rem; text-transform: uppercase; letter-spacing: 0.05em;">
                概念数
            </div>
            <div style="font-size: 2.5rem; font-weight: 700; color: #92400e; margin: 0.5rem 0;">
                {concepts:,}
            </div>
            <div style="font-size: 0.75rem; color: #64748b;">
                Concepts
            </div>
        </div>
        """.format(concepts=concepts_count), unsafe_allow_html=True)
    
    with col4:
        st.markdown("""
        <div class="dashboard-card" style="background: linear-gradient(135deg, #fef2f2 0%, #fee2e2 100%); border-left: 4px solid #ef4444;">
            <div style="font-size: 0.875rem; color: #991b1b; font-weight: 600; margin-bottom: 0.5rem; text-transform: uppercase; letter-spacing: 0.05em;">
                文档数
            </div>
            <div style="font-size: 2.5rem; font-weight: 700; color: #991b1b; margin: 0.5rem 0;">
                {documents:,}
            </div>
            <div style="font-size: 0.75rem; color: #64748b;">
                Documents
            </div>
        </div>
        """.format(documents=documents_count), unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Quick Actions and System Status
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("#### 🚀 快速操作 | Quick Actions")
        action_col1, action_col2, action_col3 = st.columns(3)
        
        with action_col1:
            if st.button("📤 上传文档", use_container_width=True, key="quick_upload"):
                st.session_state["page_redirect"] = "Upload"
        
        with action_col2:
            if st.button("🕸️ 查看图谱", use_container_width=True, key="quick_graph"):
                st.session_state["page_redirect"] = "Graph Visualization"
        
        with action_col3:
            if st.button("🔍 执行查询", use_container_width=True, key="quick_query"):
                st.session_state["page_redirect"] = "Query"
    
    with col2:
        st.markdown("#### ⚡ 系统状态 | System Status")
        st.markdown("""
        <div style="background: #ffffff; border-radius: 10px; padding: 1.25rem; border: 1px solid #e2e8f0; box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);">
            <div style="display: flex; align-items: center; margin-bottom: 1rem;">
                <div style="width: 12px; height: 12px; border-radius: 50%; background: #10b981; margin-right: 0.75rem;"></div>
                <span style="font-weight: 600; color: #1e293b;">API 服务</span>
            </div>
            <div style="display: flex; align-items: center; margin-bottom: 1rem;">
                <div style="width: 12px; height: 12px; border-radius: 50%; background: #10b981; margin-right: 0.75rem;"></div>
                <span style="font-weight: 600; color: #1e293b;">图谱数据库</span>
            </div>
            <div style="display: flex; align-items: center;">
                <div style="width: 12px; height: 12px; border-radius: 50%; background: #10b981; margin-right: 0.75rem;"></div>
                <span style="font-weight: 600; color: #1e293b;">处理引擎</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Node Type Distribution
    st.markdown("#### 📊 节点类型分布 | Node Type Distribution")
    if total_nodes > 0:
        distribution_data = {
            "类型 | Type": ["概念 | Concept", "文档 | Document", "实体 | Entity", "其他 | Other"],
            "数量 | Count": [
                concepts_count,
                documents_count,
                entities_count,
                total_nodes - concepts_count - documents_count - entities_count
            ]
        }
        df_dist = pd.DataFrame(distribution_data)
        st.bar_chart(df_dist.set_index("类型 | Type"))
    else:
        st.info("ℹ️ 暂无数据，请先上传文档进行处理 | No data available. Please upload documents first.")
    
    # Handle page redirect
    if st.session_state.get("page_redirect"):
        page = st.session_state.pop("page_redirect")
        st.session_state["page_redirect"] = None
        st.rerun()

elif page == "Upload":
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

