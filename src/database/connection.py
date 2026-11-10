from contextlib import contextmanager
from typing import Generator, Optional
import psycopg2
from psycopg2.extensions import connection, cursor
from psycopg2.pool import SimpleConnectionPool
from src.config import settings


class DatabaseManager:
    """Manages PostgreSQL connection pooling and transactional cursors."""

    def __init__(self, minconn: int = 1, maxconn: int = 10) -> None:
        self.minconn = minconn
        self.maxconn = maxconn
        self._pool: Optional[SimpleConnectionPool] = None

    def _ensure_pool(self) -> SimpleConnectionPool:
        """Lazily initializes the connection pool when first required."""
        if self._pool is None:
            self._pool = SimpleConnectionPool(
                minconn=self.minconn,
                maxconn=self.maxconn,
                host=settings.POSTGRES_HOST,
                port=settings.POSTGRES_PORT,
                dbname=settings.POSTGRES_DB,
                user=settings.POSTGRES_USER,
                password=settings.POSTGRES_PASSWORD,
            )
        return self._pool

    @contextmanager
    def get_connection(self) -> Generator[connection, None, None]:
        """Context manager to borrow a connection from the pool and return it."""
        pool = self._ensure_pool()
        conn = pool.getconn()
        try:
            yield conn
        finally:
            pool.putconn(conn)

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
        if self._pool is not None:
            self._pool.closeall()
            self._pool = None


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
