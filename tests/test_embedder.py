import numpy as np
import pytest
from pytest_mock import MockerFixture
from src.indexing.embedder import EXPECTED_EMBEDDING_DIM, BgeM3Embedder

BATCH_SIZE_TWO = 2
INVALID_EMBEDDING_DIM = 768
UNIT_NORM_EXPECTED = 1.0
UNIT_NORM_TOLERANCE = 1e-3


def test_should_generate_unit_normalized_1024_dimensional_embeddings_for_batch(
    mocker: MockerFixture,
) -> None:
    # Arrange
    embedder = BgeM3Embedder()
    fake_vectors = np.ones((BATCH_SIZE_TWO, EXPECTED_EMBEDDING_DIM), dtype=np.float32)
    fake_vectors = fake_vectors / np.linalg.norm(fake_vectors, axis=1, keepdims=True)

    mock_model = mocker.MagicMock()
    mock_model.encode.return_value = fake_vectors
    mocker.patch.object(embedder, "_get_model", return_value=mock_model)

    # Act
    results = embedder.embed_texts(["Przetarg na bazę BDOT500", "Kryteria oceny ofert"])

    # Assert
    assert len(results) == BATCH_SIZE_TWO
    assert len(results[0]) == EXPECTED_EMBEDDING_DIM
    assert len(results[1]) == EXPECTED_EMBEDDING_DIM
    assert pytest.approx(float(np.linalg.norm(results[0])), rel=UNIT_NORM_TOLERANCE) == UNIT_NORM_EXPECTED


def test_should_generate_1024_dimensional_vector_for_single_search_query(
    mocker: MockerFixture,
) -> None:
    # Arrange
    embedder = BgeM3Embedder()
    fake_vector = np.ones(EXPECTED_EMBEDDING_DIM, dtype=np.float32)
    fake_vector = fake_vector / np.linalg.norm(fake_vector)

    mock_model = mocker.MagicMock()
    mock_model.encode.return_value = fake_vector
    mocker.patch.object(embedder, "_get_model", return_value=mock_model)

    # Act
    query_vec = embedder.embed_query("Wymogi dotyczące plików .str w przetargu")

    # Assert
    assert isinstance(query_vec, list)
    assert len(query_vec) == EXPECTED_EMBEDDING_DIM


def test_should_return_empty_list_without_loading_model_when_texts_are_empty(
    mocker: MockerFixture,
) -> None:
    # Arrange
    embedder = BgeM3Embedder()
    spy_get_model = mocker.spy(embedder, "_get_model")

    # Act
    result = embedder.embed_texts([])

    # Assert
    assert result == []
    spy_get_model.assert_not_called()


def test_should_raise_value_error_when_model_returns_wrong_vector_dimension(
    mocker: MockerFixture,
) -> None:
    # Arrange
    embedder = BgeM3Embedder()
    wrong_dim_vectors = np.ones((1, INVALID_EMBEDDING_DIM), dtype=np.float32)
    mock_model = mocker.MagicMock()
    mock_model.encode.return_value = wrong_dim_vectors
    mocker.patch.object(embedder, "_get_model", return_value=mock_model)

    # Act & Assert
    with pytest.raises(ValueError, match="Generated embedding dimension 768 != required 1024"):
        embedder.embed_texts(["Nieprawidłowy wymiar modelu"])


def test_should_lazily_instantiate_sentence_transformer_once(
    mocker: MockerFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    import sys

    fake_st_module = mocker.MagicMock()
    monkeypatch.setitem(sys.modules, "sentence_transformers", fake_st_module)
    embedder = BgeM3Embedder(model_name="BAAI/bge-m3", device="cpu")

    # Act
    first = embedder._get_model()
    second = embedder._get_model()

    # Assert
    assert first is second
    fake_st_module.SentenceTransformer.assert_called_once_with("BAAI/bge-m3", device="cpu")

