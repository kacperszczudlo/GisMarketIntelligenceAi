import logging
from typing import List, Optional
import numpy as np
from src.config import settings

logger = logging.getLogger(__name__)

EXPECTED_EMBEDDING_DIM = 1024


class BgeM3Embedder:
    """Embedder wrapper for BAAI/bge-m3 generating 1024-dimensional normalized dense vectors."""

    def __init__(
        self,
        model_name: Optional[str] = None,
        device: Optional[str] = None,
    ) -> None:
        self.model_name = model_name or settings.EMBEDDING_MODEL_NAME
        self.device = device
        self._model = None

    def _get_model(self):
        """Lazy loader for SentenceTransformer model."""
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            logger.info("Loading embedding model %s (device: %s)", self.model_name, self.device)
            self._model = SentenceTransformer(self.model_name, device=self.device)
        return self._model

    def embed_texts(self, texts: List[str], batch_size: int = 16) -> List[List[float]]:
        """Generates unit-normalized dense embeddings for a batch of strings."""
        if not texts:
            return []

        model = self._get_model()
        embeddings = model.encode(
            texts,
            batch_size=batch_size,
            normalize_embeddings=True,
            show_progress_bar=False,
        )

        if isinstance(embeddings, np.ndarray):
            if embeddings.ndim == 1:
                embeddings = [embeddings.tolist()]
            else:
                embeddings = embeddings.tolist()
        elif isinstance(embeddings, list) and embeddings and not isinstance(embeddings[0], list):
            embeddings = [embeddings]

        # Validate dimensional integrity strictly
        for emb in embeddings:
            if len(emb) != EXPECTED_EMBEDDING_DIM:
                raise ValueError(
                    f"Generated embedding dimension {len(emb)} != required {EXPECTED_EMBEDDING_DIM}"
                )

        return embeddings

    def embed_query(self, query: str) -> List[float]:
        """Generates unit-normalized dense embedding for a single search query."""
        results = self.embed_texts([query])
        return results[0]
