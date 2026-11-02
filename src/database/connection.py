from contextlib import contextmanager
from typing import Generator
import psycopg2
from psycopg2.extensions import connection, cursor
from psycopg2.pool import SimpleConnectionPool
from src.config import settings


class DatabaseManager:
    """Manages PostgreSQL connection pooling and transactional cursors."""

    def __init__(self, minconn: int = 1, maxconn: int = 10) -> None:
        self._pool = SimpleConnectionPool(
            minconn=minconn,
            maxconn=maxconn,
            host=settings.POSTGRES_HOST,
            port=settings.POSTGRES_PORT,
            dbname=settings.POSTGRES_DB,
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD,
        )

    @contextmanager
    def get_connection(self) -> Generator[connection, None, None]:
        """Context manager to borrow a connection from the pool and return it."""
        conn = self._pool.getconn()
        try:
            yield conn
        finally:
            self._pool.putconn(conn)

    @contextmanager
    def get_cursor(self, commit: bool = False) -> Generator[cursor, None, None]:
        """Context manager providing a database cursor with optional auto-commit."""
        with self.get_connection() as conn:
            cur = conn.cursor()
            try:
                yield cur
                if commit:
                    conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                cur.close()

    def close_all(self) -> None:
        """Closes all connections in the pool."""
        self._pool.closeall()


db_manager = DatabaseManager()


def get_db_connection() -> connection:
    """Returns a standalone direct database connection."""
    return psycopg2.connect(
        host=settings.POSTGRES_HOST,
        port=settings.POSTGRES_PORT,
        dbname=settings.POSTGRES_DB,
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
    )
