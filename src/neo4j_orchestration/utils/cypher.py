"""
Cypher query utilities and templates.
"""

from typing import Any, Dict, List, Optional


def build_match_clause(
    node_label: str,
    node_var: str = "n",
    properties: Optional[Dict[str, Any]] = None
) -> str:
    """Build MATCH clause for Cypher query
    
    Args:
        node_label: Node label (e.g., "Vendor")
        node_var: Variable name for node (default: "n")
        properties: Property filters
    
    Returns:
        Cypher MATCH clause
    """
    if properties:
        props = ", ".join(f"{k}: ${k}" for k in properties.keys())
        return f"MATCH ({node_var}:{node_label} {{{props}}})"
    else:
        return f"MATCH ({node_var}:{node_label})"


def build_where_clause(
    conditions: Dict[str, Any],
    node_var: str = "n"
) -> str:
    """Build WHERE clause from conditions
    
    Args:
        conditions: Dictionary of conditions
        node_var: Variable name for node
    
    Returns:
        Cypher WHERE clause
    """
    if not conditions:
        return ""
    
    parts = [f"{node_var}.{k} = ${k}" for k in conditions.keys()]
    return "WHERE " + " AND ".join(parts)


def sanitize_node_label(label: str) -> str:
    """Sanitize node label for Cypher query
    
    Args:
        label: Raw label string
    
    Returns:
        Sanitized label
    """
    return ''.join(c for c in label if c.isalnum())


# Query templates
TEMPLATES = {
    "get_entity_by_id": """
        MATCH (n:{label} {{id: $entity_id}})
        RETURN n
    """,
    
    "get_entity_relationships": """
        MATCH (n:{label} {{id: $entity_id}})-[r]-(related)
        RETURN type(r) as relationship_type,
               labels(related) as related_labels,
               related
        LIMIT $limit
    """,
    
    "count_by_property": """
        MATCH (n:{label})
        RETURN n.{property} as value, count(n) as count
        ORDER BY count DESC
    """,
}


def get_template(template_name: str, **kwargs) -> str:
    """Get and format query template
    
    Args:
        template_name: Name of template
        **kwargs: Template variables
    
    Returns:
        Formatted Cypher query
    """
    template = TEMPLATES.get(template_name)
    if not template:
        raise ValueError(f"Unknown template: {template_name}")
    
    return template.format(**kwargs).strip()


__all__ = [
    "build_match_clause",
    "build_where_clause",
    "sanitize_node_label",
    "get_template",
    "TEMPLATES",
]
