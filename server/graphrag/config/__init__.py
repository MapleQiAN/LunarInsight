"""
GraphRAG 配置加载器

从 YAML 文件加载配置并提供单例访问
"""

import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional
from functools import lru_cache
from enum import Enum

# 配置文件目录
CONFIG_DIR = Path(__file__).parent


class ConstraintResult(Enum):
    """类型约束检查结果"""
    PASS = "pass"              # 通过：类型组合与标准谓词兼容
    SOFT_VIOLATION = "soft"    # 软违规：不在推荐组合里，但可能合理
    HARD_VIOLATION = "hard"    # 硬违规：明显违反本体规则


class GovernanceStatus(Enum):
    """治理状态"""
    ACCEPTED = "accepted"      # 已接受
    PENDING = "pending"        # 待复核
    REJECTED = "rejected"      # 拒绝


class PredicateConfig:
    """谓词配置"""
    
    def __init__(self, config: Dict[str, Any]):
        self.version: str = config.get("version", "1.0.0")
        self.standard: List[str] = config.get("standard", [])
        self.mappings: Dict[str, str] = config.get("mappings", {})
        self.type_constraints: List[Dict[str, Any]] = config.get("type_constraints", [])
        self.unmatched_strategy: Dict[str, Any] = config.get("unmatched_strategy", {})
    
    def is_standard_predicate(self, predicate: str) -> bool:
        """检查是否为标准谓词"""
        return predicate in self.standard
    
    def normalize_predicate(self, natural_predicate: str) -> Optional[str]:
        """将自然语言谓词映射到标准谓词"""
        return self.mappings.get(natural_predicate)
    
    def validate_type_constraint(self, source_type: str, predicate: str, target_type: str) -> ConstraintResult:
        """验证类型约束，返回三级结果"""
        # 检查硬违规：明显不合理的组合
        hard_violations = [
            # 方法不能是数据集的子类
            ("Method", "IS_A", "Dataset"),
            # 工具不能是概念的子类
            ("Tool", "IS_A", "Concept"),
            # 人物不能派生出方法
            ("Person", "DERIVES_FROM", "Method"),
            # 论断不能使用工具
            ("Claim", "USES", "Tool"),
        ]
        
        if (source_type, predicate, target_type) in hard_violations:
            return ConstraintResult.HARD_VIOLATION
        
        # 检查白名单中的推荐组合
        for constraint in self.type_constraints:
            if (constraint["source"] == source_type and 
                constraint["predicate"] == predicate):
                allowed_targets = constraint["target"]
                if isinstance(allowed_targets, list):
                    if target_type in allowed_targets:
                        return ConstraintResult.PASS
                else:
                    if target_type == allowed_targets:
                        return ConstraintResult.PASS
        
        # 不在推荐组合中，但也不是硬违规，标记为软违规
        # 检查是否属于同一大类（如都是实体类型）
        structural_predicates = {"IS_A", "PART_OF", "USES", "IMPLEMENTED_BY", "CREATES", "DERIVES_FROM", "CONTAINS", "BELONGS_TO"}
        argumentative_predicates = {"SUPPORTS", "CONTRADICTS", "CAUSES", "COMPARES_WITH", "CONDITIONS", "PURPOSE"}
        
        entity_types = {"Concept", "Method", "Tool", "Person"}
        claim_types = {"Claim", "Hypothesis"}
        
        # 检查是否跨域使用了谓词（软违规）
        if predicate in structural_predicates:
            if source_type in claim_types or target_type in claim_types:
                return ConstraintResult.SOFT_VIOLATION
        elif predicate in argumentative_predicates:
            if source_type in entity_types and target_type in entity_types:
                return ConstraintResult.SOFT_VIOLATION
        
        # 其他情况也标记为软违规
        return ConstraintResult.SOFT_VIOLATION


class OntologyConfig:
    """本体配置"""
    
    def __init__(self, config: Dict[str, Any]):
        self.version: str = config.get("version", "1.0.0")
        self.node_types: Dict[str, Any] = config.get("node_types", {})
        self.relationship_types: Dict[str, Any] = config.get("relationship_types", {})
        self.domain_constraints: Dict[str, Any] = config.get("domain_constraints", {})
        self.quality_constraints: Dict[str, Any] = config.get("quality_constraints", {})
    
    def get_node_type_schema(self, node_type: str) -> Optional[Dict[str, Any]]:
        """获取节点类型的 Schema"""
        return self.node_types.get(node_type)
    
    def get_required_properties(self, node_type: str) -> List[str]:
        """获取节点类型的必需属性"""
        schema = self.get_node_type_schema(node_type)
        if schema:
            return schema.get("required_properties", [])
        return []
    
    def validate_node(self, node_type: str, properties: Dict[str, Any]) -> tuple[bool, List[str]]:
        """验证节点数据"""
        schema = self.get_node_type_schema(node_type)
        if not schema:
            return False, [f"Unknown node type: {node_type}"]
        
        errors = []
        required_props = schema.get("required_properties", [])
        for prop in required_props:
            if prop not in properties or properties[prop] is None:
                errors.append(f"Missing required property: {prop}")
        
        return len(errors) == 0, errors
    
    def get_allowed_domains(self) -> List[str]:
        """获取允许的领域列表"""
        return self.domain_constraints.get("allowed_domains", [])


class ThresholdConfig:
    """阈值配置"""
    
    def __init__(self, config: Dict[str, Any]):
        self.entity_linking: Dict[str, Any] = config.get("entity_linking", {})
        self.claim_extraction: Dict[str, Any] = config.get("claim_extraction", {})
        self.theme_building: Dict[str, Any] = config.get("theme_building", {})
        self.predicate_governance: Dict[str, Any] = config.get("predicate_governance", {})
        self.query: Dict[str, Any] = config.get("query", {})
        self.metrics: Dict[str, Any] = config.get("metrics", {})
        self.chunking: Dict[str, Any] = config.get("chunking", {})
        self.coreference: Dict[str, Any] = config.get("coreference", {})
        self.embedding: Dict[str, Any] = config.get("embedding", {})
        self.performance: Dict[str, Any] = config.get("performance", {})
    
    def get(self, category: str, key: str, default: Any = None) -> Any:
        """获取配置值"""
        category_config = getattr(self, category, {})
        return category_config.get(key, default)


class GraphRAGConfig:
    """GraphRAG 全局配置"""
    
    def __init__(self):
        self.predicates = self._load_predicates()
        self.ontology = self._load_ontology()
        self.thresholds = self._load_thresholds()
    
    @staticmethod
    def _load_yaml(filename: str) -> Dict[str, Any]:
        """加载 YAML 文件"""
        config_path = CONFIG_DIR / filename
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")
        
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    
    def _load_predicates(self) -> PredicateConfig:
        """加载谓词配置"""
        config = self._load_yaml("predicates.yaml")
        return PredicateConfig(config)
    
    def _load_ontology(self) -> OntologyConfig:
        """加载本体配置"""
        config = self._load_yaml("ontology.yaml")
        return OntologyConfig(config)
    
    def _load_thresholds(self) -> ThresholdConfig:
        """加载阈值配置"""
        config = self._load_yaml("thresholds.yaml")
        return ThresholdConfig(config)


@lru_cache(maxsize=1)
def get_config() -> GraphRAGConfig:
    """获取全局配置单例"""
    return GraphRAGConfig()


# 导出
__all__ = [
    "ConstraintResult",
    "GovernanceStatus",
    "PredicateConfig",
    "OntologyConfig",
    "ThresholdConfig",
    "GraphRAGConfig",
    "get_config"
]

