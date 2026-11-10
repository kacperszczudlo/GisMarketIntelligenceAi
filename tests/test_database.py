import uuid
import pytest
from pytest_mock import MockerFixture
from src.config import settings
from src.database.connection import DatabaseManager, get_db_connection

POOL_MIN_CONN = 1
POOL_MAX_CONN = 3
EMBEDDING_DIMENSION = 1024
MAX_EXPECTED_COSINE_DISTANCE = 0.05


def test_should_connect_to_database_with_configured_credentials(
    mocker: MockerFixture,
) -> None:
    # Arrange
    fake_conn = mocker.MagicMock(name="PgConnection")
    mock_connect = mocker.patch("src.database.connection.psycopg2.connect", return_value=fake_conn)

    # Act
    conn = get_db_connection()

    # Assert
    assert conn is fake_conn
    mock_connect.assert_called_once_with(
        host=settings.POSTGRES_HOST,
        port=settings.POSTGRES_PORT,
        dbname=settings.POSTGRES_DB,
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
    )


def test_should_initialize_connection_pool_lazily_and_return_connection_on_exit(
    mocker: MockerFixture,
) -> None:
    # Arrange
    fake_pool = mocker.MagicMock(name="SimpleConnectionPool")
    fake_conn = mocker.MagicMock(name="PooledConnection")
    fake_cursor = mocker.MagicMock(name="PooledCursor")
    fake_cursor.fetchone.return_value = (1,)
    fake_conn.cursor.return_value = fake_cursor
    fake_pool.getconn.return_value = fake_conn

    mock_pool_cls = mocker.patch(
        "src.database.connection.SimpleConnectionPool",
        return_value=fake_pool,
    )
    manager = DatabaseManager(minconn=POOL_MIN_CONN, maxconn=POOL_MAX_CONN)

    # Act
    with manager.get_cursor(commit=True) as cur:
        cur.execute("SELECT 1;")
        row = cur.fetchone()
    manager.close_all()

    # Assert
    assert row == (1,)
    mock_pool_cls.assert_called_once()
    fake_conn.commit.assert_called_once()
    fake_cursor.close.assert_called_once()
    fake_pool.putconn.assert_called_once_with(fake_conn)
    fake_pool.closeall.assert_called_once()


def test_should_rollback_transaction_and_close_cursor_when_query_raises_error(
    mocker: MockerFixture,
) -> None:
    # Arrange
    fake_pool = mocker.MagicMock(name="SimpleConnectionPool")
    fake_conn = mocker.MagicMock(name="PooledConnection")
    fake_cursor = mocker.MagicMock(name="PooledCursor")
    fake_conn.cursor.return_value = fake_cursor
    fake_pool.getconn.return_value = fake_conn
    mocker.patch("src.database.connection.SimpleConnectionPool", return_value=fake_pool)

    manager = DatabaseManager(minconn=POOL_MIN_CONN, maxconn=POOL_MAX_CONN)

    # Act & Assert
    with pytest.raises(RuntimeError, match="constraint violation"):
        with manager.get_cursor(commit=True) as cur:
            cur.execute("INSERT INTO invalid_table VALUES (1);")
            raise RuntimeError("constraint violation")

    fake_conn.rollback.assert_called_once()
    fake_conn.commit.assert_not_called()
    fake_cursor.close.assert_called_once()
    fake_pool.putconn.assert_called_once_with(fake_conn)


def test_should_execute_vector_insertion_and_cosine_distance_query_contract(
    mocker: MockerFixture,
) -> None:
    # Arrange
    fake_pool = mocker.MagicMock(name="SimpleConnectionPool")
    fake_conn = mocker.MagicMock(name="PooledConnection")
    fake_cursor = mocker.MagicMock(name="PooledCursor")
    test_chunk_id = str(uuid.uuid4())
    fake_cursor.fetchone.return_value = (test_chunk_id, "Testowy chunk o BDOT500", 0.012)
    fake_conn.cursor.return_value = fake_cursor
    fake_pool.getconn.return_value = fake_conn
    mocker.patch("src.database.connection.SimpleConnectionPool", return_value=fake_pool)

    manager = DatabaseManager(minconn=POOL_MIN_CONN, maxconn=POOL_MAX_CONN)
    vec_1024 = [1.0] + [0.0] * (EMBEDDING_DIMENSION - 1)
    vec_str = "[" + ",".join(str(x) for x in vec_1024) + "]"

    # Act
    with manager.get_cursor(commit=True) as cur:
        cur.execute(
            """
            SELECT id, content, (embedding <=> %s::vector) AS distance
            FROM chunk_vectors
            WHERE id = %s
            ORDER BY distance ASC;
            """,
            (vec_str, test_chunk_id),
        )
        row = cur.fetchone()

    # Assert
    assert row is not None
    assert str(row[0]) == test_chunk_id
    assert row[1] == "Testowy chunk o BDOT500"
    assert row[2] < MAX_EXPECTED_COSINE_DISTANCE
    executed_sql, executed_params = fake_cursor.execute.call_args[0]
    assert "<=>" in executed_sql
    assert executed_params == (vec_str, test_chunk_id)
