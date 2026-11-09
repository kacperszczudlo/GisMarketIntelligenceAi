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
        procurement_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Executes parallel dense and sparse searches, fusing candidates via RRF."""
        kwargs: Dict[str, Any] = {"top_k": top_k, "parent_id": parent_id}
        if procurement_id is not None:
            kwargs["procurement_id"] = procurement_id

        dense_candidates = self.dense.search(query, **kwargs)
        sparse_candidates = self.sparse.search(query, **kwargs)

        fused = reciprocal_rank_fusion([dense_candidates, sparse_candidates], k=self.k)
        return fused[:top_k]
