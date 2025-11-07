"""Streamlit frontend for LunarInsight."""
import streamlit as st
import requests
import json
from typing import List, Dict, Any
import networkx as nx
from pyvis.network import Network
import pandas as pd
import os

# Configuration
API_BASE = os.getenv("API_BASE", "http://localhost:8000")  # Default for local dev

st.set_page_config(
    page_title="LunarInsight | 月悟",
    page_icon="🌙",
    layout="wide"
)

st.title("🌙 LunarInsight | 月悟")
st.markdown("> A quiet knowledge graph engine for insight.")


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
    """Visualize graph using pyvis."""
    net = Network(height="600px", width="100%", bgcolor="#222222", font_color="white")
    net.barnes_hut()
    
    # Add nodes
    for node in nodes:
        node_id = node.get("id", "")
        labels = node.get("labels", [])
        props = node.get("properties", {})
        label = props.get("name") or props.get("filename") or node_id
        
        # Color by label
        color = "#97c2fc"  # Default blue
        if "Concept" in labels:
            color = "#ff6b6b"  # Red for concepts
        elif "Document" in labels:
            color = "#4ecdc4"  # Teal for documents
        
        net.add_node(
            node_id,
            label=label[:30],  # Truncate long labels
            color=color,
            title=json.dumps(props, indent=2)
        )
    
    # Add edges
    for edge in edges:
        net.add_edge(
            edge.get("source"),
            edge.get("target"),
            label=edge.get("type", ""),
            title=json.dumps(edge.get("properties", {}), indent=2)
        )
    
    # Generate HTML
    net.set_options("""
    {
      "physics": {
        "enabled": true,
        "stabilization": {"iterations": 100}
      }
    }
    """)
    
    return net.generate_html()


# Sidebar
st.sidebar.header("Navigation")
page = st.sidebar.selectbox(
    "Choose a page",
    ["Upload", "Graph Visualization", "Query", "Status"]
)

# Main content
if page == "Upload":
    st.header("📤 Upload Document")
    
    uploaded_file = st.file_uploader(
        "Choose a file",
        type=["pdf", "md", "markdown"],
        help="Supported formats: PDF, Markdown"
    )
    
    if uploaded_file is not None:
        st.info(f"File: {uploaded_file.name} ({uploaded_file.size} bytes)")
        
        if st.button("Upload & Process"):
            with st.spinner("Uploading file..."):
                try:
                    result = upload_file(uploaded_file)
                    st.success("File uploaded successfully!")
                    st.json(result)
                    
                    doc_id = result.get("documentId")
                    if doc_id:
                        st.info(f"Document ID: {doc_id}")
                        
                        # Trigger ingestion
                        if st.button("Start Ingestion"):
                            with st.spinner("Starting ingestion..."):
                                ingest_result = make_request(
                                    "POST",
                                    f"/ingest/{doc_id}"
                                )
                                if ingest_result:
                                    st.success("Ingestion started!")
                                    st.json(ingest_result)
                                    st.session_state["job_id"] = ingest_result.get("jobId")
                                    st.session_state["doc_id"] = doc_id
                except Exception as e:
                    st.error(f"Error: {e}")

elif page == "Graph Visualization":
    st.header("🕸️ Knowledge Graph Visualization")
    
    # Query graph
    if st.button("Load Graph"):
        with st.spinner("Loading graph..."):
            result = make_request("GET", "/graph/query?limit=100")
            
            if result and "nodes" in result:
                nodes = result.get("nodes", [])
                edges = result.get("edges", [])
                
                st.success(f"Loaded {len(nodes)} nodes and {len(edges)} relationships")
                
                # Display stats
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Nodes", len(nodes))
                with col2:
                    st.metric("Edges", len(edges))
                with col3:
                    concepts = [n for n in nodes if "Concept" in n.get("labels", [])]
                    st.metric("Concepts", len(concepts))
                
                # Visualize
                if nodes:
                    html = visualize_graph(nodes, edges)
                    st.components.v1.html(html, height=600)
                else:
                    st.info("No nodes found in the graph.")
            else:
                st.warning("No data returned from API.")

elif page == "Query":
    st.header("🔍 Graph Query")
    
    query_type = st.selectbox(
        "Query Type",
        ["Cypher Query", "Get Nodes", "Get Edges"]
    )
    
    if query_type == "Cypher Query":
        cypher = st.text_area(
            "Cypher Query",
            value="MATCH (n) RETURN n LIMIT 10",
            height=100
        )
        
        if st.button("Execute"):
            with st.spinner("Executing query..."):
                import urllib.parse
                encoded_cypher = urllib.parse.quote(cypher)
                result = make_request("GET", f"/graph/query?cypher={encoded_cypher}&limit=100")
                if result:
                    st.json(result)
    
    elif query_type == "Get Nodes":
        label = st.text_input("Label (optional)", "")
        limit = st.number_input("Limit", min_value=1, max_value=1000, value=100)
        
        if st.button("Get Nodes"):
            with st.spinner("Fetching nodes..."):
                endpoint = f"/graph/nodes?limit={limit}"
                if label:
                    endpoint += f"&label={label}"
                result = make_request("GET", endpoint)
                if result:
                    st.json(result)
                    
                    # Display as table
                    if result:
                        df = pd.DataFrame([
                            {
                                "ID": n.get("id"),
                                "Labels": ", ".join(n.get("labels", [])),
                                "Properties": json.dumps(n.get("properties", {}))
                            }
                            for n in result
                        ])
                        st.dataframe(df)
    
    elif query_type == "Get Edges":
        rel_type = st.text_input("Relationship Type (optional)", "")
        limit = st.number_input("Limit", min_value=1, max_value=1000, value=100)
        
        if st.button("Get Edges"):
            with st.spinner("Fetching edges..."):
                endpoint = f"/graph/edges?limit={limit}"
                if rel_type:
                    endpoint += f"&rel_type={rel_type}"
                result = make_request("GET", endpoint)
                if result:
                    st.json(result)
                    
                    # Display as table
                    if result:
                        df = pd.DataFrame([
                            {
                                "Source": e.get("source"),
                                "Type": e.get("type"),
                                "Target": e.get("target"),
                                "Properties": json.dumps(e.get("properties", {}))
                            }
                            for e in result
                        ])
                        st.dataframe(df)

elif page == "Status":
    st.header("📊 Ingestion Status")
    
    job_id = st.text_input("Job ID", value=st.session_state.get("job_id", ""))
    
    if job_id and st.button("Check Status"):
        with st.spinner("Checking status..."):
            result = make_request("GET", f"/ingest/status/{job_id}")
            if result:
                status = result.get("status", "unknown")
                progress = result.get("progress", 0)
                message = result.get("message", "")
                
                st.metric("Status", status)
                st.progress(progress / 100)
                st.info(message)
                
                if "stats" in result:
                    st.subheader("Statistics")
                    st.json(result["stats"])
                
                st.json(result)

