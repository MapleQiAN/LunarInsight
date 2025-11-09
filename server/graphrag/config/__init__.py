"""
GraphRAG 配置加载器

从 YAML 文件加载配置并提供单例访问
"""

import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional
from functools import lru_cache

# 配置文件目录
CONFIG_DIR = Path(__file__).parent


class PredicateConfig:
    """谓词配置"""
    
    def __init__(self, config: Dict[str, Any]):
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
    
    def validate_type_constraint(self, source_type: str, predicate: str, target_type: str) -> bool:
        """验证类型约束"""
        for constraint in self.type_constraints:
            if (constraint["source"] == source_type and 
                constraint["predicate"] == predicate):
                allowed_targets = constraint["target"]
                if isinstance(allowed_targets, list):
                    return target_type in allowed_targets
                else:
                    return target_type == allowed_targets
        # 如果没有找到约束，默认允许（保守策略）
        return True


class OntologyConfig:
    """本体配置"""
    
    def __init__(self, config: Dict[str, Any]):
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
    "PredicateConfig",
    "OntologyConfig",
    "ThresholdConfig",
    "GraphRAGConfig",
    "get_config"
]

