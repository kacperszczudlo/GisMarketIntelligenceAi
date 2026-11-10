import logging
from typing import Any, Dict, List, Optional
import numpy as np
from src.config import settings

logger = logging.getLogger(__name__)


class CrossEncoderReranker:
    """Second-stage reranker using BAAI/bge-reranker-v2-m3 with full cross-attention over (query, document)."""

    def __init__(
        self,
        model_name: Optional[str] = None,
        device: Optional[str] = None,
    ) -> None:
        self.model_name = model_name or settings.RERANKER_MODEL_NAME
        self.device = device
        self._model = None

    def _get_model(self):
        """Lazy loader for sentence_transformers CrossEncoder."""
        if self._model is None:
            from sentence_transformers import CrossEncoder

            logger.info("Loading CrossEncoder model %s (device: %s)", self.model_name, self.device)
            self._model = CrossEncoder(self.model_name, device=self.device)
        return self._model

    def rerank(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        top_n: int = 5,
    ) -> List[Dict[str, Any]]:
        """Reranks candidates based on deep cross-attention scores and returns the top_n items."""
        if not candidates:
            return []

        model = self._get_model()
        pairs = [[query, c.get("content", "")] for c in candidates]
        scores = model.predict(pairs)

        if isinstance(scores, np.ndarray):
            scores = scores.tolist()
        elif not isinstance(scores, list):
            scores = [float(scores)]

        scored_candidates = []
        for candidate, score in zip(candidates, scores):
            updated = dict(candidate)
            updated["cross_encoder_score"] = float(score)
            scored_candidates.append(updated)

        scored_candidates.sort(key=lambda x: x["cross_encoder_score"], reverse=True)
        return scored_candidates[:top_n]
