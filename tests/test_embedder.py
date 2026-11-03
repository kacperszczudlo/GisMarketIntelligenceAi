from unittest.mock import MagicMock, patch
import numpy as np
import pytest
from src.indexing.embedder import BgeM3Embedder


def test_embedder_dimension_is_strictly_1024():
    embedder = BgeM3Embedder()

    # Mock SentenceTransformer output (batch of 2 texts, dim 1024)
    fake_vectors = np.ones((2, 1024), dtype=np.float32)
    fake_vectors = fake_vectors / np.linalg.norm(fake_vectors, axis=1, keepdims=True)

    mock_model = MagicMock()
    mock_model.encode.return_value = fake_vectors

    with patch.object(embedder, "_get_model", return_value=mock_model):
        results = embedder.embed_texts(["Przetarg na bazę BDOT500", "Kryteria oceny ofert"])

        assert len(results) == 2
        assert len(results[0]) == 1024
        assert len(results[1]) == 1024
        # Verify vector normalization (~1.0 norm)
        assert pytest.approx(float(np.linalg.norm(results[0])), rel=1e-3) == 1.0


def test_embedder_single_query():
    embedder = BgeM3Embedder()
    fake_vector = np.ones(1024, dtype=np.float32)
    fake_vector = fake_vector / np.linalg.norm(fake_vector)

    mock_model = MagicMock()
    mock_model.encode.return_value = fake_vector

    with patch.object(embedder, "_get_model", return_value=mock_model):
        query_vec = embedder.embed_query("Wymogi dotyczące plików .str w przetargu")
        assert len(query_vec) == 1024
        assert isinstance(query_vec, list)
