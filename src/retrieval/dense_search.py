import logging
from typing import Any, Dict, List, Optional
from src.database.connection import db_manager
from src.indexing.embedder import BgeM3Embedder

logger = logging.getLogger(__name__)


class DenseRetriever:
    """Executes HNSW vector cosine distance search against PostgreSQL chunk_vectors table."""

    def __init__(self, embedder: Optional[BgeM3Embedder] = None) -> None:
        self.embedder = embedder or BgeM3Embedder()

    def _execute_query(
        self,
        vec_str: str,
        top_k: int,
        parent_id: Optional[str] = None,
        procurement_id: Optional[str] = None,
    ) -> List[Any]:
        sql = """
            SELECT cv.id, cv.parent_id, cv.chunk_index, cv.content, cv.metadata_payload,
                   (cv.embedding <=> %s::vector) AS distance
            FROM chunk_vectors cv
        """
        params: List[Any] = [vec_str]
        conditions: List[str] = []

        if procurement_id and procurement_id.lower() != "sample":
            sql += """
                JOIN parent_nodes pn ON cv.parent_id = pn.id
                JOIN attachments a ON pn.attachment_id = a.id
                JOIN procurements p ON a.procurement_id = p.id
            """
            conditions.append("(p.ocds_id = %s OR p.id::text = %s)")
            params.extend([procurement_id, procurement_id])

        if parent_id:
            conditions.append("cv.parent_id = %s")
            params.append(parent_id)

        if conditions:
            sql += " WHERE " + " AND ".join(conditions)

        sql += " ORDER BY distance ASC LIMIT %s;"
        params.append(top_k)

        with db_manager.get_cursor() as cur:
            cur.execute(sql, tuple(params))
            return cur.fetchall()

    def search(
        self,
        query: str,
        top_k: int = 50,
        parent_id: Optional[str] = None,
        procurement_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Encodes query to 1024-dim vector and finds top_k nearest neighbors by cosine distance."""
        query_vec = self.embedder.embed_query(query)
        vec_str = "[" + ",".join(str(x) for x in query_vec) + "]"

        rows = self._execute_query(vec_str, top_k=top_k, parent_id=parent_id, procurement_id=procurement_id)

        results: List[Dict[str, Any]] = []
        for r in rows:
            dist = float(r[5])
            results.append(
                {
                    "id": str(r[0]),
                    "parent_id": str(r[1]),
                    "chunk_index": r[2],
                    "content": r[3],
                    "metadata": r[4],
                    "distance": dist,
                    "score": max(0.0, 1.0 - dist),  # Cosine similarity
                    "retrieval_mode": "dense",
                }
            )

        return results
