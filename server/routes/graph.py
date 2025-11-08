"""Graph query routes."""
from fastapi import APIRouter, HTTPException, Query, Body
from typing import Optional, List, Dict, Any
from infra.neo4j_client import neo4j_client
from models.graph import GraphQuery, GraphResponse, Node, Edge, NodeCreate, NodeUpdate, EdgeCreate, EdgeUpdate

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


# ========== Node CRUD Operations ==========

@router.post("/nodes", response_model=Node, status_code=201)
async def create_node(node_data: NodeCreate = Body(...)):
    """
    创建新节点。
    
    Args:
        node_data: 节点数据（标签和属性）
        
    Returns:
        创建的节点
    """
    try:
        import uuid
        from datetime import datetime
        
        # Generate unique ID if not provided
        if "id" not in node_data.properties:
            node_data.properties["id"] = str(uuid.uuid4())
        
        # Add creation timestamp
        if "created_at" not in node_data.properties:
            node_data.properties["created_at"] = datetime.now().isoformat()
        
        # Build labels string
        labels_str = ":".join(node_data.labels)
        
        # Build properties
        props_dict = node_data.properties
        
        # Create node
        query = f"""
        CREATE (n:{labels_str})
        SET n = $props
        RETURN n
        """
        
        results = neo4j_client.execute_query(query, {"props": props_dict})
        
        if not results:
            raise HTTPException(status_code=500, detail="Failed to create node")
        
        node = results[0]["n"]
        props = dict(node) if hasattr(node, "__getitem__") else {}
        labels = list(node.labels) if hasattr(node, "labels") else []
        
        return Node(
            id=str(props.get("id")),
            labels=labels,
            properties=props
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create node: {str(e)}")


@router.get("/nodes/{node_id}", response_model=Node)
async def get_node(node_id: str):
    """
    获取指定节点。
    
    Args:
        node_id: 节点 ID
        
    Returns:
        节点数据
    """
    try:
        # Try to find by id property first, then by name
        query = """
        MATCH (n)
        WHERE n.id = $node_id OR n.name = $node_id
        RETURN n
        LIMIT 1
        """
        
        results = neo4j_client.execute_query(query, {"node_id": node_id})
        
        if not results:
            raise HTTPException(status_code=404, detail="Node not found")
        
        node = results[0]["n"]
        props = dict(node) if hasattr(node, "__getitem__") else {}
        labels = list(node.labels) if hasattr(node, "labels") else []
        
        return Node(
            id=str(props.get("id") or props.get("name") or node_id),
            labels=labels,
            properties=props
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get node: {str(e)}")


@router.put("/nodes/{node_id}", response_model=Node)
async def update_node(node_id: str, node_data: NodeUpdate = Body(...)):
    """
    更新节点。
    
    Args:
        node_id: 节点 ID
        node_data: 更新数据
        
    Returns:
        更新后的节点
    """
    try:
        from datetime import datetime
        
        # Check if node exists
        check_query = """
        MATCH (n)
        WHERE n.id = $node_id OR n.name = $node_id
        RETURN n
        LIMIT 1
        """
        check_results = neo4j_client.execute_query(check_query, {"node_id": node_id})
        
        if not check_results:
            raise HTTPException(status_code=404, detail="Node not found")
        
        # Build update query
        updates = []
        params = {"node_id": node_id}
        
        # Update labels if provided
        if node_data.labels:
            labels_str = ":".join(node_data.labels)
            # Remove old labels and set new ones
            query_parts = [
                f"""
                MATCH (n)
                WHERE n.id = $node_id OR n.name = $node_id
                REMOVE n:{":".join(list(check_results[0]["n"].labels))}
                SET n:{labels_str}
                """
            ]
        else:
            query_parts = [
                """
                MATCH (n)
                WHERE n.id = $node_id OR n.name = $node_id
                """
            ]
        
        # Update properties
        if node_data.properties:
            node_data.properties["updated_at"] = datetime.now().isoformat()
            params["props"] = node_data.properties
            query_parts.append("SET n += $props")
        
        # Remove properties
        if node_data.remove_properties:
            for prop in node_data.remove_properties:
                query_parts.append(f"REMOVE n.{prop}")
        
        query_parts.append("RETURN n")
        query = "\n".join(query_parts)
        
        results = neo4j_client.execute_query(query, params)
        
        if not results:
            raise HTTPException(status_code=500, detail="Failed to update node")
        
        node = results[0]["n"]
        props = dict(node) if hasattr(node, "__getitem__") else {}
        labels = list(node.labels) if hasattr(node, "labels") else []
        
        return Node(
            id=str(props.get("id") or props.get("name") or node_id),
            labels=labels,
            properties=props
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update node: {str(e)}")


@router.delete("/nodes/{node_id}", status_code=204)
async def delete_node(node_id: str, force: bool = Query(False, description="Force delete with relationships")):
    """
    删除节点。
    
    Args:
        node_id: 节点 ID
        force: 是否强制删除（包括关系）
        
    Returns:
        无内容
    """
    try:
        # Check if node exists
        check_query = """
        MATCH (n)
        WHERE n.id = $node_id OR n.name = $node_id
        RETURN n
        LIMIT 1
        """
        check_results = neo4j_client.execute_query(check_query, {"node_id": node_id})
        
        if not check_results:
            raise HTTPException(status_code=404, detail="Node not found")
        
        # Check for relationships if not force delete
        if not force:
            rel_check_query = """
            MATCH (n)-[r]-()
            WHERE n.id = $node_id OR n.name = $node_id
            RETURN count(r) as rel_count
            """
            rel_results = neo4j_client.execute_query(rel_check_query, {"node_id": node_id})
            
            if rel_results and rel_results[0].get("rel_count", 0) > 0:
                raise HTTPException(
                    status_code=400,
                    detail="Node has relationships. Use force=true to delete with relationships."
                )
        
        # Delete node (and relationships if force)
        if force:
            delete_query = """
            MATCH (n)
            WHERE n.id = $node_id OR n.name = $node_id
            DETACH DELETE n
            """
        else:
            delete_query = """
            MATCH (n)
            WHERE n.id = $node_id OR n.name = $node_id
            DELETE n
            """
        
        neo4j_client.execute_query(delete_query, {"node_id": node_id})
        
        return None
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete node: {str(e)}")


# ========== Edge (Relationship) CRUD Operations ==========

@router.post("/edges", response_model=Edge, status_code=201)
async def create_edge(edge_data: EdgeCreate = Body(...)):
    """
    创建新关系。
    
    Args:
        edge_data: 关系数据
        
    Returns:
        创建的关系
    """
    try:
        from datetime import datetime
        
        # Check if source and target nodes exist
        check_query = """
        MATCH (s)
        WHERE s.id = $source_id OR s.name = $source_id
        MATCH (t)
        WHERE t.id = $target_id OR t.name = $target_id
        RETURN s, t
        """
        check_results = neo4j_client.execute_query(check_query, {
            "source_id": edge_data.source,
            "target_id": edge_data.target
        })
        
        if not check_results:
            raise HTTPException(status_code=404, detail="Source or target node not found")
        
        # Add creation timestamp
        props = edge_data.properties.copy()
        if "created_at" not in props:
            props["created_at"] = datetime.now().isoformat()
        
        # Create relationship
        query = f"""
        MATCH (s)
        WHERE s.id = $source_id OR s.name = $source_id
        MATCH (t)
        WHERE t.id = $target_id OR t.name = $target_id
        CREATE (s)-[r:{edge_data.type}]->(t)
        SET r = $props
        RETURN s, r, t
        """
        
        results = neo4j_client.execute_query(query, {
            "source_id": edge_data.source,
            "target_id": edge_data.target,
            "props": props
        })
        
        if not results:
            raise HTTPException(status_code=500, detail="Failed to create relationship")
        
        rel = results[0]["r"]
        source_node = results[0]["s"]
        target_node = results[0]["t"]
        
        # Get IDs
        source_props = dict(source_node) if hasattr(source_node, "__getitem__") else {}
        source_id = source_props.get("id") or source_props.get("name") or edge_data.source
        
        target_props = dict(target_node) if hasattr(target_node, "__getitem__") else {}
        target_id = target_props.get("id") or target_props.get("name") or edge_data.target
        
        rel_type = rel.type if hasattr(rel, "type") else edge_data.type
        rel_props = dict(rel) if hasattr(rel, "__getitem__") else {}
        
        # Generate edge ID
        edge_id = f"{source_id}-{rel_type}-{target_id}"
        
        return Edge(
            id=edge_id,
            source=str(source_id),
            target=str(target_id),
            type=rel_type,
            properties=rel_props
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create relationship: {str(e)}")


@router.put("/edges/{source_id}/{target_id}/{rel_type}", response_model=Edge)
async def update_edge(
    source_id: str,
    target_id: str,
    rel_type: str,
    edge_data: EdgeUpdate = Body(...)
):
    """
    更新关系。
    
    Args:
        source_id: 源节点 ID
        target_id: 目标节点 ID
        rel_type: 关系类型
        edge_data: 更新数据
        
    Returns:
        更新后的关系
    """
    try:
        from datetime import datetime
        
        # Check if relationship exists
        check_query = f"""
        MATCH (s)-[r:{rel_type}]->(t)
        WHERE (s.id = $source_id OR s.name = $source_id)
          AND (t.id = $target_id OR t.name = $target_id)
        RETURN r
        LIMIT 1
        """
        check_results = neo4j_client.execute_query(check_query, {
            "source_id": source_id,
            "target_id": target_id
        })
        
        if not check_results:
            raise HTTPException(status_code=404, detail="Relationship not found")
        
        # Update properties
        updates = []
        params = {
            "source_id": source_id,
            "target_id": target_id
        }
        
        if edge_data.properties:
            edge_data.properties["updated_at"] = datetime.now().isoformat()
            params["props"] = edge_data.properties
            updates.append("SET r += $props")
        
        # Remove properties
        if edge_data.remove_properties:
            for prop in edge_data.remove_properties:
                updates.append(f"REMOVE r.{prop}")
        
        # Handle type change (requires recreating the relationship)
        if edge_data.type and edge_data.type != rel_type:
            query = f"""
            MATCH (s)-[r:{rel_type}]->(t)
            WHERE (s.id = $source_id OR s.name = $source_id)
              AND (t.id = $target_id OR t.name = $target_id)
            WITH s, t, properties(r) as props
            DELETE r
            CREATE (s)-[new_r:{edge_data.type}]->(t)
            SET new_r = props
            {" ".join(updates).replace("r.", "new_r.").replace("r +=", "new_r +=")}
            RETURN s, new_r as r, t
            """
        else:
            query = f"""
            MATCH (s)-[r:{rel_type}]->(t)
            WHERE (s.id = $source_id OR s.name = $source_id)
              AND (t.id = $target_id OR t.name = $target_id)
            {" ".join(updates)}
            RETURN s, r, t
            """
        
        results = neo4j_client.execute_query(query, params)
        
        if not results:
            raise HTTPException(status_code=500, detail="Failed to update relationship")
        
        rel = results[0]["r"]
        source_node = results[0]["s"]
        target_node = results[0]["t"]
        
        # Get IDs
        source_props = dict(source_node) if hasattr(source_node, "__getitem__") else {}
        actual_source_id = source_props.get("id") or source_props.get("name") or source_id
        
        target_props = dict(target_node) if hasattr(target_node, "__getitem__") else {}
        actual_target_id = target_props.get("id") or target_props.get("name") or target_id
        
        rel_type_actual = rel.type if hasattr(rel, "type") else (edge_data.type or rel_type)
        rel_props = dict(rel) if hasattr(rel, "__getitem__") else {}
        
        edge_id = f"{actual_source_id}-{rel_type_actual}-{actual_target_id}"
        
        return Edge(
            id=edge_id,
            source=str(actual_source_id),
            target=str(actual_target_id),
            type=rel_type_actual,
            properties=rel_props
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update relationship: {str(e)}")


@router.delete("/edges/{source_id}/{target_id}/{rel_type}", status_code=204)
async def delete_edge(source_id: str, target_id: str, rel_type: str):
    """
    删除关系。
    
    Args:
        source_id: 源节点 ID
        target_id: 目标节点 ID
        rel_type: 关系类型
        
    Returns:
        无内容
    """
    try:
        # Check if relationship exists
        check_query = f"""
        MATCH (s)-[r:{rel_type}]->(t)
        WHERE (s.id = $source_id OR s.name = $source_id)
          AND (t.id = $target_id OR t.name = $target_id)
        RETURN r
        LIMIT 1
        """
        check_results = neo4j_client.execute_query(check_query, {
            "source_id": source_id,
            "target_id": target_id
        })
        
        if not check_results:
            raise HTTPException(status_code=404, detail="Relationship not found")
        
        # Delete relationship
        delete_query = f"""
        MATCH (s)-[r:{rel_type}]->(t)
        WHERE (s.id = $source_id OR s.name = $source_id)
          AND (t.id = $target_id OR t.name = $target_id)
        DELETE r
        """
        
        neo4j_client.execute_query(delete_query, {
            "source_id": source_id,
            "target_id": target_id
        })
        
        return None
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete relationship: {str(e)}")
