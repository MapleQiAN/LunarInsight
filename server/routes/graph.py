"""Graph query routes."""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List, Dict, Any
from infra.neo4j_client import neo4j_client
from models.graph import GraphQuery, GraphResponse, Node, Edge

router = APIRouter(prefix="/graph", tags=["graph"])


@router.get("/query", response_model=GraphResponse)
async def query_graph(
    cypher: Optional[str] = Query(None, description="Cypher query"),
    limit: int = Query(100, ge=1, le=1000)
):
    """
    Query the graph using Cypher.
    
    Example queries:
    - MATCH (n) RETURN n LIMIT 10
    - MATCH (c:Concept) RETURN c LIMIT 20
    - MATCH (d:Document)-[:MENTIONS]->(c:Concept) RETURN d, c LIMIT 10
    """
    if not cypher:
        # Default: get all nodes and relationships
        cypher = f"""
        MATCH (n)
        OPTIONAL MATCH (n)-[r]->(m)
        RETURN n, r, m
        LIMIT {limit}
        """
    
    try:
        results = neo4j_client.execute_query(cypher)
        
        nodes_dict = {}
        edges = []
        
        for record in results:
            # Extract nodes
            if "n" in record and record["n"]:
                node = record["n"]
                # Neo4j Node object: use dict(node) to get properties
                props = dict(node) if hasattr(node, "__getitem__") else {}
                labels = list(node.labels) if hasattr(node, "labels") else []
                
                # Get business ID from properties (id field in Document/Concept)
                # Fallback to name, or use Neo4j internal element_id
                node_id = props.get("id") or props.get("name")
                if not node_id:
                    # Use Neo4j internal ID as fallback
                    node_id = getattr(node, "element_id", None) or str(getattr(node, "id", hash(str(node))))
                
                if node_id not in nodes_dict:
                    nodes_dict[node_id] = Node(
                        id=str(node_id),
                        labels=labels,
                        properties=props
                    )
            
            if "m" in record and record["m"]:
                node = record["m"]
                props = dict(node) if hasattr(node, "__getitem__") else {}
                labels = list(node.labels) if hasattr(node, "labels") else []
                
                node_id = props.get("id") or props.get("name")
                if not node_id:
                    node_id = getattr(node, "element_id", None) or str(getattr(node, "id", hash(str(node))))
                
                if node_id not in nodes_dict:
                    nodes_dict[node_id] = Node(
                        id=str(node_id),
                        labels=labels,
                        properties=props
                    )
            
            # Extract relationships
            if "r" in record and record["r"]:
                rel = record["r"]
                source_node = record.get("n")
                target_node = record.get("m")
                
                if source_node and target_node:
                    # Get source ID (from properties first, fallback to element_id)
                    source_props = dict(source_node) if hasattr(source_node, "__getitem__") else {}
                    source_id = source_props.get("id") or source_props.get("name")
                    if not source_id:
                        source_id = getattr(source_node, "element_id", None) or str(getattr(source_node, "id", hash(str(source_node))))
                    
                    # Get target ID
                    target_props = dict(target_node) if hasattr(target_node, "__getitem__") else {}
                    target_id = target_props.get("id") or target_props.get("name")
                    if not target_id:
                        target_id = getattr(target_node, "element_id", None) or str(getattr(target_node, "id", hash(str(target_node))))
                    
                    if source_id and target_id:
                        rel_type = rel.type if hasattr(rel, "type") else str(rel)
                        rel_props = dict(rel) if hasattr(rel, "__getitem__") else {}
                        
                        edges.append(Edge(
                            source=str(source_id),
                            target=str(target_id),
                            type=rel_type,
                            properties=rel_props
                        ))
        
        return GraphResponse(
            nodes=list(nodes_dict.values()),
            edges=edges,
            stats={"count": len(results)}
        )
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Query error: {str(e)}")


