import logging
from typing import Any, Dict, List, Optional
from src.retrieval.dense_search import DenseRetriever
from src.retrieval.rrf import reciprocal_rank_fusion
from src.retrieval.sparse_search import SparseRetriever

logger = logging.getLogger(__name__)


class HybridSearchEngine:
    """Combines HNSW dense cosine search and tsvector sparse lexical search via Reciprocal Rank Fusion (k=60)."""

    def __init__(
        self,
        dense_retriever: Optional[DenseRetriever] = None,
        sparse_retriever: Optional[SparseRetriever] = None,
        k: int = 60,
    ) -> None:
        self.dense = dense_retriever or DenseRetriever()
        self.sparse = sparse_retriever or SparseRetriever()
        self.k = k

    def search(
        self,
        query: str,
        top_k: int = 50,
        parent_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Executes parallel dense and sparse searches, fusing candidates via RRF."""
        dense_candidates = self.dense.search(query, top_k=top_k, parent_id=parent_id)
        sparse_candidates = self.sparse.search(query, top_k=top_k, parent_id=parent_id)

        fused = reciprocal_rank_fusion([dense_candidates, sparse_candidates], k=self.k)
        return fused[:top_k]
