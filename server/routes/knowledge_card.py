"""Knowledge card routes."""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from infra.neo4j_client import neo4j_client
from models.knowledge_card import (
    KnowledgeCardCreate,
    KnowledgeCardUpdate,
    KnowledgeCardResponse,
    KnowledgeCardListResponse
)
from datetime import datetime

router = APIRouter(prefix="/knowledge-cards", tags=["knowledge-cards"])


@router.post("", response_model=KnowledgeCardResponse)
async def create_knowledge_card(card: KnowledgeCardCreate):
    """
    创建知识卡片并写入知识图谱。
    
    Args:
        card: 知识卡片创建请求
        
    Returns:
        创建的知识卡片信息
    """
    try:
        # 检查是否已存在同名概念
        existing = neo4j_client.execute_query(
            "MATCH (c:Concept {name: $name}) RETURN c",
            {"name": card.name}
        )
        
        if existing:
            raise HTTPException(status_code=400, detail=f"概念 '{card.name}' 已存在")
        
        # 创建概念节点
        now = datetime.utcnow().isoformat()
        properties = {
            "name": card.name,
            "description": card.description or "",
            "domain": card.domain or "",
            "category": card.category or "",
            "importance": card.importance or "medium",
            "tags": card.tags,
            "created_at": now,
            "updated_at": now,
            "source": "user_created"  # 标记为用户创建
        }
        
        # 合并自定义属性
        if card.attributes:
            properties.update(card.attributes)
        
        neo4j_client.execute_query(
            """
            CREATE (c:Concept)
            SET c = $properties
            RETURN c
            """,
            {"properties": properties}
        )
        
        # 处理别名
        for alias in card.aliases:
            neo4j_client.execute_query(
                """
                MATCH (c:Concept {name: $name})
                MERGE (a:Alias {name: $alias})
                MERGE (a)-[:REFERS_TO]->(c)
                """,
                {"name": card.name, "alias": alias}
            )
        
        # 处理关联概念
        for related_name in card.related_concepts:
            # 确保关联的概念存在
            neo4j_client.execute_query(
                """
                MERGE (c1:Concept {name: $name1})
                MERGE (c2:Concept {name: $name2})
                MERGE (c1)-[:RELATED_TO]->(c2)
                """,
                {"name1": card.name, "name2": related_name}
            )
        
        # 查询并返回创建的卡片
        result = neo4j_client.execute_query(
            """
            MATCH (c:Concept {name: $name})
            OPTIONAL MATCH (c)-[r]-()
            WITH c, count(r) as conn_count
            OPTIONAL MATCH (a:Alias)-[:REFERS_TO]->(c)
            WITH c, conn_count, collect(a.name) as aliases
            RETURN c, conn_count, aliases
            """,
            {"name": card.name}
        )
        
        if not result:
            raise HTTPException(status_code=500, detail="创建成功但无法查询到结果")
        
        record = result[0]
        concept = record["c"]
        
        return KnowledgeCardResponse(
            id=concept.get("name"),
            name=concept.get("name"),
            description=concept.get("description"),
            domain=concept.get("domain"),
            category=concept.get("category"),
            importance=concept.get("importance"),
            tags=concept.get("tags", []),
            aliases=record.get("aliases", []),
            related_concepts=card.related_concepts,
            attributes=card.attributes,
            created_at=concept.get("created_at"),
            updated_at=concept.get("updated_at"),
            connection_count=record.get("conn_count", 0)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建知识卡片失败: {str(e)}")


@router.get("", response_model=KnowledgeCardListResponse)
async def list_knowledge_cards(
    domain: Optional[str] = Query(None, description="按领域筛选"),
    category: Optional[str] = Query(None, description="按类别筛选"),
    limit: int = Query(100, ge=1, le=1000, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量")
):
    """
    获取知识卡片列表。
    
    Args:
        domain: 领域筛选（可选）
        category: 类别筛选（可选）
        limit: 返回数量限制
        offset: 偏移量
        
    Returns:
        知识卡片列表
    """
    try:
        # 构建查询条件
        where_clauses = []
        params = {"limit": limit, "offset": offset}
        
        if domain:
            where_clauses.append("c.domain = $domain")
            params["domain"] = domain
        
        if category:
            where_clauses.append("c.category = $category")
            params["category"] = category
        
        where_clause = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
        
        # 查询卡片
        query = f"""
        MATCH (c:Concept)
        {where_clause}
        OPTIONAL MATCH (c)-[r]-()
        WITH c, count(r) as conn_count
        OPTIONAL MATCH (a:Alias)-[:REFERS_TO]->(c)
        WITH c, conn_count, collect(a.name) as aliases
        OPTIONAL MATCH (c)-[:RELATED_TO]->(related:Concept)
        WITH c, conn_count, aliases, collect(related.name) as related_concepts
        RETURN c, conn_count, aliases, related_concepts
        ORDER BY c.updated_at DESC
        SKIP $offset
        LIMIT $limit
        """
        
        results = neo4j_client.execute_query(query, params)
        
        # 查询总数
        count_query = f"""
        MATCH (c:Concept)
        {where_clause}
        RETURN count(c) as total
        """
        count_result = neo4j_client.execute_query(count_query, params)
        total = count_result[0]["total"] if count_result else 0
        
        cards = []
        for record in results:
            concept = record["c"]
            cards.append(KnowledgeCardResponse(
                id=concept.get("name"),
                name=concept.get("name"),
                description=concept.get("description"),
                domain=concept.get("domain"),
                category=concept.get("category"),
                importance=concept.get("importance"),
                tags=concept.get("tags", []),
                aliases=record.get("aliases", []),
                related_concepts=record.get("related_concepts", []),
                attributes={},  # 自定义属性需要单独处理
                created_at=concept.get("created_at"),
                updated_at=concept.get("updated_at"),
                connection_count=record.get("conn_count", 0)
            ))
        
        return KnowledgeCardListResponse(cards=cards, total=total)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询知识卡片失败: {str(e)}")


@router.get("/{card_id}", response_model=KnowledgeCardResponse)
async def get_knowledge_card(card_id: str):
    """
    获取单个知识卡片详情。
    
    Args:
        card_id: 知识卡片ID（概念名称）
        
    Returns:
        知识卡片详情
    """
    try:
        result = neo4j_client.execute_query(
            """
            MATCH (c:Concept {name: $name})
            OPTIONAL MATCH (c)-[r]-()
            WITH c, count(r) as conn_count
            OPTIONAL MATCH (a:Alias)-[:REFERS_TO]->(c)
            WITH c, conn_count, collect(a.name) as aliases
            OPTIONAL MATCH (c)-[:RELATED_TO]->(related:Concept)
            WITH c, conn_count, aliases, collect(related.name) as related_concepts
            RETURN c, conn_count, aliases, related_concepts
            """,
            {"name": card_id}
        )
        
        if not result:
            raise HTTPException(status_code=404, detail=f"知识卡片 '{card_id}' 不存在")
        
        record = result[0]
        concept = record["c"]
        
        return KnowledgeCardResponse(
            id=concept.get("name"),
            name=concept.get("name"),
            description=concept.get("description"),
            domain=concept.get("domain"),
            category=concept.get("category"),
            importance=concept.get("importance"),
            tags=concept.get("tags", []),
            aliases=record.get("aliases", []),
            related_concepts=record.get("related_concepts", []),
            attributes={},
            created_at=concept.get("created_at"),
            updated_at=concept.get("updated_at"),
            connection_count=record.get("conn_count", 0)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询知识卡片失败: {str(e)}")


@router.put("/{card_id}", response_model=KnowledgeCardResponse)
async def update_knowledge_card(card_id: str, card: KnowledgeCardUpdate):
    """
    更新知识卡片。
    
    Args:
        card_id: 知识卡片ID（概念名称）
        card: 更新内容
        
    Returns:
        更新后的知识卡片
    """
    try:
        # 检查是否存在
        existing = neo4j_client.execute_query(
            "MATCH (c:Concept {name: $name}) RETURN c",
            {"name": card_id}
        )
        
        if not existing:
            raise HTTPException(status_code=404, detail=f"知识卡片 '{card_id}' 不存在")
        
        # 构建更新属性
        update_props = {}
        if card.name is not None:
            update_props["name"] = card.name
        if card.description is not None:
            update_props["description"] = card.description
        if card.domain is not None:
            update_props["domain"] = card.domain
        if card.category is not None:
            update_props["category"] = card.category
        if card.importance is not None:
            update_props["importance"] = card.importance
        if card.tags is not None:
            update_props["tags"] = card.tags
        if card.attributes is not None:
            update_props.update(card.attributes)
        
        update_props["updated_at"] = datetime.utcnow().isoformat()
        
        # 更新概念节点
        neo4j_client.execute_query(
            """
            MATCH (c:Concept {name: $old_name})
            SET c += $properties
            RETURN c
            """,
            {"old_name": card_id, "properties": update_props}
        )
        
        # 更新别名
        if card.aliases is not None:
            # 删除旧别名
            neo4j_client.execute_query(
                """
                MATCH (c:Concept {name: $name})<-[:REFERS_TO]-(a:Alias)
                DETACH DELETE a
                """,
                {"name": card.name or card_id}
            )
            
            # 创建新别名
            for alias in card.aliases:
                neo4j_client.execute_query(
                    """
                    MATCH (c:Concept {name: $name})
                    MERGE (a:Alias {name: $alias})
                    MERGE (a)-[:REFERS_TO]->(c)
                    """,
                    {"name": card.name or card_id, "alias": alias}
                )
        
        # 更新关联概念
        if card.related_concepts is not None:
            # 删除旧的 RELATED_TO 关系
            neo4j_client.execute_query(
                """
                MATCH (c:Concept {name: $name})-[r:RELATED_TO]->()
                DELETE r
                """,
                {"name": card.name or card_id}
            )
            
            # 创建新关系
            for related_name in card.related_concepts:
                neo4j_client.execute_query(
                    """
                    MERGE (c1:Concept {name: $name1})
                    MERGE (c2:Concept {name: $name2})
                    MERGE (c1)-[:RELATED_TO]->(c2)
                    """,
                    {"name1": card.name or card_id, "name2": related_name}
                )
        
        # 返回更新后的卡片
        return await get_knowledge_card(card.name or card_id)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新知识卡片失败: {str(e)}")


@router.delete("/{card_id}")
async def delete_knowledge_card(card_id: str):
    """
    删除知识卡片。
    
    Args:
        card_id: 知识卡片ID（概念名称）
        
    Returns:
        删除结果
    """
    try:
        # 检查是否存在
        existing = neo4j_client.execute_query(
            "MATCH (c:Concept {name: $name}) RETURN c",
            {"name": card_id}
        )
        
        if not existing:
            raise HTTPException(status_code=404, detail=f"知识卡片 '{card_id}' 不存在")
        
        # 删除别名
        neo4j_client.execute_query(
            """
            MATCH (c:Concept {name: $name})<-[:REFERS_TO]-(a:Alias)
            DETACH DELETE a
            """,
            {"name": card_id}
        )
        
        # 删除概念节点及其所有关系
        neo4j_client.execute_query(
            """
            MATCH (c:Concept {name: $name})
            DETACH DELETE c
            """,
            {"name": card_id}
        )
        
        return {"message": f"知识卡片 '{card_id}' 已删除", "success": True}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除知识卡片失败: {str(e)}")

