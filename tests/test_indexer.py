import uuid
from unittest.mock import MagicMock, patch
import numpy as np
import pytest
from src.database.connection import db_manager
from src.indexing.indexer import DatabaseIndexer
from src.indexing.splitter import ParentChildSplitter


def test_database_indexer_transactional_insert():
    indexer = DatabaseIndexer(splitter=ParentChildSplitter(child_size=50, child_overlap=5))

    # Setup parent procurement and attachment in DB
    proc_id = uuid.uuid4()
    att_id = uuid.uuid4()
    ocds_id = f"ocds-idx-{str(proc_id)[:8]}"

    with db_manager.get_cursor(commit=True) as cur:
        cur.execute(
            """
            INSERT INTO procurements (id, ocds_id, title, municipality_name, voivodeship, date_published, date_deadline)
            VALUES (%s, %s, %s, %s, %s, NOW(), NOW() + INTERVAL '14 days');
            """,
            (str(proc_id), ocds_id, "Tender for indexing test", "Urząd Miasta Kraków", "Małopolskie"),
        )
        cur.execute(
            """
            INSERT INTO attachments (id, procurement_id, file_name, file_type, sha256_hash, raw_markdown)
            VALUES (%s, %s, %s, %s, %s, %s);
            """,
            (str(att_id), str(proc_id), "SWZ_Krakow.pdf", "SWZ", "b" * 64, "# Raw"),
        )

    sample_md = (
        "# Rozdział I: Wymagania ogólne\n\n"
        "Modernizacja bazy danych BDOT500 oraz GESUT dla miasta Krakowa.\n\n"
        "## Rozdział II: Kluczowe terminy\n\n"
        "Termin realizacji wynosi 12 miesięcy od podpisania umowy.\n"
    )

    # Mock embedder to avoid downloading weights during test
    fake_vec = [0.0] * 1024
    fake_vec[0] = 1.0

    with patch.object(indexer.embedder, "embed_texts") as mock_embed:
        mock_embed.side_effect = lambda texts, **kwargs: [fake_vec for _ in texts]
        indexed_count = indexer.index_document(sample_md, attachment_id=att_id)

        assert indexed_count >= 2

        # Verify DB records
        with db_manager.get_cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM parent_nodes WHERE attachment_id = %s;", (str(att_id),))
            p_count = cur.fetchone()[0]
            assert p_count == 2

            cur.execute(
                """
                SELECT COUNT(*), vector_dims(embedding)
                FROM chunk_vectors cv
                JOIN parent_nodes pn ON cv.parent_id = pn.id
                WHERE pn.attachment_id = %s
                GROUP BY vector_dims(embedding);
                """,
                (str(att_id),),
            )
            c_row = cur.fetchone()
            assert c_row is not None
            assert c_row[0] == indexed_count
            assert c_row[1] == 1024

    # Cleanup test data
    with db_manager.get_cursor(commit=True) as cur:
        cur.execute("DELETE FROM procurements WHERE id = %s;", (str(proc_id),))