@router.get("/nodes", response_model=List[Node])
async def get_nodes(
    label: Optional[str] = Query(None, description="Filter by label"),
    limit: int = Query(100, ge=1, le=1000)
):
    """Get all nodes, optionally filtered by label."""
    if label:
        query = f"MATCH (n:{label}) RETURN n LIMIT $limit"
    else:
        query = "MATCH (n) RETURN n LIMIT $limit"
    
    results = neo4j_client.execute_query(query, {"limit": limit})
    
    nodes = []
    for record in results:
        node = record["n"]
        props = dict(node) if hasattr(node, "__getitem__") else {}
        labels = list(node.labels) if hasattr(node, "labels") else []
        
        node_id = props.get("id") or props.get("name")
        if not node_id:
            node_id = getattr(node, "element_id", None) or str(getattr(node, "id", hash(str(node))))
        
        nodes.append(Node(
            id=str(node_id),
            labels=labels,
            properties=props
        ))
    
    return nodes


@router.get("/edges", response_model=List[Edge])
async def get_edges(
    rel_type: Optional[str] = Query(None, description="Filter by relationship type"),
    limit: int = Query(100, ge=1, le=1000)
):
    """Get all relationships, optionally filtered by type."""
    if rel_type:
        query = f"MATCH (a)-[r:{rel_type}]->(b) RETURN a, r, b LIMIT $limit"
    else:
        query = "MATCH (a)-[r]->(b) RETURN a, r, b LIMIT $limit"
    
    results = neo4j_client.execute_query(query, {"limit": limit})
    
    edges = []
    for record in results:
        source_node = record["a"]
        target_node = record["b"]
        rel = record["r"]
        
        # Get source ID
        source_props = dict(source_node) if hasattr(source_node, "__getitem__") else {}
        source_id = source_props.get("id") or source_props.get("name")
        if not source_id:
            source_id = getattr(source_node, "element_id", None) or str(getattr(source_node, "id", hash(str(source_node))))
        
        # Get target ID
        target_props = dict(target_node) if hasattr(target_node, "__getitem__") else {}
        target_id = target_props.get("id") or target_props.get("name")
        if not target_id:
            target_id = getattr(target_node, "element_id", None) or str(getattr(target_node, "id", hash(str(target_node))))
        
        if source_id and target_id:
            rel_type_str = rel.type if hasattr(rel, "type") else str(rel)
            rel_props = dict(rel) if hasattr(rel, "__getitem__") else {}
            
            edges.append(Edge(
                source=str(source_id),
                target=str(target_id),
                type=rel_type_str,
                properties=rel_props
            ))
    
    return edges


