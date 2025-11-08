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
                if hasattr(node, "id"):
                    node_id = node.get("id") or node.get("name") or str(node.id)
                    labels = list(node.labels) if hasattr(node, "labels") else []
                    props = dict(node)
                else:
                    node_id = node.get("id") or node.get("name") or str(hash(str(node)))
                    labels = node.get("labels", [])
                    props = node if isinstance(node, dict) else {}
                
                if node_id not in nodes_dict:
                    nodes_dict[node_id] = Node(
                        id=str(node_id),
                        labels=labels,
                        properties=props
                    )
            
            if "m" in record and record["m"]:
                node = record["m"]
                if hasattr(node, "id"):
                    node_id = node.get("id") or node.get("name") or str(node.id)
                    labels = list(node.labels) if hasattr(node, "labels") else []
                    props = dict(node)
                else:
                    node_id = node.get("id") or node.get("name") or str(hash(str(node)))
                    labels = node.get("labels", [])
                    props = node if isinstance(node, dict) else {}
                
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
                    # Get source ID
                    if hasattr(source_node, "id"):
                        source_id = source_node.get("id") or source_node.get("name") or str(source_node.id)
                    else:
                        source_id = source_node.get("id") or source_node.get("name") or str(hash(str(source_node)))
                    
                    # Get target ID
                    if hasattr(target_node, "id"):
                        target_id = target_node.get("id") or target_node.get("name") or str(target_node.id)
                    else:
                        target_id = target_node.get("id") or target_node.get("name") or str(hash(str(target_node)))
                    
                    if source_id and target_id:
                        rel_type = rel.type if hasattr(rel, "type") else str(rel)
                        rel_props = dict(rel) if hasattr(rel, "__dict__") else {}
                        
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
        if hasattr(node, "id"):
            node_id = node.get("id") or node.get("name") or str(node.id)
            labels = list(node.labels) if hasattr(node, "labels") else []
            props = dict(node)
        else:
            node_id = node.get("id") or node.get("name") or str(hash(str(node)))
            labels = node.get("labels", [])
            props = node if isinstance(node, dict) else {}
        
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
        
        if hasattr(source_node, "id"):
            source_id = source_node.get("id") or source_node.get("name") or str(source_node.id)
        else:
            source_id = source_node.get("id") or source_node.get("name") or str(hash(str(source_node)))
        
        if hasattr(target_node, "id"):
            target_id = target_node.get("id") or target_node.get("name") or str(target_node.id)
        else:
            target_id = target_node.get("id") or target_node.get("name") or str(hash(str(target_node)))
        
        if source_id and target_id:
            rel_type_str = rel.type if hasattr(rel, "type") else str(rel)
            rel_props = dict(rel) if hasattr(rel, "__dict__") else {}
            
            edges.append(Edge(
                source=str(source_id),
                target=str(target_id),
                type=rel_type_str,
                properties=rel_props
            ))
    
    return edges


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
