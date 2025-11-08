"""Knowledge card models."""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class KnowledgeCardCreate(BaseModel):
    """Knowledge card creation request."""
    name: str = Field(..., description="知识卡片名称")
    description: Optional[str] = Field(None, description="描述")
    domain: Optional[str] = Field(None, description="领域/分类")
    category: Optional[str] = Field(None, description="类别")
    importance: Optional[str] = Field("medium", description="重要性: low/medium/high")
    tags: List[str] = Field(default_factory=list, description="标签列表")
    aliases: List[str] = Field(default_factory=list, description="别名列表")
    related_concepts: List[str] = Field(default_factory=list, description="关联概念名称列表")
    attributes: Dict[str, Any] = Field(default_factory=dict, description="自定义属性")


class KnowledgeCardUpdate(BaseModel):
    """Knowledge card update request."""
    name: Optional[str] = None
    description: Optional[str] = None
    domain: Optional[str] = None
    category: Optional[str] = None
    importance: Optional[str] = None
    tags: Optional[List[str]] = None
    aliases: Optional[List[str]] = None
    related_concepts: Optional[List[str]] = None
    attributes: Optional[Dict[str, Any]] = None


class KnowledgeCardResponse(BaseModel):
    """Knowledge card response."""
    id: str
    name: str
    description: Optional[str] = None
    domain: Optional[str] = None
    category: Optional[str] = None
    importance: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    aliases: List[str] = Field(default_factory=list)
    related_concepts: List[str] = Field(default_factory=list)
    attributes: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    connection_count: int = 0


class KnowledgeCardListResponse(BaseModel):
    """Knowledge card list response."""
    cards: List[KnowledgeCardResponse]
    total: int

