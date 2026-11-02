import uuid
import pytest
from src.config import settings
from src.database.connection import DatabaseManager, get_db_connection


def test_database_connection_and_pgvector():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT extname FROM pg_extension WHERE extname = 'vector';")
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    assert result is not None
    assert result[0] == "vector"


def test_database_manager_pool_and_cursor():
    manager = DatabaseManager(minconn=1, maxconn=3)
    with manager.get_cursor() as cur:
        cur.execute("SELECT 1;")
        res = cur.fetchone()
        assert res[0] == 1
    manager.close_all()


def test_vector_insertion_and_hnsw_query():
    """Verify inserting a 1024-dimension vector and querying using cosine distance <=>."""
    manager = DatabaseManager(minconn=1, maxconn=3)
    test_proc_id = str(uuid.uuid4())
    test_ocds_id = f"ocds-test-{test_proc_id[:8]}"
    test_att_id = str(uuid.uuid4())
    test_parent_id = str(uuid.uuid4())
    test_chunk_id = str(uuid.uuid4())

    with manager.get_cursor(commit=True) as cur:
        # 1. Insert test procurement
        cur.execute(
            """
            INSERT INTO procurements (id, ocds_id, title, municipality_name, voivodeship, date_published, date_deadline)
            VALUES (%s, %s, %s, %s, %s, NOW(), NOW() + INTERVAL '14 days');
            """,
            (test_proc_id, test_ocds_id, "Test Przetarg GIS", "Gmina Test", "Mazowieckie"),
        )

        # 2. Insert test attachment
        cur.execute(
            """
            INSERT INTO attachments (id, procurement_id, file_name, file_type, sha256_hash, raw_markdown)
            VALUES (%s, %s, %s, %s, %s, %s);
            """,
            (test_att_id, test_proc_id, "swz.pdf", "SWZ", "a" * 64, "# Test SWZ"),
        )

        # 3. Insert parent node
        cur.execute(
            """
            INSERT INTO parent_nodes (id, attachment_id, section_title, token_count, content)
            VALUES (%s, %s, %s, %s, %s);
            """,
            (test_parent_id, test_att_id, "Rozdział 1", 50, "Treść sekcji testowej"),
        )

        # 4. Insert 1024-dim child chunk vector
        vec_1024 = [0.0] * 1024
        vec_1024[0] = 1.0
        vec_str = "[" + ",".join(str(x) for x in vec_1024) + "]"

        cur.execute(
            """
            INSERT INTO chunk_vectors (id, parent_id, chunk_index, content, embedding, metadata_payload)
            VALUES (%s, %s, %s, %s, %s::vector, %s);
            """,
            (test_chunk_id, test_parent_id, 0, "Testowy chunk o BDOT500", vec_str, '{"source": "test"}'),
        )

        # 5. Query using cosine distance operator <=>
        query_vec = [0.0] * 1024
        query_vec[0] = 0.99
        query_vec[1] = 0.05
        query_vec_str = "[" + ",".join(str(x) for x in query_vec) + "]"

        cur.execute(
            """
            SELECT id, content, (embedding <=> %s::vector) AS distance
            FROM chunk_vectors
            WHERE id = %s
            ORDER BY distance ASC;
            """,
            (query_vec_str, test_chunk_id),
        )
        row = cur.fetchone()
        assert row is not None
        assert str(row[0]) == test_chunk_id
        assert row[1] == "Testowy chunk o BDOT500"
        # Cosine distance should be very small (< 0.05)
        assert row[2] < 0.05

        # Cleanup test data (cascades automatically delete child nodes)
        cur.execute("DELETE FROM procurements WHERE id = %s;", (test_proc_id,))

    manager.close_all()
