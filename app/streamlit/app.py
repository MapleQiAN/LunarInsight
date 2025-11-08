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
from i18n.translations import get_translations, get_language, set_language, SUPPORTED_LANGUAGES, t

# Configuration
API_BASE = os.getenv("API_BASE", "http://localhost:8000")  # Default for local dev

# Initialize translations
translations = get_translations()

st.set_page_config(
    page_title=t("app.page_title"),
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
def render_header():
    """Render header with translations."""
    title = t("app.title")
    subtitle = t("app.subtitle")
    st.markdown(f"""
    <div style="text-align: center; padding: 2.5rem 0 2rem 0;">
        <h1 style="font-size: 3.5rem; margin-bottom: 0.75rem; font-weight: 700; letter-spacing: -0.02em;">
            {title}
        </h1>
        <p style="font-size: 1.125rem; color: #64748b; font-weight: 400; margin-top: 0.5rem; letter-spacing: 0.05em;">
            {subtitle}
        </p>
    </div>
    """, unsafe_allow_html=True)

render_header()


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
st.sidebar.markdown(f"""
<div style="text-align: center; padding: 1.25rem 0; border-bottom: 1px solid rgba(255, 255, 255, 0.1);">
    <h2 style="color: #ffffff; margin: 0; font-size: 1.125rem; font-weight: 600; letter-spacing: 0.05em;">
        {t("navigation.title")}
    </h2>
</div>
""", unsafe_allow_html=True)

# Language selector
st.sidebar.markdown("---")
selected_lang = st.sidebar.selectbox(
    f"🌐 {t('common.language')}",
    options=list(SUPPORTED_LANGUAGES.keys()),
    format_func=lambda x: f"{SUPPORTED_LANGUAGES[x]}",
    index=list(SUPPORTED_LANGUAGES.keys()).index(get_language())
)

if selected_lang != get_language():
    set_language(selected_lang)
    translations = get_translations()
    st.rerun()

page = st.sidebar.selectbox(
    t("navigation.select_page"),
    ["Dashboard", "Upload", "Graph Visualization", "Query", "Status"],
    format_func=lambda x: {
        "Dashboard": t("navigation.dashboard"),
        "Upload": t("navigation.upload"),
        "Graph Visualization": t("navigation.graph_visualization"),
        "Query": t("navigation.query"),
        "Status": t("navigation.status")
    }.get(x, x)
)

# Main content
if page == "Dashboard":
    st.markdown(f"### 📊 {t('dashboard.title')}")
    st.markdown("---")
    
    # Fetch system statistics
    with st.spinner(t("dashboard.loading_data")):
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
    st.markdown(f"#### {t('dashboard.key_metrics')}")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="dashboard-card" style="background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%); border-left: 4px solid #3b82f6;">
            <div style="font-size: 0.875rem; color: #1e40af; font-weight: 600; margin-bottom: 0.5rem; text-transform: uppercase; letter-spacing: 0.05em;">
                {t('dashboard.total_nodes')}
            </div>
            <div style="font-size: 2.5rem; font-weight: 700; color: #1e40af; margin: 0.5rem 0;">
                {total_nodes:,}
            </div>
            <div style="font-size: 0.75rem; color: #64748b;">
                {t('dashboard.total_nodes_en')}
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="dashboard-card" style="background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%); border-left: 4px solid #10b981;">
            <div style="font-size: 0.875rem; color: #166534; font-weight: 600; margin-bottom: 0.5rem; text-transform: uppercase; letter-spacing: 0.05em;">
                {t('dashboard.total_edges')}
            </div>
            <div style="font-size: 2.5rem; font-weight: 700; color: #166534; margin: 0.5rem 0;">
                {total_edges:,}
            </div>
            <div style="font-size: 0.75rem; color: #64748b;">
                {t('dashboard.total_edges_en')}
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="dashboard-card" style="background: linear-gradient(135deg, #fffbeb 0%, #fef3c7 100%); border-left: 4px solid #d4af37;">
            <div style="font-size: 0.875rem; color: #92400e; font-weight: 600; margin-bottom: 0.5rem; text-transform: uppercase; letter-spacing: 0.05em;">
                {t('dashboard.concepts')}
            </div>
            <div style="font-size: 2.5rem; font-weight: 700; color: #92400e; margin: 0.5rem 0;">
                {concepts_count:,}
            </div>
            <div style="font-size: 0.75rem; color: #64748b;">
                {t('dashboard.concepts_en')}
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="dashboard-card" style="background: linear-gradient(135deg, #fef2f2 0%, #fee2e2 100%); border-left: 4px solid #ef4444;">
            <div style="font-size: 0.875rem; color: #991b1b; font-weight: 600; margin-bottom: 0.5rem; text-transform: uppercase; letter-spacing: 0.05em;">
                {t('dashboard.documents')}
            </div>
            <div style="font-size: 2.5rem; font-weight: 700; color: #991b1b; margin: 0.5rem 0;">
                {documents_count:,}
            </div>
            <div style="font-size: 0.75rem; color: #64748b;">
                {t('dashboard.documents_en')}
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Quick Actions and System Status
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown(f"#### 🚀 {t('dashboard.quick_actions')}")
        action_col1, action_col2, action_col3 = st.columns(3)
        
        with action_col1:
            if st.button(f"📤 {t('dashboard.upload_document')}", use_container_width=True, key="quick_upload"):
                st.session_state["page_redirect"] = "Upload"
        
        with action_col2:
            if st.button(f"🕸️ {t('dashboard.view_graph')}", use_container_width=True, key="quick_graph"):
                st.session_state["page_redirect"] = "Graph Visualization"
        
        with action_col3:
            if st.button(f"🔍 {t('dashboard.execute_query')}", use_container_width=True, key="quick_query"):
                st.session_state["page_redirect"] = "Query"
    
    with col2:
        st.markdown(f"#### ⚡ {t('dashboard.system_status')}")
        st.markdown(f"""
        <div style="background: #ffffff; border-radius: 10px; padding: 1.25rem; border: 1px solid #e2e8f0; box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);">
            <div style="display: flex; align-items: center; margin-bottom: 1rem;">
                <div style="width: 12px; height: 12px; border-radius: 50%; background: #10b981; margin-right: 0.75rem;"></div>
                <span style="font-weight: 600; color: #1e293b;">{t('dashboard.api_service')}</span>
            </div>
            <div style="display: flex; align-items: center; margin-bottom: 1rem;">
                <div style="width: 12px; height: 12px; border-radius: 50%; background: #10b981; margin-right: 0.75rem;"></div>
                <span style="font-weight: 600; color: #1e293b;">{t('dashboard.graph_database')}</span>
            </div>
            <div style="display: flex; align-items: center;">
                <div style="width: 12px; height: 12px; border-radius: 50%; background: #10b981; margin-right: 0.75rem;"></div>
                <span style="font-weight: 600; color: #1e293b;">{t('dashboard.processing_engine')}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Node Type Distribution
    st.markdown(f"#### 📊 {t('dashboard.node_distribution')}")
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
        st.bar_chart(df_dist.set_index(type_label))
    else:
        st.info(f"ℹ️ {t('dashboard.no_data')}")
    
    # Handle page redirect
    if st.session_state.get("page_redirect"):
        page = st.session_state.pop("page_redirect")
        st.session_state["page_redirect"] = None
        st.rerun()

elif page == "Upload":
    st.markdown(f"### 📤 {t('upload.title')}")
    st.markdown("---")
    
    uploaded_file = st.file_uploader(
        t("upload.choose_file"),
        type=["pdf", "md", "markdown"],
        help=t("upload.supported_formats")
    )
    
    if uploaded_file is not None:
        col1, col2 = st.columns([2, 1])
        with col1:
            st.info(f"📄 **{t('upload.file')}**: {uploaded_file.name} | **{t('upload.size')}**: {uploaded_file.size:,} {t('upload.bytes')}")
        
        if st.button(f"📤 {t('upload.upload_process')}", use_container_width=True):
            with st.spinner(t("upload.uploading")):
                try:
                    result = upload_file(uploaded_file)
                    st.success(f"✅ {t('upload.upload_success')}")
                    
                    with st.expander(t("upload.view_result"), expanded=False):
                        st.json(result)
                    
                    doc_id = result.get("documentId")
                    if doc_id:
                        st.info(f"📋 **{t('upload.document_id')}**: `{doc_id}`")
                        
                        # Trigger ingestion
                        if st.button(f"🚀 {t('upload.start_ingestion')}", use_container_width=True):
                            with st.spinner(t("upload.starting")):
                                ingest_result = make_request(
                                    "POST",
                                    f"/ingest/{doc_id}"
                                )
                                if ingest_result:
                                    st.success(f"✅ {t('upload.ingestion_started')}")
                                    
                                    with st.expander(t("upload.view_ingestion_result"), expanded=False):
                                        st.json(ingest_result)
                                    
                                    st.session_state["job_id"] = ingest_result.get("jobId")
                                    st.session_state["doc_id"] = doc_id
                                    
                                    if st.session_state.get("job_id"):
                                        st.info(f"💼 **{t('upload.job_id')}**: `{st.session_state['job_id']}` - {t('upload.check_status')}")
                except Exception as e:
                    st.error(f"❌ {t('upload.error')}: {e}")

elif page == "Graph Visualization":
    st.markdown(f"### 🕸️ {t('graph.title')}")
    st.markdown("---")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        limit = st.number_input(t("graph.node_limit"), min_value=10, max_value=500, value=100, step=10)
    with col2:
        st.write("")  # Spacing
        load_button = st.button(f"🔄 {t('graph.load_graph')}", use_container_width=True)
    
    if load_button:
        with st.spinner(t("graph.loading")):
            result = make_request("GET", f"/graph/query?limit={limit}")
            
            if result and "nodes" in result:
                nodes = result.get("nodes", [])
                edges = result.get("edges", [])
                
                st.success(t("graph.loaded", nodes=len(nodes), edges=len(edges)))
                
                # Display stats
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric(t("graph.nodes"), len(nodes))
                with col2:
                    st.metric(t("graph.edges"), len(edges))
                with col3:
                    concepts = [n for n in nodes if "Concept" in n.get("labels", [])]
                    st.metric(t("graph.concepts"), len(concepts))
                with col4:
                    documents = [n for n in nodes if "Document" in n.get("labels", [])]
                    st.metric(t("graph.documents"), len(documents))
                
                # Visualize
                if nodes:
                    st.markdown(f"### 📊 {t('graph.graph_view')}")
                    html = visualize_graph(nodes, edges)
                    st.components.v1.html(html, height=700)
                else:
                    st.info(f"ℹ️ {t('graph.no_nodes')}")
            else:
                st.warning(f"⚠️ {t('graph.no_data')}")

elif page == "Query":
    st.markdown(f"### 🔍 {t('query.title')}")
    st.markdown("---")
    
    query_type = st.selectbox(
        t("query.query_type"),
        ["Cypher Query", "Get Nodes", "Get Edges"],
        format_func=lambda x: {
            "Cypher Query": f"🔤 {t('query.cypher_query')}",
            "Get Nodes": f"📦 {t('query.get_nodes')}",
            "Get Edges": f"🔗 {t('query.get_edges')}"
        }.get(x, x)
    )
    
    if query_type == "Cypher Query":
        st.markdown(f"#### 🔤 {t('query.cypher_query')}")
        cypher = st.text_area(
            t("query.enter_cypher"),
            value="MATCH (n) RETURN n LIMIT 10",
            height=120,
            help=t("query.cypher_help")
        )
        
        if st.button(f"▶️ {t('query.execute')}", use_container_width=True):
            with st.spinner(t("query.executing")):
                import urllib.parse
                encoded_cypher = urllib.parse.quote(cypher)
                result = make_request("GET", f"/graph/query?cypher={encoded_cypher}&limit=100")
                if result:
                    st.success(f"✅ {t('query.success')}")
                    
                    with st.expander(t("query.view_result"), expanded=True):
                        st.json(result)
                else:
                    st.warning(f"⚠️ {t('query.no_results')}")
    
    elif query_type == "Get Nodes":
        st.markdown(f"#### 📦 {t('query.get_nodes')}")
        col1, col2 = st.columns(2)
        with col1:
            label = st.text_input(t("query.label_optional"), "", help=t("query.label_help"))
        with col2:
            limit = st.number_input(t("query.limit"), min_value=1, max_value=1000, value=100, step=10)
        
        if st.button(f"📦 {t('query.get_nodes_btn')}", use_container_width=True):
            with st.spinner(t("query.fetching_nodes")):
                endpoint = f"/graph/nodes?limit={limit}"
                if label:
                    endpoint += f"&label={label}"
                result = make_request("GET", endpoint)
                if result:
                    st.success(t("query.found_nodes", count=len(result)))
                    
                    # Display as table
                    if result:
                        df = pd.DataFrame([
                            {
                                "ID": n.get("id"),
                                t("query.labels"): ", ".join(n.get("labels", [])),
                                t("query.properties"): json.dumps(n.get("properties", {}), ensure_ascii=False)
                            }
                            for n in result
                        ])
                        st.dataframe(df, use_container_width=True)
                    
                    with st.expander(t("query.view_raw_json"), expanded=False):
                        st.json(result)
                else:
                    st.warning(f"⚠️ {t('query.no_nodes_found')}")
    
    elif query_type == "Get Edges":
        st.markdown(f"#### 🔗 {t('query.get_edges')}")
        col1, col2 = st.columns(2)
        with col1:
            rel_type = st.text_input(t("query.rel_type_optional"), "", help=t("query.rel_type_help"))
        with col2:
            limit = st.number_input(t("query.limit"), min_value=1, max_value=1000, value=100, step=10)
        
        if st.button(f"🔗 {t('query.get_edges_btn')}", use_container_width=True):
            with st.spinner(t("query.fetching_edges")):
                endpoint = f"/graph/edges?limit={limit}"
                if rel_type:
                    endpoint += f"&rel_type={rel_type}"
                result = make_request("GET", endpoint)
                if result:
                    st.success(t("query.found_edges", count=len(result)))
                    
                    # Display as table
                    if result:
                        df = pd.DataFrame([
                            {
                                t("query.source"): e.get("source"),
                                t("query.type"): e.get("type"),
                                t("query.target"): e.get("target"),
                                t("query.properties"): json.dumps(e.get("properties", {}), ensure_ascii=False)
                            }
                            for e in result
                        ])
                        st.dataframe(df, use_container_width=True)
                    
                    with st.expander(t("query.view_raw_json"), expanded=False):
                        st.json(result)
                else:
                    st.warning(f"⚠️ {t('query.no_edges_found')}")

elif page == "Status":
    st.markdown(f"### 📊 {t('status.title')}")
    st.markdown("---")
    
    job_id = st.text_input(
        t("status.job_id"), 
        value=st.session_state.get("job_id", ""),
        help=t("status.job_id_help")
    )
    
    if job_id:
        if st.button(f"🔄 {t('status.check_status')}", use_container_width=True):
            with st.spinner(t("status.checking")):
                result = make_request("GET", f"/ingest/status/{job_id}")
                if result:
                    status = result.get("status", "unknown")
                    progress = result.get("progress", 0)
                    message = result.get("message", "")
                    
                    # Status display
                    col1, col2 = st.columns([1, 2])
                    with col1:
                        status_emoji = {
                            "completed": "✅",
                            "processing": "⏳",
                            "pending": "⏸️",
                            "failed": "❌",
                            "unknown": "❓"
                        }.get(status.lower(), "❓")
                        st.metric(t("status.status"), f"{status_emoji} {status}")
                    
                    with col2:
                        st.metric(t("status.progress"), f"{progress}%")
                    
                    # Progress bar
                    st.progress(progress / 100 if progress > 0 else 0)
                    
                    if message:
                        st.info(f"💬 {message}")
                    
                    # Statistics section
                    if "stats" in result:
                        st.markdown(f"#### 📈 {t('status.statistics')}")
                        stats = result["stats"]
                        
                        if isinstance(stats, dict):
                            stats_cols = st.columns(min(len(stats), 4))
                            for idx, (key, value) in enumerate(stats.items()):
                                with stats_cols[idx % len(stats_cols)]:
                                    st.metric(key.replace("_", " ").title(), value)
                        
                        with st.expander(t("status.view_statistics"), expanded=False):
                            st.json(stats)
                    
                    # Full result
                    with st.expander(t("status.view_full_result"), expanded=False):
                        st.json(result)
                else:
                    st.error(f"❌ {t('status.fetch_error')}")
    else:
        st.info(f"ℹ️ {t('status.enter_job_id')}")