@router.get("/documents/{document_id}/graph", response_model=GraphResponse)
async def get_document_graph(
    document_id: str,
    depth: int = Query(2, ge=1, le=5, description="Relationship depth")
):
    """
    获取指定文档的知识图谱。
    
    Args:
        document_id: 文档 ID
        depth: 关系深度（1-5）
        
    Returns:
        包含节点和边的图谱数据
    """
    # Check if document exists
    doc_check = neo4j_client.execute_query(
        "MATCH (d:Document {id: $doc_id}) RETURN d",
        {"doc_id": document_id}
    )
    
    if not doc_check:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Query for document and related concepts with specified depth
    query = f"""
    MATCH (d:Document {{id: $doc_id}})
    MATCH path = (d)-[*1..{depth}]-(n)
    WITH d, n, relationships(path) as rels
    RETURN d, n, rels
    LIMIT 1000
    """
    
    results = neo4j_client.execute_query(query, {"doc_id": document_id})
    
    nodes_dict = {}
    edges = []
    
    for record in results:
        # Add document node
        if "d" in record and record["d"]:
            doc_node = record["d"]
            doc_props = dict(doc_node) if hasattr(doc_node, "__getitem__") else {}
            doc_labels = list(doc_node.labels) if hasattr(doc_node, "labels") else ["Document"]
            
            doc_id_val = doc_props.get("id")
            if not doc_id_val:
                doc_id_val = getattr(doc_node, "element_id", None) or str(getattr(doc_node, "id", hash(str(doc_node))))
            
            if doc_id_val not in nodes_dict:
                nodes_dict[doc_id_val] = Node(
                    id=str(doc_id_val),
                    labels=doc_labels,
                    properties=doc_props
                )
        
        # Add related node
        if "n" in record and record["n"]:
            node = record["n"]
            props = dict(node) if hasattr(node, "__getitem__") else {}
            labels = list(node.labels) if hasattr(node, "labels") else ["Concept"]
            
            node_id = props.get("id") or props.get("name")
            if not node_id:
                node_id = getattr(node, "element_id", None) or str(getattr(node, "id", hash(str(node))))
            
            if node_id not in nodes_dict:
                nodes_dict[node_id] = Node(
                    id=str(node_id),
                    labels=labels,
                    properties=props
                )
        
        # Add relationships
        if "rels" in record and record["rels"]:
            for rel in record["rels"]:
                if hasattr(rel, "start_node") and hasattr(rel, "end_node"):
                    # Get source ID
                    start_props = dict(rel.start_node) if hasattr(rel.start_node, "__getitem__") else {}
                    source_id = start_props.get("id") or start_props.get("name")
                    if not source_id:
                        source_id = getattr(rel.start_node, "element_id", None) or str(getattr(rel.start_node, "id", hash(str(rel.start_node))))
                    
                    # Get target ID
                    end_props = dict(rel.end_node) if hasattr(rel.end_node, "__getitem__") else {}
                    target_id = end_props.get("id") or end_props.get("name")
                    if not target_id:
                        target_id = getattr(rel.end_node, "element_id", None) or str(getattr(rel.end_node, "id", hash(str(rel.end_node))))
                    
                    rel_type = rel.type if hasattr(rel, "type") else "RELATES_TO"
                    rel_props = dict(rel) if hasattr(rel, "__getitem__") else {}
                    
                    edges.append(Edge(
                        source=str(source_id),
                        target=str(target_id),
                        type=rel_type,
                        properties=rel_props
                    ))
    
    return GraphResponse(
        nodes=list(nodes_dict.values()),
        edges=edges,
        stats={"count": len(nodes_dict), "edges": len(edges)}
    )


@router.get("/concepts/{concept_name}/graph", response_model=GraphResponse)
async def get_concept_graph(
    concept_name: str,
    depth: int = Query(2, ge=1, le=5, description="Relationship depth")
):
    """
    获取指定概念的知识图谱。
    
    Args:
        concept_name: 概念名称
        depth: 关系深度（1-5）
        
    Returns:
        包含节点和边的图谱数据
    """
    # Check if concept exists
    concept_check = neo4j_client.execute_query(
        "MATCH (c:Concept {name: $name}) RETURN c",
        {"name": concept_name}
    )
    
    if not concept_check:
        raise HTTPException(status_code=404, detail="Concept not found")
    
    # Query for concept and related nodes
    query = f"""
    MATCH (c:Concept {{name: $name}})
    MATCH path = (c)-[*1..{depth}]-(n)
    WITH c, n, relationships(path) as rels
    RETURN c, n, rels
    LIMIT 1000
    """
    
    results = neo4j_client.execute_query(query, {"name": concept_name})
    
    nodes_dict = {}
    edges = []
    
    for record in results:
        # Add central concept node
        if "c" in record and record["c"]:
            concept_node = record["c"]
            concept_props = dict(concept_node) if hasattr(concept_node, "__getitem__") else {}
            concept_labels = list(concept_node.labels) if hasattr(concept_node, "labels") else ["Concept"]
            
            concept_id = concept_props.get("name") or concept_props.get("id")
            if not concept_id:
                concept_id = getattr(concept_node, "element_id", None) or str(getattr(concept_node, "id", hash(str(concept_node))))
            
            if concept_id not in nodes_dict:
                nodes_dict[concept_id] = Node(
                    id=str(concept_id),
                    labels=concept_labels,
                    properties=concept_props
                )
        
        # Add related node
        if "n" in record and record["n"]:
            node = record["n"]
            props = dict(node) if hasattr(node, "__getitem__") else {}
            labels = list(node.labels) if hasattr(node, "labels") else []
            
            node_id = props.get("id") or props.get("name")
            if not node_id:
                node_id = getattr(node, "element_id", None) or str(getattr(node, "id", hash(str(node))))
            
            if node_id not in nodes_dict:
                nodes_dict[node_id] = Node(
                    id=str(node_id),
                    labels=labels,
                    properties=props
                )
        
        # Add relationships
        if "rels" in record and record["rels"]:
            for rel in record["rels"]:
                if hasattr(rel, "start_node") and hasattr(rel, "end_node"):
                    # Get source ID
                    start_props = dict(rel.start_node) if hasattr(rel.start_node, "__getitem__") else {}
                    source_id = start_props.get("id") or start_props.get("name")
                    if not source_id:
                        source_id = getattr(rel.start_node, "element_id", None) or str(getattr(rel.start_node, "id", hash(str(rel.start_node))))
                    
                    # Get target ID
                    end_props = dict(rel.end_node) if hasattr(rel.end_node, "__getitem__") else {}
                    target_id = end_props.get("id") or end_props.get("name")
                    if not target_id:
                        target_id = getattr(rel.end_node, "element_id", None) or str(getattr(rel.end_node, "id", hash(str(rel.end_node))))
                    
                    rel_type = rel.type if hasattr(rel, "type") else "RELATES_TO"
                    rel_props = dict(rel) if hasattr(rel, "__getitem__") else {}
                    
                    edges.append(Edge(
                        source=str(source_id),
                        target=str(target_id),
                        type=rel_type,
                        properties=rel_props
                    ))
    
    return GraphResponse(
        nodes=list(nodes_dict.values()),
        edges=edges,
        stats={"count": len(nodes_dict), "edges": len(edges)}
    )


