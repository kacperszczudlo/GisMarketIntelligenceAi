import logging
from typing import Any, Dict, List, Optional
from src.retrieval.context_reorder import reorder_lost_in_the_middle
from src.retrieval.hybrid_search import HybridSearchEngine
from src.retrieval.parent_resolver import ParentNodeResolver
from src.retrieval.reranker import CrossEncoderReranker

logger = logging.getLogger(__name__)


class RetrievalPipeline:
    """Two-stage retrieval pipeline: Hybrid Search (RRF k=60) -> Cross-Encoder -> Parent Resolution -> Lost-In-The-Middle."""

    def __init__(
        self,
        hybrid_engine: Optional[HybridSearchEngine] = None,
        reranker: Optional[CrossEncoderReranker] = None,
        parent_resolver: Optional[ParentNodeResolver] = None,
    ) -> None:
        self.hybrid = hybrid_engine or HybridSearchEngine()
        self.reranker = reranker or CrossEncoderReranker()
        self.resolver = parent_resolver or ParentNodeResolver()

    def retrieve(
        self,
        query: str,
        top_candidates: int = 30,
        top_k: int = 5,
        parent_id: Optional[str] = None,
        procurement_id: Optional[str] = None,
        reorder_context: bool = True,
    ) -> List[Dict[str, Any]]:
        """Executes the full two-stage retrieval pipeline.

        1. Hybrid Search (Dense + Sparse fused via RRF) retrieves top_candidates.
        2. Cross-Encoder reranks top_candidates to top_k most accurate child chunks.
        3. Resolves child chunks to full ParentNode sections from database.
        4. Reorders parent nodes in U-shape to counter Lost-In-The-Middle effect.
        """
        logger.info("Executing retrieval for query: '%s' (top_k=%d)", query, top_k)

        search_kwargs: Dict[str, Any] = {"top_k": top_candidates, "parent_id": parent_id}
        if procurement_id is not None:
            search_kwargs["procurement_id"] = procurement_id

        # Stage 1: Hybrid Search
        candidates = self.hybrid.search(query, **search_kwargs)
        if not candidates:
            return []

        # Stage 2: Cross-Encoder Reranking
        reranked_children = self.reranker.rerank(query, candidates, top_n=top_k)

        # Stage 3: Resolve Parent Nodes (full context)
        resolved_parents = self.resolver.resolve(reranked_children)

        # Stage 4: U-shaped Context Reordering
        if reorder_context and len(resolved_parents) > 2:
            return reorder_lost_in_the_middle(resolved_parents)

        return resolved_parents
