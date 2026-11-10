from uuid import UUID, uuid4
import pytest
from src.indexing.splitter import ChildNode, ParentChildSplitter, ParentNode

TEST_PARENT_SIZE = 1500
TEST_CHILD_SIZE = 100
TEST_CHILD_OVERLAP = 10
SMALL_CHILD_SIZE = 6
SMALL_CHILD_OVERLAP = 2
EXPECTED_TWO_PARENTS = 2


def test_should_split_markdown_into_linked_parent_and_child_hierarchy() -> None:
    # Arrange
    sample_doc = (
        "# Rozdział I: Przedmiot zamówienia\n\n"
        "Zamawiający wymaga dostarczenia bazy BDOT500 w układzie PL-2000.\n"
        "Wszystkie dane muszą być zgodne z rozporządzeniem Ministra Rozwoju.\n\n"
        "## Rozdział II: Kryteria oceny ofert\n\n"
        "Kryterium I: Cena 60%.\n"
        "Kryterium II: Doświadczenie personelu 40%.\n"
    )
    attachment_id = uuid4()
    splitter = ParentChildSplitter(
        parent_size=TEST_PARENT_SIZE,
        child_size=TEST_CHILD_SIZE,
        child_overlap=TEST_CHILD_OVERLAP,
    )

    # Act
    parents, children = splitter.split(sample_doc, attachment_id=attachment_id)

    # Assert
    assert len(parents) == EXPECTED_TWO_PARENTS
    assert all(isinstance(p, ParentNode) for p in parents)
    assert all(p.attachment_id == attachment_id for p in parents)
    assert all(isinstance(c, ChildNode) for c in children)

    parent_ids = {p.id for p in parents}
    for child in children:
        assert isinstance(child.parent_id, UUID)
        assert child.parent_id in parent_ids

    assert "Przedmiot zamówienia" in parents[0].section_title
    assert "Kryteria oceny" in parents[1].section_title


def test_should_compute_positive_token_count_and_metadata_for_chunks() -> None:
    # Arrange
    sample_doc = "# Wymagania ogólne\n\nTekst z opisem wymagań technicznych dla geoportalu."
    splitter = ParentChildSplitter()

    # Act
    parents, children = splitter.split(sample_doc)

    # Assert
    assert len(parents) == 1
    assert parents[0].token_count > 0
    assert len(children) == 1
    assert children[0].parent_id == parents[0].id
    assert children[0].metadata_payload["section_title"] == "Wymagania ogólne"
    assert children[0].metadata_payload["token_count"] > 0


def test_should_create_overlapping_child_chunks_for_long_section() -> None:
    # Arrange
    words = [f"slowo{i}" for i in range(15)]
    sample_doc = "# Sekcja Długa\n\n" + " ".join(words)
    splitter = ParentChildSplitter(child_size=SMALL_CHILD_SIZE, child_overlap=SMALL_CHILD_OVERLAP)

    # Act
    parents, children = splitter.split(sample_doc)

    # Assert
    assert len(parents) == 1
    assert len(children) >= 3
    assert [c.chunk_index for c in children] == list(range(len(children)))


def test_should_assign_default_intro_title_when_markdown_has_no_headers() -> None:
    # Arrange
    headerless_doc = "Zamawiający wymaga przekazania plików GML zgodnych ze schematem aplikacyjnym."
    splitter = ParentChildSplitter()

    # Act
    parents, children = splitter.split(headerless_doc)

    # Assert
    assert len(parents) == 1
    assert parents[0].section_title == "Wstęp"
    assert len(children) == 1


@pytest.mark.parametrize(
    "empty_text",
    ["", "   ", "\n\n\t\n"],
    ids=["empty_string", "spaces_only", "newlines_and_tabs"],
)
def test_should_return_empty_collections_when_markdown_is_blank(empty_text: str) -> None:
    # Arrange
    splitter = ParentChildSplitter()

    # Act
    parents, children = splitter.split(empty_text)

    # Assert
    assert parents == []
    assert children == []