@router.get("/stats")
async def get_graph_stats():
    """Get knowledge graph statistics."""
    try:
        # Get total counts
        stats_query = """
        MATCH (d:Document)
        WITH count(d) as totalDocs
        MATCH (c:Concept)
        WITH totalDocs, count(c) as totalConcepts
        MATCH ()-[r]->()
        RETURN 
            totalDocs,
            totalConcepts,
            count(r) as totalRelations
        """
        stats_result = neo4j_client.execute_query(stats_query)
        
        if not stats_result:
            return {
                "totalDocuments": 0,
                "totalConcepts": 0,
                "totalRelations": 0,
                "recentDocuments": [],
                "topConcepts": [],
                "relationTypes": []
            }
        
        stats = stats_result[0]
        
        # Get recent documents
        recent_docs_query = """
        MATCH (d:Document)
        RETURN d.id as id, d.filename as filename, d.created_at as createdAt, d.kind as kind
        ORDER BY d.created_at DESC
        LIMIT 5
        """
        recent_docs = neo4j_client.execute_query(recent_docs_query)
        
        # Get top concepts by connection count
        top_concepts_query = """
        MATCH (c:Concept)
        OPTIONAL MATCH (c)-[r]-()
        WITH c, count(r) as connections
        RETURN c.name as name, c.domain as domain, connections
        ORDER BY connections DESC
        LIMIT 10
        """
        top_concepts = neo4j_client.execute_query(top_concepts_query)
        
        # Get relation type distribution
        relation_types_query = """
        MATCH ()-[r]->()
        RETURN type(r) as type, count(r) as count
        ORDER BY count DESC
        """
        relation_types = neo4j_client.execute_query(relation_types_query)
        
        return {
            "totalDocuments": stats.get("totalDocs", 0),
            "totalConcepts": stats.get("totalConcepts", 0),
            "totalRelations": stats.get("totalRelations", 0),
            "recentDocuments": [
                {
                    "id": doc.get("id"),
                    "filename": doc.get("filename"),
                    "createdAt": doc.get("createdAt"),
                    "kind": doc.get("kind")
                }
                for doc in recent_docs
            ],
            "topConcepts": [
                {
                    "name": concept.get("name"),
                    "domain": concept.get("domain"),
                    "connections": concept.get("connections", 0)
                }
                for concept in top_concepts
            ],
            "relationTypes": [
                {
                    "type": rt.get("type"),
                    "count": rt.get("count", 0)
                }
                for rt in relation_types
            ]
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")
