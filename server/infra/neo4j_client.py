"""Neo4j client for graph operations."""
import json
from typing import List, Dict, Any, Optional
from neo4j import GraphDatabase, Driver
from infra.config import settings


class Neo4jClient:
    """Neo4j database client."""
    
    def __init__(self):
        self.driver: Optional[Driver] = None
        self._initialized = False
    
    def initialize(self):
        """Initialize connection and schema (call this explicitly)."""
        if not self._initialized:
            self._connect()
            self._initialize_schema()
            self._initialized = True
    
    def _connect(self):
        """Establish connection to Neo4j."""
        self.driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_pass)
        )
    
    def _initialize_schema(self):
        """Initialize database schema: constraints and indexes."""
        with self.driver.session() as session:
            # Constraints
            session.run("""
                CREATE CONSTRAINT document_checksum_unique IF NOT EXISTS
                FOR (d:Document) REQUIRE d.checksum IS UNIQUE
            """)
            
            session.run("""
                CREATE CONSTRAINT concept_name_unique IF NOT EXISTS
                FOR (c:Concept) REQUIRE c.name IS UNIQUE
            """)
            
            session.run("""
                CREATE CONSTRAINT runtime_config_id_unique IF NOT EXISTS
                FOR (r:RuntimeConfig) REQUIRE r.id IS UNIQUE
            """)
            
            # Indexes
            session.run("""
                CREATE INDEX source_hash IF NOT EXISTS
                FOR (s:Source) ON (s.hash)
            """)
            
            session.run("""
                CREATE INDEX concept_domain IF NOT EXISTS
                FOR (c:Concept) ON (c.domain)
            """)
            
            session.run("""
                CREATE INDEX document_kind IF NOT EXISTS
                FOR (d:Document) ON (d.kind)
            """)
    
    def close(self):
        """Close the driver connection."""
        if self.driver:
            self.driver.close()
    
    def execute_query(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Execute a Cypher query and return results.
        
        Args:
            query: Cypher query string
            parameters: Query parameters
            
        Returns:
            List of result records as dictionaries
        """
        if not self._initialized:
            raise RuntimeError("Neo4jClient is not initialized. Call initialize() first.")
        
        with self.driver.session() as session:
            result = session.run(query, parameters or {})
            return [dict(record) for record in result]
    
    def create_document(self, doc_id: str, filename: str, checksum: str, 
                       kind: str, size: int, mime: Optional[str] = None,
                       source_id: Optional[str] = None, meta: Optional[Dict] = None) -> bool:
        """Create or update a Document node."""
        # Serialize meta dict to JSON string for Neo4j storage
        # Neo4j only supports primitive types, so we serialize dicts to JSON strings
        meta_json = json.dumps(meta) if meta and len(meta) > 0 else None
        query = """
        MERGE (d:Document {id: $doc_id})
        SET d.filename = $filename,
            d.checksum = $checksum,
            d.kind = $kind,
            d.size = $size,
            d.mime = $mime,
            d.source_id = $source_id,
            d.meta = $meta_json,
            d.created_at = coalesce(d.created_at, datetime()),
            d.updated_at = datetime()
        RETURN d
        """
        result = self.execute_query(query, {
            "doc_id": doc_id,
            "filename": filename,
            "checksum": checksum,
            "kind": kind,
            "size": size,
            "mime": mime,
            "source_id": source_id,
            "meta_json": meta_json
        })
        return len(result) > 0
    
    def create_concept(self, name: str, domain: Optional[str] = None, 
                      meta: Optional[Dict] = None) -> bool:
        """Create or merge a Concept node."""
        # Serialize meta dict to JSON string for Neo4j storage
        # Neo4j only supports primitive types, so we serialize dicts to JSON strings
        meta_json = json.dumps(meta) if meta and len(meta) > 0 else None
        query = """
        MERGE (c:Concept {name: $name})
        ON CREATE SET 
            c.domain = $domain,
            c.meta = $meta_json,
            c.aliases = [],
            c.created_at = datetime(),
            c.updated_at = datetime()
        ON MATCH SET
            c.updated_at = datetime()
        RETURN c
        """
        result = self.execute_query(query, {
            "name": name,
            "domain": domain,
            "meta_json": meta_json
        })
        return len(result) > 0
    
    def add_concept_alias(self, canonical_name: str, alias: str) -> bool:
        """
        Add an alias to an existing concept.
        
        Args:
            canonical_name: The canonical name of the concept
            alias: The alias to add
        """
        query = """
        MATCH (c:Concept {name: $canonical_name})
        SET c.aliases = coalesce(c.aliases, []) + 
            CASE WHEN $alias IN coalesce(c.aliases, []) 
                 THEN [] 
                 ELSE [$alias] 
            END,
            c.updated_at = datetime()
        RETURN c
        """
        result = self.execute_query(query, {
            "canonical_name": canonical_name,
            "alias": alias
        })
        return len(result) > 0
    
    def create_relationship(self, source_id: str, target_id: str, 
                           rel_type: str, properties: Optional[Dict] = None) -> bool:
        """
        Create a relationship between two nodes.
        
        Args:
            source_id: Source node ID (can be document ID or concept name)
            target_id: Target node ID
            rel_type: Relationship type (e.g., MENTIONS, DERIVES_FROM)
            properties: Relationship properties
        """
        query = f"""
        MATCH (a), (b)
        WHERE (a:Document AND a.id = $source_id) OR (a:Concept AND a.name = $source_id)
        AND (b:Document AND b.id = $target_id) OR (b:Concept AND b.name = $target_id)
        MERGE (a)-[r:{rel_type}]->(b)
        SET r += $properties,
            r.created_at = coalesce(r.created_at, datetime()),
            r.updated_at = datetime()
        RETURN r
        """
        result = self.execute_query(query, {
            "source_id": source_id,
            "target_id": target_id,
            "properties": properties or {}
        })
        return len(result) > 0
    
    def link_concept_to_document(self, concept_name: str, doc_id: str, 
                                 page: Optional[int] = None, 
                                 offset: Optional[List[int]] = None,
                                 evidence: Optional[str] = None) -> bool:
        """Create MENTIONS relationship between Document and Concept."""
        properties = {}
        if page is not None:
            properties["page"] = page
        if offset:
            properties["offset"] = offset
        if evidence:
            properties["evidence"] = evidence
        
        return self.create_relationship(doc_id, concept_name, "MENTIONS", properties)
    
    def get_all_nodes(self, label: Optional[str] = None, limit: int = 100) -> List[Dict]:
        """Get all nodes, optionally filtered by label."""
        if label:
            query = f"MATCH (n:{label}) RETURN n LIMIT $limit"
        else:
            query = "MATCH (n) RETURN n LIMIT $limit"
        return self.execute_query(query, {"limit": limit})
    
    def get_all_relationships(self, rel_type: Optional[str] = None, limit: int = 100) -> List[Dict]:
        """Get all relationships, optionally filtered by type."""
        if rel_type:
            query = f"MATCH (a)-[r:{rel_type}]->(b) RETURN a, r, b LIMIT $limit"
        else:
            query = "MATCH (a)-[r]->(b) RETURN a, r, b LIMIT $limit"
        return self.execute_query(query, {"limit": limit})
    
    def find_concept_by_name(self, name: str) -> Optional[Dict]:
        """Find a concept by name."""
        query = "MATCH (c:Concept {name: $name}) RETURN c"
        result = self.execute_query(query, {"name": name})
        return result[0] if result else None
    
    def find_similar_concepts(self, name: str, threshold: float = 0.8) -> List[Dict]:
        """
        Find similar concepts with bilingual support.
        Searches by:
        - Exact match (case-insensitive)
        - Substring match
        - Alias match
        - Fuzzy matching
        """
        query = """
        MATCH (c:Concept)
        WHERE toLower(c.name) = toLower($name)
           OR c.name CONTAINS $name
           OR $name CONTAINS c.name
           OR toLower($name) IN [toLower(alias) | alias IN coalesce(c.aliases, [])]
           OR any(alias IN coalesce(c.aliases, []) WHERE alias CONTAINS $name OR $name CONTAINS alias)
        RETURN c
        ORDER BY 
            CASE 
                WHEN toLower(c.name) = toLower($name) THEN 0
                WHEN c.name CONTAINS $name OR $name CONTAINS c.name THEN 1
                ELSE 2
            END
        LIMIT 10
        """
        return self.execute_query(query, {"name": name})
    
    def search_concepts_by_alias(self, alias: str) -> List[Dict]:
        """
        Search concepts by alias.
        
        Args:
            alias: The alias to search for
            
        Returns:
            List of concepts that have this alias
        """
        query = """
        MATCH (c:Concept)
        WHERE toLower($alias) IN [toLower(a) | a IN coalesce(c.aliases, [])]
        RETURN c
        """
        return self.execute_query(query, {"alias": alias})


# Global client instance
neo4j_client = Neo4jClient()

