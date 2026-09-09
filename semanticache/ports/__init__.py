"""Port interfaces (abstract boundaries for dependency injection)."""

from semanticache.ports.embedder import Embedder
from semanticache.ports.parser import ProviderParser
from semanticache.ports.store import VectorStore

__all__ = ["Embedder", "ProviderParser", "VectorStore"]
