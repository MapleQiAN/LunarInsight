"""Graph data models."""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


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
    properties: Dict[str, Any] = Field(default_factory=dict)


class GraphQuery(BaseModel):
    """Graph query request model."""
    cypher: Optional[str] = None
    limit: int = 100


class GraphResponse(BaseModel):
    """Graph query response model."""
    nodes: List[Node]
    edges: List[Edge]
    stats: Optional[Dict[str, Any]] = None


class NodeCreate(BaseModel):
    """Node creation request model."""
    labels: List[str] = Field(..., description="Node labels", min_length=1)
    properties: Dict[str, Any] = Field(default_factory=dict, description="Node properties")


class NodeUpdate(BaseModel):
    """Node update request model."""
    labels: Optional[List[str]] = Field(None, description="New labels (replaces existing)")
    properties: Dict[str, Any] = Field(..., description="Properties to update (merge with existing)")
    remove_properties: Optional[List[str]] = Field(None, description="Properties to remove")


class EdgeCreate(BaseModel):
    """Edge creation request model."""
    source: str = Field(..., description="Source node ID")
    target: str = Field(..., description="Target node ID")
    type: str = Field(..., description="Relationship type")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Relationship properties")


class EdgeUpdate(BaseModel):
    """Edge update request model."""
    type: Optional[str] = Field(None, description="New relationship type")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Properties to update")
    remove_properties: Optional[List[str]] = Field(None, description="Properties to remove")
