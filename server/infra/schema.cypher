// ============================================
// LunarInsight Neo4j Schema 初始化脚本
// 版本: v2.0-GraphRAG
// 用途: 定义节点约束、关系类型、向量索引
// ============================================

// ============================================
// 1. 节点约束 (Constraints)
// ============================================

// Document 节点约束（保留现有）
CREATE CONSTRAINT document_id_unique IF NOT EXISTS 
FOR (d:Document) REQUIRE d.id IS UNIQUE;

CREATE CONSTRAINT document_checksum_unique IF NOT EXISTS 
FOR (d:Document) REQUIRE d.checksum IS UNIQUE;

// Concept 节点约束（保留现有）
CREATE CONSTRAINT concept_name_unique IF NOT EXISTS 
FOR (c:Concept) REQUIRE c.name IS UNIQUE;

// Topic 节点约束（保留现有）
CREATE CONSTRAINT topic_name_unique IF NOT EXISTS 
FOR (t:Topic) REQUIRE t.name IS UNIQUE;

// Chunk 节点约束（新增）
CREATE CONSTRAINT chunk_id_unique IF NOT EXISTS 
FOR (c:Chunk) REQUIRE c.id IS UNIQUE;

// Claim 节点约束（新增）
CREATE CONSTRAINT claim_id_unique IF NOT EXISTS 
FOR (cl:Claim) REQUIRE cl.id IS UNIQUE;

// Theme 节点约束（新增）
CREATE CONSTRAINT theme_id_unique IF NOT EXISTS 
FOR (t:Theme) REQUIRE t.id IS UNIQUE;

// RuntimeConfig 节点约束（保留现有）
CREATE CONSTRAINT runtime_config_id_unique IF NOT EXISTS 
FOR (r:RuntimeConfig) REQUIRE r.id IS UNIQUE;

// ============================================
// 2. 索引 (Indexes)
// ============================================

// Document 索引（保留现有）
CREATE INDEX document_checksum IF NOT EXISTS 
FOR (d:Document) ON (d.checksum);

CREATE INDEX document_kind IF NOT EXISTS 
FOR (d:Document) ON (d.kind);

// Concept 索引（保留现有）
CREATE INDEX concept_domain IF NOT EXISTS 
FOR (c:Concept) ON (c.domain);

// Source 索引（保留现有）
CREATE INDEX source_hash IF NOT EXISTS 
FOR (s:Source) ON (s.hash);

// Chunk 索引（新增）
CREATE INDEX chunk_doc_id IF NOT EXISTS 
FOR (c:Chunk) ON (c.doc_id);

CREATE INDEX chunk_section_path IF NOT EXISTS 
FOR (c:Chunk) ON (c.section_path);

// Claim 索引（新增）
CREATE INDEX claim_doc_id IF NOT EXISTS 
FOR (cl:Claim) ON (cl.doc_id);

CREATE INDEX claim_chunk_id IF NOT EXISTS 
FOR (cl:Claim) ON (cl.chunk_id);

CREATE INDEX claim_type IF NOT EXISTS 
FOR (cl:Claim) ON (cl.claim_type);

// Claim 去重索引（P0 新增）
CREATE INDEX claim_normalized_hash IF NOT EXISTS 
FOR (cl:Claim) ON (cl.normalized_text_hash);

CREATE INDEX claim_canonical_id IF NOT EXISTS 
FOR (cl:Claim) ON (cl.canonical_id);

// Claim 属性索引（P0 新增）
CREATE INDEX claim_modality IF NOT EXISTS 
FOR (cl:Claim) ON (cl.modality);

CREATE INDEX claim_polarity IF NOT EXISTS 
FOR (cl:Claim) ON (cl.polarity);

// Theme 索引（新增）
CREATE INDEX theme_community_id IF NOT EXISTS 
FOR (t:Theme) ON (t.community_id);

CREATE INDEX theme_level IF NOT EXISTS 
FOR (t:Theme) ON (t.level);

// Alias 索引（新增，用于别名映射）
CREATE INDEX alias_canonical IF NOT EXISTS 
FOR (a:Alias) ON (a.canonical);

// ============================================
// 3. 向量索引 (Vector Indexes)
// 注意: 需要 Neo4j 5.11+ 支持
// ============================================

// Concept 向量索引（用于语义检索）
// 维度: 1536 (OpenAI text-embedding-3-small)
// 注意: db.index.vector.createNodeIndex 是 void 过程，不能使用 YIELD/RETURN
CALL db.index.vector.createNodeIndex(
  'concept_embeddings',
  'Concept',
  'embedding',
  1536,
  'cosine'
);

// Chunk 向量索引（用于语义块检索）
CALL db.index.vector.createNodeIndex(
  'chunk_embeddings',
  'Chunk',
  'embedding',
  1536,
  'cosine'
);

// Claim 向量索引（P1 新增，用于 GraphRAG 检索）
CALL db.index.vector.createNodeIndex(
  'claim_embeddings',
  'Claim',
  'embedding',
  1536,
  'cosine'
);

// ============================================
// 4. 关系类型说明
// ============================================
// 以下关系类型将在运行时创建，此处仅作说明：
//
// 文档结构关系:
//   (:Document)-[:CONTAINS]->(:Chunk)
//
// 实体提及关系:
//   (:Document)-[:MENTIONS]->(:Concept)
//   (:Chunk)-[:MENTIONS]->(:Concept)
//
// 论断关系:
//   (:Chunk)-[:CONTAINS_CLAIM]->(:Claim)
//   (:Claim)-[:SUPPORTS]->(:Claim)
//   (:Claim)-[:CONTRADICTS]->(:Claim)
//   (:Claim)-[:CAUSES]->(:Claim)
//   (:Claim)-[:COMPARES_WITH]->(:Claim)
//   (:Claim)-[:CONDITIONS]->(:Claim)
//
// 主题归属关系:
//   (:Concept)-[:BELONGS_TO_THEME]->(:Theme)
//   (:Claim)-[:BELONGS_TO_THEME]->(:Theme)
//
// 证据回溯关系:
//   (:Concept)-[:EVIDENCE_FROM]->(:Chunk)
//   (:Claim)-[:EVIDENCE_FROM]->(:Chunk)
//
// 概念关系（保留现有）:
//   (:Concept)-[:DERIVES_FROM]->(:Concept)
//   (:Concept)-[:SIMILAR_TO]->(:Concept)
//   (:Concept)-[:IS_A]->(:Concept)
//   (:Concept)-[:PART_OF]->(:Concept)
//   (:Concept)-[:USES]->(:Concept)
//
// ============================================
// 5. 初始化完成提示
// ============================================
RETURN 'Schema initialization completed successfully!' AS status;

