"""knowledge_graph_service - 向后兼容 re-export 层.

本模块已重构至 app.services.knowledge.analyzer，此文件保留用于向后兼容。
请直接从 app.services.knowledge 导入。
"""
from app.services.knowledge.analyzer import (
    get_graph_data,
    get_graph_data_public,
    get_node_neighbors,
    get_node_neighbors_public,
    get_shortest_path,
    get_shortest_path_public,
)

__all__ = [
    "get_graph_data",
    "get_graph_data_public",
    "get_node_neighbors",
    "get_node_neighbors_public",
    "get_shortest_path",
    "get_shortest_path_public",
]
