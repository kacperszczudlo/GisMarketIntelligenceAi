from uuid import UUID
import pytest
from src.indexing.splitter import ParentChildSplitter, ParentNode, ChildNode


def test_parent_child_linking_and_hierarchy():
    sample_doc = (
        "# Rozdział I: Przedmiot zamówienia\n\n"
        "Zamawiający wymaga dostarczenia bazy BDOT500 w układzie PL-2000.\n"
        "Wszystkie dane muszą być zgodne z rozporządzeniem Ministra Rozwoju.\n\n"
        "## Rozdział II: Kryteria oceny ofert\n\n"
        "Kryterium I: Cena 60%.\n"
        "Kryterium II: Doświadczenie personelu 40%.\n"
    )

    splitter = ParentChildSplitter(parent_size=1500, child_size=100, child_overlap=10)
    parents, children = splitter.split(sample_doc)

    assert len(parents) == 2
    assert isinstance(parents[0], ParentNode)
    assert isinstance(children[0], ChildNode)

    # All children must have valid parent_id referencing an existing parent
    parent_ids = {p.id for p in parents}
    for child in children:
        assert isinstance(child.parent_id, UUID)
        assert child.parent_id in parent_ids

    # Section titles must be extracted
    assert "Przedmiot zamówienia" in parents[0].section_title
    assert "Kryteria oceny" in parents[1].section_title


def test_parent_node_token_count_positive():
    sample_doc = "# Wymagania ogólne\n\nTekst z opisem wymagań technicznych dla geoportalu."
    splitter = ParentChildSplitter()
    parents, children = splitter.split(sample_doc)

    assert len(parents) == 1
    assert parents[0].token_count > 0
    assert len(children) >= 1
    assert children[0].parent_id == parents[0].id
