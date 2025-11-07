"""Graph data models."""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel


class Node(BaseModel):
    """Graph node model."""
    id: str
    labels: List[str]
    properties: Dict[str, Any]


class Edge(BaseModel):
    """Graph edge model."""
    id: Optional[str] = None
    source: str
    target: str
    type: str
    properties: Dict[str, Any] = {}


class GraphQuery(BaseModel):
    """Graph query request model."""
    cypher: Optional[str] = None
    limit: int = 100


class GraphResponse(BaseModel):
    """Graph query response model."""
    nodes: List[Node]
    edges: List[Edge]
    stats: Optional[Dict[str, Any]] = None

